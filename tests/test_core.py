import datetime as dt

from app.core import matcher
from app.core.day import DayState, split_names
from app.core.models import Student
from app.core.meals import MealLayout, MealRow
from app.core.names import compute_display_names, short_name
from app.core.parser import parse_messages
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

SAMPLES = [
    ("Lớp 1D15 : 29/31\nVắng : Hồ Khánh Ngọc ,Tuấn Anh", "1D15", (29, 31), ["Hồ Khánh Ngọc", "Tuấn Anh"], False),
    ("Lớp 4D18: 38/41( lan, khuê, thanh mai)", "4D18", (38, 41), ["lan", "khuê", "thanh mai"], False),
    ("3D19. 39/40. Vắng đức Thịnh", "3D19", (39, 40), ["đức Thịnh"], False),
    ("4D19.     37/38( vắng 1 Hoài Nam)", "4D19", (37, 38), ["Hoài Nam"], False),
    ("Lớp 5D20: đủ", "5D20", (None, None), [], True),
    ("Lớp 1D16 đủ", "1D16", (None, None), [], True),
    ("3D22: đủ", "3D22", (None, None), [], True),
    ("2D21: 10/10", "2D21", (10, 10), [], True),
    ("Lớp 4D20: 38/38", "4D20", (38, 38), [], True),
    ("5D22: 7/7 đủ", "5D22", (7, 7), [], True),
    ("1D19 đủ", "1D19", (None, None), [], True),
    ("Lớp 1D20: 15/15", "1D20", (15, 15), [], True),
    ("5D18: 38/39 vắng Quỳnh Như", "5D18", (38, 39), ["Quỳnh Như"], False),
    ("Lớp 3D20 32/33 vắng Linh Đan", "3D20", (32, 33), ["Linh Đan"], False),
    ("2D16 đủ", "2D16", (None, None), [], True),
    ("Lớp 1D18: 28/28", "1D18", (28, 28), [], True),
    ("4D22: vắng Toàn", "4D22", (None, None), ["Toàn"], False),
    ("2D20:6/6", "2D20", (6, 6), [], True),
    ("5D21: 6/6", "5D21", (6, 6), [], True),
    ("3D21:7/7", "3D21", (7, 7), [], True),
    ("Lớp 2D18: 38/40\nVắng: Lộc, Na", "2D18", (38, 40), ["Lộc", "Na"], False),
    ("3D23: 15/15", "3D23", (15, 15), [], True),
    ("3D18: 40/41(Mai Trọng Đức)", "3D18", (40, 41), ["Mai Trọng Đức"], False),
]


def test_parse_each_sample():
    for text, cls, (p, t), names, full in SAMPLES:
        msgs = parse_messages(text, KNOWN)
        assert len(msgs) == 1, text
        m = msgs[0]
        assert (m.cls, m.present, m.total, m.names, m.full) == (cls, p, t, names, full), text


def test_parse_without_class():
    msgs = parse_messages("Vắng Duy Mạnh, tuấn Kiệt , Hải Long", KNOWN)
    assert len(msgs) == 1 and msgs[0].cls is None
    assert msgs[0].names == ["Duy Mạnh", "tuấn Kiệt", "Hải Long"]


def test_parse_many_with_sender_lines_and_times():
    text = """cô Hạnh 5D22
5D22: 7/7 đủ
07:40
cô Thu 5D18 (Khối Trưởng)
5D18: 38/39 vắng Quỳnh Như
07:34
thầy Lâm 3D19
3D19. 39/40. Vắng đức Thịnh
T5, 29/10
"""
    msgs = parse_messages(text, KNOWN)
    assert [(m.cls, m.names, m.full) for m in msgs] == [
        ("5D22", [], True),
        ("5D18", ["Quỳnh Như"], False),
        ("3D19", ["đức Thịnh"], False),
    ]


def test_parse_abbreviation_kept():
    msgs = parse_messages("1D19: 28/29 vắng N. Bảo Ngoc", KNOWN)
    assert msgs[0].names == ["N Bảo Ngoc"]


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


def test_guess_class(roster):
    assert matcher.guess_class(roster, ["Duy Mạnh", "tuấn Kiệt", "Hải Long"], DAY) == ["2D17"]


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
def test_day_apply_and_names(roster):
    st = DayState.new(DAY, roster, roster.class_codes())
    msg = parse_messages("Lớp 1D15 : 4/6 Vắng : Hồ Khánh Ngọc ,Tuấn Anh, Quỳnh Anh, Bảo Ngọc", KNOWN)[0]
    res = st.apply_message(msg)
    assert [r.status for r in res] == [matcher.OK, matcher.OK, matcher.NOT_BT, matcher.AMBIGUOUS]
    assert st.absent_names("1D15") == ["Tuấn Anh", "Khánh Ngọc"]
    assert st.si_so("1D15") == 6 and st.absent_count("1D15") == 2 and st.present("1D15") == 4
    # chọn em cho tên trùng
    code, pend = st.pending[0]
    st.resolve_pending(code, pend, pend.candidates[2])
    assert st.absent_count("1D15") == 3 and not st.pending
    # GV báo 4/6 (vắng 2) nhưng đang ghi 3 tên -> cảnh báo
    assert "Thừa 1 tên (GV báo vắng 2 em, đang ghi 3)" in st.class_warnings("1D15")


def test_warning_says_how_many_names_are_missing(roster):
    st = DayState.new(DAY, roster, roster.class_codes())
    msg = parse_messages("Lớp 1D15 : 3/6 Vắng : Tuấn Anh", KNOWN)[0]  # báo vắng 3 nhưng chỉ ghi 1 tên
    st.apply_message(msg)
    assert "Thiếu 2 tên (GV báo vắng 3 em, mới ghi 1)" in st.class_warnings("1D15")


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
    assert split_names("Tuấn Anh , Hồ Khánh Ngọc") == ["Tuấn Anh", "Hồ Khánh Ngọc"]


def test_meals_with_ghep(roster):
    # 1D19 chia sang 1.1 (1D15) và 1.2 (1D16); 4D21 chia sang 4.2 (4D19)
    layout = MealLayout(
        rows=[
            MealRow(72, "1.1 ghép", "I72", ["1D15"], "O72", "M72"),
            MealRow(73, "1.2 ghép", "I73", ["1D16"], "O73", "M73"),
            MealRow(78, "4.2 ghép 4.4", "I78", ["4D19"], "O78", "M78"),
            MealRow(80, "hiến", "I80", ["2D17"]),
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


def test_meals_without_full_ghep_list_uses_manual_counts(roster):
    layout = MealLayout(
        rows=[MealRow(72, "1.1 ghép", "I72", ["1D15"], "O72", "M72"),
              MealRow(73, "1.2 ghép", "I73", ["1D16"], "O73", "M73")],
        ghep_classes=["1D19"],
        o_values={"1.1": 3, "1.2": 1},
    )
    roster.students[13].an_ghep = "1.1"  # mới gán 1/4 em -> chưa đủ, giữ số O trong sổ
    st = DayState.new(DAY, roster, roster.class_codes())
    st.set_absent("1D19", roster.students[14].id, True)
    summary = st.meals(layout)
    assert {x.row.code: x.o for x in summary.lines} == {"1.1": 3, "1.2": 1}
    assert any("chưa có danh sách ghép đầy đủ" in w for w in summary.warnings)
    st.manual_m["1.2"] = 1  # giáo vụ nhập tay
    summary = st.meals(layout)
    line = {x.row.code: x for x in summary.lines}["1.2"]
    assert (line.m, line.meals) == (1, st.present("1D16") + 1 - 1)
    assert not any("ghép" in w for w in summary.warnings)  # bảng giả thiếu lớp khác nên tổng không cân


def test_match_partial_and_joined(roster):
    roster.students.append(roster.students[0].__class__("HSX1", "1D15", "Bạch Vi Vi", "01/01/2020", True))
    roster.students.append(roster.students[0].__class__("HSX2", "1D15", "Hà Bùi Minh Triết", "01/01/2020", True))
    roster.students.append(roster.students[0].__class__("HSX3", "1D15", "Lương Minh Triết", "01/01/2020", True))
    roster.invalidate()
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


def test_parse_message_after_full_class_is_separate():
    msgs = parse_messages("1D16 đủ\nVắng Duy Mạnh, Hải Long\n4D22: vắng Toàn\nVắng Bé Xíu", KNOWN)
    assert [(m.cls, m.names) for m in msgs] == [
        ("1D16", []), (None, ["Duy Mạnh", "Hải Long"]), ("4D22", ["Toàn"]), (None, ["Bé Xíu"])]


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
    roster.invalidate()
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


def test_friday_count_without_friday_students_is_not_a_mismatch(roster):
    roster.students[24].cat_thu6 = True  # Lục Thảo Mi 4D19 cắt thứ 6; lớp có 2 em
    fri = dt.date(2026, 10, 30)
    for text, ok in [("4D19: 1/2 đủ", True), ("4D19: 1/1 đủ", True), ("4D19 đủ", True), ("4D19: 2/2 đủ", False)]:
        st = DayState.new(fri, roster, roster.class_codes())
        msg = parse_messages(text, KNOWN | {"4D19"})[0]
        st.mark_full("4D19")
        c = st.cd("4D19")
        c.teacher_present, c.teacher_total = msg.present, msg.total
        assert st.absent_names("4D19") == ["Thảo Mi"]
        assert (st.class_warnings("4D19") == []) == ok, text
