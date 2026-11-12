"""Cột Ghi chú của một em trong file danh sách (app/core/notes.py)."""

import datetime as dt

import pytest

from app.core.notes import student_note

TODAY = dt.date(2026, 10, 29)


@pytest.mark.parametrize(("note", "want"), [
    ("cắt thứ 6", {"cat_thu6": True}),
    ("Cắt T6 hàng tuần", {"cat_thu6": True}),
    ("thu 6 cat", {"cat_thu6": True}),  # gõ không dấu
    ("cắt từ 30/10", {"cat_tu": dt.date(2026, 10, 30)}),
    ("Cắt BT 30/10/2026", {"cat_tu": dt.date(2026, 10, 30)}),
    ("T11 cắt", {"cat_tu": dt.date(2026, 11, 1)}),
    ("ăn từ 3/11", {"ban_tru": True, "bt_tu": dt.date(2026, 11, 3)}),
    ("thêm từ 3/11", {"ban_tru": True, "bt_tu": dt.date(2026, 11, 3)}),
    ("tháng 11 ăn BT", {"ban_tru": True, "bt_tu": dt.date(2026, 11, 1)}),
    ("ăn từ 5/1", {"ban_tru": True, "bt_tu": dt.date(2027, 1, 5)}),  # tháng 1 năm học này = năm sau
    ("cắt thứ 6, cắt từ 2/11", {"cat_thu6": True, "cat_tu": dt.date(2026, 11, 2)}),
    ("dị ứng tôm", {}),
    ("cắt", {}),  # không ghi ngày: bỏ qua (thôi ăn hẳn thì ghi cột Bán trú = Không)
    ("", {}),
])
def test_student_note(note, want):
    assert student_note(note, TODAY) == want


def test_year_from_school_year_or_written():
    assert student_note("cắt từ 15/9", dt.date(2027, 3, 1)) == {"cat_tu": dt.date(2026, 9, 15)}
    assert student_note("cắt từ 15/9/2027", dt.date(2027, 3, 1)) == {"cat_tu": dt.date(2027, 9, 15)}
    assert student_note("ăn từ 3/11/26", TODAY) == {"ban_tru": True, "bt_tu": dt.date(2026, 11, 3)}
