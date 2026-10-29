import datetime as dt

from app.core import schedule as sch
from app.core.day import DayState
from app.core.notes import suggest_from_note

THU = dt.date(2026, 10, 29)
FRI = dt.date(2026, 10, 30)


def test_cut_tomorrow_and_add_next_month(roster):
    a, b = roster.students[0], roster.students[5]  # a ăn BT 1D15, b không ăn BT 1D15
    sch.apply(roster, sch.CUT, [a], FRI)
    sch.apply(roster, sch.ADD, [b], sch.next_month_start(THU))
    assert sch.next_month_start(THU) == dt.date(2026, 11, 1)
    assert sch.next_month_start(dt.date(2026, 12, 15)) == dt.date(2027, 1, 1)
    assert roster.si_so("1D15", THU) == 6 and roster.si_so("1D15", FRI) == 5
    assert roster.si_so("1D15", dt.date(2026, 11, 2)) == 6
    kinds = {(i.kind, i.student.ho_ten) for i in sch.items(roster, THU)}
    assert (sch.CUT, a.ho_ten) in kinds and (sch.ADD, b.ho_ten) in kinds
    sch.cancel(roster, sch.ScheduleItem(sch.ADD, b, b.bt_tu))
    assert not b.ban_tru and b.bt_tu is None


def test_note_text_matches_teacher_style_and_is_readable_back(roster):
    a = roster.students[4]  # Hồ Khánh Ngọc 1D15
    assert sch.note_text(sch.CUT, [a], dt.date(2026, 11, 1)) == "T11 CẮT Hồ Khánh Ngọc"
    assert sch.note_text(sch.CUT, [a], FRI) == "Từ 30/10 cắt bán trú Hồ Khánh Ngọc"
    assert sch.note_text(sch.FRIDAY, [a], None) == "Thứ 6 hàng tuần cắt Hồ Khánh Ngọc"
    assert sch.note_text(sch.LONG, [a], THU) == "Hồ Khánh Ngọc vắng tới khi có thông báo mới"
    # ghi chú app viết, đọc lại gợi ý đúng việc đó
    sug = suggest_from_note(roster, "1D15", sch.note_text(sch.CUT, [a], FRI), THU)
    assert [(g.student.ho_ten, g.changes) for g in sug] == [("Hồ Khánh Ngọc", {"cat_tu": FRI})]
    sch.apply(roster, sch.CUT, [a], FRI)
    assert suggest_from_note(roster, "1D15", sch.note_text(sch.CUT, [a], FRI), THU) == []  # đã áp dụng thì thôi


def test_scheduled_change_is_not_a_si_so_conflict(roster):
    a = roster.students[0]
    sch.apply(roster, sch.CUT, [a], FRI)
    st = DayState.new(FRI, roster, roster.class_codes())
    st.template_date = THU
    st.cd("1D15").sheet_si_so = 6  # sổ hôm qua ghi 6 em
    assert st.si_so("1D15") == 5  # hôm nay tự giảm còn 5
    assert not st.si_so_mismatch("1D15")
    assert [i.student.id for i in st.scheduled_changes("1D15")] == [a.id]
    st.cd("1D15").sheet_si_so = 7  # sổ lệch thật với danh sách
    assert st.si_so_mismatch("1D15")


def test_friday_half_day_absences(roster):
    kids = [roster.students[1], roster.students[2]]
    sch.apply(roster, sch.FRIDAY, kids, None)
    assert DayState.new(THU, roster, ["1D15"]).absent_count("1D15") == 0
    fri = DayState.new(FRI, roster, ["1D15"])
    assert fri.absent_count("1D15") == 2
    fri.mark_full("1D15")  # GV báo "đủ" vẫn trừ các em nghỉ thứ 6
    assert fri.absent_count("1D15") == 2
