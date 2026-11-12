"""Máy chủ nội bộ khi chạy giao diện trong trình duyệt (app/web/devserver.py, app/web/run.py)."""

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from app.web import run as webrun
from app.web.devserver import HEADER, Clients, make_server
from tests.test_web_api import api  # noqa: F401  (fixture)

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture
def server(api):  # noqa: F811
    srv = make_server(api, 0, dev=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(base, name, *args, headers=None):
    h = {HEADER: "1", "Content-Type": "application/json"} if headers is None else headers
    req = urllib.request.Request(f"{base}/api/{name}", data=json.dumps(args).encode(), headers=h, method="POST")
    with OPENER.open(req, timeout=5) as r:
        return json.loads(r.read())


def test_serves_page_and_marks_browser_mode(server):
    with OPENER.open(server + "/", timeout=5) as r:
        assert "Điểm danh bán trú" in r.read().decode("utf-8")
    with OPENER.open(server + "/devmode.js", timeout=5) as r:
        assert b"BROWSER_APP" in r.read()
    with OPENER.open(server + "/ping", timeout=5) as r:
        assert json.loads(r.read())["app"] == "DiemDanhBanTru"


def test_api_needs_app_header(server):
    assert call(server, "close_check")["day"] == "29/10/2026"
    with pytest.raises(urllib.error.HTTPError) as e:  # trang web lạ không gửi được header riêng
        call(server, "close_check", headers={"Content-Type": "text/plain"})
    assert e.value.code == 403


def test_rejects_foreign_host(server):
    req = urllib.request.Request(server + "/ping", headers={"Host": "evil.example:80"})
    with pytest.raises(urllib.error.HTTPError) as e:
        OPENER.open(req, timeout=5)
    assert e.value.code == 403


def test_private_methods_not_reachable(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        call(server, "_status", "1D15")
    assert e.value.code == 404


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
    srv = make_server(api, 0, dev=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    opened = []
    monkeypatch.setattr(webrun.webbrowser, "open", opened.append)
    try:
        assert webrun.running_app(port)["app"] == "DiemDanhBanTru"
        webrun.run_in_browser(api._ws, port)  # đã có app chạy (cùng bản): chỉ mở thẻ trình duyệt rồi thôi
        assert opened == [f"http://127.0.0.1:{port}/index.html"]
    finally:
        srv.shutdown()
        srv.server_close()


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
