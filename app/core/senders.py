"""Đoán lớp theo tên Zalo của người gửi (khi tin không ghi mã lớp).

So tên Zalo với cột GVCN của sổ, ví dụ:
    "Lan Nguyễn"    ⊂ "Nguyễn Thị Ngọc Lan"    (các chữ có đủ trong tên GVCN)
    "Phamthanhtam"  = "Phạm Thanh Tâm"         (viết liền, bỏ dấu)
    "Lucton"        = "Tôn Văn Lực"             (viết liền, đảo thứ tự)
Chỉ nhận khi khớp đúng 1 lớp.
"""

from __future__ import annotations

import re

from .text import CLASS_RE, fold

_HONORIFIC = {"co", "thay", "gv", "gvcn", "c", "t", "lop", "chu", "nhiem", "giao", "vien"}


def _tokens(name: str) -> list[str]:
    name = CLASS_RE.sub(" ", name or "")
    return [w for w in re.split(r"[^a-z]+", fold(name)) if w]


def _segment(joined: str, parts: list[str]) -> bool:
    """`joined` ghép được từ ≥2 chữ trong `parts` (mỗi chữ dùng 1 lần, thứ tự bất kỳ)."""

    def go(rest: str, left: list[str], used: int) -> bool:
        if not rest:
            return used >= 2
        for i, p in enumerate(left):
            if rest.startswith(p) and go(rest[len(p):], left[:i] + left[i + 1:], used + 1):
                return True
        return False

    return go(joined, parts, 0)


def sender_key(sender: str) -> str:
    return "zalo|" + " ".join(_tokens(sender))


def match_teacher(sender: str, gvcn: dict[str, str]) -> str | None:
    """Lớp có GVCN khớp tên Zalo `sender`; None nếu không khớp hoặc khớp nhiều lớp."""
    toks = [t for t in _tokens(sender) if t not in _HONORIFIC]
    if not toks:
        return None
    want = set(toks)
    hits: list[tuple[str, list[str]]] = []
    for code, name in gvcn.items():
        parts = _tokens(name)
        if not parts:
            continue
        if want <= set(parts) or (len(toks) == 1 and len(toks[0]) >= 6 and _segment(toks[0], parts)):
            hits.append((code, parts))
    if len(hits) == 1:
        return hits[0][0]
    # nhiều lớp: ưu tiên lớp có tên gọi (chữ cuối) của GVCN nằm trong tên Zalo
    named = [code for code, parts in hits if parts[-1] in want]
    return named[0] if len(named) == 1 else None
