"""Tìm học sinh theo tên GV ghi trong tin nhắn.

Kết quả cho mỗi tên:
    OK          có trong lớp, ăn bán trú (đúng 1 em)
    AMBIGUOUS   nhiều em bán trú khớp -> cần chọn
    NOT_BT      có trong lớp nhưng không ăn bán trú
    OTHER_CLASS không có trong lớp, nhưng có ở lớp khác
    NOT_FOUND   không tìm thấy (kèm gợi ý tên gần giống)
"""

from __future__ import annotations

import datetime as dt
import difflib
from dataclasses import dataclass, field

from .models import Roster, Student
from .text import clean_spaces, fold, lower, parse_date, words

OK = "ok"
AMBIGUOUS = "ambiguous"
NOT_BT = "not_bt"
OTHER_CLASS = "other_class"
NOT_FOUND = "not_found"

STATUS_ICON = {OK: "✔", AMBIGUOUS: "⚠", NOT_BT: "⛔", OTHER_CLASS: "✖", NOT_FOUND: "✖"}


@dataclass
class MatchResult:
    query: str
    status: str
    student: Student | None = None
    candidates: list[Student] = field(default_factory=list)

    @property
    def icon(self) -> str:
        return STATUS_ICON[self.status]


def _split_query(q: str) -> tuple[list[str], list[str], str | None]:
    """Tách 'N. Bảo Ngọc' -> (['n'], ['bảo','ngọc'], None); 'Gia Hưng A' -> ([], [...], 'A')."""
    w = words(q.replace(".", " "))
    letter = None
    if len(w) >= 2 and len(w[-1]) == 1 and w[-1].isalpha() and w[-1].isupper():
        letter = w[-1]
        w = w[:-1]
    initials = []
    while len(w) >= 2 and len(w[0]) == 1 and w[0].isalpha():
        initials.append(fold(w[0]))
        w = w[1:]
    return initials, [lower(x) for x in w], letter


def _is_subsequence(part: list[str], whole: list[str]) -> bool:
    it = iter(whole)
    return all(any(p == w for w in it) for p in part)


def _match_level(s: Student, initials: list[str], core: list[str]) -> int:
    """Mức khớp (cao hơn là tốt hơn), 0 = không khớp.

    5 = đúng đuôi tên, đúng dấu ("tuấn anh")      4 = đúng đuôi tên khi bỏ dấu ("Khanh Ngoc")
    3 = coi i/y như nhau ("Khôi Vĩ" ~ "Khôi Vỹ")   2 = viết dính chữ ("Lê ViVi")
    1 = bỏ bớt tên đệm, giữ tên cuối ("Ngô Triết")
    """
    st = [lower(x) for x in words(s.ho_ten)]
    n = len(core)
    if not n or n > len(st):
        return 0
    if initials:
        if n + len(initials) > len(st):
            return 0
        before = st[len(st) - n - len(initials): len(st) - n]
        if any(not fold(b).startswith(i) for b, i in zip(before, initials, strict=True)):
            return 0
    tail = st[-n:]
    if tail == core:
        return 5
    sf, cf = [fold(x) for x in st], [fold(x) for x in core]
    if sf[-n:] == cf:
        return 4
    if [x.replace("y", "i") for x in sf[-n:]] == [x.replace("y", "i") for x in cf]:
        return 3
    if initials:
        return 0
    joined = "".join(cf)
    if len(joined) >= 4 and any("".join(sf[i:]) == joined for i in range(len(sf))):
        return 2
    if n >= 2 and cf[-1] == sf[-1] and _is_subsequence(cf[:-1], sf[:-1]):
        return 1
    return 0


def _find(students: list[Student], q: str) -> list[Student]:
    initials, core, letter = _split_query(q)
    scored = [(lvl, s) for s in students if (lvl := _match_level(s, initials, core))]
    if not scored:
        return []
    best = max(lvl for lvl, _ in scored)
    found = [s for lvl, s in scored if lvl == best]
    if letter and len(found) > 1:
        # Chữ cái cuối: A = em sinh trước trong nhóm trùng họ tên
        same: dict[str, list[Student]] = {}
        for s in found:
            same.setdefault(lower(s.ho_ten), []).append(s)
        dup = [g for g in same.values() if len(g) > 1]
        if len(dup) == 1:
            g = sorted(dup[0], key=lambda s: (parse_date(s.ngay_sinh) or dt.date.max, s.id))
            idx = ord(letter) - 65
            if 0 <= idx < len(g):
                return [g[idx]]
    return found


def match_name(roster: Roster, cls: str, query: str, day: dt.date | None = None) -> MatchResult:
    query = clean_spaces(query)
    boarding = roster.boarding(cls, day)
    # 1) Đúng tên ghi sổ (vd. "Gia Hưng A", "Đặng Bảo Ngọc")
    fq = fold(query)
    exact = [s for s in boarding if fold(roster.display_name(s)) == fq]
    if len(exact) == 1:
        return MatchResult(query, OK, exact[0], exact)

    found = _find(roster.in_class(cls), query)
    boarding_ids = {s.id for s in boarding}
    bt = [s for s in found if s.id in boarding_ids]
    if len(bt) == 1:
        return MatchResult(query, OK, bt[0], bt)
    if len(bt) > 1:
        return MatchResult(query, AMBIGUOUS, None, roster.sort_like_roster(bt))
    if found:
        return MatchResult(query, NOT_BT, found[0], found)

    elsewhere = _find([s for s in roster.students if s.lop != cls and s.lop_tinh != cls], query)
    if elsewhere:
        return MatchResult(query, OTHER_CLASS, None, elsewhere[:8])
    return MatchResult(query, NOT_FOUND, None, suggest(roster, cls, query, day))


def suggest(roster: Roster, cls: str, query: str, day: dt.date | None = None, n: int = 5) -> list[Student]:
    """Gợi ý em bán trú có tên gần giống (gõ sai chính tả)."""
    q = fold(query)
    k = max(1, len(q.split(" ")))
    pool = roster.boarding(cls, day)
    scored = []
    for s in pool:
        tail = " ".join(fold(s.ho_ten).split(" ")[-k:])
        ratio = difflib.SequenceMatcher(None, q, tail).ratio()
        if ratio >= 0.6:
            scored.append((ratio, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:n]]


def guess_class(roster: Roster, names: list[str], day: dt.date | None = None) -> list[str]:
    """Đoán lớp cho tin không ghi mã lớp: lớp có nhiều tên khớp nhất (em bán trú)."""
    if not names:
        return []
    best, out = 0, []
    for code in roster.class_codes():
        boarding = roster.boarding(code, day)
        hits = sum(1 for q in names if _find(boarding, q))
        if hits > best:
            best, out = hits, [code]
        elif hits == best and hits:
            out.append(code)
    if best < max(1, (len(names) + 1) // 2):
        return []
    return out
