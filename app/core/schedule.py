"""Lịch thêm / cắt bán trú theo ngày và cắt thứ 6 hàng tuần."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .models import Roster, Student
from .text import fmt_date

CUT = "cat"  # cắt bán trú từ ngày
ADD = "them"  # thêm vào bán trú từ ngày
FRIDAY = "thu6"  # cắt thứ 6 hàng tuần

LABEL = {
    CUT: "Cắt bán trú",
    ADD: "Thêm bán trú",
    FRIDAY: "Cắt thứ 6 hàng tuần",
}


def next_month_start(day: dt.date) -> dt.date:
    return dt.date(day.year + (day.month == 12), day.month % 12 + 1, 1)


@dataclass
class ScheduleItem:
    kind: str
    student: Student
    start: dt.date | None = None
    end: dt.date | None = None

    @property
    def text(self) -> str:
        if self.kind == CUT:
            return f"Cắt bán trú từ {fmt_date(self.start)}"
        if self.kind == ADD:
            return f"Thêm bán trú từ {fmt_date(self.start)}"
        return "Cắt thứ 6 hàng tuần (thứ 6 tự tính vắng)"


def apply(roster: Roster, kind: str, students: list[Student], start: dt.date | None, end: dt.date | None = None) -> None:
    for s in students:
        if kind == CUT:
            s.cat_tu = start
        elif kind == ADD:
            s.ban_tru = True
            s.bt_tu = start
            if s.cat_tu and start and s.cat_tu <= start:
                s.cat_tu = None  # đã cắt trước đó, nay ăn lại
        elif kind == FRIDAY:
            s.cat_thu6 = True
    roster.invalidate()


def cancel(roster: Roster, item: ScheduleItem) -> None:
    s = item.student
    if item.kind == CUT:
        s.cat_tu = None
    elif item.kind == ADD:
        s.bt_tu = None
        s.ban_tru = False
    elif item.kind == FRIDAY:
        s.cat_thu6 = False
    roster.invalidate()


def items(roster: Roster, today: dt.date, recent_days: int = 31) -> list[ScheduleItem]:
    """Các lịch đang có: sắp áp dụng, cắt thứ 6 hàng tuần, và đã áp dụng gần đây."""
    since = today - dt.timedelta(days=recent_days)
    out = []
    for s in roster.students:
        if s.cat_tu and s.cat_tu >= since:
            out.append(ScheduleItem(CUT, s, s.cat_tu))
        if s.ban_tru and s.bt_tu and s.bt_tu >= since:
            out.append(ScheduleItem(ADD, s, s.bt_tu))
        if s.ban_tru and s.cat_thu6 and s.is_boarding(today):
            out.append(ScheduleItem(FRIDAY, s))
    return out


def changes_between(roster: Roster, after: dt.date, until: dt.date, code: str | None = None) -> list[ScheduleItem]:
    """Thêm/cắt có hiệu lực trong khoảng (after, until] — làm sĩ số đổi so với sổ hôm trước."""
    out = []
    for s in roster.students:
        if code and s.lop_tinh != code:
            continue
        if s.cat_tu and after < s.cat_tu <= until and s.ban_tru:
            out.append(ScheduleItem(CUT, s, s.cat_tu))
        if s.ban_tru and s.bt_tu and after < s.bt_tu <= until:
            out.append(ScheduleItem(ADD, s, s.bt_tu))
    return out


def note_text(kind: str, students: list[Student], start: dt.date | None, end: dt.date | None = None) -> str:
    """Ghi chú cột H theo cách giáo vụ vẫn viết (app đọc lại được): "Tháng 11 cắt bán trú X"."""
    names = ", ".join(s.ho_ten for s in students)
    if kind in (CUT, ADD) and start:
        verb = "cắt bán trú" if kind == CUT else "thêm"
        if start.day == 1:
            return f"Tháng {start.month} {verb} {names}"
        return f"Từ {start:%d/%m} {verb} {names}"
    if kind == FRIDAY:
        return f"Thứ 6 hàng tuần cắt {names}"
    return ""
