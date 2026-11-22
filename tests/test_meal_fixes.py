"""Giáo vụ tự thêm / bỏ dòng suất ăn, suất ghép trong sổ bằng Excel: app hiểu, tính đúng, và khi lưu thì viết lại
công thức bảng suất ăn cho đúng (ô cộng các nhóm, ô ăn tại lớp, ô nhận em ghép lẻ). Tên học sinh là tên bịa.

Sổ giả (tests.test_nhom_an.make_book_self): dòng 21 "cô Lan" (2D17), 23 "1.1 ghép" (1D15 + em ghép lẻ),
25 "4.2 ghép 4.4" (4D19 + em ghép lẻ); G21 =SUM(I21:I25), G22 ăn tại lớp =F7 (1D16), G24 tổng cộng.
Hàng lớp: 1D15 F6, 1D16 F7, 1D19 F8, 2D17 F10, 4D19 F12, 4D21 F13."""

import datetime as dt
import os

import openpyxl
import pytest

from app.excel import sobook
from app.web.api import Api
from tests.conftest import make_roster, make_workspace
from tests.test_nhom_an import make_book_self

DAY = dt.date(2026, 10, 28)


def roster_with_ghep(extra=None):
    """1D19 ăn ghép lẻ nhóm 1.1, 4D21 nhóm 4.2 (như sổ giả); `extra`: {họ tên: mã} đổi riêng."""
    r = make_roster()
    for s in r.students:
        s.an_ghep = {"1D19": "1.1", "4D21": "4.2"}.get(s.lop, "")
        s.an_ghep = (extra or {}).get(s.ho_ten, s.an_ghep)
    return r


def edit_book(path, **cells):
    """Giáo vụ sửa sổ bằng Excel: ghi các ô (None = xóa)."""
    wb = openpyxl.load_workbook(path)
    for a, v in cells.items():
        wb["28"][a] = v
    wb.save(path)
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))  # chắc chắn thời điểm sửa khác lần đọc trước


def cell(path, a):
    return openpyxl.load_workbook(path)["28"][a].value


@pytest.fixture
def book(tmp_path):
    return make_book_self(tmp_path / "SO DIEM DANH T10.xlsx")


def test_correct_book_is_not_touched(tmp_path, book):
    ws = make_workspace(tmp_path, roster_with_ghep(), book)
    ws.load_day(DAY)
    assert ws.meal_fixes == [] and ws.meal_note == ""
    before = {a: cell(book, a) for a in ("G21", "G22", "I21", "I23", "L23", "I25")}
    ws.save()
    assert ws.saved_fixes == [] and {a: cell(book, a) for a in before} == before


def test_row_added_outside_sum_and_class_still_in_self_cell(tmp_path, book):
    """Thêm dòng 26 "cô Mai" (1D16) mà quên nới ô cộng G21 và quên bỏ 1D16 khỏi ô ăn tại lớp G22."""
    edit_book(book, I26="=F7", J26="cô Mai")
    ws = make_workspace(tmp_path, roster_with_ghep(), book)
    ws.load_day(DAY)
    assert [r.label for r in ws.layout.rows] == ["cô Lan", "1.1 ghép", "4.2 ghép 4.4", "cô Mai"]
    assert ws.meal_fixes == ["Ô G22 (ăn tại lớp): bỏ 1D16", "Ô G21 (cộng các nhóm): cộng dòng 21 tới dòng 26"]
    assert ws.meals().balanced  # app tính như sổ sau khi sửa: 1D16 chỉ tính một lần
    fixes = list(ws.meal_fixes)
    ws.save()
    assert (cell(book, "G21"), cell(book, "G22"), cell(book, "I26"), cell(book, "J26")) == ("=SUM(I21:I26)", "=0", "=F7", "cô Mai")
    assert ws.saved_fixes == fixes and ws.meal_fixes == []  # đã lưu: sổ đúng, không còn gì phải sửa


def test_ghep_row_removed_classes_go_back_to_self_cell(tmp_path, book):
    """Bỏ dòng "4.2 ghép 4.4" và cột Ăn ghép của 4D21: 4D19, 4D21 về ăn tại lớp."""
    edit_book(book, I25=None, J25=None, L25=None, M25=None, O25=None)
    ws = make_workspace(tmp_path, roster_with_ghep({n: "" for n in ("Ninh Vũ Khoa", "La Thảo Vy", "Ung Khải Minh")}), book)
    ws.load_day(DAY)
    assert ws.meal_fixes == ["Ô G22 (ăn tại lớp): thêm 4D19, 4D21", "Ô G21 (cộng các nhóm): cộng dòng 21 tới dòng 23"]
    assert ws.meals().balanced
    ws.save()
    assert (cell(book, "G21"), cell(book, "G22")) == ("=SUM(I21:I23)", "=F7+F12+F13")


def test_label_with_code_becomes_ghep_row_when_list_uses_it(tmp_path, book):
    """Dòng 26 "1.2 ghép" (1D16) chỉ có công thức =F7; danh sách chuyển 2 em 1D19 sang 1.2: app thêm ô L, O."""
    edit_book(book, I26="=F7", J26="1.2 ghép")
    ws = make_workspace(tmp_path, roster_with_ghep({"Tạ Đức Anh": "1.2", "Quách Minh Khang": "1.2"}), book)
    ws.load_day(DAY)
    assert "Dòng 26 (1.2 ghép): thêm ô nhận em ghép lẻ L26 =O26-M26, O26" in ws.meal_fixes
    m = ws.meals()
    assert m.balanced and not m.warnings and [x.o for x in m.lines if x.row.code] == [2, 3, 2]
    ws.save()
    assert (cell(book, "I26"), cell(book, "L26"), cell(book, "O26"), cell(book, "G22")) == ("=F7+L26", "=O26-M26", 2, "=0")


def test_list_code_without_row_in_book_is_reported(tmp_path, book):
    ws = make_workspace(tmp_path, roster_with_ghep({"Tạ Đức Anh": "1.3"}), book)
    ws.load_day(DAY)
    assert any(w.startswith("Cột Ăn ghép ghi 1.3 cho 1 em (Đức Anh lớp 1D19)") for w in ws.meals().warnings)
    assert ws.meal_fixes == []  # app không tự thêm dòng: chỉ giáo vụ biết dòng đó đặt ở đâu, tên gì


def test_book_edited_while_day_is_open(tmp_path, book):
    """Sửa sổ bằng Excel lúc app đang mở ngày: chưa có thay đổi thì mở lại ngày; đang có thay đổi thì chỉ đọc lại
    bảng suất ăn, tên vắng vừa chọn giữ nguyên."""
    ws = make_workspace(tmp_path, roster_with_ghep(), book)
    api = Api(ws)
    ws.load_day(DAY)
    edit_book(book, I26="=F7", J26="cô Mai")
    assert "cô Mai" in [x["label"] for x in api.meals()["lines"]]

    ws.push_undo()
    kid = next(s for s in ws.roster.students if s.ho_ten == "Viên Duy Mạnh")
    ws.state.set_absent("2D17", kid.id, True)
    ws.dirty = True
    edit_book(book, I27="=F10", J27="cô Hoa", I21=None, J21=None)  # 2D17 chuyển từ "cô Lan" sang "cô Hoa"
    out = api.state()
    assert ws.dirty and kid.id in ws.state.cd("2D17").manual
    assert [r.label for r in ws.layout.rows][-1] == "cô Hoa" and "cô Lan" not in [r.label for r in ws.layout.rows]
    assert out["meal"]["ok"]


def test_save_check_lists_fixes_and_save_reports_them(tmp_path, book):
    edit_book(book, I26="=F7", J26="cô Mai")
    ws = make_workspace(tmp_path, roster_with_ghep(), book)
    api = Api(ws)
    ws.load_day(DAY)
    assert api.save_check()["meal_fixes"] == ws.meal_fixes != []
    out = api.save()
    assert "Đã sửa công thức bảng suất ăn: Ô G22 (ăn tại lớp): bỏ 1D16" in out["ok"]
    assert sobook.analyze(sobook.load_book(book)["28"]).meal.sum_rows == (21, 26)
