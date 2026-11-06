"""Xuất danh sách học sinh dạng đơn giản: Lớp | Họ và tên | Ngày sinh | Ăn bán trú (có/không).

Một sheet, không cố định dòng, không lọc. File xuất ra nhập lại được vào app (Cài đặt → Nhập danh sách).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from ..core.models import Roster
from ..core.text import class_sort_key
from .files import safe_save

HEADERS = [("Lớp", 8), ("Họ và tên", 32), ("Ngày sinh", 13), ("Ăn bán trú", 12)]


def export_roster(roster: Roster, path: str | Path, as_of: dt.date, backup: bool = True) -> int:
    """Ghi danh sách tính theo ngày `as_of` ("có" = ăn bán trú ngày đó). Trả về số em ăn bán trú."""
    pos = {s.id: i for i, s in enumerate(roster.students)}
    students = sorted(roster.students, key=lambda s: (class_sort_key(s.lop), pos[s.id]))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sách"
    ws.append([t for t, _ in HEADERS])
    for i, (_, w) in enumerate(HEADERS, 1):
        cell = ws.cell(1, i)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    n = 0
    center = Alignment(horizontal="center")
    for s in students:
        eats = s.is_boarding(as_of)
        n += eats
        ws.append([s.lop, s.ho_ten, s.ngay_sinh, "có" if eats else "không"])
        for c in (1, 3, 4):
            ws.cell(ws.max_row, c).alignment = center
    if backup:
        safe_save(wb, path)
    else:
        wb.save(str(path))
    return n
