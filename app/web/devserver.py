"""Máy chủ thử: mở giao diện trong trình duyệt (để test, chụp ảnh). App thật dùng pywebview (run.py).

python -m app.web.devserver [cổng] [file dữ liệu]
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..service import Workspace
from .api import Api

STATIC = Path(__file__).with_name("static")


def make_server(api: Api, port: int = 0) -> ThreadingHTTPServer:
    lock = threading.Lock()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(STATIC), **k)

        def log_message(self, *a) -> None:  # yên lặng
            pass

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/devmode.js"):
                body = b"window.DEV_SERVER = true;"
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            name = self.path.removeprefix("/api/")
            n = int(self.headers.get("Content-Length") or 0)
            args = json.loads(self.rfile.read(n) or b"[]") if n else []
            fn = getattr(api, name, None)
            if name.startswith("_") or not callable(fn):
                self.send_error(404)
                return
            with lock:
                try:
                    out = fn(*args)
                except Exception as e:  # noqa: BLE001
                    out = {"error": f"Lỗi: {e}"}
            body = json.dumps(out, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ws = Workspace(sys.argv[2] if len(sys.argv) > 2 else None)
    srv = make_server(Api(ws), port)
    print(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
    srv.serve_forever()
