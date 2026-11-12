"""Sổ điểm danh tháng: mỗi ngày 1 sheet (tên = số ngày), mỗi tháng 1 file.

Không cố định địa chỉ ô: tìm hàng tiêu đề "TÊN HỌC SINH VẮNG", tìm hàng lớp theo mã lớp ở
cột LỚP, tìm bảng suất ăn theo công thức. App chỉ ghi giá trị vào các ô số liệu; định dạng,
công thức, chữ ký giữ nguyên như sheet mẫu.
"""

from __future__ import annotations

import datetime as dt
import re
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ..core.day import DayState
from ..core.meals import MealGroup, MealLayout, MealRow, MealSummary
from ..core.text import clean_spaces, fmt_date, fold, norm_class
from .files import safe_save

_REF = re.compile(r"(?<![A-Z:$])\$?([A-Z]{1,3})\$?(\d+)(?!\s*:)(?![\d(])")
_TITLE_DATE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")


@dataclass
class SheetInfo:
    ws: Worksheet
    header_row: int
    cols: dict[str, int]  # lop, gvcn, siso, vang, hien, ten, ghichu (chỉ số cột 1-based)
    class_rows: dict[str, int]
    total_row: int
    title_cell: str | None = None
    sign_cell: str | None = None
    meal: MealLayout = field(default_factory=MealLayout)

    def cell(self, code: str, key: str):
        return self.ws.cell(self.class_rows[code], self.cols[key])


@dataclass
class ClassRecord:
    code: str
    gvcn: str
    si_so: int | None
    vang: int | None
    names: str
    note: str


# ---------------------------------------------------------------- nhận diện sheet
def analyze(ws: Worksheet) -> SheetInfo | None:
    header_row = None
    cols: dict[str, int] = {}
    for r in range(1, min(ws.max_row, 20) + 1):
        for c in range(1, min(ws.max_column, 30) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and "ten hoc sinh vang" in fold(v):
                header_row, cols["ten"] = r, c
                break
        if header_row:
            break
    if not header_row:
        return None
    for c in range(1, cols["ten"]):
        f = fold(str(ws.cell(header_row, c).value or ""))
        if f == "lop" or f.startswith("lop"):
            cols.setdefault("lop", c)
        elif "giao vien" in f or "gvcn" in f:
            cols.setdefault("gvcn", c)
        elif f.startswith("si so") or f.startswith("sy so"):
            cols.setdefault("siso", c)
        elif f.startswith("vang"):
            cols.setdefault("vang", c)
        elif "hien dien" in f:
            cols.setdefault("hien", c)
    if not {"lop", "siso", "vang"} <= set(cols):
        return None
    cols.setdefault("hien", cols["vang"] + 1)
    cols["ghichu"] = cols["ten"] + 1

    class_rows: dict[str, int] = {}
    total_row = header_row
    for r in range(header_row + 1, ws.max_row + 1):
        v = ws.cell(r, cols["lop"]).value
        code = norm_class(str(v)) if isinstance(v, str) else ""
        if code and code not in class_rows:
            class_rows[code] = r
            total_row = max(total_row, r)
        a = ws.cell(r, 1).value
        if isinstance(a, str) and "tong cong" in fold(a):
            total_row = r
            break
    if not class_rows:
        return None

    info = SheetInfo(ws, header_row, cols, class_rows, total_row)
    for r in range(1, header_row):
        for c in range(1, min(ws.max_column, 30) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and "ngay" in fold(v) and _TITLE_DATE.search(v):
                info.title_cell = ws.cell(r, c).coordinate
    for r in range(total_row + 1, min(ws.max_row, total_row + 6) + 1):
        for c in range(1, min(ws.max_column, 30) + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str) and "thang" in fold(v) and "nam" in fold(v):
                info.sign_cell = ws.cell(r, c).coordinate
                break
        if info.sign_cell:
            break
    info.meal = analyze_meals(ws, info)
    return info


def _refs(formula: str) -> list[tuple[str, int]]:
    return [(m.group(1), int(m.group(2))) for m in _REF.finditer(formula.upper())]


def analyze_meals(ws: Worksheet, info: SheetInfo) -> MealLayout:
    """Đọc bảng suất ăn bên dưới: nhóm nào cộng những lớp nào, hàng nào nhận HS ghép."""
    hien = get_column_letter(info.cols["hien"])
    row_to_class = {r: c for c, r in info.class_rows.items()}
    formula_cells = []
    for row in ws.iter_rows(min_row=info.total_row + 1, max_row=ws.max_row):
        for cell in row:
            v = cell.value
            if isinstance(v, str) and v.startswith("="):
                refs = _refs(v)
                classes = [row_to_class[r] for col, r in refs if col == hien and r in row_to_class]
                others = [(col, r) for col, r in refs if not (col == hien and r in row_to_class)]
                formula_cells.append((cell, classes, others))
    if not formula_cells:
        return MealLayout()

    def label_of(cell) -> str:
        nxt = ws.cell(cell.row, cell.column + 1).value
        return clean_spaces(nxt) if isinstance(nxt, str) else ""

    score: dict[int, int] = {}
    for cell, classes, others in formula_cells:
        if label_of(cell) and (classes or others):
            score[cell.column] = score.get(cell.column, 0) + 1
    if not score:
        return MealLayout()
    meal_col = max(score, key=lambda k: score[k])

    layout = MealLayout()
    used_rows: list[int] = []
    referenced: set[str] = set()
    for cell, classes, others in formula_cells:
        referenced.update(classes)
        if cell.column == meal_col and label_of(cell):
            mr = MealRow(cell.row, label_of(cell), cell.coordinate, classes)
            for col, r in others:
                sub = ws[f"{col}{r}"].value
                m = re.match(r"=\s*\$?([A-Z]{1,3})\$?(\d+)\s*-\s*\$?([A-Z]{1,3})\$?(\d+)\s*$", str(sub or "").upper())
                if m:
                    mr.o_cell, mr.m_cell = f"{m.group(1)}{m.group(2)}", f"{m.group(3)}{m.group(4)}"
                    mr.l_cell = f"{col}{r}"
                    break
            layout.rows.append(mr)
            used_rows.append(cell.row)
        elif classes:
            layout.self_classes.extend(c for c in classes if c not in layout.self_classes)
            layout.self_cell = layout.self_cell or cell.coordinate
            used_rows.append(cell.row)
    if not layout.rows:
        return MealLayout()
    meal_letter = get_column_letter(meal_col)
    sum_re = re.compile(rf"SUM\(\s*\$?{meal_letter}\$?\d+\s*:\s*\$?{meal_letter}\$?\d+\s*\)")
    for cell, _, _ in formula_cells:
        if cell.column != meal_col and sum_re.search(str(cell.value).upper()):
            layout.sum_cell = cell.coordinate
            used_rows.append(cell.row)
            break
    # ô tổng cộng (vd. G72 =G69+G70) cũng nằm trong vùng in
    for cell, classes, others in formula_cells if layout.sum_cell else []:
        refs = {f"{col}{r}" for col, r in others}
        if cell.column != meal_col and not classes and layout.sum_cell in refs:
            layout.total_cell = cell.coordinate
            used_rows.append(cell.row)
            rest = sorted(refs - {layout.sum_cell})
            if layout.self_cell is None and len(rest) == 1:  # ô ăn tại lớp đang =0 (không lớp nào)
                layout.self_cell = rest[0]
                used_rows.append(int(re.search(r"\d+", rest[0]).group()))
            break
    if any(r.code for r in layout.rows):
        layout.ghep_classes = [c for c in info.class_rows if c not in referenced]
    for mr in layout.rows:
        if mr.code and mr.o_cell:
            v = ws[mr.o_cell].value
            layout.o_values[mr.code] = int(v) if isinstance(v, (int, float)) else 0

    # Vùng in: khung bao các ô có nội dung từ hàng tiêu đề "Suất ăn" tới hàng cuối của bảng
    r1, r2 = min(used_rows) - 1, max(used_rows)
    cmin, cmax = 10**6, 0
    for row in ws.iter_rows(min_row=r1, max_row=r2):
        for cell in row:
            if cell.value not in (None, ""):
                cmin, cmax = min(cmin, cell.column), max(cmax, cell.column)
    if cmax:
        layout.area = f"{get_column_letter(cmin)}{r1}:{get_column_letter(cmax)}{r2}"
    return layout


# ---------------------------------------------------------------- dựng lại bảng suất ăn
class MealTableError(Exception):
    """Không dựng lại được bảng suất ăn (sổ thiếu chỗ/ô cần thiết): giữ nguyên bảng cũ."""


def _ghep_cols(old: MealLayout, meal_col: int) -> tuple[str, str, str]:
    """Cột L (=O-M), M (số em ghép vắng), O (số em ghép): lấy theo dòng ghép có sẵn trong sổ."""
    for r in old.rows:
        if r.l_cell and r.m_cell and r.o_cell:
            col = lambda a: re.match(r"[A-Z]+", a).group()  # noqa: E731
            return col(r.l_cell), col(r.m_cell), col(r.o_cell)
    return tuple(get_column_letter(meal_col + k) for k in (3, 4, 6))  # như sổ mẫu: I -> L, M, O


def _strip_blanks(groups: list[MealGroup]) -> list[MealGroup]:
    gs = list(groups)
    while gs and gs[0].blank:
        gs.pop(0)
    while gs and gs[-1].blank:
        gs.pop()
    return gs


def plan_meal_table(info: SheetInfo, groups: list[MealGroup], split: set[str], o_counts: dict[str, int]) -> MealLayout:
    """Bảng suất ăn sẽ có nếu dựng theo bảng Nhóm ăn (chưa ghi gì vào sổ).

    Bắt đầu ở dòng đầu bảng cũ; mỗi nhóm một dòng, dòng trống giữ cách dòng. Lớp không thuộc nhóm nào
    và không chia em ghép lẻ (`split`) thì ăn tại lớp. `o_counts`: mã ghép lẻ -> số em ghép.
    """
    old = info.meal
    if old.is_empty:
        raise MealTableError("Sổ chưa có bảng suất ăn để làm mẫu.")
    meal_col = column_index_from_string(re.match(r"[A-Z]+", old.rows[0].meal_cell).group())
    letter = get_column_letter(meal_col)
    lc, mc, oc = _ghep_cols(old, meal_col)
    first = min(r.row for r in old.rows)
    gs = _strip_blanks(groups)
    rows: list[MealRow] = []
    for i, g in enumerate(gs):
        if g.blank:
            continue
        r = first + i
        mr = MealRow(r, g.label, f"{letter}{r}", [c for c in g.classes if c in info.class_rows])
        if g.code:
            mr.o_cell, mr.m_cell, mr.l_cell = f"{oc}{r}", f"{mc}{r}", f"{lc}{r}"
        rows.append(mr)
    grouped = {c for g in gs for c in g.classes}
    codes = [r.code for r in rows if r.code]
    ghep = [c for c in info.class_rows if c in split and c not in grouped] if codes else []
    layout = MealLayout(rows, [c for c in info.class_rows if c not in grouped and c not in ghep], ghep)
    layout.o_values = {c: o_counts.get(c, 0) for c in codes}
    layout.sum_cell, layout.self_cell, layout.total_cell = old.sum_cell, old.self_cell, old.total_cell
    m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", old.area or "")
    if m:  # vùng in: như bảng cũ, kéo tới dòng cuối của bảng mới (và các ô tổng nằm dưới bảng, nếu có)
        old_end, old_last = int(m.group(4)), max(x.row for x in old.rows)
        tail = [old_end] if old_end > old_last else []
        summary = [int(re.search(r"\d+", a).group()) for a in (old.sum_cell, old.self_cell, old.total_cell) if a]
        layout.area = f"{m.group(1)}{m.group(2)}:{m.group(3)}{max([r.row for r in rows] + summary + tail)}"
    return layout


def write_meal_table(ws: Worksheet, info: SheetInfo, plan: MealLayout) -> None:
    """Ghi bảng suất ăn `plan` (từ plan_meal_table) vào sheet, thay bảng cũ. Giữ kiểu chữ của sổ."""
    old = info.meal
    hien = get_column_letter(info.cols["hien"])
    meal_col = column_index_from_string(re.match(r"[A-Z]+", old.rows[0].meal_cell).group())
    letter, label_letter = get_column_letter(meal_col), get_column_letter(meal_col + 1)
    lc, mc, oc = _ghep_cols(old, meal_col)
    span = range(meal_col, max(meal_col + 1, column_index_from_string(oc)) + 1)
    first, old_last = min(r.row for r in old.rows), max(r.row for r in old.rows)
    new_rows = {r.row: r for r in plan.rows}
    last = max(new_rows) if new_rows else first
    if plan.self_classes and not old.self_cell:
        raise MealTableError("Sổ không có ô cộng các lớp ăn tại lớp.")
    for r in range(old_last + 1, last + 1):  # dòng thêm mới phải còn trống
        for c in span:
            if ws.cell(r, c).value not in (None, ""):
                raise MealTableError(f"Bảng suất ăn cần thêm dòng nhưng ô {ws.cell(r, c).coordinate} đang có dữ liệu.")

    ref_plain = next((r.row for r in old.rows if not r.o_cell), old.rows[0].row)
    ref_ghep = next((r.row for r in old.rows if r.o_cell), ref_plain)
    styles = {ref: [copy(ws.cell(ref, c)._style) for c in span] for ref in {ref_plain, ref_ghep}}
    heights = {ref: ws.row_dimensions[ref].height for ref in styles}
    gaps = [r for r in range(first, old_last) if r not in {x.row for x in old.rows}]
    gap_h = ws.row_dimensions[gaps[0]].height if gaps else None
    m_idx = column_index_from_string(mc)
    old_m = {x.m_cell for x in old.rows if x.m_cell}
    headers = [(r, ws.cell(r, m_idx).value) for r in range(first - 1, old_last + 1)
               if isinstance(ws.cell(r, m_idx).value, str) and not _is_formula(ws.cell(r, m_idx).value)
               and f"{mc}{r}" not in old_m]  # chữ "vắng" trên cột M

    for x in old.rows:  # xóa bảng cũ (giữ định dạng)
        for a in (x.meal_cell, f"{label_letter}{x.row}", x.o_cell, x.m_cell, x.l_cell):
            if a:
                ws[a].value = None
    for r in range(first, last + 1):
        mr = new_rows.get(r)
        if mr is None:  # dòng trống cách nhóm
            ws[f"{letter}{r}"].value = ws[f"{label_letter}{r}"].value = None
            if gap_h:
                ws.row_dimensions[r].height = gap_h
            continue
        ref = ref_ghep if mr.o_cell else ref_plain
        for c, st in zip(span, styles[ref], strict=True):
            ws.cell(r, c)._style = copy(st)
        if heights[ref]:
            ws.row_dimensions[r].height = heights[ref]
        terms = [f"{hien}{info.class_rows[c]}" for c in mr.classes]
        if mr.o_cell:
            terms.append(mr.l_cell)
            ws[mr.l_cell] = f"={oc}{r}-{mc}{r}"
            ws[mr.o_cell] = plan.o_values.get(mr.code or "", 0)
            ws[mr.m_cell] = None
        ws[f"{letter}{r}"] = "=" + "+".join(terms) if terms else "=0"
        ws[f"{label_letter}{r}"] = mr.label
    ghep_rows = sorted(r.row for r in plan.rows if r.o_cell)
    for r, text in headers:  # chữ "vắng": giữ chỗ cũ; bị dòng ghép đè thì dời lên trên dòng ghép đầu tiên
        if not ghep_rows:
            ws.cell(r, m_idx).value = None
        elif r in ghep_rows:
            up = ghep_rows[0] - 1
            if up not in ghep_rows and ws.cell(up, m_idx).value in (None, ""):
                ws.cell(up, m_idx).value = text
        else:
            ws.cell(r, m_idx).value = text
    if old.sum_cell:
        ws[old.sum_cell] = f"=SUM({letter}{first}:{letter}{last})"
    if old.self_cell:
        cells = [f"{hien}{info.class_rows[c]}" for c in plan.self_classes]
        ws[old.self_cell] = "=" + "+".join(cells) if cells else "=0"


# ---------------------------------------------------------------- đọc
def day_sheets(wb) -> dict[int, Worksheet]:
    out = {}
    for ws in wb.worksheets:
        t = ws.title.strip()
        if t.isdigit() and 1 <= int(t) <= 31:
            out[int(t)] = ws
    return out


def sheet_date(ws: Worksheet) -> dt.date | None:
    info = analyze(ws)
    if info and info.title_cell:
        m = _TITLE_DATE.search(str(ws[info.title_cell].value))
        if m:
            try:
                return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                return None
    return None


def book_month(wb, path: str | Path | None = None) -> tuple[int, int] | None:
    """(tháng, năm) của sổ, đọc từ tiêu đề sheet ngày; dự phòng: tên file 'T10'."""
    for _, ws in sorted(day_sheets(wb).items(), reverse=True):
        d = sheet_date(ws)
        if d:
            return d.month, d.year
    if path:
        m = re.search(r"T(\d{1,2})(?!\d)", Path(path).stem, re.IGNORECASE)
        if m:
            return int(m.group(1)), dt.date.today().year
    return None


def read_records(info: SheetInfo) -> dict[str, ClassRecord]:
    out = {}
    for code, r in info.class_rows.items():
        vals = {k: info.ws.cell(r, c).value for k, c in info.cols.items()}
        si, vang = vals.get("siso"), vals.get("vang")
        out[code] = ClassRecord(
            code,
            clean_spaces(str(vals.get("gvcn") or "")),
            int(si) if isinstance(si, (int, float)) else None,
            int(vang) if isinstance(vang, (int, float)) else None,
            clean_spaces(str(vals.get("ten") or "")),
            clean_spaces(str(vals.get("ghichu") or "")),
        )
    return out


def template_sheet(wb, day: dt.date) -> Worksheet | None:
    """Sheet gần nhất trước ngày `day` (hoặc sheet cuối cùng) để làm mẫu."""
    sheets = day_sheets(wb)
    before = [d for d in sheets if d < day.day]
    pick = max(before) if before else (max(sheets) if sheets else None)
    if pick is not None:
        return sheets[pick]
    for ws in reversed(wb.worksheets):
        if analyze(ws):
            return ws
    return None


# ---------------------------------------------------------------- ghi
def create_day_sheet(wb, day: dt.date, template: Worksheet) -> Worksheet:
    """Sao chép sheet mẫu thành sheet ngày mới, xóa số liệu cũ (giữ ghi chú, chữ ký)."""
    new = wb.copy_worksheet(template)
    new.title = str(day.day)
    new.sheet_view.zoomScale = template.sheet_view.zoomScale
    if template.freeze_panes:
        new.freeze_panes = template.freeze_panes
    # đặt đúng thứ tự ngày
    wb._sheets.remove(new)
    sheets = day_sheets(wb)
    idx = len(wb._sheets)
    after = [d for d in sheets if d > day.day]
    if after:
        idx = wb._sheets.index(sheets[min(after)])
    wb._sheets.insert(idx, new)

    info = analyze(new)
    if info:
        for code in info.class_rows:
            ten = info.cell(code, "ten")
            ten.value = None
            if ten.font is not None and ten.font.color is not None:  # bỏ chữ màu của sổ hôm trước: tên vắng chữ đen
                f = copy(ten.font)
                f.color = None
                ten.font = f
            vang = info.cell(code, "vang")
            if not _is_formula(vang.value):  # cột Vắng là công thức đếm tên thì giữ nguyên
                vang.value = 0
        for mr in info.meal.rows:
            if mr.m_cell:
                new[mr.m_cell].value = None
        set_dates(info, day)
    return new


def _is_formula(v) -> bool:
    return isinstance(v, str) and v.startswith("=")


def set_dates(info: SheetInfo, day: dt.date) -> None:
    ws = info.ws
    if info.title_cell:
        ws[info.title_cell].value = _TITLE_DATE.sub(fmt_date(day), str(ws[info.title_cell].value), count=1)
    if info.sign_cell:
        v = str(ws[info.sign_cell].value)
        v = re.sub(r"(tháng\s+)\d{1,2}", rf"\g<1>{day.month}", v, count=1)
        v = re.sub(r"(năm\s+)\d{4}", rf"\g<1>{day.year}", v, count=1)
        ws[info.sign_cell].value = v


def write_day(info: SheetInfo, state: DayState, summary: MealSummary | None) -> None:
    for code in info.class_rows:
        if code not in state.classes:
            continue
        names = state.absent_names(code)
        info.cell(code, "siso").value = state.si_so(code)
        vang = info.cell(code, "vang")
        if not _is_formula(vang.value):  # sổ có công thức đếm tên ở cột Vắng thì để Excel tự đếm
            vang.value = len(names)
        info.cell(code, "ten").value = ", ".join(names) if names else None
        note = state.cd(code).note
        info.cell(code, "ghichu").value = note or None
    if summary:
        for line in summary.lines:
            if line.row.o_cell and line.o is not None:
                info.ws[line.row.o_cell].value = line.o
            if line.row.m_cell:
                info.ws[line.row.m_cell].value = line.m or None


def select_only(wb, ws: Worksheet) -> None:
    """Chỉ chọn 1 sheet khi mở file (tránh Excel mở ở chế độ nhóm nhiều sheet)."""
    for s in wb.worksheets:
        s.sheet_view.tabSelected = s is ws
    wb.active = wb.worksheets.index(ws)


def load_book(path: str | Path):
    return openpyxl.load_workbook(str(path))


def month_file_name(prev: Path, month: int) -> Path:
    stem = prev.stem
    if re.search(r"T\d{1,2}(?!\d)", stem):
        idx = [m for m in re.finditer(r"T\d{1,2}(?!\d)", stem)][-1]
        stem = stem[: idx.start()] + f"T{month}" + stem[idx.end():]
    else:
        stem = f"{stem} T{month}"
    return prev.with_name(stem + prev.suffix)


def new_month_book(prev_path: str | Path, day: dt.date, new_path: str | Path) -> None:
    """Tạo sổ tháng mới từ sheet cuối của sổ tháng trước."""
    wb = load_book(prev_path)
    sheets = day_sheets(wb)
    tpl = sheets[max(sheets)] if sheets else template_sheet(wb, day)
    if tpl is None:
        raise ValueError("Sổ tháng trước không có sheet điểm danh nào để làm mẫu.")
    for ws in list(wb.worksheets):
        if ws is not tpl:
            wb.remove(ws)
    tpl.title = str(day.day)
    info = analyze(tpl)
    if info:
        for code in info.class_rows:
            info.cell(code, "ten").value = None
            info.cell(code, "vang").value = 0
        for mr in info.meal.rows:
            if mr.m_cell:
                tpl[mr.m_cell].value = None
        set_dates(info, day)
    select_only(wb, tpl)
    safe_save(wb, new_path)


def find_month_file(folder: str | Path, month: int, year: int | None = None) -> Path | None:
    folder = Path(folder)
    if not folder.is_dir():
        return None
    cands = []
    for p in folder.glob("*.xlsx"):
        if p.name.startswith(("~$", ".")) or p.stem.lower().endswith("tamthoi"):
            continue
        if re.search(rf"T0?{month}(?!\d)", p.stem, re.IGNORECASE):
            cands.append(p)
    if not cands:
        return None
    if year and len(cands) > 1:
        for p in cands:
            try:
                wb = openpyxl.load_workbook(str(p), read_only=False)
                bm = book_month(wb, p)
                if bm and bm == (month, year):
                    return p
            except Exception:  # noqa: BLE001 - file hỏng thì bỏ qua
                continue
    return sorted(cands, key=lambda p: p.stat().st_mtime)[-1]
