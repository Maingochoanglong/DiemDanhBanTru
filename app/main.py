"""Chạy app: python -m app.main

Giao diện là trang web (HTML + Bootstrap 5) mở trong trình duyệt (Edge/Chrome) qua máy chủ nội bộ 127.0.0.1.
Thêm --app để mở trong cửa sổ app riêng (pywebview, Microsoft Edge WebView2) như bản cũ.
Phần xử lý sổ Excel, danh sách, lịch, ghép lớp vẫn là Python (app/service.py, app/core, app/excel).
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

if __package__ in (None, ""):  # chạy trực tiếp file / bản đóng gói PyInstaller
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "app"  # noqa: A001

from app.service import Workspace  # noqa: E402


def log_error(text: str) -> Path | None:
    """Ghi lỗi vào file nhật ký (bản .exe không có cửa sổ dòng lệnh để in lỗi)."""
    if sys.stderr:
        print(text, file=sys.stderr)
    try:
        from app.service import config_path

        p = config_path().with_name("loi.log")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        return p
    except OSError:
        return None


def selftest() -> int:
    """Kiểm tra bản đóng gói: nạp đủ thư viện, có đủ file giao diện, đọc/ghi được Excel."""
    try:
        import tempfile

        import tkinter

        import openpyxl
        import webview  # noqa: F401
        import xlrd  # noqa: F401

        from app.web.run import static_dir

        if sys.platform == "win32":
            import clr  # noqa: F401  (pythonnet, pywebview cần trên Windows)
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        for f in ("index.html", "app.js", "app.css", "vendor/bootstrap.min.css", "vendor/bootstrap.bundle.min.js",
                  "vendor/bootstrap-icons.min.css", "vendor/fonts/bootstrap-icons.woff2"):
            assert (static_dir() / f).exists(), f"thiếu file giao diện {f}"
        tkinter.Tcl().eval("info patchlevel")  # hộp chọn file khi chạy trong trình duyệt (cần Tcl/Tk đóng kèm)
        with tempfile.TemporaryDirectory() as d:
            wb = openpyxl.Workbook()
            wb.active["A1"] = "Điểm danh"
            wb.save(Path(d) / "t.xlsx")
            assert openpyxl.load_workbook(Path(d) / "t.xlsx").active["A1"].value == "Điểm danh"
        return 0
    except Exception:  # noqa: BLE001
        log_error(traceback.format_exc())
        return 1


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        sys.exit(selftest())
    args = [a for a in argv if not a.startswith("--")]
    try:
        ws = Workspace(args[0] if args else None)
    except Exception:  # noqa: BLE001
        log_error(traceback.format_exc())
        ws = Workspace(Path.home() / "Documents" / "DiemDanhBanTru" / "DuLieu_BanTru_moi.xlsx")
    from app.web.run import run_in_browser, run_window

    if "--app" in argv:
        try:
            run_window(ws, debug="--debug" in argv)
            return
        except Exception:  # noqa: BLE001
            # cửa sổ app không mở được (thiếu thành phần Windows…): mở bằng trình duyệt để vẫn dùng được
            log_error(traceback.format_exc())
    try:
        run_in_browser(ws, open_browser="--no-open" not in argv)
    except Exception:  # noqa: BLE001
        log_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
