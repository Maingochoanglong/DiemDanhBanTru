import datetime as dt
from pathlib import Path

import pytest

from app.excel import sobook
from app.service import NeedMonthBook, Workspace, next_school_day
from tests.conftest import make_workspace
from tests.test_excel import DAY28, make_book


@pytest.fixture
def ws(tmp_path, roster):
    return make_workspace(tmp_path, roster, make_book(tmp_path / "SO DIEM DANH T10.xlsx"))


def absent(ws, code, full):
    """Bấm chọn vắng 1 em (như bấm ô tên trong cửa sổ lớp)."""
    ws.push_undo()
    ws.state.set_absent(code, next(s.id for s in ws.roster.students if s.ho_ten == full), True)


def test_new_day_click_save_reload(ws):
    day = dt.date(2026, 10, 29)
    st = ws.load_day(day)
    assert not st.exists_in_book and ws.template_name == "28"
    assert st.cd("4D21").note.startswith("Vũ Khoa")  # ghi chú mang sang ngày mới
    absent(ws, "1D15", "Lâm Quốc Tuấn Anh")
    ws.push_undo()
    ws.state.mark_full("1D16")
    absent(ws, "2D17", "Viên Duy Mạnh")
    absent(ws, "2D17", "Khổng Hải Long")
    assert ws.state.absent_names("2D17") == ["Duy Mạnh", "Hải Long"]
    assert ws.dirty
    assert ws.undo() and ws.undo() and ws.state.absent_count("2D17") == 0  # bỏ 2 lần bấm
    assert ws.state.absent_names("1D15") == ["Tuấn Anh"]
    assert ws.save() == "29"

    st2 = ws.load_day(day)
    assert st2.exists_in_book
    assert st2.absent_names("1D15") == ["Tuấn Anh"]
    assert st2.cd("1D15").reported and st2.cd("1D19").reported  # sổ đã có tên vắng: coi như các lớp đã báo
    assert not ws.temp_path().exists()  # lưu xong thì xóa sổ tạm


def test_month_change_needs_new_book(ws):
    with pytest.raises(NeedMonthBook):
        ws.load_day(dt.date(2026, 11, 2))
    new = ws.create_month_book(dt.date(2026, 11, 2))
    st = ws.load_day(dt.date(2026, 11, 2))
    assert st.exists_in_book and new.name == "SO DIEM DANH T11.xlsx"
    assert sobook.load_book(new).sheetnames == ["2"]


def test_ghep_groups_from_list_column(ws):
    ws.load_day(dt.date(2026, 10, 29))
    groups = {"Châu Bảo Ngọc": "1.1", "Phùng Gia Hân": "1.1", "Tạ Đức Anh": "1.2", "Quách Minh Khang": "1.2"}
    for s in ws.roster.students:
        s.an_ghep = groups.get(s.ho_ten, s.an_ghep)
    st = ws.state
    st.set_absent("1D19", next(s.id for s in ws.roster.students if s.ho_ten == "Tạ Đức Anh"), True)
    m = ws.meals()
    assert m.balanced and not m.ask


def test_reopen_day_infers_ghep_group_from_book(ws):
    day = dt.date(2026, 10, 29)
    st = ws.load_day(day)
    sid = next(s.id for s in ws.roster.students if s.ho_ten == "Phùng Gia Hân")
    ws.push_undo()
    st.set_absent("1D19", sid, True)
    assert [s.ho_ten for _, s in ws.meals().ask] == ["Phùng Gia Hân"] and not ws.meals().balanced
    st.pick_ghep(sid, "1.2")
    assert ws.meals().balanced
    assert ws.save() == "29"
    assert sobook.load_book(ws.book_path)["29"]["M24"].value == 1  # hàng 1.2 ghép, cột vắng
    st2 = ws.load_day(day)  # mở lại: sổ ghi 1 vắng ở 1.2, em vắng chưa có nhóm -> suy ra em đó ăn 1.2
    assert st2.ghep_pick == {sid: "1.2"} and ws.meals().balanced and not ws.meals().ask


def test_next_school_day():
    assert next_school_day(dt.date(2026, 10, 30)) == dt.date(2026, 11, 2)
    assert next_school_day(dt.date(2026, 11, 2), -1) == dt.date(2026, 10, 30)


def test_zero_padded_sheet_name(ws, tmp_path):
    from pathlib import Path

    book = Path(ws.settings["so_file"])
    wb = sobook.load_book(book)
    wb["28"].title = "01"  # sổ thật có sheet tên "01"
    wb["01"]["A3"] = "ĐIỂM DANH BÁN TRÚ NGÀY 01/10/2026"
    wb.save(book)
    st = ws.load_day(dt.date(2026, 10, 1))
    assert st.exists_in_book and ws.sheet_name == "01"
    absent(ws, "1D15", "Lâm Quốc Tuấn Anh")
    assert ws.save() == "01"
    assert sobook.load_book(book)["01"]["G6"].value == "Tuấn Anh"


def test_cut_and_add_from_note_column_end_to_end(tmp_path, roster):
    """Cột Ghi chú của file danh sách: "cắt từ 30/10" (Tô Minh Khôi), "ăn từ 2/11" (em chưa ăn BT)."""
    kid = next(s for s in roster.students if s.ho_ten == "Tô Minh Khôi")
    kid.cat_tu = dt.date(2026, 10, 30)
    new = next(s for s in roster.students if s.ho_ten == "Mạc Trần Quỳnh Anh")
    new.ban_tru, new.bt_tu = True, dt.date(2026, 11, 2)
    ws = make_workspace(tmp_path, roster, make_book(tmp_path / "SO DIEM DANH T10.xlsx"))
    kid, new = (next(s for s in ws.roster.students if s.ho_ten == n) for n in ("Tô Minh Khôi", "Mạc Trần Quỳnh Anh"))
    assert kid.cat_tu == dt.date(2026, 10, 30) and new.bt_tu == dt.date(2026, 11, 2) and not new.is_boarding(dt.date(2026, 10, 30))
    ws.load_day(dt.date(2026, 10, 29))
    assert ws.save() == "29"  # sĩ số hôm nay chưa đổi
    assert sobook.load_book(ws.book_path)["29"]["D6"].value == 6
    st = ws.load_day(dt.date(2026, 10, 30))
    assert st.si_so("1D15") == 5 and ws.si_so_conflicts() == []  # đổi theo ghi chú, không hỏi
    assert [s.ho_ten for s in st.scheduled_changes()] == ["Tô Minh Khôi"]
    ws.save()
    assert sobook.load_book(ws.book_path)["30"]["D6"].value == 5


def test_list_file_edited_is_read_again(ws, tmp_path, roster):
    """Sửa file danh sách bằng Excel (thêm "cắt thứ 6"): mở ngày là app đọc lại, không cần nhập lại."""
    import os

    from tests.conftest import write_list

    ws.load_day(dt.date(2026, 10, 30))
    assert not ws.state.auto_absent("1D15")
    roster.students[0].cat_thu6 = True
    path = write_list(tmp_path / "DanhSach.xlsx", roster)
    os.utime(path, ns=(1, os.stat(path).st_mtime_ns + 10**9))
    st = ws.load_day(dt.date(2026, 10, 30))  # thứ 6
    assert list(st.auto_absent("1D15").values()) == ["cắt thứ 6"]


def test_si_so_unchanged_after_save_with_scheduled_cut(ws):
    """Sĩ số đổi theo lịch cắt (3 -> 2) phải giữ nguyên sau khi lưu, không quay về sĩ số sheet mẫu."""
    day = dt.date(2026, 10, 29)
    s = next(x for x in ws.roster.students if x.ho_ten == "Tô Minh Khôi")
    s.cat_tu = day
    st = ws.load_day(day)
    assert st.si_so("1D15") == 5 and not ws.si_so_conflicts()
    ws.save()
    assert ws.state.si_so("1D15") == 5
    assert ws.meals().balanced
    assert ws.load_day(day).si_so("1D15") == 5


def test_note_no_message_does_not_mark_full(ws):
    """Lớp ghi chú "Không nói gì là đủ": đủ hay vắng vẫn do giáo vụ bấm, app không tự tính đủ."""
    book = ws.book_path or __import__("pathlib").Path(ws.settings["so_file"])
    wb = sobook.load_book(book)
    info = sobook.analyze(wb["28"])
    info.cell("2D17", "ghichu").value = "Không nói gì là đủ"
    wb.save(book)
    st = ws.load_day(dt.date(2026, 10, 29))
    assert "2D17" in st.unreported() and "1D15" in st.unreported()


def test_blank_sheet_made_in_advance_is_not_reported(ws):
    """Sheet tạo sẵn trong sổ còn trống: các lớp vẫn chưa báo. Sheet đã ghi tên vắng (trước khi dùng app): đã báo."""
    book = ws.book_path or __import__("pathlib").Path(ws.settings["so_file"])
    wb = sobook.load_book(book)
    blank = sobook.create_day_sheet(wb, dt.date(2026, 10, 29), wb["28"])
    sobook.analyze(blank)
    wb.save(book)
    st = ws.load_day(dt.date(2026, 10, 29))
    assert st.exists_in_book and len(st.unreported()) == len(st.classes)
    st28 = ws.load_day(DAY28)
    assert not st28.unreported()


def test_reset_day(ws):
    st = ws.load_day(DAY28)  # sổ có tên vắng: app coi như đã báo
    assert not st.unreported() and st.absent_names("1D15") == ["Tuấn Anh"]
    ws.reset_day()
    assert len(ws.state.unreported()) == len(ws.state.classes) and ws.state.absent_names("1D15") == []
    assert ws.state.cd("4D21").note.startswith("Vũ Khoa") and ws.dirty  # ghi chú giữ nguyên
    assert ws.undo() and ws.state.absent_names("1D15") == ["Tuấn Anh"]


def test_new_download_must_set_up_again(tmp_path, monkeypatch, roster):
    """Bản .exe mới tải về (mã bản dựng khác): phải chọn lại sổ và file danh sách; cài đặt ở CaiDat.txt."""
    from app import build_info, settings
    from tests.conftest import write_list

    cfg = tmp_path / "CaiDat.txt"
    settings.save(cfg, {"so_file": "C:/so cu.xlsx", "build": "aaaaaaa"})
    monkeypatch.setattr(settings, "default_path", lambda: cfg)
    monkeypatch.setattr(build_info, "BUILD", "bbbbbbb")

    w = Workspace()
    assert w.setup_needed and not w.roster.students
    with pytest.raises(ValueError, match="chọn sổ điểm danh"):
        w.finish_setup()
    w.set_book(make_book(tmp_path / "SO DIEM DANH T10.xlsx"))
    w.set_list(write_list(tmp_path / "DS.xlsx", roster))
    w.finish_setup()
    assert not w.setup_needed and settings.load(cfg)["build"] == "bbbbbbb" and len(w.roster.students) == len(roster.students)
    assert "so_file = " in cfg.read_text(encoding="utf-8") and not Workspace().setup_needed  # mở lại cùng bản: không hỏi nữa


def test_old_sheet_name_of_kid_no_longer_boarding(ws):
    """Sổ cũ ghi vắng em nay đã cắt bán trú (vd. Vũ Khoa 4D21): app báo "không ăn BT", không phải tên lạ."""
    from app.web.api import Api

    s = next(x for x in ws.roster.students if x.ho_ten == "Ninh Vũ Khoa")
    s.ban_tru = False
    st = ws.load_day(DAY28)
    c = st.cd("4D21")
    assert c.not_bt == ["Vũ Khoa"] and c.extra == [] and st.class_warnings("4D21") == []
    assert st.absent_names("4D21") == ["Vũ Khoa"]  # giữ như sổ khi lưu lại
    api = Api(ws)
    row = next(r for r in api.state()["rows"] if r.get("code") == "4D21")
    assert row["status"] != "err" and row["not_bt"] == "Vũ Khoa"
    assert api.class_detail("4D21")["not_bt"] == ["Vũ Khoa"]


def test_day_saved_with_every_class_full_reopens_as_reported(ws):
    """Lưu ngày mà lớp nào cũng đủ (sổ không có tên vắng nào): mở lại vẫn là "đã báo" (sổ tự nhớ sheet app đã lưu)."""
    day = dt.date(2026, 10, 29)
    st = ws.load_day(day)
    ws.push_undo()
    for code in st.classes:
        st.mark_full(code)
    st.cd("4D21").note = ""
    assert ws.save() == "29"
    assert "29" in sobook.saved_sheets(sobook.load_book(ws.book_path))
    assert not ws.load_day(day).unreported()


def test_settings_not_writable_gives_clear_message(tmp_path, monkeypatch):
    """Thư mục cạnh .exe không ghi được: báo rõ cách sửa (không ghi CaiDat.txt ở chỗ khác)."""
    from app import settings

    def denied(self, *a, **k):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(Path, "write_text", denied)
    with pytest.raises(OSError, match="thư mục ghi được"):
        settings.save(tmp_path / "CaiDat.txt", {})
