"""Tên ghi sổ theo quy tắc của giáo vụ.

- Không trùng: tên đệm + tên (2 chữ cuối): "Lâm Quốc Tuấn Anh" -> "Tuấn Anh".
- Trùng tên đệm + tên nhưng khác họ tên: ghi họ tên đầy đủ.
- Trùng cả họ tên: tên đệm + tên + A/B/C… theo ngày sinh (em sinh trước là A).
Chỉ so giữa các em bán trú trong cùng một lớp.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

from .text import clean_spaces, letter_label, lower, parse_date, words


def short_name(full: str) -> str:
    w = words(full)
    return " ".join(w[-2:]) if len(w) >= 2 else clean_spaces(full)


def compute_display_names(members: Iterable[tuple[str, str, str]]) -> dict[str, str]:
    """members: (id, họ tên, ngày sinh). Trả về {id: tên ghi sổ}."""
    members = list(members)
    by_short: dict[str, list[tuple[str, str, str]]] = {}
    for m in members:
        by_short.setdefault(lower(short_name(m[1])), []).append(m)

    out: dict[str, str] = {}
    for group in by_short.values():
        if len(group) == 1:
            sid, full, _ = group[0]
            out[sid] = short_name(full)
            continue
        by_full: dict[str, list[tuple[str, str, str]]] = {}
        for m in group:
            by_full.setdefault(lower(m[1]), []).append(m)
        for same in by_full.values():
            if len(same) == 1:
                sid, full, _ = same[0]
                out[sid] = clean_spaces(full)
                continue
            same.sort(key=lambda m: (parse_date(m[2]) or dt.date.max, m[0]))
            for i, (sid, full, _) in enumerate(same):
                out[sid] = f"{short_name(full)} {letter_label(i)}"
    return out
