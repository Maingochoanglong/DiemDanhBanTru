"""Chạy app: python -m app.main"""

from __future__ import annotations

import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

if __package__ in (None, ""):  # chạy trực tiếp file / bản đóng gói PyInstaller
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "app"  # noqa: A001

from app.service import Workspace  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.widgets import setup_style  # noqa: E402


def _dpi_aware() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass


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
    """Kiểm tra bản đóng gói: nạp đủ thư viện, dựng được cửa sổ, đọc/ghi được Excel."""
    try:
        import tempfile

        import openpyxl
        import xlrd  # noqa: F401

        if sys.platform == "win32":
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        with tempfile.TemporaryDirectory() as d:
            wb = openpyxl.Workbook()
            wb.active["A1"] = "Điểm danh"
            wb.save(Path(d) / "t.xlsx")
            assert openpyxl.load_workbook(Path(d) / "t.xlsx").active["A1"].value == "Điểm danh"
        root = tk.Tk()
        setup_style(root)
        root.update()
        root.destroy()
        return 0
    except Exception:  # noqa: BLE001
        log_error(traceback.format_exc())
        return 1


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        sys.exit(selftest())
    _dpi_aware()
    root = tk.Tk()
    setup_style(root)

    def report(exc, val, tb):
        where = log_error("".join(traceback.format_exception(exc, val, tb)))
        extra = f"\n\nChi tiết lỗi đã ghi vào:\n{where}" if where else ""
        messagebox.showerror("Lỗi", f"Có lỗi xảy ra:\n{val}\n\nDữ liệu đã lưu không bị ảnh hưởng.{extra}")

    root.report_callback_exception = report
    data_path = argv[0] if argv else None
    try:
        ws = Workspace(data_path)
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Không mở được dữ liệu", f"Không đọc được file dữ liệu:\n{e}")
        ws = Workspace(Path.home() / "Documents" / "DiemDanhBanTru" / "DuLieu_BanTru_moi.xlsx")
    MainWindow(root, ws)
    try:
        root.state("zoomed")
    except tk.TclError:
        root.geometry("1360x820")
    root.mainloop()


if __name__ == "__main__":
    main()
