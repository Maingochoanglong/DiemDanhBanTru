"""Đọc cột "Ghi chú" của một em trong file danh sách học sinh.

Giáo vụ ghi ngắn, nhiều ý cách nhau dấu phẩy / chấm phẩy / xuống dòng; viết hoa hay không dấu đều được:
    cắt thứ 6                       -> cat_thu6 = True (thứ 6 tự tính vắng)
    cắt từ 30/10 | thôi ăn từ 30/10 | T11 cắt  -> cat_tu = ngày đó (từ ngày đó không ăn; "không ăn", "nghỉ ăn" cũng vậy)
    ăn từ 3/11 | thêm từ 3/11 | tháng 11 ăn BT   -> ban_tru = True, bt_tu = ngày đó
Chữ khác trong ô (vd. "dị ứng tôm") bỏ qua. Ngày không ghi năm: lấy theo năm học đang học (tháng 8 – tháng 7).
"""

from __future__ import annotations

import datetime as dt
import re

from .text import fold

_DATE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?")
_MONTH = re.compile(r"\b(?:thang|t)\s*(\d{1,2})\b")
_FRIDAY = re.compile(r"\b(?:thu\s*(?:6|sau)|t6)\b")


def _date(day: int, month: int, today: dt.date) -> dt.date | None:
    """Ngày trong năm học chứa `today` (năm học: tháng 8 năm nay tới tháng 7 năm sau)."""
    start = today.year if today.month >= 8 else today.year - 1
    year = start if month >= 8 else start + 1
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def _when(part: str, today: dt.date) -> dt.date | None:
    m = _DATE.search(part)
    if m and m.group(3):  # ghi đủ năm: 30/10/2026 hoặc 30/10/26
        year = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        try:
            return dt.date(year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    if m:
        return _date(int(m.group(1)), int(m.group(2)), today)
    m = _MONTH.search(part)
    return _date(1, int(m.group(1)), today) if m and 1 <= int(m.group(1)) <= 12 else None


def student_note(note: str, today: dt.date) -> dict:
    """Các trường của Student đọc được từ ghi chú (chỉ những gì ghi chú nói tới)."""
    out: dict = {}
    for part in re.split(r"[,;\n]", fold(note)):
        cut = re.search(r"\b(?:cat|thoi|nghi|khong)\b", part)  # cắt / thôi / nghỉ / không (ăn)
        if cut and _FRIDAY.search(part):
            out["cat_thu6"] = True
            continue
        day = _when(part, today)
        if cut and day:
            out["cat_tu"] = day
        elif re.search(r"\b(?:an|them)\b", part) and day:
            out["ban_tru"], out["bt_tu"] = True, day
    return out
