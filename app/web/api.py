"""Cầu nối giữa giao diện web (HTML/Bootstrap) và phần xử lý sổ (Workspace).

Mọi hàm trả về dict/list đơn giản (JSON). Giao diện gọi qua `window.pywebview.api.<tên hàm>(...)`
(app thật) hoặc POST /api/<tên hàm> (máy chủ thử, dùng để test và chụp ảnh).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .. import __version__
from ..core import matcher
from ..core import schedule as sch
from ..core.models import Student
from ..core.search import matches
from ..core.text import class_sort_key, clean_spaces, fmt_date, norm_class, parse_date
from ..excel import printing
from ..excel.files import FileLockedError
from ..excel.roster_import import RosterFormatError, flag_mismatches
from ..service import NeedMonthBook, Workspace, next_school_day, search_students

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
PROBLEM = (matcher.AMBIGUOUS, matcher.OTHER_CLASS, matcher.NOT_FOUND)


class NoDialogs:
    """Hộp chọn file (app thật dùng hộp của Windows qua pywebview; máy chủ thử thì không có)."""

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        return None

    def save_file(self, title: str, name: str) -> str | None:
        return None


def _iso(d: dt.date | None) -> str:
    return d.isoformat() if d else ""


def _day(text: str | None) -> dt.date | None:
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return parse_date(text)


class Api:
    def __init__(self, ws: Workspace, dialogs=None):
        self._ws = ws
        self._dlg = dialogs or NoDialogs()
        self._pending_import = None  # (changes, path) chờ giáo vụ duyệt
        self._pending_notes = None
        self._temp = None  # sổ tạm tìm thấy lúc mở app (chờ hỏi khôi phục)

    # ================================================================== ngày
    def boot(self) -> dict:
        """Mở app: mở ngày học hôm nay (thứ 7/CN thì ngày học kế tiếp). Không hỏi chọn file."""
        today = dt.date.today()
        res = self.open_day(_iso(today if today.weekday() < 5 else next_school_day(today)), True)
        self._temp = self._ws.find_temp()
        if self._temp is not None:
            res["restore"] = {"day": fmt_date(self._temp.day), "at": self._temp.saved_at, "file": self._temp.path.name}
        return res

    def restore_temp(self, yes: bool) -> dict:
        """Lần trước app tắt khi chưa lưu vào sổ: khôi phục từ sổ tạm, hoặc bỏ sổ tạm."""
        info, self._temp = self._temp, None
        if info is None:
            return {"state": self.state()}
        if not yes:
            self._ws.discard_temp(info.path)
            return {"state": self.state(), "flash": "Đã bỏ bản lưu tạm."}
        try:
            self._ws.restore_temp(info)
        except NeedMonthBook:
            return {"error": f"Không tìm thấy sổ {info.book.name} để khôi phục. Bản lưu tạm vẫn giữ ở:\n{info.path}",
                    "state": self.state()}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không khôi phục được:\n{e}\n\nBản lưu tạm vẫn giữ ở:\n{info.path}", "state": self.state()}
        return {"state": self.state(), "flash": f"Đã khôi phục ngày {fmt_date(info.day)} — nhớ bấm Lưu vào sổ."}

    def discard_temp(self) -> dict:
        """Thoát app và chọn Không lưu: bỏ sổ tạm."""
        self._ws.discard_temp()
        return {"ok": ""}

    def open_day(self, iso: str, force: bool = False) -> dict:
        day = _day(iso)
        if day is None:
            return {"error": "Ngày không đúng. Hãy nhập ngày dạng dd/mm/yyyy."}
        if self._ws.state is not None and self._ws.dirty and not force:
            return {"ask_save": {"day": fmt_date(self._ws.day), "target": _iso(day)}}
        try:
            self._ws.load_day(day)
        except NeedMonthBook as e:
            if e.prev is not None:
                return {"need_month": {"month": e.month, "year": e.year, "folder": str(e.prev.parent),
                                       "prev": e.prev.name, "target": _iso(day)}, "state": self.state()}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không mở được sổ điểm danh:\n{e}", "state": self.state()}
        return {"state": self.state()}

    def step_day(self, step: int, force: bool = False) -> dict:
        return self.open_day(_iso(next_school_day(self._ws.day, int(step))), force)

    def create_month_book(self, iso: str) -> dict:
        day = _day(iso)
        try:
            new = self._ws.create_month_book(day)
            msg = f"Đã tạo sổ mới: {new.name}"
        except FileExistsError as ex:
            self._ws.set_book(ex.args[0])
            msg = f"Dùng sổ có sẵn: {Path(ex.args[0]).name}"
        except Exception as ex:  # noqa: BLE001
            return {"error": f"Không tạo được sổ mới:\n{ex}"}
        res = self.open_day(iso, True)
        res["flash"] = msg
        return res

    # ================================================================== màn chính
    def setup_hint(self) -> str:
        steps = []
        if not self._ws.roster.students:
            steps.append("nhập danh sách học sinh")
        if not self._ws.book_path:
            steps.append("chọn sổ điểm danh tháng này")
        return ("Vào Cài đặt để " + " và ".join(steps) + ".") if steps else ""

    def _status(self, code: str) -> str:
        st = self._ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        if c.extra or any(p[0] == code for p in st.pending) or st.class_warnings(code):
            return "err"
        if not c.reported and not n:
            return "muted"
        return "warn" if n else "ok"

    def state(self) -> dict:
        ws, st = self._ws, self._ws.state
        ws.autosave_request()  # có thay đổi mới thì ghi sổ tạm (chạy nền)
        bp = ws.book_path
        out = {
            "date": _iso(ws.day), "date_text": fmt_date(ws.day), "weekday": WEEKDAYS[ws.day.weekday()],
            "book": bp.name if bp else "", "book_stem": bp.stem if bp else "",
            "exists": bool(st and st.exists_in_book), "sheet": ws.sheet_name or str(ws.day.day),
            "dirty": ws.dirty, "data_dirty": ws.data_dirty, "temp_at": ws.temp_saved_at, "temp_error": ws.temp_error, "hint": self.setup_hint(),
            "rows": [], "totals": None, "meal": None, "todo": [], "info": [], "unresolved": 0,
        }
        if st is None:
            return out
        by_khoi: dict[int, list[str]] = {}
        for code in st.classes:
            by_khoi.setdefault(int(code[0]) if code[:1].isdigit() else 9, []).append(code)
        rows = []
        for k, codes in sorted(by_khoi.items()):
            for code in codes:
                c = st.cd(code)
                info = ws.roster.classes.get(code)
                n = st.absent_count(code)
                names = ", ".join(st.absent_names(code))
                note = c.note
                warns = st.class_warnings(code)
                rows.append({
                    "kind": "class", "code": code, "ma": info.ma_ngan if info else "",
                    "gvcn": info.gvcn if info else "", "si": st.si_so(code), "vang": n, "hd": st.present(code),
                    "ten": names if (c.reported or n) else "", "reported": c.reported or bool(n),
                    "note": note, "warn": warns[0] if warns else "", "sched": bool(st.scheduled_changes(code)),
                    "status": self._status(code),
                })
            si = sum(st.si_so(c) for c in codes)
            ab = sum(st.absent_count(c) for c in codes)
            rows.append({"kind": "khoi", "code": f"KHỐI {k}", "si": si, "vang": ab, "hd": si - ab})
        si, ab, pr = st.totals()
        out["rows"] = rows
        out["totals"] = {"si": si, "vang": ab, "hd": pr, "rep": sum(1 for c in st.classes.values() if c.reported),
                         "n": len(st.classes)}
        if not ws.layout.is_empty:
            m = ws.meals()
            out["meal"] = {"total": m.total_meals, "present": m.total_present, "ok": m.balanced}
        n_pending = len(st.pending)
        out["unresolved"] = ws.unresolved_count()
        if n_pending:
            first = next((code for code in st.classes if any(p[0] == code for p in st.pending)), None)
            out["todo"].append({"text": f"{n_pending} tên chưa rõ trong sổ — bấm để xử lý", "code": first, "level": "err"})
        checks = ws.sheet_checks
        if checks and not n_pending:
            n = sum(len(v) for v in checks.values())
            out["info"].append(f"Sổ ngày {fmt_date(st.date)}: {n} tên vắng đã có, đều khớp danh sách")
        changes = st.scheduled_changes()
        if changes:
            out["info"].append(f"{len(changes)} em thêm/cắt bán trú từ hôm nay — sĩ số đã tự đổi")
        return out

    # ================================================================== một lớp
    def class_detail(self, code: str) -> dict:
        ws, st = self._ws, self._ws.state
        if st is None or code not in st.classes:
            return {"error": "Không có lớp này."}
        roster = ws.roster
        c = st.cd(code)
        auto = st.auto_absent(code)
        names = []
        for s in roster.sort_like_roster(roster.boarding(code, st.date)):
            tags = []
            if s.id in auto:
                tags.append(auto[s.id])
            elif s.cat_thu6:
                tags.append("nghỉ T6")
            if s.cat_tu and s.cat_tu > st.date:
                tags.append(f"cắt từ {s.cat_tu:%d/%m}")
            if s.an_ghep:
                tags.append(f"ăn {s.an_ghep}")
            names.append({"id": s.id, "name": roster.display_name(s), "full": s.ho_ten, "dob": s.ngay_sinh,
                          "alias": s.ten_ghi_so, "absent": st.is_absent(code, s.id), "tags": tags,
                          "friday": s.cat_thu6})
        pending = []
        for i, (p_code, res) in enumerate(st.pending):
            if p_code != code:
                continue
            board = {s.id for s in roster.boarding(code, st.date)}
            cands = [{"id": cd.id, "name": roster.display_name(cd), "full": cd.ho_ten, "dob": cd.ngay_sinh}
                     for cd in res.candidates if cd.id in board]
            other = [f"{cd.ho_ten} lớp {cd.lop}{' (ăn BT)' if cd.ban_tru else ''}" for cd in res.candidates
                     if cd.id not in board] if res.status == matcher.OTHER_CLASS else []
            pending.append({"idx": i, "query": res.query, "cands": cands, "other": other})
        info = roster.classes.get(code)
        upcoming = [f"{'cắt' if s.cat_tu and s.cat_tu > st.date else 'thêm'} {s.ho_ten} từ "
                    f"{(s.cat_tu if s.cat_tu and s.cat_tu > st.date else s.bt_tu):%d/%m}"
                    for s in roster.in_class(code)
                    if (s.cat_tu and s.cat_tu > st.date) or (s.ban_tru and s.bt_tu and s.bt_tu > st.date)]
        return {
            "code": code, "ma": info.ma_ngan if info else "", "gvcn": info.gvcn if info else "",
            "si": st.si_so(code), "vang": st.absent_count(code), "hd": st.present(code),
            "reported": c.reported, "note": c.note, "warnings": st.class_warnings(code), "extra": list(c.extra),
            "names": names, "pending": pending, "upcoming": upcoming,
        }

    def _after(self, code: str | None = None) -> dict:
        out = {"state": self.state()}
        if code:
            out["detail"] = self.class_detail(code)
        return out

    def set_absent(self, code: str, sid: str, absent: bool) -> dict:
        st = self._ws.state
        if st.is_absent(code, sid) != bool(absent):
            self._ws.push_undo()
            st.set_absent(code, sid, bool(absent))
        return self._after(code)

    def mark_full(self, code: str) -> dict:
        self._ws.push_undo()
        self._ws.state.mark_full(code)
        return self._after(code)

    def set_note(self, code: str, text: str) -> dict:
        c = self._ws.state.cd(code)
        val = clean_spaces(text)
        if val != c.note:
            self._ws.push_undo()
            c.note = val
        return self._after(code)

    def clear_extra(self, code: str) -> dict:
        self._ws.push_undo()
        self._ws.state.cd(code).extra.clear()
        return self._after(code)

    def resolve(self, code: str, idx: int, action: str, sid: str | None = None) -> dict:
        """Tên chưa rõ trong sổ: chọn em đúng (pick), giữ nguyên chữ đã ghi (raw) hoặc bỏ qua (skip)."""
        st = self._ws.state
        if not (0 <= idx < len(st.pending)) or st.pending[idx][0] != code:
            return self._after(code)
        res = st.pending[idx][1]
        self._ws.push_undo()
        if action == "pick" and sid:
            st.resolve_pending(code, res, self._ws.roster.by_id(sid))
        elif action == "raw":
            st.resolve_pending(code, res, None, keep_raw=True)
        else:
            st.resolve_pending(code, res, None)
        st.cd(code).reported = True
        return self._after(code)

    def undo(self) -> dict:
        ok = self._ws.undo()
        return {"state": self.state(), "flash": "Đã hoàn tác." if ok else "Không còn gì để hoàn tác."}

    # ================================================================== lưu / in
    def save(self, choice: str | None = None) -> dict:
        """Lưu vào sổ. Có thể trả về: blocked (còn tên chưa rõ), conflicts (hỏi sĩ số), locked, error, ok."""
        ws, st = self._ws, self._ws.state
        if st is None:
            return {"error": "Chưa mở ngày nào."}
        if not ws.book_path:
            return {"error": "Chưa có sổ điểm danh cho tháng này. Vào Cài đặt → Chọn sổ."}
        n = ws.unresolved_count()
        if n:
            lines = [f"Lớp {code}: {', '.join(names)}" for code, names in ws.pending_names().items()]
            first = next(iter(ws.pending_names()), None)
            return {"blocked": {"n": n, "lines": lines, "code": first}}
        conflicts = ws.si_so_conflicts()
        if conflicts and choice is None:
            return {"conflicts": [f"{c}: theo danh sách {ds} em, trong sổ đang ghi {so} em" for c, ds, so in conflicts]}
        if conflicts and choice == "keep":
            ws.keep_sheet_si_so([c for c, _, _ in conflicts])
        try:
            sheet = ws.save()
        except FileLockedError as e:
            return {"locked": f"File đang mở trong Excel nên chưa ghi được:\n{e}\n\nHãy đóng file đó trong Excel rồi bấm Thử lại."}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không lưu được:\n{e}"}
        msg = ws.warning or f"Đã lưu vào sổ {ws.book_path.name}, sheet {sheet}. Bản cũ đã sao lưu trong thư mục SaoLuu."
        return {"ok": msg, "state": self.state()}

    def print_check(self) -> dict:
        """Trước khi in: còn tên chưa rõ thì chặn; còn lớp chưa báo / chưa lưu thì hỏi."""
        ws, st = self._ws, self._ws.state
        if st is None or not ws.book_path:
            return {"error": "Chưa có sổ điểm danh cho tháng này. Vào Cài đặt → Chọn sổ."}
        need_save = ws.dirty or not st.exists_in_book
        if need_save and ws.unresolved_count():
            return self.save()
        return {"need_save": need_save, "unreported": st.unreported()}

    def print_day(self) -> dict:
        areas = self._ws.print_areas()
        try:
            printing.print_areas(self._ws.book_path, self._ws.sheet_name, areas)
        except printing.PrintError as e:
            return {"print_error": f"{e}\n\nCó thể mở sổ bằng Excel để in tay (vùng in: {' và '.join(areas)})."}
        return {"ok": "Đã gửi lệnh in 2 tờ."}

    def open_book(self) -> dict:
        if self._ws.book_path:
            printing.open_file(self._ws.book_path)
            return {"ok": ""}
        return {"error": "Chưa chọn sổ. Vào Cài đặt → Chọn sổ."}

    # ================================================================== suất ăn
    def meals(self) -> dict:
        ws, st = self._ws, self._ws.state
        layout = ws.layout
        if st is None or layout.is_empty:
            return {"empty": True}
        summary = ws.meals()
        manual = st.manual_codes(layout)
        lines = []
        for line in summary.lines:
            r = line.row
            gom = " + ".join(r.classes)
            if r.code:
                gom += f" + ghép {line.o} em"
                if line.m:
                    gom += f" − vắng {line.m}"
            lines.append({"label": r.label, "gom": gom, "meals": line.meals, "m": line.m or 0,
                          "absent": line.absent_names, "code": r.code or "",
                          "manual": bool(r.code and r.code in manual), "manual_m": st.manual_m.get(r.code, 0) if r.code else 0})
        self_line = None
        if layout.self_classes:
            self_line = {"label": "Tự ăn tại lớp", "gom": ", ".join(layout.self_classes), "meals": summary.self_meals}
        return {"lines": lines, "self": self_line, "total": summary.total_meals, "present": summary.total_present,
                "ok": summary.balanced, "warnings": summary.warnings}

    def set_manual_m(self, code: str, value: int) -> dict:
        self._ws.push_undo()
        self._ws.state.manual_m[code] = max(0, int(value))
        return {"meals": self.meals(), "state": self.state()}

    # ================================================================== học sinh
    def students(self, q: str = "", cls: str = "", only_bt: bool = True) -> dict:
        roster, day = self._ws.roster, self._ws.day
        items = search_students(roster, "", cls or None, only_bt)
        items = [s for s in items if matches(q, s.ho_ten + " " + roster.display_name(s))]
        items.sort(key=lambda s: class_sort_key(s.lop_tinh))
        rows = []
        for s in items:
            special = []
            if s.lop_bt and s.lop_bt != s.lop:
                special.append(f"tính BT lớp {s.lop_bt}")
            if s.cat_thu6:
                special.append("cắt thứ 6")
            if s.bt_tu:
                special.append(f"ăn từ {fmt_date(s.bt_tu)}")
            if s.cat_tu:
                special.append(f"cắt từ {fmt_date(s.cat_tu)}")
            rows.append({"id": s.id, "lop": s.lop, "ten": s.ho_ten, "ns": s.ngay_sinh, "bt": s.ban_tru,
                         "ghiso": roster.display_name(s) if s.ban_tru else "", "ghep": s.an_ghep,
                         "db": "; ".join(special), "gc": s.ghi_chu, "now": s.is_boarding(day)})
        return {"rows": rows, "classes": roster.class_codes(), "data_dirty": self._ws.data_dirty}

    def student(self, sid: str) -> dict:
        s = self._ws.roster.by_id(sid)
        if s is None:
            return {"error": "Không tìm thấy học sinh."}
        return {"id": s.id, "lop": s.lop, "ho_ten": s.ho_ten, "ngay_sinh": s.ngay_sinh, "ban_tru": s.ban_tru,
                "ten_ghi_so": s.ten_ghi_so, "lop_bt": s.lop_bt, "an_ghep": s.an_ghep, "cat_thu6": s.cat_thu6,
                "bt_tu": fmt_date(s.bt_tu) if s.bt_tu else "", "cat_tu": fmt_date(s.cat_tu) if s.cat_tu else "",
                "ghi_chu": s.ghi_chu}

    def save_student(self, data: dict) -> dict:
        lop = norm_class(data.get("lop", ""))
        name = clean_spaces(data.get("ho_ten", ""))
        if not lop or not name:
            return {"error": "Cần nhập lớp (vd. 1D15) và họ tên."}
        dates = {}
        for f in ("bt_tu", "cat_tu"):
            raw = clean_spaces(data.get(f, ""))
            d = parse_date(raw)
            if raw and not d:
                return {"error": f"Ngày '{raw}' không đúng dạng dd/mm/yyyy."}
            dates[f] = d
        roster = self._ws.roster
        s = roster.by_id(data.get("id") or "")
        if s is None:
            s = Student(roster.next_id(), lop, name)
            roster.students.append(s)
        lop_bt = norm_class(data.get("lop_bt", "")) if clean_spaces(data.get("lop_bt", "")) else ""
        s.lop, s.ho_ten = lop, name
        s.ngay_sinh = fmt_date(parse_date(data.get("ngay_sinh", ""))) or clean_spaces(data.get("ngay_sinh", ""))
        s.ban_tru, s.cat_thu6 = bool(data.get("ban_tru")), bool(data.get("cat_thu6"))
        if "ten_ghi_so" in data:
            s.ten_ghi_so = clean_spaces(data["ten_ghi_so"])
        s.lop_bt = "" if lop_bt == lop else lop_bt
        s.an_ghep = clean_spaces(data.get("an_ghep", "")).replace(",", ".")
        s.ghi_chu = clean_spaces(data.get("ghi_chu", ""))
        for f, d in dates.items():
            setattr(s, f, d)
        return self._roster_changed()

    def delete_student(self, sid: str) -> dict:
        s = self._ws.roster.by_id(sid)
        if s is not None:
            self._ws.roster.students.remove(s)
        return self._roster_changed()

    def _roster_changed(self) -> dict:
        self._ws.roster.invalidate()
        self._ws.data_dirty = True
        return {"ok": True, "state": self.state()}

    def save_data(self) -> dict:
        try:
            self._ws.save_data()
        except FileLockedError:
            return {"error": f"File dữ liệu đang mở trong Excel:\n{self._ws.data.path}\nHãy đóng Excel rồi lưu lại."}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không lưu được:\n{e}"}
        return {"ok": "Đã lưu danh sách học sinh.", "state": self.state()}

    # ================================================================== lịch thêm / cắt
    def schedules(self) -> dict:
        today = self._ws.day
        groups = {"soon": [], "weekly": [], "done": []}
        for it in self._ws.schedule_items():
            key = "weekly" if it.kind == sch.FRIDAY else ("soon" if it.start and it.start > today else "done")
            groups[key].append(it)
        out = {}
        for key, lst in groups.items():
            lst.sort(key=lambda i: (i.start or dt.date.min, class_sort_key(i.student.lop_tinh)))
            out[key] = [{"key": f"{it.kind}|{it.student.id}", "ngay": fmt_date(it.start) if it.start else
                         ("mỗi thứ 6" if it.kind == sch.FRIDAY else ""), "lop": it.student.lop_tinh,
                         "hs": it.student.ho_ten, "viec": it.text} for it in lst]
        return out

    def schedule_options(self, kind: str, code: str, q: str = "") -> dict:
        roster, day = self._ws.roster, self._ws.day
        if kind == sch.ADD:
            pool = [s for s in roster.in_class(code) if not s.is_boarding(day) and not (s.bt_tu and s.bt_tu > day)]
        else:
            pool = roster.boarding(code, day)
            if kind == sch.FRIDAY:
                pool = [s for s in pool if not s.cat_thu6]
            if kind == sch.CUT:
                pool = [s for s in pool if not s.cat_tu]
        pool = [s for s in roster.sort_like_roster(pool) if matches(q, s.ho_ten)]
        nxt, month = next_school_day(day), sch.next_month_start(day)
        return {"students": [{"id": s.id, "ten": s.ho_ten, "ns": s.ngay_sinh, "bt": s.ban_tru} for s in pool],
                "classes": roster.class_codes(), "today": fmt_date(day), "next": fmt_date(nxt),
                "month": fmt_date(month)}

    def add_schedule(self, kind: str, code: str, ids: list, start: str = "", new_name: str = "",
                     new_dob: str = "", note: bool = True) -> dict:
        new_name = clean_spaces(new_name)
        if not ids and not new_name:
            return {"error": "Chọn ít nhất một học sinh."}
        d = None
        if kind != sch.FRIDAY:
            d = parse_date(start)
            if not d:
                return {"error": "Ngày áp dụng phải có dạng dd/mm/yyyy."}
        dob = parse_date(new_dob)
        try:
            text = self._ws.schedule(kind, code, list(ids), d, None, new_name, fmt_date(dob) if dob else "", bool(note))
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không lưu được lịch:\n{e}"}
        msg = f"Đã đặt lịch: {sch.LABEL[kind].lower()}" + (f" từ {fmt_date(d)}" if d else "")
        if text:
            msg += f". Đã ghi chú cột H lớp {code}: \"{text}\" — nhớ bấm Lưu vào sổ."
        self._ws.roster.invalidate()
        return {"ok": msg, "state": self.state()}

    def cancel_schedules(self, keys: list) -> dict:
        items = {f"{it.kind}|{it.student.id}": it for it in self._ws.schedule_items()}
        n = 0
        try:
            for k in keys:
                if k in items:
                    self._ws.cancel_schedule(items[k])
                    n += 1
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không lưu được:\n{e}"}
        self._ws.roster.invalidate()
        return {"ok": f"Đã hủy {n} lịch. Nếu đã ghi chú ở cột H, hãy xóa ghi chú đó trong ô Ghi chú của lớp.",
                "state": self.state()}

    def undo_friday(self, sid: str) -> dict:
        s = self._ws.roster.by_id(sid)
        if s is not None:
            return self.cancel_schedules([f"{sch.FRIDAY}|{s.id}"])
        return {"state": self.state()}

    # ================================================================== ghép lớp
    def ghep(self) -> dict:
        ws = self._ws
        layout = ws.layout
        if ws.state is None or layout.is_empty or not layout.ghep_classes:
            return {"classes": []}
        o_now = ws.state.o_values(layout)
        out = []
        for code in layout.ghep_classes:
            groups = layout.ghep_codes(int(code[0]))
            students = ws.ghep_students(code)
            info = ws.roster.classes.get(code)
            out.append({
                "code": code, "ma": info.ma_ngan if info else "", "groups": [
                    {"g": g, "n": sum(1 for s in students if s.an_ghep == g), "book": layout.o_values.get(g)}
                    for g in groups],
                "students": [{"id": s.id, "name": ws.roster.display_name(s), "full": s.ho_ten, "dob": s.ngay_sinh,
                              "g": s.an_ghep, "ok": s.an_ghep in groups} for s in students],
                "total": sum(o_now.get(g, 0) for g in groups), "n": len(students)})
        return {"classes": out, "data_dirty": ws.data_dirty}

    def assign_ghep(self, ids: list, group: str) -> dict:
        self._ws.assign_ghep(list(ids), group)
        self._ws.roster.invalidate()
        return {"ghep": self.ghep(), "state": self.state()}

    def assign_ghep_text(self, code: str, text: str) -> dict:
        n, problems = self._ws.assign_ghep_text(code, text)
        self._ws.roster.invalidate()
        return {"ghep": self.ghep(), "state": self.state(), "n": n, "problems": problems[:20]}

    # ================================================================== cài đặt
    def settings(self) -> dict:
        st = self._ws.settings
        return {"data": str(self._ws.data.path), "so_file": st.get("so_file", ""), "cdhs_file": st.get("cdhs_file", ""),
                "version": __version__}

    def choose_book(self, path: str | None = None) -> dict:
        path = path or self._dlg.open_file("Chọn sổ điểm danh tháng (.xlsx)", ("Excel (*.xlsx)",))
        if not path:
            return {"cancel": True}
        self._ws.set_book(path)
        res = self.open_day(_iso(self._ws.day), True)
        res["flash"] = f"Đã chọn sổ {Path(path).name}."
        return res

    def import_list(self, path: str | None = None) -> dict:
        """Đọc file danh sách học sinh; trả về các thay đổi để giáo vụ duyệt (apply_import)."""
        path = path or self._dlg.open_file("Chọn file danh sách học sinh (Excel)", ("Excel (*.xlsx;*.xls)",))
        if not path:
            return {"cancel": True}
        try:
            changes, rows = self._ws.import_cdhs(path)
        except RosterFormatError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không đọc được file:\n{e}"}
        self._pending_import = (changes, path)
        mism = flag_mismatches(rows)
        return {"file": Path(path).name, "n": len(rows), "n_bt": sum(1 for r in rows if r.red),
                "first": not self._ws.roster.students,
                "changes": [{"i": i, "text": c.text, "apply": c.apply, "removed": c.kind == "removed"}
                            for i, c in enumerate(changes)],
                "mismatch": [f"{r.ho_ten} ({r.lop})" for r in mism[:8]]}

    def apply_import(self, selected: list) -> dict:
        if not self._pending_import:
            return {"error": "Chưa chọn file."}
        changes, path = self._pending_import
        keep = {int(i) for i in selected}
        for i, c in enumerate(changes):
            c.apply = i in keep
        try:
            n = self._ws.apply_import(changes, path)
        except Exception as e:  # noqa: BLE001
            self._ws.data_dirty = True
            return {"error": f"Đã nhập nhưng chưa ghi được file dữ liệu:\n{e}"}
        self._pending_import = None
        self._ws.roster.invalidate()
        res = self.open_day(_iso(self._ws.day), True) if not self._ws.dirty else {"state": self.state()}
        res["flash"] = f"Đã áp dụng {n} thay đổi từ {Path(path).name}."
        return res

    def note_suggestions(self) -> dict:
        try:
            sugs = self._ws.note_suggestions()
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không đọc được sổ:\n{e}"}
        self._pending_notes = sugs
        return {"items": [{"i": i, "text": g.text, "apply": g.apply} for i, g in enumerate(sugs)]}

    def apply_notes(self, selected: list) -> dict:
        sugs = self._pending_notes or []
        keep = {int(i) for i in selected}
        for i, g in enumerate(sugs):
            g.apply = i in keep
        try:
            n = self._ws.apply_note_suggestions(sugs)
        except Exception as e:  # noqa: BLE001
            self._ws.data_dirty = True
            return {"error": f"Đã cập nhật nhưng chưa ghi được file dữ liệu:\n{e}"}
        self._pending_notes = None
        self._ws.roster.invalidate()
        res = self.open_day(_iso(self._ws.day), True) if not self._ws.dirty else {"state": self.state()}
        res["flash"] = f"Đã cập nhật {n} học sinh theo ghi chú trong sổ."
        return res

    def export_list(self, day_text: str, path: str | None = None) -> dict:
        from ..excel.roster_export import export_roster

        day = parse_date(day_text) or _day(day_text)
        if not day:
            return {"error": "Hãy nhập ngày dạng dd/mm/yyyy."}
        path = path or self._dlg.save_file("Lưu danh sách học sinh ăn bán trú", "DANH_SACH_BAN_TRU.xlsx")
        if not path:
            return {"cancel": True}
        try:
            n = export_roster(self._ws.roster, path, day)
        except FileLockedError:
            return {"error": "File đang mở trong Excel. Hãy đóng rồi xuất lại."}
        return {"ok": f"Đã xuất danh sách ({n} em ăn bán trú ngày {fmt_date(day)}) ra {path}"}

    def open_path(self, kind: str) -> dict:
        st = self._ws.settings
        paths = {"data": str(self._ws.data.path), "so_file": st.get("so_file", ""), "cdhs_file": st.get("cdhs_file", "")}
        if kind in paths:
            p = Path(paths[kind]) if paths[kind] else None
            if p and p.exists():
                printing.open_file(p)
                return {"ok": ""}
            return {"error": "Chưa có file này."}
        if kind == "so_folder" and st.get("so_file"):
            printing.open_folder(Path(st["so_file"]))
        elif kind == "backup" and st.get("so_file"):
            b = Path(st["so_file"]).parent / "SaoLuu"
            printing.open_folder(b if b.exists() else Path(st["so_file"]))
        elif kind == "data_folder":
            printing.open_folder(self._ws.data.path)
        return {"ok": ""}

    # ================================================================== đóng app
    def close_check(self) -> dict:
        return {"dirty": self._ws.dirty, "data_dirty": self._ws.data_dirty, "day": fmt_date(self._ws.day)}
