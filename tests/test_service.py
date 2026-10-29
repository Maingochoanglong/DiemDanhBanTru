import datetime as dt

import pytest

from app.excel import sobook
from app.excel.database import AppData
from app.service import NeedMonthBook, Workspace, next_school_day
from tests.test_excel import make_book


@pytest.fixture
def ws(tmp_path, monkeypatch, roster):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    book = make_book(tmp_path / "SO DIEM DANH T10.xlsx")
    data = AppData(tmp_path / "DuLieu_BanTru.xlsx", roster)
    data.save()
    w = Workspace(tmp_path / "DuLieu_BanTru.xlsx")
    w.set_book(book)
    return w


def test_new_day_paste_save_reload(ws):
    day = dt.date(2026, 10, 29)
    st = ws.load_day(day)
    assert not st.exists_in_book and ws.template_name == "28"
    assert st.cd("4D21").note.startswith("Vũ Khoa")  # ghi chú mang sang ngày mới
    out = ws.paste("""Lớp 1D15 : 5/6
Vắng : Tuấn Anh
1D16 đủ
Vắng Duy Mạnh, Hải Long""")
    assert [o.message.cls for o in out] == ["1D15", "1D16", "2D17"]
    assert out[2].message.guessed
    assert ws.state.absent_names("2D17") == ["Duy Mạnh", "Hải Long"]
    assert ws.dirty
    assert ws.undo() and ws.state.absent_count("1D15") == 0
    ws.paste("Lớp 1D15 : 5/6 Vắng : Tuấn Anh")
    assert ws.save() == "29"

    st2 = ws.load_day(day)
    assert st2.exists_in_book
    assert st2.absent_names("1D15") == ["Tuấn Anh"]
    assert st2.cd("1D15").reported and not st2.cd("1D19").reported
    assert ws.print_areas() == ["A1:G21", "G20:O25"]


def test_month_change_needs_new_book(ws):
    with pytest.raises(NeedMonthBook):
        ws.load_day(dt.date(2026, 11, 2))
    new = ws.create_month_book(dt.date(2026, 11, 2))
    st = ws.load_day(dt.date(2026, 11, 2))
    assert st.exists_in_book and new.name == "SO DIEM DANH T11.xlsx"
    assert sobook.load_book(new).sheetnames == ["2"]


def test_ghep_text_assign(ws):
    ws.load_day(dt.date(2026, 10, 29))
    n, problems = ws.assign_ghep_text("1D19", "1.1: Bảo Ngọc, Gia Hân\n1.2 - Đức Anh, Minh Khang\nxyz")
    assert n == 4 and problems == ["Không hiểu dòng: xyz"]
    assert ws.meals().balanced


def test_next_school_day():
    assert next_school_day(dt.date(2026, 10, 30)) == dt.date(2026, 11, 2)
    assert next_school_day(dt.date(2026, 11, 2), -1) == dt.date(2026, 10, 30)


def test_zero_padded_sheet_name_and_data_file_locked(ws, tmp_path):
    from app.excel.files import lock_file

    from pathlib import Path

    book = Path(ws.settings["so_file"])
    wb = sobook.load_book(book)
    wb["28"].title = "01"  # sổ thật có sheet tên "01"
    wb["01"]["A3"] = "ĐIỂM DANH BÁN TRÚ NGÀY 01/10/2026"
    wb.save(book)
    st = ws.load_day(dt.date(2026, 10, 1))
    assert st.exists_in_book and ws.sheet_name == "01"
    ws.paste("Lớp 1D15 : 5/6 Vắng : Tuấn Anh")
    lock_file(ws.data.path).write_text("x")  # file dữ liệu đang mở trong Excel
    assert ws.save() == "01"
    assert "chưa ghi được file dữ liệu" in ws.warning and ws.data_dirty
    assert sobook.load_book(book)["01"]["G6"].value == "Tuấn Anh"


def test_schedule_cut_tomorrow_end_to_end(ws, roster):
    from app.core import schedule as sch

    ws.load_day(dt.date(2026, 10, 29))
    kid = next(s for s in ws.roster.students if s.ho_ten == "Tô Minh Khôi")
    note = ws.schedule(sch.CUT, "1D15", [kid.id], dt.date(2026, 10, 30))
    assert note == "Từ 30/10 cắt bán trú Tô Minh Khôi"
    assert ws.state.cd("1D15").note == note and ws.dirty
    assert ws.save() == "29"  # sĩ số hôm nay chưa đổi
    assert sobook.load_book(ws.book_path)["29"]["D6"].value == 6

    st = ws.load_day(dt.date(2026, 10, 30))
    assert st.si_so("1D15") == 5 and ws.si_so_conflicts() == []  # đổi theo lịch, không hỏi
    assert [i.student.ho_ten for i in st.scheduled_changes()] == ["Tô Minh Khôi"]
    assert st.cd("1D15").note == note  # ghi chú mang sang ngày sau
    ws.save()
    assert sobook.load_book(ws.book_path)["30"]["D6"].value == 5


def test_schedule_new_student_from_next_month(ws):
    from app.core import schedule as sch

    ws.load_day(dt.date(2026, 10, 29))
    ws.schedule(sch.ADD, "2D17", [], dt.date(2026, 11, 1), new_name="Em Chuyển Đến", new_dob="05/05/2019")
    s = next(s for s in ws.roster.students if s.ho_ten == "Em Chuyển Đến")
    assert s.lop == "2D17" and not s.is_boarding(dt.date(2026, 10, 30)) and s.is_boarding(dt.date(2026, 11, 2))
    back = AppData.load(ws.data.path)  # đã lưu vào file dữ liệu
    assert any(x.ho_ten == "Em Chuyển Đến" and x.bt_tu == dt.date(2026, 11, 1) for x in back.roster.students)
