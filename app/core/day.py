"""Dữ liệu điểm danh của một ngày và các kiểm tra trước khi ghi sổ."""

from __future__ import annotations

import copy
import datetime as dt
import re
from dataclasses import dataclass, field

from . import matcher
from .meals import MealLayout, MealSummary, compute_meals
from .models import Roster, Student
from .parser import ParsedMessage, extract_names
from .text import clean_spaces, fold, lower, title_words


@dataclass
class ClassDay:
    code: str
    manual: list[str] = field(default_factory=list)  # id HS vắng do nhập
    extra: list[str] = field(default_factory=list)  # tên chưa xác định, ghi nguyên văn
    auto_off: set[str] = field(default_factory=set)  # id vắng tự động đã bỏ tích
    reported: bool = False
    note: str = ""
    sheet_si_so: int | None = None  # sĩ số đang có trong sổ (sheet mẫu / sheet cũ)
    keep_sheet_si_so: bool = False
    teacher_present: int | None = None
    teacher_total: int | None = None


@dataclass
class DayState:
    date: dt.date
    roster: Roster
    classes: dict[str, ClassDay] = field(default_factory=dict)
    exists_in_book: bool = False  # sheet ngày này đã có trong sổ
    pending: list[tuple[str, matcher.MatchResult]] = field(default_factory=list)  # tên cần xử lý
    manual_m: dict[str, int] = field(default_factory=dict)  # số em ghép vắng nhập tay theo mã nhóm
    template_date: dt.date | None = None  # ngày của sheet mẫu (sổ hôm trước) khi tạo ngày mới

    # ---------- khởi tạo ----------
    @classmethod
    def new(cls, day: dt.date, roster: Roster, codes: list[str]) -> DayState:
        st = cls(day, roster)
        for c in codes:
            st.classes[c] = ClassDay(c)
        return st

    def cd(self, code: str) -> ClassDay:
        if code not in self.classes:
            self.classes[code] = ClassDay(code)
        return self.classes[code]

    def snapshot(self) -> DayState:
        """Bản sao để hoàn tác (không sao chép danh sách HS)."""
        roster, self.roster = self.roster, None  # type: ignore[assignment]
        try:
            snap = copy.deepcopy(self)
        finally:
            self.roster = roster
        snap.roster = roster
        return snap

    # ---------- truy vấn ----------
    def si_so(self, code: str) -> int:
        c = self.cd(code)
        if c.keep_sheet_si_so and c.sheet_si_so is not None:
            return c.sheet_si_so
        return self.roster.si_so(code, self.date)

    def auto_absent(self, code: str) -> dict[str, str]:
        """id -> lý do vắng tự động (cắt thứ 6)."""
        out = {}
        for s in self.roster.boarding(code, self.date):
            reason = s.auto_absent_reason(self.date)
            if reason:
                out[s.id] = reason
        return out

    def absent_students(self, code: str) -> list[Student]:
        c = self.cd(code)
        ids = set(c.manual) | (set(self.auto_absent(code)) - c.auto_off)
        boarding = self.roster.boarding(code, self.date)
        return self.roster.sort_like_roster([s for s in boarding if s.id in ids])

    def absent_names(self, code: str) -> list[str]:
        names = [self.roster.display_name(s) for s in self.absent_students(code)]
        return names + list(self.cd(code).extra)

    def absent_count(self, code: str) -> int:
        return len(self.absent_names(code))

    def present(self, code: str) -> int:
        return self.si_so(code) - self.absent_count(code)

    def is_absent(self, code: str, sid: str) -> bool:
        return any(s.id == sid for s in self.absent_students(code))

    # ---------- thay đổi ----------
    def set_absent(self, code: str, sid: str, absent: bool) -> None:
        c = self.cd(code)
        auto = self.auto_absent(code)
        if absent:
            if sid in auto:
                c.auto_off.discard(sid)
            elif sid not in c.manual:
                c.manual.append(sid)
        else:
            if sid in c.manual:
                c.manual.remove(sid)
            if sid in auto:
                c.auto_off.add(sid)
        c.reported = True

    def mark_full(self, code: str) -> None:
        c = self.cd(code)
        c.manual.clear()
        c.extra.clear()
        c.reported = True
        self.pending = [p for p in self.pending if p[0] != code]

    def apply_message(self, msg: ParsedMessage) -> list[matcher.MatchResult]:
        """Ghi tin nhắn của 1 lớp: danh sách vắng của lớp = các tên trong tin."""
        assert msg.cls
        code = msg.cls
        c = self.cd(code)
        results = [matcher.match_name(self.roster, code, q, self.date) for q in msg.names]
        c.manual = []
        c.extra = []
        self.pending = [p for p in self.pending if p[0] != code]
        for r in results:
            if r.status == matcher.OK and r.student and r.student.id not in c.manual:
                c.manual.append(r.student.id)
            elif r.status in (matcher.AMBIGUOUS, matcher.NOT_FOUND, matcher.OTHER_CLASS):
                self.pending.append((code, r))
        c.reported = True
        c.teacher_present, c.teacher_total = msg.present, msg.total
        return results

    def resolve_pending(self, code: str, result: matcher.MatchResult, student: Student | None, keep_raw: bool = False) -> None:
        """Giáo vụ chọn em đúng cho tên chưa rõ (hoặc giữ nguyên văn / bỏ qua)."""
        c = self.cd(code)
        self.pending = [p for p in self.pending if p[1] is not result]
        if result.query in c.extra:  # tên đọc từ sổ đang được ghi nguyên văn
            c.extra.remove(result.query)
        if student is not None:
            if student.id not in c.manual:
                c.manual.append(student.id)
        elif keep_raw:
            raw = title_words(result.query)
            if raw not in c.extra:
                c.extra.append(raw)

    # ---------- đọc lại từ sổ ----------
    def load_class_from_sheet(self, code: str, si_so, names_text: str, note: str) -> list[matcher.MatchResult]:
        """Đọc ô tên vắng đã có trong sổ (gõ tay hoặc app ghi) và kiểm tra từng tên."""
        c = self.cd(code)
        c.sheet_si_so = si_so if isinstance(si_so, int) else None
        c.note = note or ""
        c.manual, c.extra = [], []
        results = []
        auto = self.auto_absent(code)
        names, notes = split_sheet_cell(names_text)
        for n in notes:
            if fold(n) not in fold(c.note):
                c.note = f"{c.note}, {n}" if c.note else n
        for q in names:
            r = matcher.match_name(self.roster, code, q, self.date)
            results.append(r)
            if r.status == matcher.OK and r.student:
                if r.student.id not in c.manual and r.student.id not in auto:
                    c.manual.append(r.student.id)
            else:
                c.extra.append(q)
        # Em vắng tự động mà sổ không ghi thì coi như đã bỏ tích
        written = {r.student.id for r in results if r.student and r.status == matcher.OK}
        c.auto_off = {sid for sid in auto if sid not in written}
        c.reported = bool(names_text and names_text.strip())
        return results

    # ---------- suất ăn ----------
    def ghep_ready(self, layout: MealLayout, code: str) -> bool:
        """Lớp ghép đã gán nhóm ăn cho tất cả các em chưa (khi đó app tự tính)."""
        codes = layout.ghep_codes(int(code[0]))
        boarding = self.roster.boarding(code, self.date)
        return bool(boarding) and all(s.an_ghep in codes for s in boarding)

    def manual_codes(self, layout: MealLayout) -> set[str]:
        """Mã nhóm phải nhập tay số vắng ghép (lớp ghép chưa gán đủ danh sách)."""
        out: set[str] = set()
        for code in layout.ghep_classes:
            if not self.ghep_ready(layout, code):
                out.update(layout.ghep_codes(int(code[0])))
        return out

    def ghep_absent(self, layout: MealLayout) -> dict[str, list[str]]:
        """mã nhóm -> tên em ghép vắng (chỉ với lớp ghép đã gán đủ)."""
        out: dict[str, list[str]] = {}
        for code in layout.ghep_classes:
            if not self.ghep_ready(layout, code):
                continue
            for s in self.absent_students(code):
                out.setdefault(s.an_ghep, []).append(self.roster.display_name(s))
        return out

    def o_values(self, layout: MealLayout) -> dict[str, int]:
        """Số em ghép mỗi nhóm: theo danh sách ghép nếu đã gán đủ, không thì giữ số trong sổ."""
        out = dict(layout.o_values)
        for code in layout.ghep_classes:
            if self.ghep_ready(layout, code):
                boarding = self.roster.boarding(code, self.date)
                for gc in layout.ghep_codes(int(code[0])):
                    out[gc] = sum(1 for s in boarding if s.an_ghep == gc)
        return out

    def meals(self, layout: MealLayout) -> MealSummary:
        present = {c: self.present(c) for c in self.classes}
        manual = self.manual_codes(layout)
        m_values = {gc: self.manual_m.get(gc, 0) for gc in manual}
        o_vals = self.o_values(layout)
        summary = compute_meals(layout, present, self.ghep_absent(layout), o_vals, m_values)
        for code in layout.ghep_classes:
            codes = layout.ghep_codes(int(code[0]))
            if not codes:
                continue
            o_sum = sum(o_vals.get(gc, 0) for gc in codes)
            if o_sum != self.si_so(code):
                summary.warnings.append(
                    f"Lớp ghép {code}: tổng số em ghép ở các nhóm {', '.join(codes)} là {o_sum}, "
                    f"khác sĩ số {self.si_so(code)}"
                )
            if not self.ghep_ready(layout, code):
                n_abs = self.absent_count(code)
                m_sum = sum(m_values.get(gc, 0) for gc in codes)
                if n_abs != m_sum:
                    summary.warnings.append(
                        f"Lớp ghép {code} chưa có danh sách ghép đầy đủ: có {n_abs} em vắng "
                        f"({', '.join(self.absent_names(code))}) nhưng mới đánh {m_sum} vắng ghép. "
                        "Bấm đúp vào hàng nhóm để nhập, hoặc gán ghép ở tab Ghép lớp."
                        if n_abs else
                        f"Lớp ghép {code} không có em vắng nhưng đang đánh {m_sum} vắng ghép."
                    )
        if not summary.balanced and not summary.warnings:
            summary.warnings.append(
                f"Tổng suất ăn {summary.total_meals} khác tổng hiện diện {summary.total_present}"
            )
        return summary

    # ---------- kiểm tra ----------
    def class_warnings(self, code: str) -> list[str]:
        c = self.cd(code)
        out = []
        n = self.absent_count(code)
        if c.teacher_total is not None and c.teacher_total != self.si_so(code):
            out.append(f"GV báo sĩ số {c.teacher_total}, sổ tính {self.si_so(code)}")
        if c.teacher_present is not None and c.teacher_total is not None:
            if c.teacher_total - c.teacher_present != n:
                out.append(f"GV báo vắng {c.teacher_total - c.teacher_present} em, đang ghi {n} tên")
        if c.extra:
            out.append("Tên chưa xác định: " + ", ".join(c.extra))
        if self.si_so_mismatch(code):
            out.append(f"Sĩ số theo danh sách {self.roster.si_so(code, self.date)}, trong sổ đang ghi {c.sheet_si_so}")
        return out

    def si_so_mismatch(self, code: str) -> bool:
        """Danh sách và sổ lệch nhau thật (không tính phần thay đổi do lịch thêm/cắt đã đặt).

        So sĩ số theo danh sách tại ngày của sheet mẫu với sĩ số ghi trong sheet mẫu: nếu khớp thì
        mọi khác biệt hôm nay đều do lịch thêm/cắt có hiệu lực, app tự dùng sĩ số mới."""
        c = self.cd(code)
        if c.sheet_si_so is None or c.keep_sheet_si_so:
            return False
        return self.roster.si_so(code, self.template_date or self.date) != c.sheet_si_so

    def scheduled_changes(self, code: str | None = None):
        """Các em thêm/cắt có hiệu lực từ sau sheet mẫu tới hôm nay."""
        from .schedule import changes_between

        if self.exists_in_book or not self.template_date or self.template_date >= self.date:
            return []
        return changes_between(self.roster, self.template_date, self.date, code)

    def unreported(self) -> list[str]:
        return [c for c, v in self.classes.items() if not v.reported]

    def totals(self) -> tuple[int, int, int]:
        si = sum(self.si_so(c) for c in self.classes)
        ab = sum(self.absent_count(c) for c in self.classes)
        return si, ab, si - ab


NOTE_PREFIXES = ("cắt ", "thêm ", "chuyển ", "nghỉ học", "từ ngày")  # so đúng dấu: "Cát Tiên" là tên


def split_sheet_cell(text: str | None) -> tuple[list[str], list[str]]:
    """Tách ô tên vắng trong sổ thành (tên vắng, ghi chú lẫn vào như 'cắt …', 'thêm …')."""
    if not text or not str(text).strip():
        return [], []
    names, notes = [], []
    for chunk in re.split(r"[,;\n]", str(text)):
        chunk = clean_spaces(chunk)
        if not chunk:
            continue
        if lower(chunk).startswith(NOTE_PREFIXES):
            notes.append(chunk)
        else:
            names.extend(extract_names(chunk))
    return names, notes


def split_names(text: str | None) -> list[str]:
    """Tách ô tên vắng trong sổ: 'Tuấn Anh , Hồ Khánh Ngọc' -> 2 tên."""
    return split_sheet_cell(text)[0]
