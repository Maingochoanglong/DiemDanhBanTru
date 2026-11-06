"""Kiểu trình bày đơn giản cho các file Excel app tự tạo (file dữ liệu, file danh sách xuất ra).

Chữ Times New Roman màu đen, viền mảnh đen, không tô nền, không cố định dòng, không lọc.
"""

from __future__ import annotations

from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

FONT_NAME = "Times New Roman"
_side = Side(style="thin", color="FF000000")
BORDER = Border(left=_side, right=_side, top=_side, bottom=_side)
FONT = Font(name=FONT_NAME, size=12, color="FF000000")
FONT_BOLD = Font(name=FONT_NAME, size=12, bold=True, color="FF000000")
HEAD_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(vertical="center")


def plain_sheet(ws, widths: list[int], center_cols: tuple[int, ...] = ()) -> None:
    """Định dạng cả sheet: dòng 1 là tiêu đề (đậm, giữa), các dòng sau chữ thường. Cột đếm từ 1."""
    ncol = len(widths)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=max(1, ws.max_row), max_col=ncol), 1):
        for c, cell in enumerate(row, 1):
            cell.border = BORDER
            if r == 1:
                cell.font = FONT_BOLD
                cell.alignment = HEAD_ALIGN
            else:
                cell.font = FONT
                cell.alignment = CENTER if c in center_cols else LEFT
    ws.freeze_panes = None
    ws.auto_filter.ref = None
