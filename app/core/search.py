"""Tìm học sinh theo tên gõ vào ô tìm (không cần gõ dấu, có thể gõ kèm mã lớp)."""

from __future__ import annotations

import datetime as dt
import re

from .models import Student
from .text import class_sort_key, fold

_CLASS = re.compile(r"^\d[a-z]\d{1,2}$")  # mã lớp đã bỏ dấu, viết thường: 1d15


def find_students(students: list[Student], query: str, day: dt.date | None = None, limit: int = 60) -> list[Student]:
    """Các em khớp với chữ gõ vào.

    - Mỗi từ gõ vào phải là đầu của một chữ trong họ tên: "long" khớp "Nguyễn Hải Long", "h long" cũng khớp.
    - Gõ mã lớp (vd. 1D15) thì chỉ tìm trong lớp đó; chỉ gõ mã lớp thì ra cả lớp.
    - Xếp trước: em ăn bán trú, em có tên (chữ cuối) khớp từ gõ cuối cùng, rồi theo lớp và tên.
    """
    tokens = fold(query).split()
    codes = {t.upper() for t in tokens if _CLASS.match(t)}
    words = [t for t in tokens if not _CLASS.match(t)]
    if not words and not codes:
        return []
    found = []
    for s in students:
        if codes and s.lop.upper() not in codes and s.lop_tinh.upper() not in codes:
            continue
        parts = fold(s.ho_ten).split()
        if not all(any(p.startswith(w) for p in parts) for w in words):
            continue
        given_first = 0 if (not words or (parts and parts[-1].startswith(words[-1]))) else 1
        found.append(((not s.is_boarding(day), given_first, class_sort_key(s.lop_tinh), fold(s.ho_ten)), s))
    found.sort(key=lambda x: x[0])
    return [s for _, s in found[:limit]]
