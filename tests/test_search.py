import datetime as dt

from app.core.search import find_students

DAY = dt.date(2026, 11, 4)


def names(found):
    return [(s.lop, s.ho_ten) for s in found]


def test_find_without_accents_and_by_word_start(roster):
    assert names(find_students(roster.students, "hai long", DAY)) == [("2D17", "Khổng Hải Long")]
    assert names(find_students(roster.students, "long", DAY)) == [("2D17", "Khổng Hải Long")]
    assert names(find_students(roster.students, "h long", DAY)) == [("2D17", "Khổng Hải Long")]
    # "ong" chỉ khớp chữ bắt đầu bằng "ong" (họ Ông), không khớp giữa chữ "Long"
    assert names(find_students(roster.students, "ong", DAY)) == [("1D16", "Ông Minh Thư")]


def test_given_name_first_then_boarding_then_class(roster):
    found = names(find_students(roster.students, "ngoc", DAY))
    # em có tên "Ngọc" lên trước em có "Ngọc" ở chữ đệm (Âu Ngọc Khuê)
    assert found[-1] == ("1D16", "Âu Ngọc Khuê")
    assert ("1D15", "Kha Bảo Ngọc") in found and ("1D19", "Châu Bảo Ngọc") in found
    # em không ăn bán trú xếp sau em có ăn
    vy = names(find_students(roster.students, "vy", DAY))
    assert vy.index(("1D16", "Doãn Thanh Vy")) > vy.index(("4D21", "La Thảo Vy"))


def test_class_code_filters(roster):
    assert names(find_students(roster.students, "1D19 ngoc", DAY)) == [("1D19", "Châu Bảo Ngọc")]
    assert names(find_students(roster.students, "ngoc 1d15", DAY))[0][0] == "1D15"
    assert len(find_students(roster.students, "4D21", DAY)) == 3  # chỉ gõ mã lớp: ra cả lớp
    assert find_students(roster.students, "   ", DAY) == []
