"""Đọc ghi chú cột H trong sổ để gợi ý cập nhật danh sách học sinh.

Hiểu các ghi chú giáo vụ đang viết, ví dụ:
    Thứ 6 hàng tuần cắt 2 em Bảo Ngân, Minh Phúc     -> cắt thứ 6
    Lục Thảo Mi cắt thứ 6 hàng tuần             -> cắt thứ 6
    Vũ Khoa vắng tới khi có thông báo mới              -> vắng dài hạn
    T11 CẮT Hồ Khánh Ngọc                            -> cắt bán trú từ 01/11
    Từ 12/10 cắt bán trú Tô Minh Khôi          -> cắt bán trú từ 12/10
    Cắt bán trú 12/10 Tô Minh Khôi, 19/10 Bảo Ngân
    Cắt Kim Chi                                         -> cắt bán trú (từ ngày ghi chú xuất hiện)
    thêm Khôi Vĩ ghép 1.3                               -> thêm vào bán trú lớp này, ăn ghép 1.3
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from . import matcher
from .models import Roster, Student
from .parser import extract_names
from .text import clean_spaces, fmt_date

_B = r"(?<![\w/])"
_KEY = re.compile(
    rf"(?P<thu6>{_B}th[ứu]\s*(?:6|sáu)\s*(?:hàng|hang)\s*tu[ầa]n\s*c[ắa]t(?:\s*bán\s*trú)?(?:\s*\d+\s*em)?)"
    rf"|(?P<thu6_after>{_B}c[ắa]t\s*(?:bán\s*trú\s*)?th[ứu]\s*(?:6|sáu)(?:\s*hàng\s*tuần)?)"
    rf"|(?P<long>{_B}v[ắa]ng\s*(?:cho\s*)?(?:tới|đến|toi|den)\s*khi(?:\s*có\s*thông\s*báo\s*mới)?)"
    rf"|(?P<month_cut>{_B}t\s*(?P<m>\d{{1,2}})\s*c[ắa]t(?:\s*bán\s*trú)?(?!\w))"
    rf"|(?P<date_cut>{_B}(?:từ\s*)?(?P<d1>\d{{1,2}})\s*/\s*(?P<m1>\d{{1,2}})\s*c[ắa]t(?:\s*bán\s*trú)?(?!\w))"
    rf"|(?P<from_cut>{_B}từ\s*(?:ngày\s*)?(?P<d2>\d{{1,2}})\s*/\s*(?P<m2>\d{{1,2}}))"
    rf"|(?P<cut>{_B}c[ắa]t(?:\s*bán\s*trú)?(?!\w))"
    rf"|(?P<month_add>{_B}(?:tháng|t)\s*(?P<ma>\d{{1,2}})\s*thêm(?:\s*bán\s*trú)?(?!\w))"
    rf"|(?P<date_add>{_B}(?:từ\s*)?(?P<da>\d{{1,2}})\s*/\s*(?P<mda>\d{{1,2}})\s*thêm(?:\s*bán\s*trú)?(?!\w))"
    rf"|(?P<add>{_B}thêm(?:\s*bán\s*trú)?(?!\w))",
    re.IGNORECASE,
)
KINDS = ("thu6", "thu6_after", "long", "month_cut", "date_cut", "from_cut", "cut", "month_add", "date_add", "add")
AFTER = ("thu6_after", "long")  # tên đứng TRƯỚC từ khóa
_ITEM_DATE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s+")
_GHEP = re.compile(r"ghép\s*(\d)\s*[./]\s*(\d)", re.IGNORECASE)
_TAIL_NOISE = re.compile(r"(ghép\s*\d\s*[./]\s*\d|chú\s*ý.*|lưu\s*ý.*|\(.*?\))", re.IGNORECASE)


@dataclass
class Suggestion:
    code: str  # lớp có ghi chú
    text: str  # mô tả cho giáo vụ
    student: Student | None
    changes: dict  # trường -> giá trị mới
    new_name: str = ""  # HS chưa có trong danh sách
    apply: bool = True
    source: str = ""  # ghi chú gốc

    def key(self) -> tuple:
        sid = self.student.id if self.student else self.new_name.lower()
        return (self.code, sid)

    def merge(self, other: Suggestion) -> None:
        """Gộp gợi ý cùng một em (vd. 'thêm Khôi Vĩ' rồi 'thêm Khôi Vĩ ghép 1.3')."""
        added = {k: v for k, v in other.changes.items() if k not in self.changes}
        if not added:
            return
        self.changes.update(added)
        extra = []
        for k, v in added.items():
            if k == "an_ghep":
                extra.append(f"ăn ghép {v}")
            elif k == "bt_tu":
                extra.append(f"ăn từ {fmt_date(v)}")
            elif k == "lop_bt":
                extra.append(f"tính bán trú lớp {v}")
            elif k == "cat_thu6":
                extra.append("cắt thứ 6 hàng tuần")
            elif k == "vang_tu":
                extra.append(f"vắng dài hạn từ {fmt_date(v)}")
            elif k == "cat_tu":
                extra.append(f"cắt bán trú từ {fmt_date(v)}")
        if extra:
            self.text = f"{self.text}, {', '.join(extra)}"


def _date(day: int, month: int, ref: dt.date) -> dt.date | None:
    year = ref.year
    if month < ref.month - 6:
        year += 1
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def _clauses(note: str):
    """Trả về (loại, khớp, phần chữ chứa tên) cho từng ý trong ghi chú."""
    ms = list(_KEY.finditer(note))
    kinds = [next(k for k in KINDS if m.group(k)) for m in ms]
    owned: dict[int, int] = {}  # vị trí bắt đầu phần tên của ý kiểu "tên + từ khóa"
    for i, m in enumerate(ms):
        if kinds[i] in AFTER:
            prev_end = ms[i - 1].end() if i else 0
            seg = note[prev_end:m.start()]
            cut = max(seg.rfind(","), seg.rfind(";"))
            owned[i] = prev_end + cut + 1 if cut >= 0 else prev_end
    out = []
    for i, m in enumerate(ms):
        if kinds[i] in AFTER:
            arg = note[owned[i]:m.start()]
        else:
            end = len(note) if i + 1 == len(ms) else owned.get(i + 1, ms[i + 1].start())
            arg = note[m.end():end]
        out.append((kinds[i], m, arg))
    # "Từ 12/10 cắt bán trú X" viết tách: cụm 'từ ngày' ngay trước 'cắt' -> gộp
    merged = []
    for kind, m, arg in out:
        if merged and merged[-1][0] == "from_cut" and kind == "cut" and not merged[-1][2].strip():
            prev = merged.pop()
            merged.append(("date_from", prev[1], arg))
        else:
            merged.append((kind, m, arg))
    return merged


def _names(arg: str) -> list[tuple[str, tuple[int, int] | None]]:
    """Tách tên, mỗi tên có thể kèm ngày đứng trước: '12/10 Khả An, 19/10 Khánh Ngân'."""
    out = []
    for chunk in re.split(r"[,;]|\s+và\s+", arg):
        d = None
        m = _ITEM_DATE.match(chunk)
        if m:
            d = (int(m.group(1)), int(m.group(2)))
            chunk = chunk[m.end():]
        chunk = _TAIL_NOISE.sub(" ", chunk)
        for n in extract_names(chunk):
            if len(n) > 1:
                out.append((n, d))
    return out


def _find_student(roster: Roster, code: str, name: str, adding: bool) -> tuple[Student | None, list[Student]]:
    found = matcher._find(roster.in_class(code), name)  # noqa: SLF001
    if len(found) == 1:
        return found[0], found
    if found:
        bt = [s for s in found if s.ban_tru]
        return (bt[0], found) if len(bt) == 1 else (None, found)
    pool = roster.students
    if adding:  # em được thêm vào lớp: chỉ tìm ở các lớp cùng khối
        pool = [s for s in roster.students if s.lop[:1] == code[:1]]
    found = matcher._find(pool, name)  # noqa: SLF001
    return (found[0], found) if len(found) == 1 else (None, found)


def suggest_from_note(roster: Roster, code: str, note: str, seen: dt.date) -> list[Suggestion]:
    """seen: ngày của sheet có ghi chú (dùng làm ngày hiệu lực khi ghi chú không ghi ngày)."""
    note = clean_spaces(note)
    if not note:
        return []
    out: list[Suggestion] = []
    for kind, m, arg in _clauses(note):
        if kind in (None, "from_cut"):
            continue
        ghep = _GHEP.search(arg)
        for name, item_date in _names(arg):
            adding = kind in ("add", "month_add", "date_add")
            s, cands = _find_student(roster, code, name, adding)
            changes: dict = {}
            desc = ""
            if kind in ("thu6", "thu6_after"):
                changes, desc = {"cat_thu6": True}, "cắt thứ 6 hàng tuần"
            elif kind == "long":
                changes, desc = {"vang_tu": seen, "vang_den": None}, f"vắng dài hạn từ {fmt_date(seen)}"
            elif kind == "month_cut":
                d = _date(1, int(m.group("m")), seen)
                changes, desc = {"cat_tu": d}, f"cắt bán trú từ {fmt_date(d)}"
            elif kind in ("date_cut", "date_from"):
                d = _date(int(m.group("d1") or m.group("d2")), int(m.group("m1") or m.group("m2")), seen)
                changes, desc = {"cat_tu": d}, f"cắt bán trú từ {fmt_date(d)}"
            elif kind == "cut":
                d = _date(*item_date, seen) if item_date else seen
                changes, desc = {"cat_tu": d}, f"cắt bán trú từ {fmt_date(d)}"
            elif kind in ("add", "month_add", "date_add"):
                changes = {"ban_tru": True}
                desc = "thêm vào bán trú"
                start = None
                if kind == "month_add":
                    start = _date(1, int(m.group("ma")), seen)
                elif kind == "date_add":
                    start = _date(int(m.group("da")), int(m.group("mda")), seen)
                if start:
                    changes["bt_tu"] = start
                    desc += f" từ {fmt_date(start)}"
                if s is not None and s.lop != code and s.lop_tinh != code:
                    changes["lop_bt"] = code
                    desc += f" (học lớp {s.lop}, tính bán trú lớp {code})"
                if ghep:
                    changes["an_ghep"] = f"{ghep.group(1)}.{ghep.group(2)}"
                    desc += f", ăn ghép {changes['an_ghep']}"
            if s is None and adding and not cands:
                out.append(Suggestion(code, f"{code}: {name} — HS chưa có trong danh sách, thêm mới và {desc}",
                                      None, changes, new_name=name, source=note))
                continue
            if s is None:
                if cands:
                    who = ", ".join(f"{c.ho_ten} ({c.lop})" for c in cands[:4])
                    out.append(Suggestion(code, f"{code}: '{name}' trùng nhiều em ({who}) — hãy sửa tay ở danh sách",
                                          None, {}, apply=False, source=note))
                continue
            todo = {k: v for k, v in changes.items() if getattr(s, k) != v}
            if kind == "long" and s.vang_tu:
                todo = {}
            if kind in ("cut", "month_cut", "date_cut", "date_from") and (not s.ban_tru or s.cat_tu):
                todo = {}
            if not todo:
                continue
            out.append(Suggestion(code, f"{code}: {s.ho_ten} — {desc}", s, todo, source=note))
    return out


def suggest_from_book(roster: Roster, notes: list[tuple[dt.date, str, str]]) -> list[Suggestion]:
    """notes: (ngày sheet, lớp, ghi chú) theo thứ tự ngày tăng dần. Gộp trùng, giữ lần xuất hiện đầu."""
    by_key: dict[tuple, Suggestion] = {}
    out = []
    for day, code, note in sorted(notes, key=lambda x: x[0]):
        for sug in suggest_from_note(roster, code, note, day):
            k = sug.key()
            if k in by_key:
                by_key[k].merge(sug)
                continue
            by_key[k] = sug
            out.append(sug)
    return out


def apply_suggestions(roster: Roster, sugs: list[Suggestion]) -> int:
    n = 0
    for sug in sugs:
        if not sug.apply or not sug.changes:
            continue
        s = sug.student
        if s is None and sug.new_name:
            s = Student(roster.next_id(), sug.code, sug.new_name, "", ban_tru=True, ghi_chu="thêm từ ghi chú sổ")
            roster.students.append(s)
        if s is None:
            continue
        for k, v in sug.changes.items():
            setattr(s, k, v)
        n += 1
    roster.invalidate()
    return n
