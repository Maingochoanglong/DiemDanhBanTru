"""Điều phối các thao tác của app (không phụ thuộc giao diện).

App chỉ làm việc với 3 file:
- file Excel danh sách học sinh (chỉ đọc: excel/roster_import.py, đọc lại khi file được sửa);
- sổ điểm danh tháng (excel/sobook.py) + sổ tạm "… tamthoi.xlsx" cạnh sổ (excel/tamthoi.py), ghi sau mỗi thao tác,
  xóa khi đã lưu vào sổ;
- CaiDat.txt cạnh file .exe (settings.py).
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

from . import build_info, config
from . import settings as cfg
from .core import matcher
from .core.day import DayState
from .core.meals import MealLayout, MealSummary
from .core.models import ClassInfo, Roster
from .core.text import fold
from .excel import sobook, tamthoi
from .excel.files import safe_save
from .excel.roster_import import ListData, load_list

def next_school_day(day: dt.date, step: int = 1) -> dt.date:
    day += dt.timedelta(days=step)
    while day.weekday() >= config.SCHOOL_DAYS:
        day += dt.timedelta(days=step)
    return day


class NeedMonthBook(Exception):
    """Chưa có sổ cho tháng của ngày đang chọn."""

    def __init__(self, month: int, year: int, prev: Path | None):
        super().__init__(f"Chưa có sổ tháng {month}/{year}")
        self.month, self.year, self.prev = month, year, prev


class Workspace:
    def __init__(self, settings_path: str | Path | None = None):
        self.settings_path = Path(settings_path) if settings_path else cfg.default_path()
        self.settings = cfg.load(self.settings_path)
        # Bản .exe mới tải về (mã bản dựng khác lần trước): bắt chọn lại sổ điểm danh và file danh sách
        self.setup_needed = settings_path is None and build_info.BUILD != "dev" and self.settings.get("build") != build_info.BUILD
        self.setup_steps: set[str] = set()  # "book", "list" đã làm trong lần thiết lập này
        self.list = ListData(Roster())  # file danh sách học sinh đã đọc
        self.list_error = ""  # lỗi đọc file danh sách
        self._list_key: tuple | None = None  # (đường dẫn, thời điểm sửa) của bản đã đọc
        if not self.setup_needed:
            self.refresh_list()
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
        self.meal_note: str = ""  # bảng suất ăn ngày đang mở so với bảng Nhóm ăn (dựng lại / khác / lỗi)
        self._src_info: sobook.SheetInfo | None = None  # sheet ngày đang mở (hoặc sheet mẫu nếu chưa có)
        self._src_exists = False  # sheet ngày đang mở đã có trong sổ
        self.dirty = False  # ngày đang mở có thay đổi chưa ghi vào sổ
        self.version = 0  # tăng mỗi lần ngày đang mở thay đổi
        self._temp_version = 0  # version đã ghi vào sổ tạm
        self.temp_saved_at = ""  # giờ lưu tạm gần nhất
        self.temp_error = ""

    # ---------------------------------------------------------------- 3 file: cài đặt, danh sách học sinh
    @property
    def roster(self) -> Roster:
        return self.list.roster

    def save_settings(self) -> None:
        cfg.save(self.settings_path, self.settings)

    def refresh_list(self) -> None:
        """Đọc lại file danh sách học sinh nếu đã đổi file / file được sửa từ lần đọc trước."""
        path = self.settings.get("cdhs_file")
        try:
            key = (path, Path(path).stat().st_mtime_ns) if path else None
        except OSError:
            key = None
        if key == self._list_key:
            return
        self._list_key, self.list_error = key, ""
        self.list = ListData(Roster())
        if key is None:
            self.list_error = "Không tìm thấy file danh sách học sinh." if path else ""
            return
        try:
            self.list = load_list(path)
        except Exception as e:  # noqa: BLE001 - báo ở giao diện, app vẫn mở được sổ
            self.list_error = f"Không đọc được file danh sách học sinh: {e}"

    def set_list(self, path: str | Path) -> None:
        """Chọn file danh sách học sinh (đọc thử trước: file không đọc được thì không đổi cài đặt)."""
        load_list(path)
        self.settings["cdhs_file"] = str(path)
        self.save_settings()
        self._list_key = None
        self.refresh_list()
        if self.setup_needed:
            self.setup_steps.add("list")

    # ---------------------------------------------------------------- thiết lập lần đầu (bản mới tải về)
    def setup_missing(self) -> list[str]:
        need = [("book", "chọn sổ điểm danh"), ("list", "chọn file danh sách học sinh")]
        return [text for key, text in need if key not in self.setup_steps]

    def finish_setup(self) -> None:
        missing = self.setup_missing()
        if missing:
            raise ValueError("Còn thiếu: " + ", ".join(missing) + ".")
        self.settings["build"] = build_info.BUILD
        self.save_settings()
        self.setup_needed = False

    def _ensure_classes(self, gvcn: dict[str, str]) -> None:
        """Tên GVCN lấy theo sổ."""
        for code, name in gvcn.items():
            info = self.roster.classes.setdefault(code, ClassInfo(code))
            if name and not info.gvcn:
                info.gvcn = name

    # ---------------------------------------------------------------- sổ tháng
    def set_book(self, path: str | Path) -> None:
        path = Path(path)
        self.settings["so_file"] = str(path)
        self.save_settings()
        if self.setup_needed:
            self.setup_steps.add("book")

    def _book(self, path: str | Path):
        """Đọc sổ (dùng lại bản đã đọc nếu file chưa thay đổi). Chỉ để đọc, không sửa bản này."""
        key = (str(path), Path(path).stat().st_mtime_ns)
        if self._wb_cache and self._wb_cache[0] == key:
            return self._wb_cache[1]
        wb = sobook.load_book(path)
        self._wb_cache = (key, wb)
        return wb

    def book_for(self, day: dt.date) -> Path | None:
        """Sổ đang chọn (CaiDat.txt) nếu đúng tháng của ngày; không thì None (app hỏi tạo sổ tháng mới / chọn sổ).
        App không tự mở các file khác trong thư mục."""
        cur = self.settings.get("so_file")
        if cur and Path(cur).exists():
            wb = self._book(cur)
            bm = sobook.book_month(wb, cur)
            if bm is None or bm == (day.month, day.year):
                return Path(cur)
        return None

    def create_month_book(self, day: dt.date) -> Path:
        prev = self.settings.get("so_file")
        if not prev or not Path(prev).exists():
            raise FileNotFoundError("Chưa chọn sổ tháng trước để làm mẫu.")
        new = sobook.month_file_name(Path(prev), day.month)
        if new.exists():
            raise FileExistsError(str(new))
        sobook.new_month_book(prev, day, new)
        if self.list.meal_groups:
            wb = sobook.load_book(new)
            ws = sobook.day_sheets(wb).get(day.day)
            if ws is not None:
                self._rebuild_meal_table(ws, day)
                safe_save(wb, new)
        self.set_book(new)
        return new

    # ---------------------------------------------------------------- bảng suất ăn theo Nhóm ăn
    def meal_plan(self, info: sobook.SheetInfo | None, day: dt.date) -> MealLayout | None:
        """Bảng suất ăn dựng theo bảng Nhóm ăn, nếu khác bảng của sheet `info`; None = giữ bảng của sổ."""
        groups = self.list.meal_groups
        if not groups or info is None or info.meal.is_empty:
            return None
        codes = {g.code for g in groups if g.code}
        grouped = {c for g in groups for c in g.classes}
        split: set[str] = set()
        counts: dict[str, int] = {}
        for code in info.class_rows:
            if code in grouped:
                continue
            for st in self.roster.boarding(code, day):
                if st.an_ghep in codes:
                    split.add(code)
                    counts[st.an_ghep] = counts.get(st.an_ghep, 0) + 1
        plan = sobook.plan_meal_table(info, groups, split, counts)
        return None if plan.signature() == info.meal.signature() else plan

    def _apply_meal_plan(self) -> None:
        """Bảng suất ăn ngày đang mở: theo sổ, hoặc theo sheet Nhóm ăn (file danh sách) nếu tờ chưa có trong sổ."""
        info, exists = self._src_info, self._src_exists
        self.layout = info.meal if info else MealLayout()
        self.meal_note = ""
        if info is None or not self.list.meal_groups:
            return
        try:
            plan = self.meal_plan(info, self.day)
        except sobook.MealTableError as e:
            plan, self.meal_note = None, f"Chưa dựng được bảng suất ăn theo cách ghép đã đặt: {e}"
        if plan is not None and not exists:
            self.layout = plan
            self.meal_note = "Ngày này chưa có trong sổ: khi lưu, app dựng bảng suất ăn theo sheet Nhóm ăn."
        elif plan is not None:
            self.meal_note = ("Bảng suất ăn của tờ này trong sổ khác sheet Nhóm ăn. App tính theo sổ; "
                              "từ tờ ngày mới app dựng theo sheet Nhóm ăn.")

    def _rebuild_meal_table(self, ws, day: dt.date) -> sobook.SheetInfo | None:
        """Tờ ngày mới: dựng lại bảng suất ăn theo sheet Nhóm ăn, nếu khác. Trả về thông tin sheet sau khi ghi."""
        info = sobook.analyze(ws)
        try:
            plan = self.meal_plan(info, day)
            if plan is not None:
                sobook.write_meal_table(ws, info, plan)
                info = sobook.analyze(ws)
        except sobook.MealTableError as e:
            self.warning = f"Chưa dựng lại được bảng suất ăn theo bảng Nhóm ăn: {e} Bảng suất ăn giữ như tờ trước."
        return info

    # ---------------------------------------------------------------- ngày
    def load_day(self, day: dt.date) -> DayState:
        """Mở ngày: nếu sổ đã có sheet ngày đó thì đọc lại và kiểm tra; không thì lấy sheet trước làm mẫu."""
        if self.dirty:  # bỏ thay đổi chưa lưu của ngày đang mở thì bỏ luôn sổ tạm
            self.discard_temp()
        self.refresh_list()
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
            self._src_info, self._src_exists = None, False
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
        recs: dict = {}
        self._src_info, self._src_exists = info, ws is not None
        self._apply_meal_plan()
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
        if ws is not None and (ws.title in sobook.saved_sheets(wb) or any(rec.names for rec in recs.values())):
            # ngày app đã lưu (kể cả lớp nào cũng đủ), hoặc đã điểm danh tay trong sổ (có tên vắng): các lớp đã báo.
            # Sheet tạo sẵn còn trống thì các lớp vẫn "chưa báo": đủ hay vắng do giáo vụ bấm.
            for c in st.classes.values():
                c.reported = True
        self.state = st
        return st

    # ---------------------------------------------------------------- nhập liệu
    def reset_day(self) -> None:
        """Đặt lại điểm danh ngày đang mở: mọi lớp về "chưa báo", bỏ hết tên vắng đã chọn (giữ ghi chú, sĩ số).
        Dùng khi sheet trong sổ đã tạo sẵn nên app hiểu nhầm là đã điểm danh."""
        assert self.state is not None
        self.push_undo()
        for c in self.state.classes.values():
            c.manual, c.extra, c.auto_off = [], [], set()
            c.reported = False
        self.state.ghep_pick.clear()

    def push_undo(self) -> None:
        if self.state is not None:
            self._undo.append(self.state.snapshot())
            del self._undo[:-config.UNDO_DEPTH]
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

    def save(self) -> str:
        """Ghi ngày đang mở vào sổ (đọc lại file mới nhất trước khi ghi). Trả về tên sheet."""
        assert self.state is not None
        if not self.book_path:
            raise FileNotFoundError("Chưa chọn sổ điểm danh tháng.")
        self.warning = ""
        self.autosave()  # sổ tạm có đủ thao tác trước khi ghi sổ (lưu lỗi giữa chừng thì vẫn còn sổ tạm)
        wb = self._book(self.book_path)  # bản đã đọc khi mở ngày (đọc lại nếu file đã bị sửa từ đó)
        self._wb_cache = None  # bản này sắp bị sửa: lưu lỗi thì lần sau đọc lại từ file
        wb, ws = _render_day(self.book_path, self.state, self._rebuild_meal_table, wb=wb)
        sobook.mark_saved(wb, ws.title)
        safe_save(wb, self.book_path)
        self._wb_cache = ((str(self.book_path), Path(self.book_path).stat().st_mtime_ns), wb)
        self.discard_temp()
        self.sheet_name = ws.title
        info = sobook.analyze(ws)
        if info is not None:
            self.layout = info.meal
            self.meal_note = ""
            self._src_info, self._src_exists = info, True
        self.state.exists_in_book = True
        for code in self.state.classes:
            c = self.state.cd(code)
            c.sheet_si_so = self.state.si_so(code)  # lấy sĩ số vừa ghi TRƯỚC khi chuyển sang "giữ sĩ số trong sổ"
            c.keep_sheet_si_so = True
        self.dirty = False
        return ws.title

    # ---------------------------------------------------------------- sổ tạm (tự lưu)
    def temp_path(self) -> Path | None:
        return tamthoi.temp_path(self.book_path) if self.book_path else None

    def autosave(self) -> None:
        """Ghi sổ tạm ngay (gọi sau mỗi thao tác) nếu ngày đang mở có thay đổi chưa ghi tạm. File nhỏ, ghi nhanh."""
        if self.state is None or not self.book_path or not self.dirty or self.version == self._temp_version:
            return
        try:
            safe_save(tamthoi.build(self.state, self.book_path), tamthoi.temp_path(self.book_path))
            self._temp_version = self.version
            self.temp_saved_at, self.temp_error = time.strftime("%H:%M:%S"), ""
        except Exception as e:  # noqa: BLE001 - lưu tạm lỗi thì báo nhẹ, không chặn công việc
            self.temp_error = f"Chưa lưu tạm được ({e})"

    def discard_temp(self, path: Path | None = None) -> None:
        """Xóa sổ tạm (đã lưu vào sổ chính, hoặc giáo vụ chọn không lưu)."""
        for p in {path, self.temp_path()} - {None}:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        self._temp_version = self.version
        self.temp_saved_at = self.temp_error = ""

    def find_temp(self) -> tamthoi.TempInfo | None:
        """Sổ tạm còn lại từ lần trước (app bị tắt khi chưa lưu vào sổ)."""
        if not self.settings.get("so_file"):
            return None
        p = tamthoi.temp_path(self.settings["so_file"])  # chỉ sổ tạm của sổ đang chọn
        return tamthoi.read(p) if p.exists() else None

    def restore_temp(self, info: tamthoi.TempInfo) -> None:
        """Mở lại ngày trong sổ tạm và đưa các thao tác đã làm vào."""
        self.dirty = False
        self.load_day(info.day)
        tamthoi.apply(info, self.state)
        self.dirty = True
        self.version += 1

    # ---------------------------------------------------------------- ghép lớp
    def ghep_students(self, code: str):
        return self.roster.sort_like_roster(self.roster.boarding(code, self.day))


def _render_day(book: Path, state: DayState, on_new_sheet=None, wb=None):
    """Đọc sổ và ghi ngày `state` vào sheet của ngày đó (tạo sheet từ mẫu nếu chưa có). Chưa lưu file.
    on_new_sheet(ws, ngày): dựng lại bảng suất ăn của sheet vừa tạo."""
    wb = wb if wb is not None else sobook.load_book(book)
    ws = sobook.day_sheets(wb).get(state.date.day)
    if ws is None:
        tpl = sobook.template_sheet(wb, state.date)
        if tpl is None:
            raise ValueError("Sổ không có sheet điểm danh nào để làm mẫu.")
        ws = sobook.create_day_sheet(wb, state.date, tpl)
        if on_new_sheet is not None:
            on_new_sheet(ws, state.date)
    info = sobook.analyze(ws)
    if info is None:
        raise ValueError(f"Sheet {ws.title} không đúng mẫu điểm danh.")
    sobook.write_day(info, state, state.meals(info.meal))
    sobook.select_only(wb, ws)
    return wb, ws


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
