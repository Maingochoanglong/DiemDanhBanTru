"""Cầu nối giao diện web ↔ phần xử lý sổ (app/web/api.py). Dữ liệu tên bịa."""

import datetime as dt
import json

import openpyxl
import pytest

from app.excel.database import AppData
from app.service import Workspace
from app.web.api import Api
from tests.test_excel import make_book


@pytest.fixture
def api(tmp_path, monkeypatch, roster):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    book = make_book(tmp_path / "SO DIEM DANH T10.xlsx")
    AppData(tmp_path / "DuLieu_BanTru.xlsx", roster).save()
    ws = Workspace(tmp_path / "DuLieu_BanTru.xlsx")
    ws.set_book(book)
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
    assert row["status"] == "muted" and not row["reported"]
    assert any(r["kind"] == "khoi" for r in st["rows"])
    assert st["hint"] == ""


def test_click_names_then_save(api):
    sid = sid_of(api, "1D15", "Lâm Quốc Tuấn Anh")
    r = api.set_absent("1D15", sid, True)
    row = next(x for x in r["state"]["rows"] if x.get("code") == "1D15")
    assert row["vang"] == 1 and row["ten"] == "Tuấn Anh" and row["status"] == "warn"
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
    assert next(x for x in r["state"]["rows"] if x.get("code") == "2D17")["status"] == "ok"
    r = api.set_note("2D17", "  ghi  chú ")
    assert r["detail"]["note"] == "ghi chú"
    r = api.undo()
    assert next(x for x in r["state"]["rows"] if x.get("code") == "2D17")["note"] != "ghi chú"


def test_new_month_asks_to_create_book(api):
    r = api.open_day("2026-11-02", True)
    assert r["need_month"]["month"] == 11 and r["need_month"]["prev"] == "SO DIEM DANH T10.xlsx"
    r = api.create_month_book("2026-11-02")
    assert r["state"]["book"] == "SO DIEM DANH T11.xlsx" and r["flash"].startswith("Đã tạo sổ mới")


def test_students_edit_and_schedule(api):
    rows = api.students("long", "", True)["rows"]
    assert [r["ten"] for r in rows] == ["Khổng Hải Long"]
    sid = rows[0]["id"]
    data = api.student(sid)
    data["cat_tu"] = "abc"
    assert api.save_student(data)["error"].startswith("Ngày 'abc'")
    data["cat_tu"] = "01/11/2026"
    assert api.save_student(data)["ok"]
    assert "cắt từ 01/11/2026" in api.students("long", "", True)["rows"][0]["db"]
    # lịch cắt thứ 6 cho 1 em
    opt = api.schedule_options("thu6", "2D17", "")
    target = next(s for s in opt["students"] if s["ten"] == "Viên Duy Mạnh")
    r = api.add_schedule("thu6", "2D17", [target["id"]], "", "", "", False)
    assert r["ok"].startswith("Đã đặt lịch")
    weekly = api.schedules()["weekly"]
    assert [w["hs"] for w in weekly] == ["Viên Duy Mạnh"]
    assert api.cancel_schedules([weekly[0]["key"]])["ok"].startswith("Đã hủy 1 lịch")


def test_import_simple_list_preview_then_apply(api, tmp_path):
    p = tmp_path / "ds.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ tên", "Ngày tháng năm sinh", "Bán trú"])
    ws.append(["1D15", "Kha Bảo Ngọc", dt.datetime(2020, 3, 2), "Không"])  # đang ăn → thôi ăn
    ws.append(["1D15", "Bùi Văn Mới", dt.datetime(2020, 1, 1), "Có"])  # em mới
    wb.save(p)
    prev = api.import_list(str(p))
    assert prev["n"] == 2 and prev["n_bt"] == 1
    texts = [c["text"] for c in prev["changes"]]
    assert any("Bùi Văn Mới" in t for t in texts) and any("Kha Bảo Ngọc" in t for t in texts)
    sel = [c["i"] for c in prev["changes"] if "Bùi Văn Mới" in c["text"]]
    r = api.apply_import(sel)
    assert r["flash"].startswith("Đã áp dụng 1 thay đổi")
    assert [x["ten"] for x in api.students("bui van", "", False)["rows"]] == ["Bùi Văn Mới"]


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
