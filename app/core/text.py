"""Xử lý chữ tiếng Việt: chuẩn hóa, bỏ dấu, tách từ, mã lớp, ngày tháng."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

_WS = re.compile(r"\s+")

# Mã lớp kiểu 1D15, 5d22, "3 D 19". Không ăn vào số dính liền phía trước/sau.
CLASS_RE = re.compile(r"(?<![0-9A-Za-z])([1-5])\s*[DdĐđ]\s*(\d{2})(?!\d)")


def nfc(s: str | None) -> str:
    return unicodedata.normalize("NFC", s or "")


def clean_spaces(s: str | None) -> str:
    return _WS.sub(" ", nfc(s)).strip()


def lower(s: str | None) -> str:
    return clean_spaces(s).lower()


def fold(s: str | None) -> str:
    """Chữ thường, bỏ dấu, đ -> d. Dùng để so khớp khi gõ thiếu dấu."""
    s = unicodedata.normalize("NFD", lower(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d")


def words(s: str | None) -> list[str]:
    s = clean_spaces(s)
    return s.split(" ") if s else []


def title_words(s: str | None) -> str:
    """Viết hoa chữ đầu mỗi từ: 'đại quang' -> 'Đại Quang'."""
    return " ".join(w[:1].upper() + w[1:] for w in words(s))


def norm_class(code: str | None) -> str:
    """'Lớp 1d15' -> '1D15'; trả về '' nếu không phải mã lớp."""
    m = CLASS_RE.search(nfc(code))
    return f"{m.group(1)}D{m.group(2)}" if m else ""


def class_sort_key(code: str) -> tuple[int, int]:
    try:
        return int(code[0]), int(code[2:])
    except (ValueError, IndexError):
        return 9, 99


def parse_date(value) -> dt.date | None:
    """Đọc ngày dạng dd/mm/yyyy, dd-mm-yyyy hoặc kiểu ngày của Excel."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    m = re.search(r"(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{2,4})", str(value))
    if not m:
        return None
    d, mth, y = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    try:
        return dt.date(y, mth, d)
    except ValueError:
        return None


def fmt_date(d: dt.date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def letter_label(i: int) -> str:
    """0 -> A, 1 -> B, ... 25 -> Z, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
