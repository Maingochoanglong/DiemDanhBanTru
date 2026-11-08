"""Điều phối các thao tác của app (không phụ thuộc giao diện)."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import time
from pathlib import Path

from .core import matcher
from .core.day import DayState
from .core.meals import MealLayout, MealSummary
from .core.models import ClassInfo
from .core.text import class_sort_key, fold
from .excel import sobook, tamthoi
from .excel.database import AppData, default_data_path, short_codes
from .excel.files import is_locked
from .excel.roster_import import apply_changes, diff_roster, read_cdhs

APP_NAME = "DiemDanhBanTru"


def config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / APP_NAME / "config.json"


def load_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def next_school_day(day: dt.date, step: int = 1) -> dt.date:
    day += dt.timedelta(days=step)
    while day.weekday() >= 5:
        day += dt.timedelta(days=step)
    return day


# ghi chú lớp kiểu "Không nói gì là đủ" / "ko báo thì đủ": GV không nhắn nghĩa là lớp đủ
NOTE_FULL = re.compile(r"\b(khong|ko|k)\s+(noi|bao|nhan|nt|ib)(\s+gi)?\s*(la|thi|coi nhu|tuc la)\s+du\b")


class NeedMonthBook(Exception):
    """Chưa có sổ cho tháng của ngày đang chọn."""

    def __init__(self, month: int, year: int, prev: Path | None):
        super().__init__(f"Chưa có sổ tháng {month}/{year}")
        self.month, self.year, self.prev = month, year, prev


class Workspace:
    def __init__(self, data_path: str | Path | None = None):
        cfg = load_config()
        self.data = AppData.load(data_path or cfg.get("data_path") or default_data_path())
        self.day: dt.date = dt.date.today()
        self.book_path: Path | None = None
        self.state: DayState | None = None
        self.layout: MealLayout = MealLayout()
        self.sheet_checks: dict[str, list[matcher.MatchResult]] = {}
        self.template_name: str | None = None
        self._undo: list[DayState] = []
        self._wb_cache: tuple[tuple, object] | None = None
        self.sheet_name: str = ""  # tên sheet của ngày đang mở (vd. "01" hoặc "29")
        self.warning: str = ""  # cảnh báo sau lần lưu gần nhất
        self.dirty = False  # ngày đang mở có thay đổi chưa ghi vào sổ
        self.data_dirty = False  # danh sách HS / ghép lớp có thay đổi chưa lưu
        # sổ tạm: tự lưu sau mỗi thao tác (chạy nền), xóa khi đã lưu vào sổ chính
        self.version = 0  # tăng mỗi lần ngày đang mở thay đổi
        self.temp_saved_at = ""  # giờ lưu tạm gần nhất
        self.temp_error = ""
        self.autosave_delay = 0.6  # giây chờ sau thao tác cuối rồi mới ghi
        self._as_version = 0
        self._as_gen = 0  # tăng khi bỏ sổ tạm: việc ghi đang chờ của lần trước bị bỏ
        self._as_job: tuple | None = None
        self._as_lock = threading.Lock()  # giữ chỗ việc đang chờ
        self._as_write = threading.Lock()  # giữ trong lúc ghi file
        self._as_event = threading.Event()
        self._as_thread: threading.Thread | None = None

    # ---------------------------------------------------------------- dữ liệu
    @property
    def roster(self):
        return self.data.roster

    @property
    def settings(self) -> dict[str, str]:
        return self.data.settings

    @property
    def needs_setup(self) -> bool:
        return not self.roster.students

    def remember_data_path(self) -> None:
        cfg = load_config()
        cfg["data_path"] = str(self.data.path)
        save_config(cfg)

    def save_data(self) -> None:
        self.roster.invalidate()
        self.data.save()
        self.remember_data_path()
        self.data_dirty = False

    def import_cdhs(self, path: str | Path):
        """Trả về (các thay đổi, các dòng đọc được) để giao diện cho duyệt."""
        rows = read_cdhs(path)
        return diff_roster(self.roster, rows), rows

    def apply_import(self, changes, cdhs_path: str | Path) -> int:
        n = apply_changes(self.roster, changes)
        self.settings["cdhs_file"] = str(cdhs_path)
        try:
            self.settings["cdhs_mtime"] = str(Path(cdhs_path).stat().st_mtime_ns)
        except OSError:
            self.settings["cdhs_mtime"] = ""
        self._ensure_classes()
        self.save_data()
        return n

    def list_changed(self) -> Path | None:
        """File Excel danh sách đã nhập lần trước nay đã được sửa (cần nhập lại)."""
        path, seen = self.settings.get("cdhs_file"), self.settings.get("cdhs_mtime")
        if not path or not seen:
            return None
        p = Path(path)
        try:
            return p if str(p.stat().st_mtime_ns) != seen else None
        except OSError:
            return None

    def _ensure_classes(self, gvcn: dict[str, str] | None = None) -> None:
        codes = sorted({s.lop_tinh for s in self.roster.students if s.ban_tru} | set(self.roster.classes), key=class_sort_key)
        for code, ma in short_codes(codes).items():
            info = self.roster.classes.setdefault(code, ClassInfo(code))
            if not info.ma_ngan:
                info.ma_ngan = ma
        for code, name in (gvcn or {}).items():
            info = self.roster.classes.setdefault(code, ClassInfo(code))
            if name and not info.gvcn:
                info.gvcn = name

    # ---------------------------------------------------------------- sổ tháng
    def set_book(self, path: str | Path) -> None:
        path = Path(path)
        self.settings["so_file"] = str(path)
        self.settings["so_folder"] = str(path.parent)
        self.save_data()

    def _book(self, path: str | Path):
        """Đọc sổ (dùng lại bản đã đọc nếu file chưa thay đổi). Chỉ để đọc, không sửa bản này."""
        key = (str(path), Path(path).stat().st_mtime_ns)
        if self._wb_cache and self._wb_cache[0] == key:
            return self._wb_cache[1]
        wb = sobook.load_book(path)
        self._wb_cache = (key, wb)
        return wb

    def book_for(self, day: dt.date) -> Path | None:
        cur = self.settings.get("so_file")
        if cur and Path(cur).exists():
            wb = self._book(cur)
            bm = sobook.book_month(wb, cur)
            if bm is None or bm == (day.month, day.year):
                return Path(cur)
        folder = self.settings.get("so_folder")
        if folder:
            found = sobook.find_month_file(folder, day.month, day.year)
            if found:
                self.settings["so_file"] = str(found)
                return found
        return None

    def create_month_book(self, day: dt.date) -> Path:
        prev = self.settings.get("so_file")
        if not prev or not Path(prev).exists():
            raise FileNotFoundError("Chưa chọn sổ tháng trước để làm mẫu.")
        new = sobook.month_file_name(Path(prev), day.month)
        if new.exists():
            raise FileExistsError(str(new))
        sobook.new_month_book(prev, day, new)
        self.set_book(new)
        return new

    def page1_area(self, info: sobook.SheetInfo | None) -> str:
        if self.settings.get("vung_in_1"):
            return self.settings["vung_in_1"]
        return "A1:G46" if info is None else f"A1:{_col(info.cols['ten'])}{info.total_row + 6}"

    def page2_area(self) -> str:
        return self.settings.get("vung_in_2") or self.layout.area

    # ---------------------------------------------------------------- ngày
    def load_day(self, day: dt.date) -> DayState:
        """Mở ngày: nếu sổ đã có sheet ngày đó thì đọc lại và kiểm tra; không thì lấy sheet trước làm mẫu."""
        if self.dirty:  # bỏ thay đổi chưa lưu của ngày đang mở thì bỏ luôn sổ tạm
            self.discard_temp()
        self.day = day
        self._undo.clear()
        self.dirty = False
        self.sheet_checks = {}
        path = self.book_for(day)
        self.book_path = path
        if path is None:
            prev = Path(self.settings["so_file"]) if self.settings.get("so_file") else None
            self.state = DayState.new(day, self.roster, self.roster.class_codes())
            self.layout = MealLayout()
            raise NeedMonthBook(day.month, day.year, prev)

        wb = self._book(path)
        sheets = sobook.day_sheets(wb)
        ws = sheets.get(day.day)
        if ws is not None and sobook.sheet_date(ws) not in (None, day):
            ws = None  # sheet trùng số ngày nhưng khác tháng
        self.sheet_name = ws.title if ws is not None else str(day.day)
        src = ws or sobook.template_sheet(wb, day)
        info = sobook.analyze(src) if src is not None else None
        codes = list(info.class_rows) if info else self.roster.class_codes()
        st = DayState.new(day, self.roster, codes)
        self.template_name = src.title if src is not None else None
        self.layout = info.meal if info else MealLayout()
        if info:
            recs = sobook.read_records(info)
            self._ensure_classes({c: r.gvcn for c, r in recs.items()})
            for code, rec in recs.items():
                if ws is not None:
                    self.sheet_checks[code] = st.load_class_from_sheet(code, rec.si_so, rec.names, rec.note)
                    st.cd(code).keep_sheet_si_so = True
                else:
                    c = st.cd(code)
                    c.sheet_si_so = rec.si_so
                    c.note = rec.note
        st.exists_in_book = ws is not None
        if ws is None and src is not None:
            st.template_date = sobook.sheet_date(src)
        if ws is not None and info:
            m_book = {}  # số em ghép vắng đã ghi trong sổ (cột M): suy ra nhóm của em vắng chưa ghi nhóm
            for mr in info.meal.rows:
                v = ws[mr.m_cell].value if mr.code and mr.m_cell else None
                if isinstance(v, (int, float)) and v:
                    m_book[mr.code] = int(v)
            if m_book:
                st.picks_from_book(info.meal, m_book)
        flags = self.data.reported_flags(day)
        if ws is not None and not flags:
            for c in st.classes.values():  # ngày đã ghi sổ trước khi dùng app: coi như các lớp đã báo
                c.reported = True
        for code, flag in flags.items():
            if code in st.classes:
                st.cd(code).reported = flag
        for code, c in st.classes.items():  # ghi chú sổ "Không nói gì là đủ": GV không nhắn thì lớp đủ
            if code not in flags and not c.reported and NOTE_FULL.search(fold(c.note)):
                c.reported = True
        self.state = st
        return st

    # ---------------------------------------------------------------- nhập liệu
    def push_undo(self) -> None:
        if self.state is not None:
            self._undo.append(self.state.snapshot())
            del self._undo[:-50]
        self.dirty = True
        self.version += 1

    def undo(self) -> bool:
        if not self._undo:
            return False
        self.state = self._undo.pop()
        self.dirty = True
        self.version += 1
        return True

    # ---------------------------------------------------------------- việc còn dở trước khi lưu
    def pending_names(self) -> dict[str, list[str]]:
        """Tên GV ghi mà app chưa xác định được em nào (chưa tính vắng), theo lớp."""
        assert self.state is not None
        out: dict[str, list[str]] = {}
        for code, res in self.state.pending:
            out.setdefault(code, []).append(res.query)
        return out

    def unresolved_count(self) -> int:
        """Số tên GV báo vắng chưa xác định được em nào (chưa tính vắng). Còn > 0 thì chưa cho lưu."""
        if self.state is None:
            return 0
        return len(self.state.pending)

    # ---------------------------------------------------------------- lưu & in
    def si_so_conflicts(self) -> list[tuple[str, int, int]]:
        """Lớp có sĩ số theo danh sách khác sĩ số đang ghi trong sổ."""
        assert self.state is not None
        out = []
        for code, c in self.state.classes.items():
            if self.state.si_so_mismatch(code):
                out.append((code, self.roster.si_so(code, self.day), c.sheet_si_so))
        return out

    def keep_sheet_si_so(self, codes: list[str]) -> None:
        assert self.state is not None
        for code in codes:
            self.state.cd(code).keep_sheet_si_so = True

    def meals(self) -> MealSummary:
        assert self.state is not None
        return self.state.meals(self.layout)

    def book_locked(self) -> bool:
        return bool(self.book_path and is_locked(self.book_path))

    def save(self) -> str:
        """Ghi ngày đang mở vào sổ (đọc lại file mới nhất trước khi ghi). Trả về tên sheet."""
        assert self.state is not None
        if not self.book_path:
            raise FileNotFoundError("Chưa chọn sổ điểm danh tháng.")
        wb, ws = _render_day(self.book_path, self.state)
        sobook.save_book(wb, self.book_path)
        self.discard_temp()
        self.sheet_name = ws.title
        self.state.exists_in_book = True
        for code in self.state.classes:
            c = self.state.cd(code)
            c.sheet_si_so = self.state.si_so(code)  # lấy sĩ số vừa ghi TRƯỚC khi chuyển sang "giữ sĩ số trong sổ"
            c.keep_sheet_si_so = True
            self.data.set_log(self.day, code, self.state.cd(code).reported, self.state.si_so(code), self.state.absent_names(code))
        self.dirty = False
        self.warning = ""
        try:
            self.save_data()
        except Exception as e:  # noqa: BLE001 - sổ đã lưu xong; chỉ nhật ký của app chưa ghi được
            self.data_dirty = True
            self.warning = f"Sổ đã lưu, nhưng chưa ghi được file dữ liệu của app ({e}). Hãy đóng file đó nếu đang mở."
        return ws.title

    # ---------------------------------------------------------------- sổ tạm (tự lưu)
    def temp_path(self) -> Path | None:
        return tamthoi.temp_path(self.book_path) if self.book_path else None

    def autosave_request(self) -> None:
        """Gọi sau mỗi thao tác: nếu ngày đang mở có thay đổi mới thì ghi sổ tạm (chạy nền)."""
        if self.state is None or not self.book_path or not self.dirty or self.version == self._as_version:
            return
        self._as_version = self.version
        with self._as_lock:
            self._as_job = (self._as_gen, self.book_path, self.state.snapshot())
        if self._as_thread is None or not self._as_thread.is_alive():
            self._as_thread = threading.Thread(target=self._autosave_loop, name="tamthoi", daemon=True)
            self._as_thread.start()
        self._as_event.set()

    def _autosave_loop(self) -> None:
        while True:
            self._as_event.wait()
            time.sleep(self.autosave_delay)  # gom các thao tác liên tiếp thành một lần ghi
            self._as_event.clear()
            self.autosave_flush()

    def autosave_flush(self) -> None:
        """Ghi ngay việc lưu tạm đang chờ (nếu có)."""
        with self._as_lock:
            job, self._as_job = self._as_job, None
        if job is None:
            return
        gen, book, state = job
        with self._as_write:
            if gen != self._as_gen:
                return
            try:
                wb, _ = _render_day(book, state)
                tamthoi.write_state_sheet(wb, state, book)
                tamthoi.save(wb, tamthoi.temp_path(book))
                self.temp_saved_at = time.strftime("%H:%M:%S")
                self.temp_error = ""
            except Exception as e:  # noqa: BLE001 - lưu tạm lỗi thì báo nhẹ, không chặn công việc
                self.temp_error = f"Chưa lưu tạm được ({e})"

    def discard_temp(self, path: Path | None = None) -> None:
        """Bỏ sổ tạm (đã lưu vào sổ chính, hoặc người dùng chọn không lưu)."""
        with self._as_lock:
            self._as_gen += 1
            self._as_job = None
        with self._as_write:
            for p in {path, self.temp_path()} - {None}:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
        self.temp_saved_at = ""
        self.temp_error = ""

    def find_temp(self) -> tamthoi.TempInfo | None:
        """Sổ tạm còn lại từ lần trước (app bị tắt khi chưa lưu vào sổ)."""
        cands: list[Path] = []
        if self.settings.get("so_file"):
            cands.append(tamthoi.temp_path(self.settings["so_file"]))
        folder = self.settings.get("so_folder")
        if folder and Path(folder).is_dir():
            cands += sorted(Path(folder).glob(f"* {tamthoi.TAG}.xls*"))
        for p in cands:
            if p.exists():
                info = tamthoi.read(p)
                if info is not None:
                    return info
        return None

    def restore_temp(self, info: tamthoi.TempInfo) -> None:
        """Mở lại ngày trong sổ tạm và đưa các thao tác đã làm vào."""
        if info.book.exists():
            self.settings["so_file"] = str(info.book)
            self.settings["so_folder"] = str(info.book.parent)
        self.dirty = False
        self.load_day(info.day)
        tamthoi.apply(info, self.state)
        self.dirty = True
        self.version += 1

    def print_areas(self) -> list[str]:
        info = None
        if self.book_path:
            wb = self._book(self.book_path)
            ws = sobook.day_sheets(wb).get(self.day.day)
            info = sobook.analyze(ws) if ws is not None else None
        return [a for a in (self.page1_area(info), self.page2_area()) if a]

    # ---------------------------------------------------------------- lịch thêm / cắt
    def schedule(self, kind: str, code: str, ids: list[str], start: dt.date | None, end: dt.date | None = None,
                 new_name: str = "", new_dob: str = "", add_note: bool = True) -> str:
        """Đặt lịch cho các em (hoặc thêm em mới chưa có trong danh sách). Trả về ghi chú đã thêm vào cột H."""
        from .core import schedule as sch
        from .core.models import Student

        students = [s for s in self.roster.students if s.id in ids]
        if new_name:
            s = Student(self.roster.next_id(), code, new_name, new_dob, ban_tru=False, ghi_chu="thêm bằng app")
            self.roster.students.append(s)
            students.append(s)
        if not students:
            return ""
        sch.apply(self.roster, kind, students, start, end)
        self.data_dirty = True
        note = sch.note_text(kind, students, start, end) if add_note else ""
        if note and self.state is not None and code in self.state.classes:
            self.push_undo()
            c = self.state.cd(code)
            if note not in c.note:
                c.note = f"{c.note}, {note}" if c.note else note
        self.save_data()
        return note

    def cancel_schedule(self, item) -> None:
        from .core import schedule as sch

        sch.cancel(self.roster, item)
        self.data_dirty = True
        self.save_data()

    def schedule_items(self):
        from .core import schedule as sch

        return sch.items(self.roster, self.day)

    # ---------------------------------------------------------------- ghi chú trong sổ
    def note_suggestions(self):
        """Đọc ghi chú cột H ở mọi sheet của sổ, gợi ý cập nhật danh sách (cắt thứ 6, cắt/thêm theo ngày…)."""
        from .core.notes import suggest_from_book

        if not self.book_path:
            return []
        wb = self._book(self.book_path)
        notes = []
        for _, ws in sorted(sobook.day_sheets(wb).items()):
            info = sobook.analyze(ws)
            d = sobook.sheet_date(ws)
            if not info or not d:
                continue
            for code, rec in sobook.read_records(info).items():
                if rec.note:
                    notes.append((d, code, rec.note))
                # ghi chú lẫn trong ô tên vắng ("cắt …", "thêm …")
                from .core.day import split_sheet_cell

                for extra in split_sheet_cell(rec.names)[1]:
                    notes.append((d, code, extra))
        return suggest_from_book(self.roster, notes)

    def apply_note_suggestions(self, sugs) -> int:
        from .core.notes import apply_suggestions

        n = apply_suggestions(self.roster, sugs)
        if n:
            self.data_dirty = True
            self.save_data()
        return n

    # ---------------------------------------------------------------- ghép lớp
    def ghep_students(self, code: str):
        return self.roster.sort_like_roster(self.roster.boarding(code, self.day))


def _render_day(book: Path, state: DayState):
    """Đọc sổ và ghi ngày `state` vào sheet của ngày đó (tạo sheet từ mẫu nếu chưa có). Chưa lưu file."""
    wb = sobook.load_book(book)
    ws = sobook.day_sheets(wb).get(state.date.day)
    if ws is None:
        tpl = sobook.template_sheet(wb, state.date)
        if tpl is None:
            raise ValueError("Sổ không có sheet điểm danh nào để làm mẫu.")
        ws = sobook.create_day_sheet(wb, state.date, tpl)
    info = sobook.analyze(ws)
    if info is None:
        raise ValueError(f"Sheet {ws.title} không đúng mẫu điểm danh.")
    sobook.write_day(info, state, state.meals(info.meal))
    sobook.select_only(wb, ws)
    return wb, ws


def _col(i: int) -> str:
    from openpyxl.utils import get_column_letter

    return get_column_letter(i)


def search_students(roster, text: str, cls: str | None = None, only_bt: bool = False):
    f = fold(text)
    out = []
    for s in roster.students:
        if cls and s.lop != cls and s.lop_tinh != cls:
            continue
        if only_bt and not s.ban_tru:
            continue
        if f and f not in fold(s.ho_ten):
            continue
        out.append(s)
    return out
