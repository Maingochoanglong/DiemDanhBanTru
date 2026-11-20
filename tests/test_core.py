import datetime as dt

from app.core import matcher
from app.core.day import DayState, split_sheet_cell
from app.core.models import Student
from app.core.meals import MealLayout, MealRow
from app.core.names import compute_display_names, short_name
from app.core.parser import extract_names
from app.core.text import fold, norm_class, parse_date

DAY = dt.date(2026, 10, 29)  # thứ 5


# ---------- tên ghi sổ ----------
def test_short_name():
    assert short_name("Lâm Quốc Tuấn Anh") == "Tuấn Anh"
    assert short_name("Mai An") == "Mai An"


def test_display_names_rules(roster):
    names = {s.ho_ten + s.ngay_sinh: roster.display_name(s) for s in roster.students if s.ban_tru}
    # trùng tên đệm + tên -> họ tên đầy đủ
    assert names["Kha Bảo Ngọc02/03/2020"] == "Kha Bảo Ngọc"
    assert names["Võ Hoàng Bảo Ngọc05/06/2020"] == "Võ Hoàng Bảo Ngọc"
    # không trùng -> 2 chữ cuối
    assert names["Lâm Quốc Tuấn Anh09/10/2020"] == "Tuấn Anh"
    # trùng cả họ tên -> A/B theo ngày sinh (em sinh trước là A)
    assert names["Lý Gia Hưng13/03/2020"] == "Gia Hưng A"
    assert names["Lý Gia Hưng24/04/2020"] == "Gia Hưng B"
    # em không ăn BT không làm trùng: Thanh Vy (1D16) vẫn ghi ngắn
    assert names["Kiều Thanh Vy15/05/2020"] == "Thanh Vy"


def test_short_name_keeps_written_ab_letter():
    assert short_name("Lý Gia Hưng A") == "Gia Hưng A"
    assert short_name("Lâm Quốc Tuấn Anh") == "Tuấn Anh"


def test_display_names_mixed_group():
    out = compute_display_names([
        ("a", "Lã Minh Khang", "01/01/2018"),
        ("b", "Tào Minh Khang", "08/04/2018"),
        ("c", "Tào Minh Khang", "22/03/2018"),
    ])
    assert out == {"a": "Lã Minh Khang", "b": "Minh Khang B", "c": "Minh Khang A"}


def test_text_helpers():
    assert fold("Đặng Bảo Ngọc") == "dang bao ngoc"
    assert norm_class("Lớp 1d15") == "1D15"
    assert parse_date("13/03/2020") == dt.date(2020, 3, 13)


# ---------- đọc tin nhắn (đúng các dạng trong ảnh Zalo, tên đã thay) ----------
KNOWN = {"1D15", "1D16", "1D18", "1D19", "1D20", "2D16", "2D17", "2D18", "2D20", "2D21",
         "3D18", "3D19", "3D20", "3D21", "3D22", "3D23", "4D18", "4D19", "4D20", "4D22",
         "5D18", "5D20", "5D21", "5D22"}



# ---------- so khớp tên ----------
def test_match_statuses(roster):
    m = lambda cls, q: matcher.match_name(roster, cls, q, DAY)  # noqa: E731
    assert m("1D15", "tuấn anh").status == matcher.OK
    assert m("1D15", "Khanh Ngoc").student.ho_ten == "Hồ Khánh Ngọc"  # thiếu dấu
    r = m("1D15", "Bảo Ngọc")
    assert r.status == matcher.AMBIGUOUS and len(r.candidates) == 3
    assert m("1D15", "Đ. Bảo Ngọc").student.ho_ten == "Đặng Bảo Ngọc"  # viết tắt họ
    assert m("1D15", "Quỳnh Anh").status == matcher.NOT_BT
    assert m("1D15", "Duy Mạnh").status == matcher.OTHER_CLASS
    assert m("1D15", "Xuân Mai").status == matcher.NOT_FOUND
    assert m("1D16", "thư").student.ho_ten == "Ông Minh Thư"  # chỉ ghi tên
    assert m("1D16", "Gia Hưng A").student.ngay_sinh == "13/03/2020"
    assert m("1D16", "Gia Hưng B").student.ngay_sinh == "24/04/2020"
    assert m("1D16", "Gia Hưng").status == matcher.AMBIGUOUS
    # Thanh Vy: 1 em ăn BT, 1 em không -> lấy em ăn BT
    assert m("1D16", "thanh vy").student.ho_ten == "Kiều Thanh Vy"


def test_suggest_typo(roster):
    r = matcher.match_name(roster, "1D15", "Minh Khoa", DAY)
    assert r.status == matcher.NOT_FOUND
    assert r.candidates and r.candidates[0].ho_ten == "Tô Minh Khôi"


# ---------- quy tắc theo ngày ----------
def test_boarding_dates_and_auto_absent(roster):
    s = roster.students[0]
    s.cat_tu = dt.date(2026, 11, 1)
    assert s.is_boarding(dt.date(2026, 10, 31)) and not s.is_boarding(dt.date(2026, 11, 2))
    n = roster.students[24]  # Lục Thảo Mi 4D19
    n.cat_thu6 = True
    assert n.auto_absent_reason(DAY) == ""
    assert n.auto_absent_reason(dt.date(2026, 10, 30)) == "cắt thứ 6"


# ---------- một ngày điểm danh ----------
def test_day_names_from_sheet_and_pick_ambiguous(roster):
    st = DayState.new(DAY, roster, roster.class_codes())
    res = st.load_class_from_sheet("1D15", 6, "Hồ Khánh Ngọc ,Tuấn Anh, Bảo Ngọc", "")
    assert [r.status for r in res] == [matcher.OK, matcher.OK, matcher.AMBIGUOUS]
    assert st.absent_names("1D15") == ["Tuấn Anh", "Khánh Ngọc", "Bảo Ngọc"]  # tên trùng giữ nguyên chữ tới khi chọn em
    assert st.si_so("1D15") == 6 and st.absent_count("1D15") == 3 and st.present("1D15") == 3
    st.resolve_pending("1D15", res[2], res[2].candidates[2])  # chọn em cho tên trùng
    assert st.absent_count("1D15") == 3 and not st.cd("1D15").extra and len(st.cd("1D15").manual) == 3


def test_day_friday_auto_absent(roster):
    roster.students[24].cat_thu6 = True  # Lục Thảo Mi 4D19
    st = DayState.new(dt.date(2026, 10, 30), roster, roster.class_codes())
    assert st.absent_names("4D19") == ["Thảo Mi"]
    st.set_absent("4D19", roster.students[24].id, False)  # bỏ tích
    assert st.absent_names("4D19") == []


def test_load_from_sheet_text(roster):
    st = DayState.new(DAY, roster, roster.class_codes())
    res = st.load_class_from_sheet("1D16", 5, "Gia Hưng A, thư, Bé Xíu", "")
    assert [r.status for r in res] == [matcher.OK, matcher.OK, matcher.NOT_FOUND]
    assert st.absent_names("1D16") == ["Gia Hưng A", "Minh Thư", "Bé Xíu"]
    assert split_sheet_cell("Tuấn Anh , Hồ Khánh Ngọc")[0] == ["Tuấn Anh", "Hồ Khánh Ngọc"]


def test_meals_with_ghep(roster):
    # 1D19 chia sang 1.1 (1D15) và 1.2 (1D16); 4D21 chia sang 4.2 (4D19)
    layout = MealLayout(
        rows=[
            MealRow(72, "1.1 ghép", "I72", ["1D15"], "O72", "M72"),
            MealRow(73, "1.2 ghép", "I73", ["1D16"], "O73", "M73"),
            MealRow(78, "4.2 ghép 4.4", "I78", ["4D19"], "O78", "M78"),
            MealRow(80, "cô Lan", "I80", ["2D17"]),
        ],
        self_classes=[],
        ghep_classes=["1D19", "4D21"],
        o_values={"1.1": 2, "1.2": 2, "4.2": 3},
    )
    for s in roster.students:
        if s.lop == "1D19":
            s.an_ghep = "1.1" if s.ho_ten in ("Châu Bảo Ngọc", "Phùng Gia Hân") else "1.2"
        if s.lop == "4D21":
            s.an_ghep = "4.2"
    st = DayState.new(DAY, roster, roster.class_codes())
    st.set_absent("1D19", roster.students[13].id, True)  # Châu Bảo Ngọc -> nhóm 1.1
    summary = st.meals(layout)
    line = {x.row.label: x for x in summary.lines}
    assert (line["1.1 ghép"].o, line["1.1 ghép"].m) == (2, 1)
    assert line["1.1 ghép"].absent_names == ["Bảo Ngọc"]
    assert line["1.1 ghép"].meals == st.present("1D15") + 1
    assert summary.balanced, summary.warnings


GHEP_LAYOUT = dict(
    rows=[MealRow(72, "1.1 ghép", "I72", ["1D15"], "O72", "M72"),
          MealRow(73, "1.2 ghép", "I73", ["1D16"], "O73", "M73")],
    ghep_classes=["1D19"],
    o_values={"1.1": 3, "1.2": 1},
)


def test_meals_ask_group_for_absent_ghep_without_group(roster):
    layout = MealLayout(**GHEP_LAYOUT)
    roster.students[13].an_ghep = "1.1"  # Châu Bảo Ngọc đã có nhóm; 3 em còn lại chưa -> giữ số O trong sổ
    st = DayState.new(DAY, roster, roster.class_codes())
    st.set_absent("1D19", roster.students[13].id, True)  # đã có nhóm: tự trừ ở 1.1, không hỏi
    st.set_absent("1D19", roster.students[14].id, True)  # Phùng Gia Hân chưa có nhóm: app hỏi
    summary = st.meals(layout)
    line = {x.row.code: x for x in summary.lines}
    assert {c: x.o for c, x in line.items()} == {"1.1": 3, "1.2": 1}
    assert [s.ho_ten for _, s in summary.ask] == ["Phùng Gia Hân"]
    assert line["1.1"].m == 1 and line["1.1"].absent_names == ["Bảo Ngọc"]

    st.pick_ghep(roster.students[14].id, "1.2")
    summary = st.meals(layout)
    line = {x.row.code: x for x in summary.lines}
    assert not summary.ask
    assert (line["1.2"].m, line["1.2"].meals, line["1.2"].absent_names) == (1, st.present("1D16") + 1 - 1, ["Gia Hân"])
    st.pick_ghep(roster.students[14].id, "")  # chọn lại
    assert st.meals(layout).ask


def test_picks_from_book_only_when_sure(roster):
    layout = MealLayout(**GHEP_LAYOUT)
    a, b = roster.students[14].id, roster.students[15].id

    def day(*absent):
        st = DayState.new(DAY, roster, roster.class_codes())
        for sid in absent:
            st.set_absent("1D19", sid, True)
        return st

    st = day(a)
    st.picks_from_book(layout, {"1.2": 1})
    assert st.ghep_pick == {a: "1.2"} and not st.meals(layout).ask
    st = day(a, b)
    st.picks_from_book(layout, {"1.2": 2})
    assert st.ghep_pick == {a: "1.2", b: "1.2"}
    st = day(a, b)
    st.picks_from_book(layout, {"1.1": 1, "1.2": 1})  # không biết em nào nhóm nào: để app hỏi lại
    assert st.ghep_pick == {} and len(st.meals(layout).ask) == 2



def test_match_partial_and_joined(roster):
    roster.students.append(roster.students[0].__class__("HSX1", "1D15", "Bạch Vi Vi", "01/01/2020", True))
    roster.students.append(roster.students[0].__class__("HSX2", "1D15", "Hà Bùi Minh Triết", "01/01/2020", True))
    roster.students.append(roster.students[0].__class__("HSX3", "1D15", "Lương Minh Triết", "01/01/2020", True))
    m = lambda q: matcher.match_name(roster, "1D15", q, DAY)  # noqa: E731
    assert m("Bạch ViVi").student.id == "HSX1"  # viết dính
    assert m("Hà Triết").student.id == "HSX2"  # họ + tên, bỏ tên đệm
    assert m("Minh Triết").status == matcher.AMBIGUOUS


def test_sheet_cell_notes(roster):
    from app.core.day import split_sheet_cell

    assert split_sheet_cell("Tuấn Anh, cắt Hồ Khánh Ngọc, thêm Bé Xíu") == (["Tuấn Anh"], ["cắt Hồ Khánh Ngọc", "thêm Bé Xíu"])
    assert split_sheet_cell("Cát Tường, Cắt Bé Xíu") == (["Cát Tường"], ["Cắt Bé Xíu"])  # "Cát" là tên
    st = DayState.new(DAY, roster, roster.class_codes())
    st.load_class_from_sheet("1D15", 6, "Tuấn Anh, cắt Hồ Khánh Ngọc", "")
    assert st.absent_names("1D15") == ["Tuấn Anh"]
    assert st.cd("1D15").note == "cắt Hồ Khánh Ngọc"


def test_initial_matches_family_name_and_asks_when_two_fit(roster):
    day = dt.date(2026, 10, 29)
    # chữ viết tắt là họ: "V. Bảo Ngọc" = Võ Hoàng Bảo Ngọc; là từ ngay trước tên: "Đ. Bảo Ngọc" = Đặng Bảo Ngọc
    assert matcher.match_name(roster, "1D15", "V. Bảo Ngọc", day).student.ho_ten == "Võ Hoàng Bảo Ngọc"
    assert matcher.match_name(roster, "1D15", "Đ. Bảo Ngọc", day).student.ho_ten == "Đặng Bảo Ngọc"
    # "K. Bảo Ngọc": em có chữ K sát tên (Kha Bảo Ngọc) được ưu tiên hơn em chỉ có họ Kha (Kha Văn Bảo Ngọc)
    roster.students.append(Student(id="HS9001", lop="1D15", ho_ten="Kha Văn Bảo Ngọc", ngay_sinh="01/01/2020",
                                   ban_tru=True))
    # 2 em chỉ khớp họ như nhau -> hỏi chọn em, không tự chọn
    for i, name in enumerate(("Hà Văn Bảo Ngọc", "Hà Thị Bảo Ngọc")):
        roster.students.append(Student(id=f"HS910{i}", lop="1D16", ho_ten=name, ngay_sinh="01/01/2020", ban_tru=True))
    assert matcher.match_name(roster, "1D15", "K. Bảo Ngọc", day).student.ho_ten == "Kha Bảo Ngọc"
    r = matcher.match_name(roster, "1D16", "H. Bảo Ngọc", day)
    assert r.status == matcher.AMBIGUOUS and len(r.candidates) == 2


def test_wrong_names_are_matched_or_reported(roster):
    """Tên GV gõ sai: sai dấu / i-y / không dấu thì tự nhận; sai hẳn hoặc không có trong lớp thì hỏi."""
    day = dt.date(2026, 10, 29)

    def m(cls, q):
        return matcher.match_name(roster, cls, q, day)

    for q, want in [("Minh Thu", "Ông Minh Thư"), ("Thanh Vi", "Kiều Thanh Vy"), ("Khue", "Âu Ngọc Khuê"),
                    ("Gia Hưng B", "Lý Gia Hưng"), ("Thư", "Ông Minh Thư")]:
        r = m("1D16", q)
        assert r.status == matcher.OK and r.student.ho_ten == want, q
    r = m("1D16", "Ngọc Khuyê")  # sai hẳn chữ -> chưa rõ, em gần giống nhất đứng đầu gợi ý
    assert r.status == matcher.NOT_FOUND and r.candidates[0].ho_ten == "Âu Ngọc Khuê"
    r = m("1D16", "Tuấn Kiệt")  # có ở lớp khác -> chưa rõ, báo lớp khác
    assert r.status == matcher.OTHER_CLASS and r.candidates[0].lop == "2D17"
    assert m("1D15", "Bảo Ngọc").status == matcher.AMBIGUOUS  # 3 em cùng tên -> hỏi


def test_names_that_look_like_stop_words():
    assert extract_names("31/41 (Hoàng Nghi, Gia Lâm)") == ["Hoàng Nghi", "Gia Lâm"]
    assert extract_names("vang Minh Anh, nghi phep Bao Ngoc") == ["Minh Anh", "Bao Ngoc"]
    assert extract_names("Vang Minh Anh") == ["Minh Anh"]
    assert extract_names("vắng: Duy kien, quỳnh anh") == ["Duy kien", "quỳnh anh"]


THU, FRI = dt.date(2026, 10, 29), dt.date(2026, 10, 30)


def test_scheduled_change_is_not_a_si_so_conflict(roster):
    """Em "cắt từ 30/10" (cột Ghi chú): sĩ số hôm nay tự giảm, không hỏi sĩ số khác sổ."""
    a = roster.students[0]
    a.cat_tu = FRI
    st = DayState.new(FRI, roster, roster.class_codes())
    st.template_date = THU
    st.cd("1D15").sheet_si_so = 6  # sổ hôm qua ghi 6 em
    assert st.si_so("1D15") == 5 and not st.si_so_mismatch("1D15")
    assert st.scheduled_changes("1D15") == [a]
    st.cd("1D15").sheet_si_so = 7  # sổ lệch thật với danh sách
    assert st.si_so_mismatch("1D15")


def test_friday_half_day_absences(roster):
    for kid in roster.students[1:3]:
        kid.cat_thu6 = True  # "cắt thứ 6"
    assert DayState.new(THU, roster, ["1D15"]).absent_count("1D15") == 0
    fri = DayState.new(FRI, roster, ["1D15"])
    assert fri.absent_count("1D15") == 2
    fri.mark_full("1D15")  # GV báo "đủ" vẫn trừ các em nghỉ thứ 6
    assert fri.absent_count("1D15") == 2
