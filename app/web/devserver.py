"""Máy chủ web nội bộ (127.0.0.1): giao diện chạy trong trình duyệt (Edge/Chrome) gọi Python qua /api/<tên hàm>.

Dùng cho app thật (run.py → run_in_browser) và để thử/chụp giao diện:
python -m app.web.devserver [cổng] [file dữ liệu]
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..build_info import BUILD
from ..service import Workspace
from .api import Api

APP_ID = "DiemDanhBanTru"
HEADER = "X-DDBT"  # giao diện gửi kèm mọi lời gọi /api: trang web lạ không gửi được (trình duyệt chặn)


def static_dir() -> Path:
    """Thư mục giao diện: cạnh mã nguồn, hoặc trong file .exe (PyInstaller giải nén vào sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "app" / "web" / "static"
    return Path(__file__).with_name("static")


class Clients:
    """Các thẻ trình duyệt đang mở giao diện. Thẻ cuối cùng đóng (không mở lại trong vài giây) thì gọi on_empty."""

    def __init__(self, on_empty=None, grace: float = 6.0):
        self.on_empty = on_empty
        self.grace = grace
        self._ids: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def seen(self, cid: str) -> None:
        if not cid:
            return
        with self._lock:
            self._ids.add(cid[:64])
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def bye(self, cid: str) -> None:
        with self._lock:
            if cid not in self._ids:
                return
            self._ids.discard(cid)
            if self._ids or self.on_empty is None:
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.grace, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            if self._ids or self._timer is None:
                return
            self._timer = None
        self.on_empty()


def make_server(api: Api, port: int = 0, clients: Clients | None = None, dev: bool = True) -> ThreadingHTTPServer:
    """dev=True: máy chủ thử (giao diện không gọi hộp chọn file của Windows)."""
    lock = threading.Lock()
    clients = clients or Clients()
    static = str(static_dir())

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=static, **k)

        def log_message(self, *a) -> None:  # yên lặng
            pass

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")  # bản mới của app: trình duyệt không dùng file cũ
            super().end_headers()

        def _host_ok(self) -> bool:
            # chặn trang web lạ trỏ tên miền về 127.0.0.1 (DNS rebinding)
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return host in ("127.0.0.1", "localhost", "::1")

        def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_ok():
                self.send_error(403)
                return
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/index.html")
                self.end_headers()
                return
            if path == "/devmode.js":
                js = "window.DEV_SERVER = true;" if dev else "window.BROWSER_APP = true;"
                self._send(js.encode(), "text/javascript")
                return
            if path == "/ping":  # lần mở app sau: nhận ra app đang chạy sẵn
                self._send(json.dumps({"app": APP_ID, "build": BUILD}).encode(), "application/json")
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_ok():
                self.send_error(403)
                return
            path = self.path.split("?", 1)[0]
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            if path == "/bye":  # thẻ trình duyệt đóng (navigator.sendBeacon không gửi được header riêng)
                clients.bye(raw.decode("utf-8", "ignore").strip())
                self._send(b"", "text/plain", 204)
                return
            if self.headers.get(HEADER) != "1":
                self.send_error(403)
                return
            clients.seen(self.headers.get("X-Client") or "")
            name = path.removeprefix("/api/")
            args = json.loads(raw or b"[]") if raw else []
            fn = getattr(api, name, None)
            if name.startswith("_") or not callable(fn):
                self.send_error(404)
                return
            with lock:
                try:
                    out = fn(*args)
                except Exception as e:  # noqa: BLE001
                    out = {"error": f"Lỗi: {e}"}
            self._send(json.dumps(out, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    return Server(("127.0.0.1", port), Handler)


class Server(ThreadingHTTPServer):
    # Windows: SO_REUSEADDR cho phép 2 chương trình cùng chiếm 1 cổng → tắt để nhận ra app đang chạy sẵn
    allow_reuse_address = sys.platform != "win32"


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ws = Workspace(sys.argv[2] if len(sys.argv) > 2 else None)
    srv = make_server(Api(ws), port)
    print(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
    srv.serve_forever()
