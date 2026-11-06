"""Lọc tên trong ô tìm (không cần gõ dấu)."""

from __future__ import annotations

from .text import fold


def matches(query: str, text: str) -> bool:
    """Mỗi từ gõ vào phải là đầu của một chữ trong `text`: "long", "hai long", "h long" đều khớp "Nguyễn Hải Long".

    Ô tìm trống thì khớp tất cả."""
    words = fold(text).split()
    return all(any(w.startswith(t) for w in words) for t in fold(query).split())
