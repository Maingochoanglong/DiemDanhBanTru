"""Máy chủ nội bộ (FastAPI, app/web/server.py) và cách mở app (app/web/run.py)."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.web import run as webrun
from app import config
from app.web.server import Clients, Server, create_app
from tests.test_web_api import api  # noqa: F401  (fixture)

APP = {config.API_HEADER: "1"}


@pytest.fixture
def client(api):  # noqa: F811
    return TestClient(create_app(api), base_url="http://127.0.0.1")


def test_serves_page_config_and_ping(client):
    r = client.get("/")
    assert r.status_code == 200 and "Điểm danh bán trú" in r.text
    assert r.headers["cache-control"] == "no-store"
    assert '"mode": "app"' in client.get("/config.js").text and config.API_HEADER in client.get("/config.js").text
    assert client.get("/js/main.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/ping").json()["app"] == "DiemDanhBanTru"


def test_api_call(client):
    r = client.post("/api/close_check", json=[], headers=APP)
    assert r.json()["day"] == "29/10/2026"
    r = client.post("/api/class_detail", json=["1D15"], headers=APP)
    assert r.json()["code"] == "1D15"


def test_api_needs_app_header(client):
    assert client.post("/api/close_check", json=[]).status_code == 403  # trang web lạ không gửi được header riêng


def test_rejects_foreign_host(api):  # noqa: F811
    c = TestClient(create_app(api), base_url="http://evil.example")  # tên miền lạ trỏ về 127.0.0.1
    assert c.get("/ping").status_code == 400


def test_private_or_unknown_functions_not_reachable(client):
    assert client.post("/api/_status", json=["1D15"], headers=APP).status_code == 404
    assert client.post("/api/khong_co", json=[], headers=APP).status_code == 404


def test_python_error_is_reported_to_ui(client):
    r = client.post("/api/class_detail", json=[], headers=APP)  # thiếu tham số
    assert r.status_code == 200 and r.json()["error"].startswith("Lỗi")


def test_docs_only_in_dev_mode(api):  # noqa: F811
    assert TestClient(create_app(api), base_url="http://127.0.0.1").get("/docs").status_code == 404
    dev = TestClient(create_app(api, dev=True), base_url="http://127.0.0.1")
    assert dev.get("/docs").status_code == 200
    assert '"mode": "dev"' in dev.get("/config.js").text


def test_closing_tab_tracks_clients(api):  # noqa: F811
    gone = threading.Event()
    c = TestClient(create_app(api, Clients(on_empty=gone.set, grace=0.05)), base_url="http://127.0.0.1")
    c.post("/api/close_check", json=[], headers={**APP, config.CLIENT_HEADER: "tab1"})
    c.post("/bye", content=b"tab1")
    assert gone.wait(2)


def test_last_tab_closed_stops_app():
    gone = threading.Event()
    c = Clients(on_empty=gone.set, grace=0.1)
    c.seen("a")
    c.seen("b")
    c.bye("a")
    time.sleep(0.3)
    assert not gone.is_set()  # còn thẻ b
    c.bye("b")
    c.seen("c")  # tải lại trang: thẻ mới đến kịp trước khi hết giờ chờ
    time.sleep(0.3)
    assert not gone.is_set()
    c.bye("c")
    assert gone.wait(2)


def test_unknown_bye_is_ignored():
    gone = threading.Event()
    c = Clients(on_empty=gone.set, grace=0.05)
    c.seen("a")
    c.bye("x")
    time.sleep(0.2)
    assert not gone.is_set()


def test_reload_keeps_unsaved_day(api):  # noqa: F811
    api._booted = True  # giao diện đã mở một lần (fixture đã mở ngày 29/10)
    sid = api.class_detail("1D15")["names"][0]["id"]
    api.set_absent("1D15", sid, True)
    assert api.state()["dirty"]
    res = api.boot()  # trình duyệt tải lại trang: không mở lại ngày hôm nay, giữ thay đổi chưa lưu
    assert res["state"]["dirty"] and res["state"]["date"] == "2026-10-29"
    assert "setup" not in res


def test_quit_stops_browser_app(api):  # noqa: F811
    stop = threading.Event()
    assert webrun.BrowserApi(api._ws, None, stop).quit() == {"ok": ""}
    assert stop.wait(3)


def test_second_launch_reuses_running_app(api, monkeypatch):  # noqa: F811
    srv = Server(create_app(api), 0).start()
    opened = []
    monkeypatch.setattr(webrun.webbrowser, "open", opened.append)
    try:
        assert webrun.running_app(srv.port)["app"] == "DiemDanhBanTru"
        webrun.run(api._ws, srv.port)  # đã có app chạy (cùng bản): chỉ mở thẻ trình duyệt rồi thôi
        assert opened == [srv.url]
    finally:
        srv.stop()
    assert webrun.running_app(srv.port) is None


def test_busy_port_falls_back_to_free_port(api):  # noqa: F811
    a = Server(create_app(api), 0).start()
    try:
        b = Server(create_app(api), a.port).start()  # cổng đã bị chiếm: lấy cổng khác
        assert b.port != a.port
        b.stop()
    finally:
        a.stop()


def test_file_dialogs_run_on_main_thread():
    """Hộp chọn file (tkinter) phải chạy ở luồng chính, dù máy chủ gọi từ luồng khác."""
    d = webrun.MainThreadDialogs()
    seen = []

    class FakeTk:
        def open_file(self, title, types):
            seen.append(threading.current_thread() is threading.main_thread())
            return "C:/so.xlsx"

    d._tk = FakeTk()
    stop, out = threading.Event(), []

    def worker():
        out.append(d.open_file("Chọn sổ", ()))
        stop.set()

    threading.Thread(target=worker).start()
    d.loop(stop)
    assert out == ["C:/so.xlsx"] and seen == [True]


def test_run_starts_and_stops_cleanly(api, monkeypatch):  # noqa: F811
    """Vòng đời mở app → thoát (đóng thẻ / bấm Thoát): máy chủ chạy rồi tắt, không lỗi."""
    seen = []

    def user_quits(self, stop):  # thay vòng chờ hộp chọn file: người dùng bấm Thoát ngay
        seen.append(True)
        stop.set()

    monkeypatch.setattr(webrun.MainThreadDialogs, "loop", user_quits)
    webrun.run(api._ws, port=0, open_browser=False)
    assert seen == [True]
