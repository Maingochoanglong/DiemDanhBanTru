import datetime as dt

import openpyxl
import pytest
from openpyxl.styles import Font

from app.core.day import DayState
from app.core.models import Student
from app.excel import sobook
from app.excel.files import FileLockedError, safe_save
from app.excel.roster_import import load_list, read_cdhs, short_codes
from tests.conftest import write_list

DAY28 = dt.date(2026, 10, 28)


def make_book(path):
    """Sổ giả cùng cấu trúc sổ thật: tiêu đề, khối, tổng, chữ ký, bảng suất ăn có công thức."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "28"
    tnr = Font(name="Times New Roman", size=11)
    ws["A1"] = "UBND PHƯỜNG X"
    ws["A2"] = "TRƯỜNG TIỂU HỌC X"
    ws["A3"] = "ĐIỂM DANH BÁN TRÚ NGÀY 28/10/2026"
    ws["A3"].font = Font(name="Times New Roman", size=14, bold=True)
    ws["A4"] = "Người lấy sĩ số: Giáo Vụ"
    for c, h in zip("ABCDEFG", ["STT", "LỚP", "GIÁO VIÊN CHỦ NHIỆM", "SỈ số", "Vắng", "HIỆN DIỆN", "TÊN HỌC SINH VẮNG"], strict=True):
        ws[f"{c}5"] = h
    rows = [(6, "1D15", 6, 1, "Tuấn Anh"), (7, "1D16", 5, 0, None), (8, "1D19", 4, 0, None), (9, "KHỐI 1",),
            (10, "2D17", 4, 0, None), (11, "KHỐI 2",), (12, "4D19", 2, 0, None), (13, "4D21", 3, 1, "Vũ Khoa"),
            (14, "KHỐI 4",)]
    for item in rows:
        r = item[0]
        if len(item) == 2:
            ws[f"A{r}"] = item[1]
            continue
        _, code, si, vang, names = item
        ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"] = r - 5, code, "GV " + code, si, vang
        ws[f"F{r}"] = f"=D{r}-E{r}"
        ws[f"G{r}"] = names
        ws[f"B{r}"].font = tnr
    ws["H13"] = "Vũ Khoa vắng tới khi có thông báo mới"
    ws["A15"] = "TỔNG CỘNG"
    ws["G16"] = "Phường X, ngày     tháng 10 năm 2026  "
    ws["I20"] = "Suất ăn"
    ws["I21"], ws["J21"] = "=F10", "cô Lan"
    ws["G21"] = "=SUM(I21:I25)"
    ws["M22"] = "vắng"
    ws["I23"], ws["J23"], ws["L23"], ws["O23"] = "=F6+L23", "1.1 ghép", "=O23-M23", 2
    ws["I24"], ws["J24"], ws["L24"], ws["O24"] = "=F7+L24", "1.2 ghép", "=O24-M24", 2
    ws["I25"], ws["J25"], ws["L25"], ws["O25"], ws["M25"] = "=F12+L25", "4.2 ghép 4.4", "=O25-M25", 3, 1
    ws.page_setup.orientation = "landscape"
    wb.save(path)
    return path


@pytest.fixture
def book(tmp_path):
    return make_book(tmp_path / "SO DIEM DANH T10.xlsx")


def test_analyze_layout(book):
    wb = sobook.load_book(book)
    info = sobook.analyze(wb["28"])
    assert list(info.class_rows) == ["1D15", "1D16", "1D19", "2D17", "4D19", "4D21"]
    assert info.total_row == 15 and info.title_cell == "A3" and info.sign_cell == "G16"
    m = info.meal
    assert m.ghep_classes == ["1D19", "4D21"]
    assert [(r.label, r.classes, r.code) for r in m.rows] == [
        ("cô Lan", ["2D17"], None),
        ("1.1 ghép", ["1D15"], "1.1"),
        ("1.2 ghép", ["1D16"], "1.2"),
        ("4.2 ghép 4.4", ["4D19"], "4.2"),
    ]
    assert m.o_values == {"1.1": 2, "1.2": 2, "4.2": 3}
    assert m.area == "G20:O25"
    assert sobook.book_month(wb) == (10, 2026)


def test_create_write_and_read_back(book, roster):
    wb = sobook.load_book(book)
    tpl = sobook.template_sheet(wb, dt.date(2026, 10, 29))
    ws = sobook.create_day_sheet(wb, dt.date(2026, 10, 29), tpl)
    assert wb.sheetnames == ["28", "29"]
    info = sobook.analyze(ws)
    assert ws["A3"].value == "ĐIỂM DANH BÁN TRÚ NGÀY 29/10/2026"
    assert ws["G6"].value is None and ws["E6"].value == 0 and ws["M25"].value is None
    assert ws["H13"].value.startswith("Vũ Khoa")  # ghi chú giữ nguyên
    assert ws["B6"].font.name == "Times New Roman"  # định dạng giữ nguyên
    assert ws["I23"].value == "=F6+L23"  # công thức giữ nguyên

    for s in roster.students:
        if s.lop == "1D19":
            s.an_ghep = "1.1" if s.ho_ten in ("Châu Bảo Ngọc", "Phùng Gia Hân") else "1.2"
        if s.lop == "4D21":
            s.an_ghep = "4.2"
    st = DayState.new(dt.date(2026, 10, 29), roster, list(info.class_rows))
    st.set_absent("1D15", roster.students[3].id, True)  # Tuấn Anh
    st.set_absent("1D19", roster.students[15].id, True)  # Tạ Đức Anh -> 1.2
    st.cd("1D15").note = "ghi chú thử"
    summary = st.meals(info.meal)
    assert summary.balanced, summary.warnings
    sobook.write_day(info, st, summary)
    sobook.select_only(wb, ws)
    safe_save(wb, book)

    wb2 = sobook.load_book(book)
    ws2 = wb2["29"]
    rec = sobook.read_records(sobook.analyze(ws2))
    assert (rec["1D15"].si_so, rec["1D15"].vang, rec["1D15"].names, rec["1D15"].note) == (6, 1, "Tuấn Anh", "ghi chú thử")
    assert rec["1D19"].names == "Đức Anh"
    assert ws2["M24"].value == 1 and ws2["M23"].value is None and ws2["O24"].value == 2
    assert [s.sheet_view.tabSelected for s in wb2.worksheets] == [False, True]
    assert not (book.parent / "SaoLuu").exists()  # không còn sao lưu: chỉ có sổ tạm khi chưa lưu


def test_new_day_sheet_black_names_and_keeps_count_formula(book, roster):
    """Sổ có cột Vắng là công thức đếm tên, và tên hôm trước tô đỏ: sheet ngày mới giữ công thức, tên chữ đen."""
    count = '=IF(TRIM(G{r})="",0,LEN(TRIM(G{r}))-LEN(SUBSTITUTE(TRIM(G{r}),",",""))+1)'
    wb = sobook.load_book(book)
    tpl = wb["28"]
    for r in (6, 7, 8):
        tpl[f"E{r}"] = count.format(r=r)
    tpl["G6"].font = Font(name="Times New Roman", color="FFFF0000")
    safe_save(wb, book)

    wb = sobook.load_book(book)
    ws = sobook.create_day_sheet(wb, dt.date(2026, 10, 29), wb["28"])
    assert ws["G6"].font.color is None and ws["G6"].font.name == "Times New Roman"
    assert wb["28"]["G6"].font.color.rgb == "FFFF0000"  # sheet cũ giữ nguyên
    assert ws["E6"].value == count.format(r=6) and ws["E12"].value == 0  # lớp không có công thức: về 0
    info = sobook.analyze(ws)
    st = DayState.new(dt.date(2026, 10, 29), roster, list(info.class_rows))
    st.set_absent("1D15", roster.students[3].id, True)
    st.set_absent("4D19", next(s.id for s in roster.students if s.lop == "4D19"), True)
    sobook.write_day(info, st, None)
    assert ws["E6"].value == count.format(r=6) and ws["G6"].value == "Tuấn Anh"  # Excel tự đếm
    assert ws["E12"].value == 1  # cột Vắng không có công thức: app ghi số


def test_new_month_book(book, tmp_path):
    new = sobook.month_file_name(book, 11)
    assert new.name == "SO DIEM DANH T11.xlsx"
    sobook.new_month_book(book, dt.date(2026, 11, 2), new)
    wb = sobook.load_book(new)
    assert wb.sheetnames == ["2"]
    ws = wb["2"]
    assert ws["A3"].value == "ĐIỂM DANH BÁN TRÚ NGÀY 02/11/2026"
    assert "tháng 11 năm 2026" in ws["G16"].value
    assert ws["G6"].value is None and ws["M25"].value is None
    assert sobook.find_month_file(tmp_path, 11) == new


def test_safe_save_refuses_when_open_in_excel(book):
    book.with_name("~$" + book.name).write_text("x")  # file khóa Excel tạo khi đang mở
    wb = sobook.load_book(book)
    with pytest.raises(FileLockedError):
        safe_save(wb, book)


def test_load_list_reads_note_column_and_keeps_ids(tmp_path, roster):
    """File danh sách là nơi duy nhất về học sinh: cột Ghi chú cho cắt thứ 6 / cắt từ ngày / ăn từ ngày."""
    roster.students[0].cat_thu6 = True
    roster.students[0].cat_tu = dt.date(2026, 11, 1)
    roster.students[1].an_ghep = "1.2"
    roster.students[5].bt_tu = dt.date(2026, 11, 3)  # Mạc Trần Quỳnh Anh: chưa ăn BT, "ăn từ 03/11"
    roster.students[5].ban_tru = True
    p = write_list(tmp_path / "ds.xlsx", roster)
    data = load_list(p, today=dt.date(2026, 10, 29))
    s0, s1, s5 = (data.roster.students[i] for i in (0, 1, 5))
    assert (s0.ho_ten, s0.cat_thu6, s0.cat_tu, s0.ban_tru) == ("Kha Bảo Ngọc", True, dt.date(2026, 11, 1), True)
    assert s1.an_ghep == "1.2"
    assert (s5.ban_tru, s5.bt_tu, s5.is_boarding(dt.date(2026, 11, 2)), s5.is_boarding(dt.date(2026, 11, 3))) == (
        True, dt.date(2026, 11, 3), False, True)
    assert s0.id == "1D15|Kha Bảo Ngọc|02/03/2020" and load_list(p).roster.students[0].id == s0.id  # đọc lại: mã không đổi
    assert data.roster.classes["1D16"].ma_ngan == "1.2" and data.meal_groups is None
    assert short_codes(["1D16", "1D15", "2D17"]) == {"1D15": "1.1", "1D16": "1.2", "2D17": "2.1"}


def _write_fake_cdhs_xls(path):
    import xlwt

    wb = xlwt.Workbook()
    ws = wb.add_sheet("CDAN")
    red = xlwt.easyxf("font: colour red")
    for c, h in enumerate(["TT", "Tên lớp học", "Họ tên", "Ngày sinh", "Phân loại HS"]):
        ws.write(0, c, h)
    data = [("Lớp 1D15", "Kha Bảo Ngọc", "02/03/2020", True, "Bán trú"),
            ("Lớp 1D15", "Mạc Trần Quỳnh Anh", "01/01/2020", False, "Không"),
            ("Lớp 1D16", "Lý Gia Hưng", "13/03/2020", True, "Không")]
    for r, (lop, name, dob, is_red, pl) in enumerate(data, 1):
        ws.write(r, 0, r)
        ws.write(r, 1, lop)
        ws.write(r, 2, name, red if is_red else xlwt.easyxf(""))
        ws.write(r, 3, dob)
        ws.write(r, 4, pl)
    wb.save(str(path))


def test_read_cdhs_xls_red_font(tmp_path):
    p = tmp_path / "cdhs.xls"
    _write_fake_cdhs_xls(p)
    rows = read_cdhs(p)
    assert [(r.lop, r.ho_ten, r.red) for r in rows] == [
        ("1D15", "Kha Bảo Ngọc", True), ("1D15", "Mạc Trần Quỳnh Anh", False), ("1D16", "Lý Gia Hưng", True)]


def test_read_cdhs_xlsx_red_font(tmp_path):
    p = tmp_path / "cdhs.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["TT", "Tên lớp học", "Họ tên", "Ngày sinh"])
    ws.append([1, "Lớp 1D15", "Kha Bảo Ngọc", "02/03/2020"])
    ws.append([2, "Lớp 1D16", "Em Mới", "05/05/2020"])
    ws["C3"].font = Font(color="FFFF0000")
    wb.save(p)
    assert [(r.lop, r.red) for r in read_cdhs(p)] == [("1D15", False), ("1D16", True)]


def test_xls_file_with_wrong_extension_is_read(tmp_path):
    p = tmp_path / "cdhs.xls"
    _write_fake_cdhs_xls(p)
    wrong = tmp_path / "ds_26_27.xlsx"
    wrong.write_bytes(p.read_bytes())
    assert [r.red for r in read_cdhs(wrong)] == [True, False, True]


def test_read_list_with_full_date_header_and_co_khong(tmp_path):
    """Dạng file giáo vụ đang dùng: Lớp | Họ tên | Ngày tháng năm sinh (ô ngày) | Bán trú (Có/Không)."""
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ tên", "Ngày tháng năm sinh", "Bán trú"])
    ws.append(["1D16", "Lý Gia Hưng A", dt.datetime(2020, 3, 13), "Có"])
    ws.append(["1D16", "Lý Gia Hưng B", dt.datetime(2020, 4, 24), "Có"])
    ws.append(["1D16", "Kiều Thanh Vy", dt.datetime(2020, 5, 15), "Không"])
    ws.freeze_panes = "A2"
    wb.save(p)
    rows = read_cdhs(p)
    assert [(r.lop, r.ho_ten, r.ngay_sinh, r.red) for r in rows] == [
        ("1D16", "Lý Gia Hưng A", "13/03/2020", True),
        ("1D16", "Lý Gia Hưng B", "24/04/2020", True),
        ("1D16", "Kiều Thanh Vy", "15/05/2020", False),
    ]


def test_other_name_column_and_match(tmp_path):
    """Cột "Tên gọi khác": GV báo "Mi Mi" thì app nhận ra em có tên nước ngoài (tên bịa); sổ ghi "Mi Mi"."""
    from app.core import matcher

    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ và tên", "Ngày sinh", "Ăn bán trú", "Tên gọi khác"])
    ws.append(["1D16", "Smith Emily", "01/02/2020", "có", "Mi Mi, Emmy"])
    ws.append(["1D16", "Kiều Thanh Vy", "15/05/2020", "có", None])
    wb.save(p)
    roster = load_list(p).roster
    sa, vy = roster.students
    assert sa.aliases() == ["Mi Mi", "Emmy"] and roster.display_name(sa) == "Mi Mi" and vy.ten_ghi_so == ""
    for q in ("Mi Mi", "emmy", "MI MI"):
        r = matcher.match_name(roster, "1D16", q)
        assert r.status == matcher.OK and r.student is sa, q


def test_same_full_name_letters_in_other_name_column(tmp_path):
    """Em trùng cả họ tên: file ghi họ tên thật, chữ A/B ở cột Tên gọi khác (tên bịa)."""
    from app.core import matcher

    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ và tên", "Ngày sinh", "Ăn bán trú", "Tên gọi khác"])
    ws.append(["1D16", "Lý Gia Hưng", "24/04/2020", "có", "Gia Hưng B"])
    ws.append(["1D16", "Lý Gia Hưng", "13/03/2020", "có", "Gia Hưng A"])
    ws.append(["1D16", "Kiều Thanh Vy", "15/05/2020", "có", None])
    wb.save(p)
    roster = load_list(p).roster
    b, a = roster.students[:2]
    assert (roster.display_name(a), roster.display_name(b)) == ("Gia Hưng A", "Gia Hưng B")
    for q, who in (("Gia Hưng A", a), ("Hưng A", a), ("Gia Hưng B", b), ("hưng B", b)):
        r = matcher.match_name(roster, "1D16", q)
        assert r.status == matcher.OK and r.student is who, q
    assert matcher.match_name(roster, "1D16", "Gia Hưng").status == matcher.AMBIGUOUS


def test_old_list_names_with_letter_still_match():
    from app.core import matcher
    from app.core.models import Roster

    roster = Roster()
    roster.students += [Student("HS1", "5D19", "Đinh Quốc Bảo A", "26/02/2016", True),
                        Student("HS2", "5D19", "Đinh Quốc Bảo B", "21/05/2016", True)]
    assert matcher.match_name(roster, "5D19", "Bảo B").student.id == "HS2"
    assert matcher.match_name(roster, "5D19", "Quốc Bảo").status == matcher.AMBIGUOUS
