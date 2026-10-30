import datetime as dt

from app.core.models import Student
from app.core.notes import apply_suggestions, suggest_from_book, suggest_from_note

SEEN = dt.date(2026, 10, 15)


def _by_name(sugs):
    return {(g.student.ho_ten if g.student else g.new_name): g.changes for g in sugs}


def test_friday_cut_and_month_cut(roster):
    sugs = suggest_from_note(roster, "4D19", "Thứ 6 hàng tuần cắt 1 em Lục Thảo Mi, T11 CẮT Hoài Nam", SEEN)
    assert _by_name(sugs) == {"Lục Thảo Mi": {"cat_thu6": True}, "Bế Hoài Nam": {"cat_tu": dt.date(2026, 11, 1)}}
    # viết đầy đủ "tháng 11 cắt" (cách app ghi và GV nhắn)
    sugs = suggest_from_note(roster, "4D19", "Tháng 11 cắt bán trú Hoài Nam", SEEN)
    assert _by_name(sugs) == {"Bế Hoài Nam": {"cat_tu": dt.date(2026, 11, 1)}}


def test_names_before_keyword_are_split(roster):
    sugs = suggest_from_note(roster, "4D21", "cắt Thảo Vy, Vũ Khoa vắng tới khi có thông báo mới", SEEN)
    assert _by_name(sugs) == {"La Thảo Vy": {"cat_tu": SEEN}}  # "vắng tới khi…" không còn tạo gợi ý


def test_dates_in_cut_list_and_from_date(roster):
    sugs = suggest_from_note(roster, "1D15", "Cắt bán trú 12/10 Tô Minh Khôi, 19/10 Khánh Ngọc", SEEN)
    assert _by_name(sugs) == {"Tô Minh Khôi": {"cat_tu": dt.date(2026, 10, 12)}, "Hồ Khánh Ngọc": {"cat_tu": dt.date(2026, 10, 19)}}
    sugs = suggest_from_note(roster, "1D15", "Từ 12/10 cắt bán trú Tô Minh Khôi", SEEN)
    assert _by_name(sugs) == {"Tô Minh Khôi": {"cat_tu": dt.date(2026, 10, 12)}}


def test_add_from_same_grade_with_ghep_and_new_student(roster):
    roster.students.append(Student("HSX9", "1D16", "Kha Khôi Vỹ", "01/01/2020", False))
    sugs = suggest_from_book(roster, [
        (SEEN, "1D19", "thêm Khôi Vĩ"),
        (SEEN, "1D19", "thêm Khôi Vĩ ghép 1.3, chú ý 1.5"),
        (SEEN, "2D17", "tháng 11 thêm Bé Mới"),
    ])
    got = _by_name(sugs)
    assert got["Kha Khôi Vỹ"] == {"ban_tru": True, "bt_tu": SEEN, "lop_bt": "1D19", "an_ghep": "1.3"}
    assert got["Bé Mới"] == {"ban_tru": True, "bt_tu": dt.date(2026, 11, 1)}
    n = apply_suggestions(roster, sugs)
    assert n == 2
    new = [s for s in roster.students if s.ho_ten == "Bé Mới"][0]
    assert new.lop == "2D17" and not new.is_boarding(dt.date(2026, 10, 30)) and new.is_boarding(dt.date(2026, 11, 2))
    assert [s.ho_ten for s in roster.boarding("1D19")][-1] == "Kha Khôi Vỹ"


def test_name_starting_with_cat_is_not_a_cut(roster):
    roster.students.append(Student("HSX8", "1D15", "Bùi Cát Tiên", "01/01/2020", True))
    assert suggest_from_note(roster, "1D15", "Cát Tiên nghỉ ốm", SEEN) == []


def test_already_applied_is_skipped(roster):
    roster.students[24].cat_thu6 = True
    assert suggest_from_note(roster, "4D19", "Thứ 6 hàng tuần cắt Thảo Mi", SEEN) == []


def test_earliest_date_wins_across_notes(roster):
    """Ghi chú cũ 'tháng 11 thêm X' nhưng sổ ngày 26/10 đã ghi 'thêm X' -> tính từ 26/10."""
    sugs = suggest_from_book(roster, [
        (dt.date(2026, 10, 22), "2D17", "tháng 11 thêm Bé Mới"),
        (dt.date(2026, 10, 26), "2D17", "thêm Bé Mới"),
        (dt.date(2026, 10, 27), "4D21", "T11 CẮT Thảo Vy"),
        (dt.date(2026, 10, 29), "4D21", "Cắt Thảo Vy"),
    ])
    got = _by_name(sugs)
    assert got["Bé Mới"]["bt_tu"] == dt.date(2026, 10, 26)
    assert got["La Thảo Vy"] == {"cat_tu": dt.date(2026, 10, 29)}
