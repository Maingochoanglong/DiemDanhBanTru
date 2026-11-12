"""Máy chủ web nội bộ (FastAPI + uvicorn) chỉ nghe ở 127.0.0.1.

Phục vụ giao diện (static/) và nhận lời gọi của giao diện: POST /api/<tên hàm> với thân là mảng JSON tham số,
gọi sang hàm cùng tên của Api (api.py).

Chạy thử với dữ liệu có sẵn (không hộp chọn file, không nút Thoát):
python -m app.web.server [cổng] [file dữ liệu]   → mở http://127.0.0.1:8765, tài liệu API ở /docs
"""

from __future__ import annotations

import inspect
import mimetypes
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

# uvicorn nạp các phần này theo tên (chuỗi): import thẳng để PyInstaller đóng gói kèm
import uvicorn.lifespan.off  # noqa: F401
import uvicorn.loops.asyncio  # noqa: F401
import uvicorn.protocols.http.h11_impl  # noqa: F401

from ..build_info import BUILD
from .api import Api

APP_ID = "DiemDanhBanTru"
HEADER = "X-DDBT"  # giao diện gửi kèm mọi lời gọi /api: trang web lạ không gửi được (trình duyệt chặn)
HOSTS = ["127.0.0.1", "localhost"]

# Windows có thể khai báo sai kiểu file .js trong registry (text/plain) → trình duyệt không chạy module
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/woff2", ".woff2")


def static_dir() -> Path:
    """Thư mục giao diện: cạnh mã nguồn, hoặc trong file .exe (PyInstaller giải nén vào sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "app" / "web" / "static"
    return Path(__file__).with_name("static")


def api_methods(api: Api) -> set[str]:
    """Các hàm giao diện được gọi: hàm công khai (không bắt đầu bằng _) của lớp Api."""
    return {n for n, _ in inspect.getmembers(type(api), inspect.isfunction) if not n.startswith("_")}


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


def create_app(api: Api, clients: Clients | None = None, dev: bool = False) -> FastAPI:
    """dev=True: chạy thử (có trang tài liệu /docs, giao diện ẩn nút Thoát)."""
    clients = clients or Clients()
    methods = api_methods(api)
    lock = threading.Lock()  # sổ Excel / dữ liệu: mỗi lúc chỉ một việc
    app = FastAPI(title="Điểm danh bán trú", version=BUILD,
                  docs_url="/docs" if dev else None, redoc_url=None, openapi_url="/openapi.json" if dev else None)
    # chặn trang web lạ trỏ tên miền về 127.0.0.1 (DNS rebinding)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=HOSTS)

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"  # bản app mới: trình duyệt không dùng file giao diện cũ
        return resp

    def from_app(x_ddbt: str | None = Header(default=None), x_client: str | None = Header(default=None)) -> None:
        if x_ddbt != "1":
            raise HTTPException(403, "Chỉ giao diện của app được gọi.")
        clients.seen(x_client or "")

    @app.post("/api/{name}", dependencies=[Depends(from_app)])
    def call(name: str, args: Annotated[list, Body(default_factory=list)]):
        if name not in methods:
            raise HTTPException(404, f"Không có hàm {name}.")
        with lock:
            try:
                return getattr(api, name)(*args)
            except Exception as e:  # noqa: BLE001
                return {"error": f"Lỗi: {e}"}

    @app.post("/bye", status_code=204)
    async def bye(request: Request) -> Response:
        """Thẻ trình duyệt đóng (navigator.sendBeacon không gửi được header riêng)."""
        clients.bye((await request.body()).decode("utf-8", "ignore").strip())
        return Response(status_code=204)

    @app.get("/ping")
    def ping() -> dict:
        """Lần mở app sau nhận ra app đang chạy sẵn."""
        return {"app": APP_ID, "build": BUILD}

    @app.get("/config.js")
    def config() -> Response:
        return Response(f"window.APP_MODE = {'dev' if dev else 'app'!r};", media_type="text/javascript")

    app.mount("/", StaticFiles(directory=static_dir(), html=True), name="static")
    return app


def bind(port: int) -> socket.socket:
    """Mở cổng ở 127.0.0.1; cổng đang bị chương trình khác dùng thì lấy cổng trống bất kỳ."""
    def make(p: int) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sys.platform != "win32":  # Windows: SO_REUSEADDR cho 2 chương trình chiếm chung 1 cổng
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", p))
        except OSError:
            s.close()
            raise
        return s

    try:
        return make(port)
    except OSError:
        if not port:
            raise
        return make(0)


class Server:
    """uvicorn chạy ở luồng riêng (luồng chính để dành cho hộp chọn file)."""

    def __init__(self, app: FastAPI, port: int = 0):
        self.sock = bind(port)
        self.port = self.sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}/"
        cfg = uvicorn.Config(app, log_config=None, log_level="warning", access_log=False,
                             loop="asyncio", http="h11", ws="none", lifespan="off")
        self._uv = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._uv.run, kwargs={"sockets": [self.sock]}, name="web", daemon=True)

    def start(self) -> Server:
        self._thread.start()
        for _ in range(200):
            if self._uv.started or not self._thread.is_alive():
                break
            time.sleep(0.025)
        if not self._uv.started:
            raise RuntimeError("Không khởi động được máy chủ giao diện.")
        return self

    def stop(self) -> None:
        self._uv.should_exit = True
        self._thread.join(5)
        self.sock.close()


if __name__ == "__main__":
    from ..service import Workspace

    srv = Server(create_app(Api(Workspace(sys.argv[2] if len(sys.argv) > 2 else None)), dev=True),
                 int(sys.argv[1]) if len(sys.argv) > 1 else 8765).start()
    print(srv.url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
