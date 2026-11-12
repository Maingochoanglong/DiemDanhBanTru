"""Chạy app: python -m app.main

Giao diện là trang web (Vue 3 + PrimeVue) mở trong trình duyệt (Edge/Chrome); máy chủ nội bộ 127.0.0.1 dùng FastAPI.
Phần xử lý sổ Excel, danh sách, lịch, ghép lớp vẫn là Python (app/service.py, app/core, app/excel).
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

if __package__ in (None, ""):  # chạy trực tiếp file / bản đóng gói PyInstaller
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "app"  # noqa: A001

from app import config  # noqa: E402
from app.service import Workspace  # noqa: E402


def show_error(text: str) -> None:
    """Lỗi nặng lúc mở app: hiện hộp thông báo (bản .exe không có cửa sổ dòng lệnh). Không ghi file nhật ký:
    app chỉ đụng 3 file trong cài đặt và sổ tạm."""
    if sys.stderr:
        print(text, file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Điểm danh bán trú", text[-config.ERROR_TEXT_MAX:], parent=root)
        root.destroy()
    except Exception:  # noqa: BLE001 - không có giao diện (máy chủ CI): đã in ra stderr nếu có
        pass


def selftest() -> int:
    """Kiểm tra bản đóng gói: nạp đủ thư viện, có đủ file giao diện, máy chủ giao diện chạy được, đọc/ghi được Excel."""
    try:
        import io
        import tkinter
        import urllib.request

        import openpyxl
        import xlrd  # noqa: F401

        from app.web.api import Api
        from app.web.server import Server, create_app, static_dir

        for f in ("index.html", "app.css", "js/main.js", "vendor/vue.global.prod.js", "vendor/primevue.min.js",
                  "vendor/primevue-aura.js", "vendor/primeicons.css", "vendor/fonts/primeicons.woff2"):
            assert (static_dir() / f).exists(), f"thiếu file giao diện {f}"
        tkinter.Tcl().eval("info patchlevel")  # hộp chọn file (cần Tcl/Tk đóng kèm)
        srv = Server(create_app(Api(None)), 0).start()  # FastAPI + uvicorn đóng gói đủ
        try:
            get = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
            assert config.APP_ID.encode() in get(srv.url + "ping", timeout=config.PING_TIMEOUT).read()
            assert "Điểm danh".encode() in get(srv.url, timeout=config.PING_TIMEOUT).read()
        finally:
            srv.stop()
        buf = io.BytesIO()  # đọc/ghi Excel trong bộ nhớ: tự kiểm tra cũng không tạo file nào
        wb = openpyxl.Workbook()
        wb.active["A1"] = "Điểm danh"
        wb.save(buf)
        assert openpyxl.load_workbook(io.BytesIO(buf.getvalue())).active["A1"].value == "Điểm danh"
        return 0
    except Exception:  # noqa: BLE001
        if sys.stderr:
            print(traceback.format_exc(), file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        sys.exit(selftest())
    args = [a for a in argv if not a.startswith("--")]  # tham số: đường dẫn CaiDat.txt khác (chạy thử)
    from app.web.run import run

    try:
        run(Workspace(args[0] if args else None), open_browser="--no-open" not in argv)
    except Exception:  # noqa: BLE001
        show_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
