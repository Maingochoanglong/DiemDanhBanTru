"""Đọc file Excel danh sách học sinh (.xls hoặc .xlsx) — nguồn duy nhất về học sinh của app (app chỉ đọc, không ghi).

Hai dạng file:
- file danh sách học sinh toàn trường: em tô chữ đỏ là ăn bán trú;
- file danh sách bán trú gọn: cột "Ăn bán trú" đánh X hoặc có/không, có thể kèm cột "Ghép lớp" (vd. 1.2),
  cột "Tên gọi khác" (tên GV hay báo, vd. "Mi Mi"; tên đầu được ghi vào sổ)
  và cột "Ghi chú" (vd. "cắt thứ 6", "cắt từ 30/10", "ăn từ 3/11": xem core/notes.py).

File gọn có thể có thêm sheet "Nhóm ăn": mỗi dòng là một dòng bảng suất ăn trong sổ
(Tên dòng | Các lớp ăn chung | Mã ghép lẻ). App dựng bảng suất ăn của tờ ngày mới theo sheet này.

Hàm chính: load_list(path) -> ListData.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.meals import CODE_RE, MealGroup
from ..core.models import ClassInfo, Roster, Student
from ..core.notes import student_note
from ..core.text import class_sort_key, clean_spaces, fmt_date, fold, norm_class, parse_date


@dataclass
class RosterRow:
    lop: str
    ho_ten: str
    ngay_sinh: str
    red: bool  # ăn bán trú (chữ đỏ hoặc X)
    ghep: str | None = None  # None = file không có cột "Ghép lớp"
    ten_goi: str | None = None  # None = file không có cột "Tên gọi khác"
    ghi_chu: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return fold(self.ho_ten), self.ngay_sinh


class RosterFormatError(Exception):
    pass


def _is_red_rgb(r: int, g: int, b: int) -> bool:
    return r >= 180 and g <= 100 and b <= 100


def _find_columns(header: list[str]) -> dict[str, int] | None:
    cols: dict[str, int] = {}
    for i, h in enumerate(header):
        f = fold(str(h or ""))
        if "lop" not in cols and ("ten lop" in f or f in ("lop", "lop hoc")):
            cols["lop"] = i
        elif f in ("ho ten", "ho va ten", "ho ten hoc sinh", "ho va ten hoc sinh") and "ten" not in cols:
            cols["ten"] = i
        elif (f.startswith("ngay sinh") or (f.startswith("ngay") and f.endswith("sinh"))) and "ns" not in cols:
            # "Ngày sinh", "Ngày tháng năm sinh"
            cols["ns"] = i
        elif f.startswith("ghi chu") and "gc" not in cols:
            cols["gc"] = i
        elif (f.startswith(("an ban tru", "ban tru")) or f in ("bt", "an bt")) and "bt" not in cols:
            # cột đánh X; không nhận nhầm cột "Loại bán trú" (ghi "Thường") của file danh sách học sinh toàn trường
            cols["bt"] = i
        elif "ghep" in f and "ghep" not in cols:
            cols["ghep"] = i
        elif ("ten goi" in f or "biet danh" in f or f.startswith("ten ghi so")) and "goi" not in cols:
            cols["goi"] = i
    if "lop" in cols and "ten" in cols:
        return cols
    return None


def _is_x(v) -> bool:
    return fold(str(v or "")) in ("x", "co", "1", "v", "ban tru", "true")


def _fmt_ghep(v) -> str:
    t = clean_spaces(str(v if v is not None else "")).replace(",", ".")
    if isinstance(v, float):
        t = f"{v:.1f}"
    return t


def _fmt_dob(v) -> str:
    d = parse_date(v)
    return fmt_date(d) if d else clean_spaces(str(v or ""))


def _read_xls(path: Path) -> list[RosterRow]:
    import xlrd

    book = xlrd.open_workbook(str(path), formatting_info=True)
    for sh in book.sheets():
        for hr in range(min(10, sh.nrows)):
            cols = _find_columns([str(v) for v in sh.row_values(hr)])
            if not cols:
                continue
            rows = []
            for r in range(hr + 1, sh.nrows):
                name = clean_spaces(str(sh.cell_value(r, cols["ten"])))
                lop = norm_class(str(sh.cell_value(r, cols["lop"])))
                if not name or not lop:
                    continue
                font_idx = book.xf_list[sh.cell_xf_index(r, cols["ten"])].font_index
                runs = sh.rich_text_runlist_map.get((r, cols["ten"]))
                if runs and runs[0][0] == 0:
                    font_idx = runs[0][1]
                rgb = book.colour_map.get(book.font_list[font_idx].colour_index)
                red = bool(rgb) and _is_red_rgb(*rgb)
                dob = ""
                if "ns" in cols:
                    cell = sh.cell(r, cols["ns"])
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        dob = fmt_date(xlrd.xldate_as_datetime(cell.value, book.datemode).date())
                    else:
                        dob = _fmt_dob(cell.value)
                if "bt" in cols:
                    red = _is_x(sh.cell_value(r, cols["bt"]))
                ghep = _fmt_ghep(sh.cell_value(r, cols["ghep"])) if "ghep" in cols else None
                goi = clean_spaces(str(sh.cell_value(r, cols["goi"]))) if "goi" in cols else None
                gc = clean_spaces(str(sh.cell_value(r, cols["gc"]))) if "gc" in cols else ""
                rows.append(RosterRow(lop, name, dob, red, ghep, goi, gc))
            return rows
    raise RosterFormatError("Không tìm thấy cột 'Tên lớp học' và 'Họ tên' trong file.")


def _openpyxl_red(cell) -> bool:
    from openpyxl.styles.colors import COLOR_INDEX

    color = cell.font.color if cell.font else None
    if color is None:
        return False
    hexv = None
    if color.type == "rgb" and isinstance(color.rgb, str):
        hexv = color.rgb[-6:]
    elif color.type == "indexed" and color.indexed is not None and color.indexed < len(COLOR_INDEX):
        hexv = COLOR_INDEX[color.indexed][-6:]
    if not hexv:
        return False
    try:
        return _is_red_rgb(int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16))
    except ValueError:
        return False


def _read_xlsx(path: Path) -> list[RosterRow]:
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True)
    for ws in wb.worksheets:
        for hr in range(1, min(10, ws.max_row) + 1):
            header = [c.value for c in ws[hr]]
            cols = _find_columns([str(v) if v is not None else "" for v in header])
            if not cols:
                continue
            rows = []
            for r in range(hr + 1, ws.max_row + 1):
                name_cell = ws.cell(r, cols["ten"] + 1)
                name = clean_spaces(str(name_cell.value or ""))
                lop = norm_class(str(ws.cell(r, cols["lop"] + 1).value or ""))
                if not name or not lop:
                    continue
                dob = ""
                if "ns" in cols:
                    dob = _fmt_dob(ws.cell(r, cols["ns"] + 1).value)
                red = _is_x(ws.cell(r, cols["bt"] + 1).value) if "bt" in cols else _openpyxl_red(name_cell)
                ghep = _fmt_ghep(ws.cell(r, cols["ghep"] + 1).value) if "ghep" in cols else None
                goi = clean_spaces(str(ws.cell(r, cols["goi"] + 1).value or "")) if "goi" in cols else None
                gc = clean_spaces(str(ws.cell(r, cols["gc"] + 1).value or "")) if "gc" in cols else ""
                rows.append(RosterRow(lop, name, dob, red, ghep, goi, gc))
            return rows
    raise RosterFormatError("Không tìm thấy cột 'Tên lớp học' và 'Họ tên' trong file.")


def read_cdhs(path: str | Path) -> list[RosterRow]:
    """Đọc theo nội dung file (file .xls cũ đặt đuôi .xlsx vẫn đọc được)."""
    path = Path(path)
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(b"\xd0\xcf\x11\xe0"):  # định dạng Excel 97-2003 (.xls)
        return _read_xls(path)
    return _read_xlsx(path)


# ---------------- sheet "Nhóm ăn" ----------------
def _is_xls(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(8).startswith(b"\xd0\xcf\x11\xe0")


def read_meal_groups(path: str | Path) -> list[tuple[int, str, str, str]] | None:
    """Sheet "Nhóm ăn" của file danh sách: (số dòng, tên dòng, các lớp, mã ghép lẻ). None = không có sheet này."""
    path = Path(path)
    if _is_xls(path):
        return None
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = next((w for w in wb.worksheets if fold(w.title).replace(" ", "") == "nhoman"), None)
    if ws is None:
        return None
    hr, cols = 1, {"label": 0, "classes": 1, "code": 2}
    for r in range(1, min(5, ws.max_row) + 1):
        vals = [fold(str(c.value or "")) for c in ws[r]]
        if any("ten dong" in v for v in vals):
            hr = r
            for i, v in enumerate(vals[:6]):
                if "ten dong" in v:
                    cols["label"] = i
                elif "lop" in v:
                    cols["classes"] = i
                elif v.startswith("ma") or "ghep le" in v:
                    cols["code"] = i
            break
    out = []
    for r in range(hr + 1, ws.max_row + 1):
        label, classes = (clean_spaces(str(ws.cell(r, cols[k] + 1).value or "")) for k in ("label", "classes"))
        code = _fmt_ghep(ws.cell(r, cols["code"] + 1).value)
        out.append((r, label, classes, "" if code in ("", "None") else code))
    while out and not any(out[-1][1:]):
        out.pop()
    return out


def check_meal_groups(raw: list[tuple[int, str, str, str]], class_codes: list[str],
                      kid_codes: dict[str, set[str]]) -> tuple[list[MealGroup], list[str], list[str]]:
    """Kiểm tra bảng Nhóm ăn. class_codes: các lớp trong danh sách; kid_codes: lớp -> mã Ăn ghép của các em ăn BT.
    Trả về (các dòng, lỗi, lưu ý). Có lỗi thì không dùng bảng này."""
    short = {v: k for k, v in short_codes(class_codes).items()}  # "1.2" -> "1D16"
    groups: list[MealGroup] = []
    errors: list[str] = []
    where: dict[str, str] = {}
    codes: dict[str, str] = {}
    for r, label, cls_text, code in raw:
        if not (label or cls_text or code):
            groups.append(MealGroup(""))  # dòng trống: cách dòng trong bảng suất ăn
            continue
        name = f"dòng {r}" + (f" ({label})" if label else "")
        classes = []
        for tok in re.split(r"[,;+\s]+", cls_text):
            if not tok:
                continue
            c = short.get(tok) or norm_class(tok)
            if c not in class_codes:
                errors.append(f"Nhóm ăn, {name}: danh sách không có lớp \"{tok}\".")
            elif c in where:
                errors.append(f"Nhóm ăn: lớp {c} nằm ở 2 dòng, {where[c]} và {name}.")
            else:
                where[c] = name
                classes.append(c)
        if code:
            m = CODE_RE.search(label)
            if not re.fullmatch(r"\d\.\d", code):
                errors.append(f"Nhóm ăn, {name}: mã ghép lẻ \"{code}\" phải dạng số.số, vd. 1.2.")
            elif code in codes:
                errors.append(f"Nhóm ăn: mã ghép lẻ {code} ở 2 dòng, {codes[code]} và {name}.")
            elif m and f"{m.group(1)}.{m.group(2)}" != code:
                errors.append(f"Nhóm ăn, {name}: tên dòng phải bắt đầu bằng mã ghép lẻ {code} (vd. \"{code} ghép\").")
            else:
                codes[code] = name
                label = label if m else f"{code} {label}".strip()
        if not label:
            errors.append(f"Nhóm ăn, {name}: chưa có tên dòng.")
        elif not classes and not code:
            errors.append(f"Nhóm ăn, {name}: chưa có lớp nào.")
        groups.append(MealGroup(label, classes, code))
    while groups and groups[-1].blank:
        groups.pop()
    warnings = []
    for c in sorted(kid_codes):
        kc = kid_codes[c]
        if c in where and kc:
            warnings.append(f"Lớp {c} đã ăn cả lớp ở {where[c]} nên cột Ăn ghép của các em lớp này không dùng.")
        elif c not in where and kc - set(codes):
            warnings.append(f"Lớp {c} có em ghi Ăn ghép {', '.join(sorted(kc - set(codes)))} "
                            "nhưng bảng Nhóm ăn không có mã ghép lẻ này: các em đó tính ăn tại lớp.")
    if not any(not g.blank for g in groups):
        warnings.append("Sheet Nhóm ăn chưa có dòng nào nên app chưa dùng.")
    return groups, errors, warnings


def short_codes(codes: list[str]) -> dict[str, str]:
    """Mã ngắn theo thứ tự trong khối: 1D15 -> 1.1, 1D16 -> 1.2…"""
    out: dict[str, str] = {}
    by_khoi: dict[str, list[str]] = {}
    for c in sorted(codes, key=class_sort_key):
        by_khoi.setdefault(c[0], []).append(c)
    for k, lst in by_khoi.items():
        for i, c in enumerate(lst, 1):
            out[c] = f"{k}.{i}"
    return out


# ---------------- đọc cả file cho app ----------------
@dataclass
class ListData:
    roster: Roster
    meal_groups: list[MealGroup] | None = None  # sheet Nhóm ăn (None = không có / có lỗi: giữ bảng suất ăn của sổ)
    meal_errors: list[str] = field(default_factory=list)
    meal_warnings: list[str] = field(default_factory=list)


def _student(row: RosterRow, sid: str, today: dt.date) -> Student:
    s = Student(sid, row.lop, row.ho_ten, row.ngay_sinh, ban_tru=row.red, ten_ghi_so=row.ten_goi or "",
                an_ghep=row.ghep or "", ghi_chu=row.ghi_chu)
    for key, value in student_note(row.ghi_chu, today).items():  # "cắt thứ 6", "cắt từ 30/10", "ăn từ 3/11"
        setattr(s, key, value)
    return s


def load_list(path: str | Path, today: dt.date | None = None) -> ListData:
    """Đọc file danh sách học sinh thành danh sách cho app. Mã học sinh = lớp|họ tên|ngày sinh
    (không đổi giữa các lần đọc, nên sổ tạm vẫn khớp khi file danh sách được sửa chỗ khác)."""
    today = today or dt.date.today()
    rows = read_cdhs(path)
    roster, seen = Roster(), set()
    for row in rows:
        sid = f"{row.lop}|{row.ho_ten}|{row.ngay_sinh}"
        n = 2
        while sid in seen:  # trùng cả lớp, họ tên, ngày sinh (hiếm)
            sid, n = f"{row.lop}|{row.ho_ten}|{row.ngay_sinh}|{n}", n + 1
        seen.add(sid)
        roster.students.append(_student(row, sid, today))
    codes = sorted({s.lop_tinh for s in roster.students if s.ban_tru}, key=class_sort_key)
    roster.classes = {c: ClassInfo(c, ma_ngan=ma) for c, ma in short_codes(codes).items()}
    data = ListData(roster)
    raw = read_meal_groups(path)
    if raw is not None:
        kid_codes: dict[str, set[str]] = {}
        for s in roster.students:
            if s.ban_tru and s.an_ghep:
                kid_codes.setdefault(s.lop_tinh, set()).add(s.an_ghep)
        groups, data.meal_errors, data.meal_warnings = check_meal_groups(raw, sorted({r.lop for r in rows}), kid_codes)
        if not data.meal_errors and any(not g.blank for g in groups):
            data.meal_groups = groups
    return data
