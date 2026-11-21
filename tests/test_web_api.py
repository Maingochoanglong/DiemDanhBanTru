"""Cầu nối giao diện web ↔ phần xử lý sổ (app/web/api.py). Dữ liệu tên bịa."""

import datetime as dt
import json

import openpyxl
import pytest

from app.service import Workspace
from app.web.api import Api
from tests.conftest import make_workspace
from tests.test_excel import make_book


@pytest.fixture
def api(tmp_path, roster):
    ws = make_workspace(tmp_path, roster, make_book(tmp_path / "SO DIEM DANH T10.xlsx"))
    a = Api(ws)
    assert "state" in a.open_day("2026-10-29")
    return a


def sid_of(api, code, name):
    d = api.class_detail(code)
    return next(n["id"] for n in d["names"] if n["full"] == name)


def test_state_has_book_columns_and_is_json(api):
    st = api.state()
    json.dumps(st)  # gửi được sang giao diện
    assert st["date_text"] == "29/10/2026" and st["weekday"] == "Thứ 5"
    row = next(r for r in st["rows"] if r.get("code") == "1D15")
    assert {"gvcn", "si", "vang", "hd", "ten", "note", "status"} <= set(row)
    assert row["status"] == "todo" and not row["reported"]
    assert any(r["kind"] == "khoi" for r in st["rows"])
    assert st["hint"] == ""


def test_click_names_then_save(api):
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    r = api.set_absent("1D15", sid, True)
    row = next(x for x in r["state"]["rows"] if x.get("code") == "1D15")
    assert row["vang"] == 1 and row["ten"] == "Tuấn Anh" and row["status"] == "absent"
    assert r["detail"]["vang"] == 1 and next(n for n in r["detail"]["names"] if n["id"] == sid)["absent"]
    assert r["state"]["dirty"]
    r = api.set_absent("1D15", sid, False)
    assert r["detail"]["vang"] == 0
    api.set_absent("1D15", sid, True)
    out = api.save()
    while "conflicts" in out:  # sổ giả có thể lệch sĩ số: giữ như sổ
        out = api.save("keep")
    assert "ok" in out and not out["state"]["dirty"]
    assert "29" in out["ok"]
    # mở lại ngày đã lưu
    again = api.open_day("2026-10-29")["state"]
    assert again["exists"] and next(x for x in again["rows"] if x.get("code") == "1D15")["ten"] == "Tuấn Anh"


def test_day_change_asks_when_unsaved(api):
    sid = sid_of(api, "1D16", "Kiều Thanh Vy")
    api.set_absent("1D16", sid, True)
    r = api.step_day(1)
    assert r == {"ask_save": {"day": "29/10/2026", "target": "2026-10-30"}}
    r = api.step_day(1, True)
    assert r["state"]["date"] == "2026-10-30"


def test_mark_full_note_undo(api):
    r = api.mark_full("2D17")
    assert next(x for x in r["state"]["rows"] if x.get("code") == "2D17")["status"] == "done"
    r = api.set_note("2D17", "  ghi  chú ")
    assert r["detail"]["note"] == "ghi chú"
    r = api.undo()
    assert next(x for x in r["state"]["rows"] if x.get("code") == "2D17")["note"] != "ghi chú"


def test_new_month_asks_to_create_book(api):
    r = api.open_day("2026-11-02", True)
    assert r["need_month"]["month"] == 11 and r["need_month"]["prev"] == "SO DIEM DANH T10.xlsx"
    r = api.create_month_book("2026-11-02")
    assert r["state"]["book"] == "SO DIEM DANH T11.xlsx" and r["flash"].startswith("Đã tạo sổ mới")


def test_students_lookup(api):
    rows = api.students("long", "", True)["rows"]
    assert [r["ten"] for r in rows] == ["Khổng Hải Long"]
    for name in ("save_student", "export_list", "import_list", "schedules", "add_schedule", "save_meal_groups"):
        assert not hasattr(api, name)  # thêm / sửa học sinh, nhóm ăn: sửa trong file Excel danh sách (lịch: set_schedule)


def test_choose_list_reads_file_directly(api, tmp_path):
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ tên", "Ngày tháng năm sinh", "Bán trú", "Cắt thứ 6", "Ghi chú"])
    ws.append(["1D15", "Kha Bảo Ngọc", dt.datetime(2020, 3, 2), "Có", "x", "mẹ đón sớm"])
    ws.append(["1D15", "Bùi Văn Mới", dt.datetime(2020, 1, 1), "Có", None, None])
    wb.save(p)
    r = api.choose_list(str(p))
    assert r["flash"] == "Đã chọn ds.xlsx: 2 học sinh." and api.settings()["cdhs_file"] == str(p)
    rows = api.students("", "", False)["rows"]
    assert [(x["ten"], x["lich"], x["gc"]) for x in rows] == [("Kha Bảo Ngọc", "cắt thứ 6", "mẹ đón sớm"), ("Bùi Văn Mới", "", "")]
    bad = tmp_path / "sai.xlsx"
    openpyxl.Workbook().save(bad)
    assert "error" in api.choose_list(str(bad)) and api.settings()["cdhs_file"] == str(p)  # file sai: giữ file cũ


def test_save_blocked_when_names_unclear(api):
    st = api._ws.state
    from app.core import matcher

    res = matcher.MatchResult("Xyz Không Có", matcher.NOT_FOUND)
    st.pending.append(("1D15", res))
    api._ws.dirty = True
    out = api.save()
    assert out["blocked"]["n"] == 1 and out["blocked"]["code"] == "1D15"
    d = api.class_detail("1D15")
    assert d["pending"][0]["query"] == "Xyz Không Có"
    r = api.resolve("1D15", d["pending"][0]["idx"], "skip")
    assert r["detail"]["pending"] == [] and api.state()["unresolved"] == 0


def test_temp_book_autosaves_and_is_removed_after_save(api, tmp_path):
    ws = api._ws
    temp = tmp_path / "SO DIEM DANH T10 tamthoi.xlsx"
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    api.set_absent("1D15", sid, True)
    assert temp.exists()  # ghi ngay sau mỗi thao tác
    api.set_note("1D15", "ghi chú tạm")
    assert temp.exists() and ws.temp_saved_at and not ws.temp_error
    wb = openpyxl.load_workbook(temp)
    assert wb["TAMTHOI"].sheet_state == "hidden" and len(wb.sheetnames) == 2  # file gọn, không chép cả sổ
    view = wb["Dang diem danh"]
    assert any("Tuấn Anh" in str(c.value) for row in view.iter_rows() for c in row if c.value)
    assert temp.stat().st_size < 20_000
    assert api.state()["temp_at"] == ws.temp_saved_at  # giao diện hiện giờ lưu tạm
    out = api.save()
    while "conflicts" in out:
        out = api.save("keep")
    assert "ok" in out and not temp.exists()


def test_restore_after_power_loss(api, tmp_path):
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    api.set_absent("1D15", sid, True)
    api.mark_full("2D17")
    api.set_note("2D17", "ghi chú tạm")
    temp = tmp_path / "SO DIEM DANH T10 tamthoi.xlsx"
    assert temp.exists()

    # mở lại app (lần trước tắt đột ngột, chưa lưu vào sổ)
    a2 = Api(Workspace(tmp_path / "CaiDat.txt"))
    r = a2.boot()
    assert r["restore"]["day"] == "29/10/2026" and r["restore"]["file"] == temp.name
    r = a2.restore_temp(True)
    st = r["state"]
    assert st["date"] == "2026-10-29" and st["dirty"]
    row = next(x for x in st["rows"] if x.get("code") == "1D15")
    assert row["vang"] == 1 and row["ten"] == "Tuấn Anh"
    row = next(x for x in st["rows"] if x.get("code") == "2D17")
    assert row["status"] == "done" and row["note"] == "ghi chú tạm"
    assert temp.exists()  # vẫn giữ cho tới khi lưu vào sổ

    # mở lại lần nữa và chọn bỏ bản lưu tạm
    a3 = Api(Workspace(tmp_path / "CaiDat.txt"))
    assert a3.boot()["restore"]
    a3.restore_temp(False)
    assert not temp.exists() and "restore" not in Api(Workspace(tmp_path / "CaiDat.txt")).boot()


def test_temp_removed_when_changes_discarded(api, tmp_path):
    sid = sid_of(api, "1D16", "Kiều Thanh Vy")
    api.set_absent("1D16", sid, True)
    temp = tmp_path / "SO DIEM DANH T10 tamthoi.xlsx"
    assert temp.exists()
    api.step_day(1, True)  # đổi ngày, chọn Không lưu
    assert not temp.exists()
    api.set_absent("1D16", sid_of(api, "1D16", "Kiều Thanh Vy"), True)
    assert temp.exists()
    api.discard_temp()  # thoát app, chọn Không lưu
    assert not temp.exists()


def test_pick_unknown_name_from_whole_class(api):
    """Tên trong sổ không khớp ai: chọn em trong lớp. App không tự đặt tên gọi khác (chỉ lấy từ file Excel)."""
    from app.core import matcher

    st = api._ws.state
    res = matcher.match_name(api._ws.roster, "1D15", "Bé Bông")
    assert res.status == matcher.NOT_FOUND
    st.pending.append(("1D15", res))
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    d = api.class_detail("1D15")
    r = api.resolve("1D15", d["pending"][0]["idx"], "pick", sid)
    assert r["detail"]["pending"] == [] and next(n for n in r["detail"]["names"] if n["id"] == sid)["absent"]
    assert api._ws.roster.by_id(sid).ten_ghi_so == ""


def test_state_lists_unreported_classes(api):
    st = api.state()
    assert "1D15" in st["unreported"]
    assert st["unreported"] == [r["code"] for r in st["rows"] if r["kind"] == "class" and not r["reported"]]
    api.mark_full("1D15")
    assert "1D15" not in api.state()["unreported"]


def test_class_detail_lists_non_boarding_students_with_reason(api):
    d = api.class_detail("1D15")
    assert all(n["full"] != "Mạc Trần Quỳnh Anh" for n in d["names"])
    o = next(x for x in d["others"] if "Mạc Trần Quỳnh Anh" in x["s"])
    assert o["why"] == "Không ăn bán trú"


def test_pick_ghep_group_and_keep_it_in_temp_book(api, tmp_path):
    sid = sid_of(api, "1D19", "Phùng Gia Hân")
    api.set_absent("1D19", sid, True)
    m = api.meals()
    assert [a["full"] for a in m["ask"]] == ["Phùng Gia Hân"] and m["ask"][0]["groups"] == ["1.1", "1.2"]
    assert not m["ok"] and api.state()["meal"]["ask"] == 1
    r = api.pick_ghep(sid, "1.2")
    assert r["meals"]["ok"] and not r["meals"]["ask"] and r["state"]["meal"]["ask"] == 0
    line = next(x for x in r["meals"]["lines"] if x["code"] == "1.2")
    assert line["absent"] == [{"sid": sid, "name": "Gia Hân", "picked": True}] and "em ghép lớp 1D19" in line["gom"]
    assert r["meals"]["groups_total"] + (r["meals"]["self"] or {}).get("meals", 0) == r["meals"]["total"]

    a2 = Api(Workspace(tmp_path / "CaiDat.txt"))  # mất điện, mở lại app: nhóm đã chọn vẫn còn
    a2.boot()
    a2.restore_temp(True)
    assert a2._ws.state.ghep_pick == {sid: "1.2"} and a2.meals()["ok"]


def test_meals_show_ghep_list_progress(api):
    g = {x["code"]: x for x in api.meals()["ghep"]}
    assert (g["1D19"]["n"], g["1D19"]["done"]) == (4, 0)
    for name in ("ghep", "assign_ghep", "assign_ghep_text", "undo_friday"):
        assert not hasattr(api, name)  # nhóm ghép: chỉ ghi ở file Excel danh sách


def test_save_check_gathers_all_questions(api):
    ck = api.save_check()
    assert "1D15" in ck["unreported"] and ck["meal"] is None and ck["conflicts"] == []
    sid = sid_of(api, "1D19", "Phùng Gia Hân")
    api.set_absent("1D19", sid, True)  # em ghép chưa có nhóm vắng -> suất ăn lệch
    ck = api.save_check()
    assert ck["meal"] == {"total": ck["meal"]["present"] + 1, "present": ck["meal"]["present"], "ask": 1}


def test_friday_class_with_only_auto_absent_is_still_unreported(api):
    kid = next(s for s in api._ws.roster.students if s.ho_ten == "Lục Thảo Mi")  # 4D19
    kid.cat_thu6 = True
    api.open_day("2026-10-30", True)  # thứ 6
    row = next(r for r in api.state()["rows"] if r.get("code") == "4D19")
    assert not row["reported"] and row["status"] == "todo" and row["auto"] == "Thảo Mi" and row["ten"] == ""
    ck = api.save_check()
    assert "4D19" in ck["unreported"] and ck["unreported_auto"] == ["4D19"]



def test_change_files_refused_while_day_unsaved(api, tmp_path):
    """Đổi sổ / file danh sách khi còn thay đổi chưa lưu: không cho (tránh mất thay đổi, xóa nhầm sổ tạm)."""
    api.set_absent("1D15", sid_of(api, "1D15", "Lâm Quốc Tuấn Anh"), True)
    before = dict(api._ws.settings)
    for r in (api.choose_book(str(tmp_path / "khac.xlsx")), api.choose_list(str(tmp_path / "khac.xlsx"))):
        assert "chưa lưu" in r["error"]
    assert api._ws.settings == before and api._ws.dirty and (tmp_path / "SO DIEM DANH T10 tamthoi.xlsx").exists()


def test_book_must_be_xlsx(api, tmp_path):
    assert ".xlsx" in api.choose_book(str(tmp_path / "SO T11.xls"))["error"]


def test_reload_right_after_first_setup_keeps_unsaved_day(tmp_path, monkeypatch, roster):
    """Bản .exe mới: thiết lập xong, điểm danh dở rồi tải lại trang (F5): không mất thay đổi."""
    from app import build_info, settings
    from tests.conftest import write_list

    cfg = tmp_path / "CaiDat.txt"
    monkeypatch.setattr(settings, "default_path", lambda: cfg)
    monkeypatch.setattr(build_info, "BUILD", "bbbbbbb")
    a = Api(Workspace())
    assert a.boot()["setup"]
    a.choose_book(str(make_book(tmp_path / "SO DIEM DANH T10.xlsx")))
    a.choose_list(str(write_list(tmp_path / "DS.xlsx", roster)))
    a.finish_setup()
    a.open_day("2026-10-29", True)
    a.set_absent("1D15", sid_of(a, "1D15", "Lâm Quốc Tuấn Anh"), True)
    r = a.boot()  # F5
    assert r["state"]["dirty"] and r["state"]["date"] == "2026-10-29"


def test_settings_show_app_folder_and_files_outside_it(api, tmp_path, monkeypatch):
    """Trang Cài đặt: thư mục app (mở được), file nào nằm ngoài thư mục app."""
    from app.web import api as api_mod

    st = api.settings()
    assert st["app_dir"] == str(tmp_path.absolute()) and st["outside"] == []
    other = tmp_path.parent / f"{tmp_path.name} khac" / "SO DIEM DANH T10.xlsx"
    other.parent.mkdir()
    api.choose_book(str(make_book(other)))
    assert api.settings()["outside"] == ["so_file"]
    opened = []
    monkeypatch.setattr(api_mod, "open_folder", opened.append)
    assert api.open_path("settings_folder") == {"ok": ""} and opened == [tmp_path / "CaiDat.txt"]


def test_class_with_unknown_names_is_flagged_not_called_all_matched(tmp_path, roster):
    """Sổ có tên ghi tay không khớp ai: đầu trang báo lớp cần xem, không nói "đều khớp danh sách"."""
    book = make_book(tmp_path / "SO DIEM DANH T10.xlsx")
    wb = openpyxl.load_workbook(book)
    wb["28"]["G7"], wb["28"]["E7"] = "Bông", 1  # 1D16: tên không có trong lớp
    wb.save(book)
    api = Api(make_workspace(tmp_path, roster, book))
    st = api.open_day("2026-10-28")["state"]
    assert st["need_look"] == ["1D16"]
    assert not any("đều khớp" in i for i in st["info"])


def test_hint_offers_new_month_book_when_previous_book_exists(api):
    """Ngày của tháng chưa có sổ: lời nhắc bấm được để tạo sổ tháng mới (không bắt vào Cài đặt)."""
    st = api.open_day("2026-11-19")["state"]
    assert st["hint_month"] and "11/2026" in st["hint"] and "Cài đặt" not in st["hint"]
    assert not api.open_day("2026-10-29")["state"]["hint_month"]


def test_save_check_mentions_unknown_names(tmp_path, roster):
    """Trước khi lưu: nhắc lớp còn tên chưa xác định (sẽ lưu nguyên chữ)."""
    book = make_book(tmp_path / "SO DIEM DANH T10.xlsx")
    wb = openpyxl.load_workbook(book)
    wb["28"]["G7"], wb["28"]["E7"] = "Bông", 1
    wb.save(book)
    api = Api(make_workspace(tmp_path, roster, book))
    api.open_day("2026-10-28")
    assert api.save_check()["extra"] == ["Lớp 1D16: Bông"]


def _add_new_student(tmp_path, roster):
    """Giáo vụ ghi thêm em chuyển đến vào file danh sách (bằng Excel) khi app đang mở."""
    import os

    from app.core.models import Student
    from tests.conftest import write_list

    roster.students.append(Student(id="HS9999", lop="1D15", ho_ten="Lò Văn Mới", ngay_sinh="05/05/2020", ban_tru=True))
    path = write_list(tmp_path / "DanhSach.xlsx", roster)
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))  # chắc chắn khác lần sửa trước


def test_new_student_in_list_shows_without_changing_day(api, tmp_path, roster):
    """Thêm em chuyển đến vào file danh sách: mở lớp là thấy em đó, không phải chuyển ngày."""
    _add_new_student(tmp_path, roster)
    d = api.class_detail("1D15")
    assert "Lò Văn Mới" in [n["full"] for n in d["names"]] and d["si"] == 7


def test_new_student_keeps_absent_already_chosen(api, tmp_path, roster):
    """Đã chọn em vắng (chưa lưu) rồi mới thêm em mới vào danh sách: em đã chọn vắng vẫn giữ."""
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    api.set_absent("1D15", sid, True)
    _add_new_student(tmp_path, roster)
    d = api.class_detail("1D15")
    assert "Lò Văn Mới" in [n["full"] for n in d["names"]]
    assert next(n for n in d["names"] if n["id"] == sid)["absent"] and api.state()["dirty"]
    api.undo()  # hoàn tác vẫn dùng danh sách mới
    assert "Lò Văn Mới" in [n["full"] for n in api.class_detail("1D15")["names"]]


def test_students_page_shows_list_just_edited(api, tmp_path, roster):
    """Sửa file danh sách bằng Excel rồi xem trang Học sinh: hiện ngay em mới (không phải đổi ngày)."""
    _add_new_student(tmp_path, roster)
    assert "Lò Văn Mới" in [r["ten"] for r in api.students("moi", "1D15")["rows"]]


def test_set_schedule_writes_three_columns_of_list_file(api, tmp_path):
    """Hộp Lịch bán trú: ghi 3 cột Ăn từ / Cắt từ / Cắt thứ 6 của đúng dòng em đó; ô khác giữ nguyên; dùng ngay."""
    sid = sid_of(api, "1D15", "Tô Minh Khôi")
    r = api.set_schedule(sid, "", "2026-11-02", True)
    assert r["flash"].startswith("Đã lưu lịch của Tô Minh Khôi")
    wb = openpyxl.load_workbook(tmp_path / "DanhSach.xlsx")
    ws = wb.active
    head = [c.value for c in ws[1]]
    row = next(r for r in ws.iter_rows(min_row=2, values_only=True) if r[1] == "Tô Minh Khôi")
    rec = dict(zip(head, row, strict=False))
    assert (rec["Ăn từ"], rec["Cắt từ"].date(), rec["Cắt thứ 6"], rec["Lớp"]) == (None, dt.date(2026, 11, 2), "x", "1D15")
    s = next(x for x in api.students("khoi", "1D15")["rows"])
    assert (s["lich"], s["cat_tu"], s["t6"]) == ("cắt thứ 6; cắt từ 02/11/2026", "2026-11-02", True)
    assert api.open_day("2026-10-30")["state"]["rows"][0]["auto"] == "Minh Khôi"  # thứ 6: tự tính vắng ngay
    api.set_schedule(sid, "", "", False)  # bỏ lịch
    s = next(x for x in api.students("khoi", "1D15")["rows"])
    assert (s["lich"], s["t6"]) == ("", False)


def test_set_schedule_adds_missing_columns(api, tmp_path):
    """File danh sách chưa có 3 cột lịch: app thêm cột vào cuối bảng."""
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ tên", "Ngày sinh", "Bán trú", "Ghi chú"])
    ws.append(["1D15", "Kha Bảo Ngọc", "02/03/2020", "Có", "dị ứng tôm"])
    ws.append(["1D15", "Bùi Văn Mới", "01/01/2020", "Không", None])
    wb.save(p)
    api.choose_list(str(p))
    sid = next(r["id"] for r in api.students("moi", "", False)["rows"])
    assert "error" not in api.set_schedule(sid, "03/11/2026", "", False)
    ws = openpyxl.load_workbook(p).active
    assert [c.value for c in ws[1]] == ["Lớp", "Họ tên", "Ngày sinh", "Bán trú", "Ghi chú", "Ăn từ", "Cắt từ", "Cắt thứ 6"]
    assert ws["F3"].value.date() == dt.date(2026, 11, 3) and ws["E2"].value == "dị ứng tôm"
    s = next(r for r in api.students("moi", "", False)["rows"])
    assert s["bt"] and s["lich"] == "ăn từ 03/11/2026"  # có ngày Ăn từ là tính ăn bán trú từ ngày đó


def test_set_schedule_errors(api, tmp_path, monkeypatch):
    from app.excel import files

    sid = sid_of(api, "1D15", "Tô Minh Khôi")
    assert "phải sau" in api.set_schedule(sid, "2026-11-05", "2026-11-02", False)["error"]
    monkeypatch.setattr(files, "is_locked", lambda p: True)
    assert "đang mở trong Excel" in api.set_schedule(sid, "", "", True)["error"]


def test_set_schedule_on_xls_list_explains(api, tmp_path):
    """File danh sách dạng .xls cũ: app đọc được nhưng không ghi lịch được, báo lưu lại thành .xlsx."""
    from tests.test_excel import _write_fake_cdhs_xls

    p = tmp_path / "cdhs.xls"
    _write_fake_cdhs_xls(p)
    api.choose_list(str(p))
    sid = api.students("", "", True)["rows"][0]["id"]
    assert ".xlsx" in api.set_schedule(sid, "", "", True)["error"]
