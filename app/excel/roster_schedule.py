"""Ghi lịch bán trú của một em vào file danh sách học sinh, khi giáo vụ bấm Lưu lịch (trang Học sinh).

Chỉ sửa 3 ô của đúng dòng em đó: "Ăn từ" (ngày bắt đầu ăn), "Cắt từ" (ngày thôi ăn), "Cắt thứ 6" (x).
File chưa có cột nào thì thêm cột đó vào cuối bảng (tên cột: config.SCHEDULE_COLUMNS). Phần còn lại giữ nguyên.
File .xls (Excel 97-2003) không ghi được: báo giáo vụ lưu lại thành .xlsx.
"""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

from .. import config
from .files import safe_save
from .roster_import import SCHEDULE_HEADERS, find_table, is_xls, student_ids, xlsx_rows


class ScheduleError(Exception):
    """Không ghi được lịch (giải thích cho giáo vụ)."""


def _add_column(ws, hr: int, title: str) -> int:
    """Thêm cột tiêu đề `title` sau cột cuối của dòng tiêu đề; trả về chỉ số cột (0-based)."""
    last = max(c.column for c in ws[hr] if c.value is not None)
    cell, prev = ws.cell(hr, last + 1, title), ws.cell(hr, last)
    cell.font, cell.fill, cell.border, cell.alignment = (copy.copy(x) for x in (prev.font, prev.fill, prev.border, prev.alignment))
    ws.column_dimensions[get_column_letter(last + 1)].width = max(len(title) + 4, 12)
    return last  # 0-based


def save_schedule(path: str | Path, sid: str, bt_tu: dt.date | None, cat_tu: dt.date | None, cat_thu6: bool) -> None:
    path = Path(path)
    if is_xls(path):
        raise ScheduleError("File danh sách là dạng Excel cũ (.xls) nên app không ghi được. Mở file bằng Excel, "
                            "Lưu thành (Save As) dạng .xlsx, rồi vào Cài đặt chọn lại file.")
    wb = openpyxl.load_workbook(path)
    ws, hr, cols = find_table(wb)
    rows = xlsx_rows(ws, hr, cols)
    r = next((r for (r, _), s in zip(rows, student_ids([row for _, row in rows]), strict=True) if s == sid), None)
    if r is None:
        raise ScheduleError("Không thấy em này trong file danh sách (file vừa được sửa?). Mở lại trang Học sinh rồi thử lại.")
    for key, title in zip(SCHEDULE_HEADERS, config.SCHEDULE_COLUMNS, strict=True):
        if key not in cols:
            cols[key] = _add_column(ws, hr, title)
    for key, value in (("bttu", bt_tu), ("cattu", cat_tu), ("t6", config.SCHEDULE_MARK if cat_thu6 else None)):
        cell = ws.cell(r, cols[key] + 1)
        cell.value = value  # (ws.cell(r, c, None) không xóa được ô)
        if isinstance(value, dt.date):
            cell.number_format = config.EXCEL_DATE_FORMAT
    safe_save(wb, path)
