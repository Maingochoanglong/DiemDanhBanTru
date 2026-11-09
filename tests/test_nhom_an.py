"""Bảng Nhóm ăn: sheet trong file danh sách -> app dựng bảng suất ăn của tờ ngày mới. Tên học sinh là tên bịa."""

import datetime as dt

import openpyxl
import pytest

from app.core.day import DayState
from app.core.meals import MealGroup as G
from app.excel import sobook
from app.excel.database import AppData
from app.excel.roster_import import check_meal_groups, describe_meal_change, read_meal_groups
from app.service import Workspace
from tests.test_excel import make_book

SPLIT = {"1D19", "4D21"}
COUNTS = {"1.1": 2, "1.2": 2, "4.2": 3}
CLASSES = ["1D15", "1D16", "1D19", "2D17", "4D19", "4D21"]


def make_book_self(path):
    """Sổ giả có thêm ô cộng lớp ăn tại lớp (G22, lớp 1D16) và ô tổng cộng (G24), như sổ thật."""
    make_book(path)
    wb = openpyxl.load_workbook(path)
    ws = wb["28"]
    for c in "IJLO":
        ws[f"{c}24"] = None
    ws["G22"], ws["G24"] = "=F7", "=G21+G22"
    wb.save(path)
    return path


@pytest.fixture
def book_self(tmp_path):
    return make_book_self(tmp_path / "SO DIEM DANH T10.xlsx")


def same_as_book():
    return [G("cô Lan", ["2D17"]), G(""), G("1.1 ghép", ["1D15"], "1.1"), G(""), G("4.2 ghép 4.4", ["4D19"], "4.2")]


def test_layout_cells_of_book(book_self):
    m = sobook.analyze(sobook.load_book(book_self)["28"]).meal
    assert (m.sum_cell, m.self_cell, m.total_cell, m.self_classes) == ("G21", "G22", "G24", ["1D16"])
    assert [r.l_cell for r in m.rows if r.code] == ["L23", "L25"]


def test_same_groups_do_not_touch_book(book_self):
    info = sobook.analyze(sobook.load_book(book_self)["28"])
    plan = sobook.plan_meal_table(info, same_as_book(), SPLIT, COUNTS)
    assert plan.signature() == info.meal.signature()


def test_rebuild_merge_and_new_row(book_self):
    wb = sobook.load_book(book_self)
    ws = wb["28"]
    info = sobook.analyze(ws)
    groups = [G("cô Lan", ["2D17", "1D16"]), G("1.1 ghép", ["1D15"], "1.1"), G("1.2 riêng", [], "1.2"),
              G("4.2 ghép 4.4", ["4D19"], "4.2")]
    plan = sobook.plan_meal_table(info, groups, SPLIT, COUNTS)
    assert plan.self_classes == [] and plan.ghep_classes == ["1D19", "4D21"]
    sobook.write_meal_table(ws, info, plan)
    vals = {a: ws[a].value for a in ("I21", "J21", "I22", "J22", "L22", "O22", "I23", "J23", "I24", "J24", "I25", "J25",
                                    "L25", "O25", "M25", "G21", "G22", "M21", "M22")}
    assert vals == {"I21": "=F10+F7", "J21": "cô Lan", "I22": "=F6+L22", "J22": "1.1 ghép", "L22": "=O22-M22", "O22": 2,
                    "I23": "=L23", "J23": "1.2 riêng", "I24": "=F12+L24", "J24": "4.2 ghép 4.4",
                    "I25": None, "J25": None, "L25": None, "O25": None, "M25": None,
                    "G21": "=SUM(I21:I24)", "G22": "=0", "M21": "vắng", "M22": None}  # chữ "vắng" dời lên trên dòng ghép
    after = sobook.analyze(ws).meal
    assert after.signature() == plan.signature() and after.self_cell == "G22"
    assert after.o_values == {"1.1": 2, "1.2": 2, "4.2": 3}


def test_rebuild_grows_table_and_copies_style(book_self):
    wb = sobook.load_book(book_self)
    ws = wb["28"]
    ws["J23"].font = openpyxl.styles.Font(bold=True)
    info = sobook.analyze(ws)
    groups = same_as_book() + [G(""), G("1.2 ghép", ["1D16"], "1.2")]
    plan = sobook.plan_meal_table(info, groups, SPLIT, COUNTS)
    sobook.write_meal_table(ws, info, plan)
    assert (ws["I27"].value, ws["J27"].value, ws["O27"].value, ws["J27"].font.b) == ("=F7+L27", "1.2 ghép", 2, True)
    assert ws["G21"].value == "=SUM(I21:I27)" and ws["G22"].value == "=0"
    assert sobook.analyze(ws).meal.area == "G20:O27"


def test_rebuild_refuses_when_no_room_or_no_self_cell(book_self, tmp_path):
    wb = sobook.load_book(book_self)
    ws = wb["28"]
    ws["K27"] = "ghi chú"
    info = sobook.analyze(ws)
    plan = sobook.plan_meal_table(info, same_as_book() + [G(""), G("1.2 ghép", ["1D16"], "1.2")], SPLIT, COUNTS)
    with pytest.raises(sobook.MealTableError, match="K27"):
        sobook.write_meal_table(ws, info, plan)
    assert ws["I27"].value is None and ws["I21"].value == "=F10"  # không ghi gì

    plain = sobook.load_book(make_book(tmp_path / "khong_o_tai_lop.xlsx"))["28"]  # sổ không có ô ăn tại lớp
    info = sobook.analyze(plain)
    plan = sobook.plan_meal_table(info, [G("1.1 ghép", ["1D15"], "1.1"), G("4.2 ghép", ["4D19"], "4.2")], SPLIT, COUNTS)
    with pytest.raises(sobook.MealTableError, match="ăn tại lớp"):
        sobook.write_meal_table(plain, info, plan)


def test_check_meal_groups():
    raw = [(2, "cô Lan", "2D17, 1.2", ""), (3, "", "", ""), (4, "ghép", "1D15", "1.1"), (5, "4.3 ghép", "4D19", "4.2"),
           (6, "xuân", "9D99", ""), (7, "thu", "2d17", ""), (8, "đông", "", ""), (9, "1.5", "", "1-5")]
    groups, errors, warnings = check_meal_groups(raw, CLASSES, {"1D19": {"1.1", "1.4"}, "1D16": {"1.1"}})
    assert groups[0] == G("cô Lan", ["2D17", "1D16"]) and groups[1].blank
    assert groups[2] == G("1.1 ghép", ["1D15"], "1.1")  # tên dòng tự thêm mã
    assert errors == [
        'Nhóm ăn, dòng 5 (4.3 ghép): tên dòng phải bắt đầu bằng mã ghép lẻ 4.2 (vd. "4.2 ghép").',
        'Nhóm ăn, dòng 6 (xuân): danh sách không có lớp "9D99".',
        "Nhóm ăn, dòng 6 (xuân): chưa có lớp nào.",
        "Nhóm ăn: lớp 2D17 nằm ở 2 dòng, dòng 2 (cô Lan) và dòng 7 (thu).",
        "Nhóm ăn, dòng 7 (thu): chưa có lớp nào.",
        "Nhóm ăn, dòng 8 (đông): chưa có lớp nào.",
        'Nhóm ăn, dòng 9 (1.5): mã ghép lẻ "1-5" phải dạng số.số, vd. 1.2.',
    ]
    assert warnings == [
        "Lớp 1D16 đã ăn cả lớp ở dòng 2 (cô Lan) nên cột Ăn ghép của các em lớp này không dùng.",
        "Lớp 1D19 có em ghi Ăn ghép 1.4 nhưng bảng Nhóm ăn không có mã ghép lẻ này: các em đó tính ăn tại lớp.",
    ]


def test_describe_meal_change():
    old = same_as_book()
    assert describe_meal_change(old, same_as_book()) is None
    assert describe_meal_change(None, old).endswith("(3 dòng).")
    new = [G("cô Lan", ["2D17", "1D16"]), G("1.1 ghép", ["1D15"], "1.1"), G("1.2 riêng", [], "1.2")]
    text = describe_meal_change(old, new)
    assert 'dòng "cô Lan": 2D17 → 2D17, 1D16' in text and 'thêm dòng "1.2 riêng" (em ghép 1.2)' in text
    assert 'bỏ dòng "4.2 ghép 4.4"' in text
    renamed = describe_meal_change(old, [G("cô Lan", ["2D17"]), G("1.1 ghép 1.2", ["1D15", "1D16"], "1.1")])
    assert 'dòng "1.1 ghép" → "1.1 ghép 1.2": 1D15 + em ghép 1.1 → 1D15, 1D16 + em ghép 1.1' in renamed


def test_app_data_keeps_groups(tmp_path, roster):
    d = AppData(tmp_path / "DuLieu.xlsx", roster)
    d.meal_groups = same_as_book()
    d.save()
    assert AppData.load(tmp_path / "DuLieu.xlsx").meal_groups == same_as_book()


def write_list(path, groups_rows):
    """File danh sách gọn (tên bịa) + sheet Nhóm ăn."""
    from tests.conftest import FAKE

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sách"
    ws.append(["Lớp", "Họ tên", "Ngày sinh", "Bán trú", "Tên gọi khác", "Ăn ghép"])
    ghep = {"Châu Bảo Ngọc": "1.1", "Phùng Gia Hân": "1.1", "Tạ Đức Anh": "1.2", "Quách Minh Khang": "1.2"}
    for lop, name, dob, bt in FAKE:
        ws.append([lop, name, dob, "Có" if bt else "Không", None, ghep.get(name) or ("4.2" if lop == "4D21" else None)])
    wn = wb.create_sheet("Nhóm ăn")
    wn.append(["Tên dòng (in ở sổ)", "Các lớp ăn chung", "Mã ghép lẻ", None, "Cách dùng: mỗi dòng là 1 dòng bảng suất ăn"])
    for row in groups_rows:
        wn.append(list(row))
    wb.save(path)
    return path


@pytest.fixture
def wsp(tmp_path, monkeypatch, roster):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    book = make_book_self(tmp_path / "SO DIEM DANH T10.xlsx")
    AppData(tmp_path / "DuLieu_BanTru.xlsx", roster).save()
    w = Workspace(tmp_path / "DuLieu_BanTru.xlsx")
    w.set_book(book)
    return w


def test_import_list_with_groups_then_new_day_rebuilds(wsp, tmp_path):
    rows = [("cô Lan", "2D17, 1D16", None), (None, None, None), ("1.1 ghép", "1D15", 1.1), ("1.2 riêng", None, "1.2"),
            ("4.2 ghép 4.4", "4.1", 4.2)]
    path = write_list(tmp_path / "DS.xlsx", rows)
    assert read_meal_groups(path)[0] == (2, "cô Lan", "2D17, 1D16", "")
    changes, _ = wsp.import_cdhs(path)
    assert wsp.meal_check == ([], [])
    nhom = [c for c in changes if c.kind == "nhom_an"]
    assert len(nhom) == 1 and nhom[0].text.startswith("Bảng Nhóm ăn: từ tờ ngày mới")
    wsp.apply_import(changes, path)
    assert AppData.load(wsp.data.path).meal_groups[4] == G("4.2 ghép 4.4", ["4D19"], "4.2")

    st = wsp.load_day(dt.date(2026, 10, 28))  # tờ đã có: giữ bảng của sổ, chỉ báo khác
    assert [r.label for r in wsp.layout.rows] == ["cô Lan", "1.1 ghép", "4.2 ghép 4.4"] and "khác cách ghép đã đặt" in wsp.meal_note

    st = wsp.load_day(dt.date(2026, 10, 29))  # tờ mới: tính theo bảng sẽ dựng
    assert [r.label for r in wsp.layout.rows] == ["cô Lan", "1.1 ghép", "1.2 riêng", "4.2 ghép 4.4"]
    assert "khi lưu" in wsp.meal_note
    wsp.push_undo()
    st.set_absent("1D19", next(s.id for s in wsp.roster.students if s.ho_ten == "Tạ Đức Anh"), True)
    m = wsp.meals()
    assert m.balanced and not m.ask and [x.meals for x in m.lines] == [4 + 5, 6 + 2, 2 - 1, 2 + 3]
    assert wsp.save() == "29" and not wsp.warning and wsp.meal_note == ""

    wb = sobook.load_book(wsp.book_path)
    new, old = wb["29"], wb["28"]
    assert [new[f"I{r}"].value for r in range(21, 26)] == ["=F10+F7", None, "=F6+L23", "=L24", "=F12+L25"]  # dòng 22 trống
    assert (new["M24"].value, new["O24"].value, new["G22"].value) == (1, 2, "=0")
    assert old["I21"].value == "=F10" and old["J24"].value is None  # tờ cũ giữ nguyên
    assert [r.label for r in wsp.layout.rows] == ["cô Lan", "1.1 ghép", "1.2 riêng", "4.2 ghép 4.4"]


def test_import_list_with_bad_groups_keeps_old(wsp, tmp_path):
    path = write_list(tmp_path / "DS.xlsx", [("cô Lan", "2D17, 9D99", None)])
    changes, _ = wsp.import_cdhs(path)
    assert not [c for c in changes if c.kind == "nhom_an"]
    assert wsp.meal_check[0] == ['Nhóm ăn, dòng 2 (cô Lan): danh sách không có lớp "9D99".']


def test_new_month_book_rebuilds_first_sheet(wsp, tmp_path):
    wsp.data.meal_groups = [G("cô Lan", ["2D17", "1D16"]), G("1.1 ghép", ["1D15"], "1.1"), G("1.2 ghép", [], "1.2"),
                            G("4.2 ghép 4.4", ["4D19"], "4.2")]
    for s in wsp.roster.students:
        s.an_ghep = {"1D19": "1.1" if s.ho_ten in ("Châu Bảo Ngọc", "Phùng Gia Hân") else "1.2", "4D21": "4.2"}.get(s.lop, "")
    new = wsp.create_month_book(dt.date(2026, 11, 2))
    ws = sobook.load_book(new)["2"]
    assert (ws["I21"].value, ws["J23"].value, ws["G22"].value) == ("=F10+F7", "1.2 ghép", "=0")
    st = wsp.load_day(dt.date(2026, 11, 2))
    assert st.exists_in_book and wsp.meal_note == "" and wsp.meals().balanced


def test_ghep_kid_can_eat_with_other_grade(roster):
    """Em lớp ghép khối 1 ăn cùng nhóm khối 2 (cột Ăn ghép ghi 2.1): app trừ đúng nhóm, không hỏi."""
    from app.core.meals import MealLayout, MealRow

    layout = MealLayout([MealRow(21, "1.1 ghép", "I21", ["1D15"], "O21", "M21", "L21"),
                         MealRow(22, "2.1 ghép", "I22", ["2D17"], "O22", "M22", "L22")], ["1D16", "4D19", "4D21"], ["1D19"])
    for s in roster.students:
        if s.lop == "1D19":
            s.an_ghep = "2.1" if s.ho_ten == "Tạ Đức Anh" else "1.1"
    st = DayState.new(dt.date(2026, 10, 29), roster, CLASSES)
    st.set_absent("1D19", next(s.id for s in roster.students if s.ho_ten == "Tạ Đức Anh"), True)
    assert st.groups_for(layout, "1D19") == ["1.1", "2.1"]
    m = st.meals(layout)
    assert not m.ask and m.balanced and [(x.o, x.m) for x in m.lines] == [(3, 0), (1, 1)]


def test_edit_groups_in_app_and_rebuild_open_sheet(wsp):
    """Sửa cách ghép ở trang Suất ăn: lấy theo sổ khi chưa đặt; lưu; chọn dựng lại cả tờ đang mở."""
    wsp.load_day(dt.date(2026, 10, 28))
    groups, saved = wsp.meal_groups_current()
    assert not saved and groups == same_as_book()
    assert wsp.set_meal_groups([("cô Lan", ["2D17", "2D17"], "")], False) == [
        "Lớp 2D17 nằm ở 2 dòng, dòng 1 (cô Lan) và dòng 1 (cô Lan)."]
    raw = [("cô Lan", ["2D17", "1D16"], ""), ("", [], ""), ("1.1 ghép", ["1D15"], "1.1"), ("1.2 riêng", [], "1.2"),
           ("4.2 ghép 4.4", ["4D19"], "4.2")]
    for s in wsp.roster.students:
        s.an_ghep = {"1D19": "1.1" if s.ho_ten in ("Châu Bảo Ngọc", "Phùng Gia Hân") else "1.2", "4D21": "4.2"}.get(s.lop, "")
    assert wsp.set_meal_groups(raw, apply_today=True) == []
    assert wsp.meal_groups_current()[1] and "Khi lưu" in wsp.meal_note
    assert [r.label for r in wsp.layout.rows] == ["cô Lan", "1.1 ghép", "1.2 riêng", "4.2 ghép 4.4"]
    assert wsp.meals().balanced
    wsp.push_undo()
    assert wsp.save() == "28"
    ws = sobook.load_book(wsp.book_path)["28"]
    assert (ws["I21"].value, ws["I24"].value, ws["G22"].value) == ("=F10+F7", "=L24", "=0")
    assert wsp.meal_note == "" and wsp.meal_force is None
