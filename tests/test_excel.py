import datetime as dt

import openpyxl
import pytest
from openpyxl.styles import Font

from app.core.day import DayState
from app.core.models import Student
from app.excel import sobook
from app.excel.database import AppData, short_codes
from app.excel.files import FileLockedError, lock_file, safe_save
from app.excel.roster_import import apply_changes, diff_roster, flag_mismatches, read_cdhs

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
    sobook.save_book(wb, book)

    wb2 = sobook.load_book(book)
    ws2 = wb2["29"]
    rec = sobook.read_records(sobook.analyze(ws2))
    assert (rec["1D15"].si_so, rec["1D15"].vang, rec["1D15"].names, rec["1D15"].note) == (6, 1, "Tuấn Anh", "ghi chú thử")
    assert rec["1D19"].names == "Đức Anh"
    assert ws2["M24"].value == 1 and ws2["M23"].value is None and ws2["O24"].value == 2
    assert [s.sheet_view.tabSelected for s in wb2.worksheets] == [False, True]
    assert (book.parent / "SaoLuu").is_dir()  # đã sao lưu bản cũ


def test_new_day_sheet_black_names_and_keeps_count_formula(book, roster):
    """Sổ có cột Vắng là công thức đếm tên, và tên hôm trước tô đỏ: sheet ngày mới giữ công thức, tên chữ đen."""
    count = '=IF(TRIM(G{r})="",0,LEN(TRIM(G{r}))-LEN(SUBSTITUTE(TRIM(G{r}),",",""))+1)'
    wb = sobook.load_book(book)
    tpl = wb["28"]
    for r in (6, 7, 8):
        tpl[f"E{r}"] = count.format(r=r)
    tpl["G6"].font = Font(name="Times New Roman", color="FFFF0000")
    sobook.save_book(wb, book)

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
    lock_file(book).write_text("x")
    wb = sobook.load_book(book)
    with pytest.raises(FileLockedError):
        safe_save(wb, book)


def test_app_data_roundtrip(tmp_path, roster):
    roster.students[0].cat_thu6 = True
    roster.students[0].cat_tu = dt.date(2026, 11, 1)
    roster.students[1].an_ghep = "1.2"
    data = AppData(tmp_path / "DuLieu_BanTru.xlsx", roster)
    data.settings["so_folder"] = str(tmp_path)
    data.set_log(DAY28, "1D15", True, 6, ["Tuấn Anh"])
    data.save()
    back = AppData.load(tmp_path / "DuLieu_BanTru.xlsx")
    s0, s1 = back.roster.students[0], back.roster.students[1]
    assert (s0.ho_ten, s0.cat_thu6, s0.cat_tu, s0.ban_tru) == ("Kha Bảo Ngọc", True, dt.date(2026, 11, 1), True)
    assert s1.an_ghep == "1.2"
    assert len(back.roster.students) == len(roster.students)
    assert back.settings["so_folder"] == str(tmp_path)
    assert back.reported_flags(DAY28) == {"1D15": True}
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
    assert [r.ho_ten for r in flag_mismatches(rows)] == ["Lý Gia Hưng"]


def test_read_cdhs_xlsx_and_diff(tmp_path, roster):
    p = tmp_path / "cdhs.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["TT", "Tên lớp học", "Họ tên", "Ngày sinh"])
    ws.append([1, "Lớp 1D15", "Kha Bảo Ngọc", "02/03/2020"])  # thôi ăn BT (không đỏ)
    ws.append([2, "Lớp 1D16", "Mạc Trần Quỳnh Anh", "01/01/2020"])  # đổi lớp
    ws.append([3, "Lớp 1D16", "Em Mới", "05/05/2020"])
    ws["C4"].font = Font(color="FFFF0000")
    wb.save(p)
    rows = read_cdhs(p)
    assert [r.red for r in rows] == [False, False, True]
    changes = diff_roster(roster, rows)
    kinds = sorted(c.kind for c in changes)
    assert kinds.count("removed") == len(roster.students) - 2
    assert {"new", "class", "boarding"} <= set(kinds)
    n_before = len(roster.students)
    apply_changes(roster, changes)  # mặc định không xóa HS vắng mặt trong file mới
    assert len(roster.students) == n_before + 1
    assert roster.students[0].ban_tru is False and roster.students[5].lop == "1D16"


def test_old_data_file_with_removed_columns_still_loads(tmp_path):
    """File dữ liệu bản cũ còn 2 cột vắng dài hạn: đọc theo tên cột nên không lệch."""
    p = tmp_path / "cu.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "HocSinh"
    ws.append(["Mã", "Lớp", "Họ tên", "Ngày sinh", "Bán trú (x)", "Tên ghi sổ (sửa tay)", "Lớp tính BT", "Ăn ghép tại",
               "Cắt thứ 6 (x)", "Vắng dài hạn từ", "Vắng dài hạn đến", "Ăn BT từ ngày", "Cắt BT từ ngày", "Ghi chú"])
    ws.append(["HS0001", "1D15", "Kha Bảo Ngọc", "02/03/2020", "x", "", "", "1.2", "x", "10/10/2026", "", "", "01/11/2026", "gc"])
    wb.save(p)
    s = AppData.load(p).roster.students[0]
    assert (s.ban_tru, s.an_ghep, s.cat_thu6, s.cat_tu, s.ghi_chu) == (True, "1.2", True, dt.date(2026, 11, 1), "gc")


def test_simple_list_reimport_keeps_cuts_and_ghep(tmp_path, roster):
    """Nhập lại file danh sách đơn giản: em đã có lịch cắt thì không bị đổi; file không có cột ghép thì giữ ghép cũ."""
    roster.students[13].an_ghep = "1.1"  # Châu Bảo Ngọc 1D19
    roster.students[0].cat_tu = dt.date(2026, 11, 1)  # Kha Bảo Ngọc: tháng 11 cắt
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ và tên", "Ngày sinh", "Ăn bán trú"])
    for s in roster.students:
        ws.append([s.lop, s.ho_ten, s.ngay_sinh, "có" if s.is_boarding(dt.date(2026, 11, 2)) else "không"])
    wb.save(p)
    rows = read_cdhs(p)
    by = {r.ho_ten: r for r in rows}
    assert by["Châu Bảo Ngọc"].red and by["Châu Bảo Ngọc"].ghep is None
    assert not by["Kha Bảo Ngọc"].red and not by["Mạc Trần Quỳnh Anh"].red
    changes = diff_roster(roster, rows)
    assert not [c for c in changes if c.kind in ("boarding", "ghep", "new")]


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


def test_other_name_column_import_and_match(tmp_path, roster):
    """Cột "Tên gọi khác": GV báo "Mi Mi" thì app nhận ra em có tên nước ngoài (tên bịa); sổ ghi "Mi Mi"."""
    from app.core import matcher

    roster.students.append(Student("HS900", "1D16", "Smith Emily", "01/02/2020", True))
    roster.invalidate()
    assert matcher.match_name(roster, "1D16", "Mi Mi").status == matcher.NOT_FOUND
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ và tên", "Ngày sinh", "Ăn bán trú", "Tên gọi khác"])
    ws.append(["1D16", "Smith Emily", "01/02/2020", "có", "Mi Mi, Emmy"])
    ws.append(["1D16", "Kiều Thanh Vy", "15/05/2020", "có", None])  # ô trống: file Excel là gốc -> bỏ tên gọi cũ
    wb.save(p)
    vy = next(s for s in roster.students if s.ho_ten == "Kiều Thanh Vy")
    vy.ten_ghi_so = "Vy Vy"
    rows = read_cdhs(p)
    assert [r.ten_goi for r in rows] == ["Mi Mi, Emmy", ""]
    changes = [c for c in diff_roster(roster, rows) if c.kind == "ten_goi"]
    assert [c.text for c in changes] == ['Smith Emily (1D16): tên gọi khác "Mi Mi, Emmy"',
                                         "Kiều Thanh Vy (1D16): bỏ tên gọi khác"]
    apply_changes(roster, changes)
    assert vy.ten_ghi_so == ""
    sa = roster.by_id("HS900")
    assert sa.aliases() == ["Mi Mi", "Emmy"] and roster.display_name(sa) == "Mi Mi"
    for q in ("Mi Mi", "emmy", "MI MI"):
        r = matcher.match_name(roster, "1D16", q)
        assert r.status == matcher.OK and r.student is sa, q
    # lưu / mở lại file dữ liệu
    AppData(tmp_path / "DuLieu.xlsx", roster).save()
    again = AppData.load(tmp_path / "DuLieu.xlsx").roster.by_id("HS900")
    assert again.ten_ghi_so == "Mi Mi, Emmy"


def test_same_full_name_letters_move_to_other_name_column(tmp_path):
    """Em trùng cả họ tên: file mới ghi họ tên thật, chữ A/B ở cột Tên gọi khác (tên bịa).

    App nhận ra đó là em cũ ("Lý Gia Hưng A" -> "Lý Gia Hưng"), không thêm em mới / bỏ em cũ."""
    from app.core import matcher
    from app.core.models import Roster

    roster = Roster()
    roster.students += [Student("HS1", "1D16", "Lý Gia Hưng A", "13/03/2020", True),
                        Student("HS2", "1D16", "Lý Gia Hưng B", "24/04/2020", True),
                        Student("HS3", "1D16", "Kiều Thanh Vy", "15/05/2020", True)]
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ và tên", "Ngày sinh", "Ăn bán trú", "Tên gọi khác"])
    ws.append(["1D16", "Lý Gia Hưng", "24/04/2020", "có", "Gia Hưng B"])
    ws.append(["1D16", "Lý Gia Hưng", "13/03/2020", "có", "Gia Hưng A"])
    ws.append(["1D16", "Kiều Thanh Vy", "15/05/2020", "có", None])
    wb.save(p)
    changes = diff_roster(roster, read_cdhs(p))
    assert sorted(c.kind for c in changes) == ["rename", "rename", "ten_goi", "ten_goi"]
    apply_changes(roster, changes)
    a, b = roster.by_id("HS1"), roster.by_id("HS2")
    assert a.ho_ten == b.ho_ten == "Lý Gia Hưng"
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


def _assert_plain(ws):
    """Kiểu đơn giản: Times New Roman, chữ đen, viền đen, không tô nền, không cố định dòng, không lọc."""
    assert ws.freeze_panes is None and ws.auto_filter.ref is None
    for row in ws.iter_rows(max_row=min(ws.max_row, 6)):
        for c in row:
            assert c.font.name == "Times New Roman" and c.font.color.rgb == "FF000000"
            assert c.border.left.style == "thin" and c.border.bottom.color.rgb == "FF000000"
            assert c.fill.fill_type is None


def test_data_file_is_plain_style(tmp_path, roster):
    from app.excel.database import AppData

    d = AppData(tmp_path / "DuLieu.xlsx", roster)
    d.set_log(dt.date(2026, 10, 29), "1D15", True, 31, ["Tuấn Anh"])
    d.save()
    wb = openpyxl.load_workbook(tmp_path / "DuLieu.xlsx")
    for name in ("HocSinh", "Lop", "NhatKy", "CaiDat"):
        _assert_plain(wb[name])
    again = AppData.load(tmp_path / "DuLieu.xlsx")
    assert len(again.roster.students) == len(roster.students)
