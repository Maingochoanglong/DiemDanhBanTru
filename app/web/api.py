"""Cầu nối giữa giao diện web và phần xử lý sổ (Workspace).

Mọi hàm công khai trả về dict/list đơn giản (JSON); giao diện gọi qua máy chủ nội bộ: POST /api/<tên hàm> (server.py).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .. import __version__
from ..core import matcher
from ..core.search import matches
from ..core.text import class_sort_key, clean_spaces, fmt_date, parse_date
from ..excel.files import FileLockedError, open_file, open_folder
from ..excel.roster_import import RosterFormatError
from ..service import NeedMonthBook, Workspace, next_school_day, search_students

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


class NoDialogs:
    """Không có hộp chọn file (máy chủ chạy thử, test). App thật dùng hộp của Windows (run.py)."""

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
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
        self._temp = None  # sổ tạm tìm thấy lúc mở app (chờ hỏi khôi phục)
        self._booted = False

    # ================================================================== ngày
    def boot(self) -> dict:
        """Mở app: mở ngày học hôm nay (thứ 7/CN thì ngày học kế tiếp). Bản mới tải về: hiện màn Thiết lập."""
        if self._ws.setup_needed:
            return {"setup": self.setup_info(), "state": self.state()}
        if self._booted and self._ws.state is not None and self._ws.dirty:
            # trình duyệt tải lại trang / mở thêm thẻ khi đang làm dở: giữ nguyên ngày đang mở, không mất thay đổi
            return {"state": self.state()}
        self._booted = True
        today = dt.date.today()
        res = self.open_day(_iso(today if today.weekday() < 5 else next_school_day(today)), True)
        self._temp = self._ws.find_temp()
        if self._temp is not None:
            res["restore"] = {"day": fmt_date(self._temp.day), "at": self._temp.saved_at, "file": self._temp.path.name}
        return res

    # ================================================================== thiết lập (bản mới tải về)
    def setup_info(self) -> dict:
        ws = self._ws
        st = ws.settings
        steps = ws.setup_steps
        return {"book": Path(st.get("so_file") or "").name if "book" in steps else "", "book_done": "book" in steps,
                "list": Path(st.get("cdhs_file") or "").name if "list" in steps else "", "list_done": "list" in steps,
                "n": len(ws.roster.students) if "list" in steps else 0, "missing": ws.setup_missing()}

    def finish_setup(self) -> dict:
        try:
            self._ws.finish_setup()
        except ValueError as e:
            return {"error": str(e), "setup": self.setup_info()}
        today = dt.date.today()
        res = self.open_day(_iso(today if today.weekday() < 5 else next_school_day(today)), True)
        res["flash"] = "Đã thiết lập xong. Bắt đầu điểm danh."
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
    def _setup_hint(self) -> str:
        if self._ws.list_error:
            return self._ws.list_error + " Vào Cài đặt để chọn lại file."
        steps = []
        if not self._ws.roster.students:
            steps.append("chọn file danh sách học sinh")
        if not self._ws.book_path:
            steps.append("chọn sổ điểm danh tháng này")
        return ("Vào Cài đặt để " + " và ".join(steps) + ".") if steps else ""

    def _status(self, code: str) -> str:
        st = self._ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        if c.extra or any(p[0] == code for p in st.pending) or st.class_warnings(code):
            return "err"
        if not c.reported:  # chưa báo (có thể đã có em nghỉ thứ 6 tự tính vắng)
            return "muted"
        return "warn" if n else "ok"

    def state(self) -> dict:
        ws, st = self._ws, self._ws.state
        ws.autosave()  # mọi thao tác đều trả về state(): có thay đổi mới thì ghi ngay vào sổ tạm
        bp = ws.book_path
        out = {
            "date": _iso(ws.day), "date_text": fmt_date(ws.day), "weekday": WEEKDAYS[ws.day.weekday()],
            "book": bp.name if bp else "", "book_stem": bp.stem if bp else "",
            "exists": bool(st and st.exists_in_book), "sheet": ws.sheet_name or str(ws.day.day),
            "dirty": ws.dirty, "temp_at": ws.temp_saved_at, "temp_error": ws.temp_error, "hint": self._setup_hint(),
            "rows": [], "totals": None, "meal": None, "todo": [], "info": [], "unresolved": 0,
            "unreported": [],
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
                    "ten": names if c.reported else "", "reported": c.reported,
                    "auto": names if not c.reported and n else "",  # chưa báo: chỉ có em nghỉ thứ 6 tự tính vắng
                    "note": note, "warn": warns[0] if warns else "",
                    "not_bt": ", ".join(c.not_bt),
                    "sched": bool(st.scheduled_changes(code)),
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
            out["meal"] = {"total": m.total_meals, "present": m.total_present, "ok": m.balanced, "ask": len(m.ask)}
        n_pending = len(st.pending)
        out["unresolved"] = ws.unresolved_count()
        out["unreported"] = st.unreported()
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
        board_ids = {s.id for s in roster.boarding(code, st.date)}
        others = []  # em của lớp không có trong bảng chọn hôm nay: để báo lý do khi gõ / dán tên các em này
        for s in roster.in_class(code):
            if s.id in board_ids:
                continue
            if s.lop_tinh != code and s.is_boarding(st.date):
                why = f"Tính bán trú ở lớp {s.lop_tinh}"
            elif not s.ban_tru:
                why = "Không ăn bán trú"
            elif s.bt_tu and st.date < s.bt_tu:
                why = f"Ăn bán trú từ {s.bt_tu:%d/%m}"
            elif s.cat_tu and st.date >= s.cat_tu:
                why = f"Đã cắt bán trú từ {s.cat_tu:%d/%m}"
            else:
                why = "Không ăn bán trú hôm nay"
            others.append({"s": f"{s.ho_ten} {roster.display_name(s)} {s.ten_ghi_so or ''}", "why": why})
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
            "not_bt": list(c.not_bt),
            "names": names, "others": others, "pending": pending, "upcoming": upcoming,
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

    def reset_day(self) -> dict:
        """Đặt lại điểm danh ngày đang mở: mọi lớp về "chưa báo", bỏ tên vắng đã chọn."""
        if self._ws.state is None:
            return {"state": self.state()}
        self._ws.reset_day()
        return {"state": self.state(), "flash": "Đã đặt lại: các lớp về \"chưa báo\". Bấm Hoàn tác nếu nhầm."}

    def undo(self) -> dict:
        ok = self._ws.undo()
        return {"state": self.state(), "flash": "Đã hoàn tác." if ok else "Không còn gì để hoàn tác."}

    # ================================================================== lưu / in
    def _blocked(self) -> dict | None:
        ws = self._ws
        n = ws.unresolved_count()
        if not n:
            return None
        lines = [f"Lớp {code}: {', '.join(names)}" for code, names in ws.pending_names().items()]
        return {"n": n, "lines": lines, "code": next(iter(ws.pending_names()), None)}

    def _conflict_lines(self) -> list[str]:
        return [f"{c}: theo danh sách {ds} em, trong sổ đang ghi {so} em" for c, ds, so in self._ws.si_so_conflicts()]

    def save_check(self) -> dict:
        """Mọi điều cần hỏi trước khi lưu, để giao diện hỏi một lần: còn tên chưa rõ (không lưu được),
        lớp chưa báo, suất ăn lệch, sĩ số danh sách khác sổ."""
        ws, st = self._ws, self._ws.state
        if st is None or not ws.book_path:
            return {}
        blocked = self._blocked()
        if blocked:
            return {"blocked": blocked}
        out = {"unreported": st.unreported(), "meal": None, "conflicts": self._conflict_lines(),
               "unreported_auto": [c for c in st.unreported() if st.absent_count(c)]}
        if not ws.layout.is_empty:
            m = ws.meals()
            if not m.balanced:
                out["meal"] = {"total": m.total_meals, "present": m.total_present, "ask": len(m.ask)}
        return out

    def save(self, choice: str | None = None) -> dict:
        """Lưu vào sổ. Có thể trả về: blocked (còn tên chưa rõ), conflicts (hỏi sĩ số), locked, error, ok."""
        ws, st = self._ws, self._ws.state
        if st is None:
            return {"error": "Chưa mở ngày nào."}
        if not ws.book_path:
            return {"error": "Chưa có sổ điểm danh cho tháng này. Vào Cài đặt → Chọn sổ."}
        blocked = self._blocked()
        if blocked:
            return {"blocked": blocked}
        conflicts = ws.si_so_conflicts()
        if conflicts and choice is None:
            return {"conflicts": self._conflict_lines()}
        if conflicts and choice == "keep":
            ws.keep_sheet_si_so([c for c, _, _ in conflicts])
        try:
            sheet = ws.save()
        except FileLockedError as e:
            return {"locked": f"File đang mở trong Excel nên chưa ghi được:\n{e}\n\nHãy đóng file đó trong Excel rồi bấm Thử lại."}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không lưu được:\n{e}"}
        msg = ws.warning or f"Đã lưu vào sổ {ws.book_path.name}, sheet {sheet}. Đã xóa sổ tạm."
        return {"ok": msg, "state": self.state()}

    def open_book(self) -> dict:
        if self._ws.book_path:
            open_file(self._ws.book_path)
            return {"ok": ""}
        return {"error": "Chưa chọn sổ. Vào Cài đặt → Chọn sổ."}

    # ================================================================== suất ăn
    def meals(self) -> dict:
        ws, st = self._ws, self._ws.state
        layout = ws.layout
        if st is None or layout.is_empty:
            return {"empty": True}
        summary = ws.meals()
        name = ws.roster.display_name
        lines = []
        for line in summary.lines:
            r = line.row
            gom = " + ".join(r.classes)
            absent = []
            if r.code:
                src = [c for c in layout.ghep_classes if r.code in st.groups_for(layout, c)]
                gom += f" + {line.o} em ghép lớp {', '.join(src)}" if src else f" + {line.o} em ghép"
                for code in src:
                    groups = st.groups_for(layout, code)
                    for s in st.absent_students(code):
                        if s.an_ghep in groups:
                            g, picked = s.an_ghep, False
                        else:
                            g, picked = st.ghep_pick.get(s.id), True
                        if g == r.code:
                            absent.append({"sid": s.id, "name": name(s), "picked": picked})
            lines.append({"label": r.label, "gom": gom, "meals": line.meals, "m": line.m or 0, "code": r.code or "",
                          "absent": absent, "row": r.row})
        self_line = None
        if layout.self_classes:
            self_line = {"label": "Tự ăn tại lớp", "gom": ", ".join(layout.self_classes), "meals": summary.self_meals}
        ask = [{"sid": s.id, "name": name(s), "full": s.ho_ten, "cls": code, "groups": st.groups_for(layout, code)}
               for code, s in summary.ask]
        ghep = []  # lớp ghép: đã ghi nhóm ăn ghép (cột Ăn ghép trong file Excel danh sách) cho bao nhiêu em
        for code in layout.ghep_classes:
            groups = st.groups_for(layout, code)
            kids = ws.ghep_students(code)
            info = ws.roster.classes.get(code)
            ghep.append({"code": code, "ma": info.ma_ngan if info else "", "n": len(kids),
                         "done": sum(1 for s in kids if s.an_ghep in groups)})
        return {"lines": lines, "self": self_line, "total": summary.total_meals, "present": summary.total_present,
                "groups_total": summary.group_meals, "ok": summary.balanced, "warnings": summary.warnings, "ask": ask,
                "ghep": ghep, "note": ws.meal_note}

    def pick_ghep(self, sid: str, group: str) -> dict:
        """Chọn nhóm ăn cho em ghép vắng (chỉ ngày đang mở); group rỗng = chọn lại."""
        self._ws.push_undo()
        self._ws.state.pick_ghep(sid, group)
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
                         "goi": s.ten_ghi_so or "", "ghep": s.an_ghep,
                         "db": "; ".join(special), "gc": s.ghi_chu, "now": s.is_boarding(day)})
        return {"rows": rows, "classes": roster.class_codes()}

    # ================================================================== cài đặt (3 file: sổ, danh sách, CaiDat.txt)
    def settings(self) -> dict:
        ws, st = self._ws, self._ws.settings
        groups = ws.list.meal_groups or []
        return {"so_file": st.get("so_file", ""), "cdhs_file": st.get("cdhs_file", ""), "settings_file": str(ws.settings_path),
                "version": __version__, "list_error": ws.list_error, "n": len(ws.roster.students),
                "nhom_an": sum(1 for g in groups if not g.blank), "nhom_an_errors": ws.list.meal_errors + ws.list.meal_warnings}

    def choose_book(self, path: str | None = None) -> dict:
        path = path or self._dlg.open_file("Chọn sổ điểm danh tháng (.xlsx)", ("Excel (*.xlsx)",))
        if not path:
            return {"cancel": True}
        self._ws.set_book(path)
        res = self.open_day(_iso(self._ws.day), True)
        res["flash"] = f"Đã chọn sổ {Path(path).name}."
        return res

    def choose_list(self, path: str | None = None) -> dict:
        """Chọn file Excel danh sách học sinh (app đọc thẳng file này, sửa file thì app tự đọc lại)."""
        path = path or self._dlg.open_file("Chọn file danh sách học sinh (Excel)", ("Excel (*.xlsx;*.xls)",))
        if not path:
            return {"cancel": True}
        try:
            self._ws.set_list(path)
        except RosterFormatError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Không đọc được file:\n{e}"}
        res = self.open_day(_iso(self._ws.day), True) if not self._ws.dirty else {"state": self.state()}
        res["flash"] = f"Đã chọn {Path(path).name}: {len(self._ws.roster.students)} học sinh."
        return res

    def open_path(self, kind: str) -> dict:
        """Mở file (so_file, cdhs_file, settings) hoặc thư mục chứa file (so_folder, cdhs_folder)."""
        files = {"so_file": self._ws.settings.get("so_file", ""), "cdhs_file": self._ws.settings.get("cdhs_file", ""),
                 "settings": str(self._ws.settings_path)}
        key = kind.removesuffix("_folder") + ("_file" if kind.endswith("_folder") else "")
        p = Path(files.get(key) or "")
        if not files.get(key) or not p.exists():
            return {"error": "Chưa có file này."}
        (open_folder if kind.endswith("_folder") else open_file)(p)
        return {"ok": ""}

    # ================================================================== đóng app
    def close_check(self) -> dict:
        return {"dirty": self._ws.dirty, "day": fmt_date(self._ws.day)}
