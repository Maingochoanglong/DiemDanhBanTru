"""Lịch thêm / cắt bán trú theo ngày, cắt thứ 6 hàng tuần, vắng dài hạn."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .models import Roster, Student
from .text import fmt_date

CUT = "cat"  # cắt bán trú từ ngày
ADD = "them"  # thêm vào bán trú từ ngày
FRIDAY = "thu6"  # cắt thứ 6 hàng tuần
LONG = "vang"  # vắng dài hạn

LABEL = {
    CUT: "Cắt bán trú",
    ADD: "Thêm bán trú",
    FRIDAY: "Cắt thứ 6 hàng tuần",
    LONG: "Vắng dài hạn",
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
        if self.kind == FRIDAY:
            return "Cắt thứ 6 hàng tuần (thứ 6 tự tính vắng)"
        end = f" đến {fmt_date(self.end)}" if self.end else " (tới khi có thông báo mới)"
        return f"Vắng dài hạn từ {fmt_date(self.start)}{end}"


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
        elif kind == LONG:
            s.vang_tu, s.vang_den = start, end
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
    elif item.kind == LONG:
        s.vang_tu = s.vang_den = None
    roster.invalidate()


def items(roster: Roster, today: dt.date, recent_days: int = 31) -> list[ScheduleItem]:
    """Các lịch đang có: sắp áp dụng, hàng tuần, vắng dài hạn, và đã áp dụng gần đây."""
    since = today - dt.timedelta(days=recent_days)
    out = []
    for s in roster.students:
        if s.cat_tu and s.cat_tu >= since:
            out.append(ScheduleItem(CUT, s, s.cat_tu))
        if s.ban_tru and s.bt_tu and s.bt_tu >= since:
            out.append(ScheduleItem(ADD, s, s.bt_tu))
        if s.ban_tru and s.cat_thu6 and s.is_boarding(today):
            out.append(ScheduleItem(FRIDAY, s))
        if s.vang_tu and (s.vang_den is None or s.vang_den >= since):
            out.append(ScheduleItem(LONG, s, s.vang_tu, s.vang_den))
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
    """Ghi chú cột H theo cách giáo vụ vẫn viết (app đọc lại được)."""
    names = ", ".join(s.ho_ten for s in students)
    if kind in (CUT, ADD) and start:
        verb = "CẮT" if kind == CUT else "thêm"
        if start.day == 1:
            return f"T{start.month} {verb} {names}"
        return f"Từ {start:%d/%m} {'cắt bán trú' if kind == CUT else 'thêm'} {names}"
    if kind == FRIDAY:
        return f"Thứ 6 hàng tuần cắt {names}"
    if kind == LONG:
        if end:
            return f"{names} vắng từ {start:%d/%m} đến {end:%d/%m}" if start else f"{names} vắng đến {end:%d/%m}"
        return f"{names} vắng tới khi có thông báo mới"
    return ""
