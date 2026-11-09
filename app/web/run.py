"""Mở giao diện web trong cửa sổ app (pywebview; trên Windows dùng Microsoft Edge WebView2)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..service import Workspace
from .api import Api


def static_dir() -> Path:
    """Thư mục giao diện: cạnh mã nguồn, hoặc trong file .exe (PyInstaller giải nén vào sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "app" / "web" / "static"
    return Path(__file__).with_name("static")


class WebviewDialogs:
    """Hộp chọn/lưu file của Windows, mở qua cửa sổ pywebview."""

    def __init__(self):
        self.window = None

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        import webview

        res = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=types)
        return res[0] if res else None

    def save_file(self, title: str, name: str) -> str | None:
        import webview

        res = self.window.create_file_dialog(webview.SAVE_DIALOG, save_filename=name,
                                             file_types=("Excel (*.xlsx)",))
        if not res:
            return None
        return res if isinstance(res, str) else res[0]

    def choose_folder(self, title: str) -> str | None:
        return _webview_folder(self.window)


def _webview_folder(window) -> str | None:
    import webview

    res = window.create_file_dialog(webview.FOLDER_DIALOG)
    if not res:
        return None
    return res[0] if isinstance(res, (list, tuple)) else str(res)


class TkDialogs:
    """Hộp chọn file dự phòng khi chạy trong trình duyệt (máy không có WebView2)."""

    def _root(self):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        return root

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        from tkinter import filedialog

        root = self._root()
        try:
            return filedialog.askopenfilename(parent=root, title=title,
                                              filetypes=[("Excel", "*.xlsx *.xls"), ("Tất cả", "*.*")]) or None
        finally:
            root.destroy()

    def save_file(self, title: str, name: str) -> str | None:
        from tkinter import filedialog

        root = self._root()
        try:
            return filedialog.asksaveasfilename(parent=root, title=title, initialfile=name, defaultextension=".xlsx",
                                                filetypes=[("Excel", "*.xlsx")]) or None
        finally:
            root.destroy()

    def choose_folder(self, title: str) -> str | None:
        from tkinter import filedialog

        root = self._root()
        try:
            return filedialog.askdirectory(parent=root, title=title) or None
        finally:
            root.destroy()


def has_webview2() -> bool:
    """Máy Windows có Microsoft Edge WebView2 Runtime chưa (Windows 11 có sẵn, Windows 10 đa số có)."""
    if sys.platform != "win32":
        return True
    import winreg

    key = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, key.replace("SOFTWARE\\", "SOFTWARE\\WOW6432Node\\")),
                       (winreg.HKEY_LOCAL_MACHINE, key), (winreg.HKEY_CURRENT_USER, key)):
        try:
            with winreg.OpenKey(hive, path) as k:
                ver, _ = winreg.QueryValueEx(k, "pv")
                if ver and ver != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def run_in_browser(ws: Workspace) -> None:
    """Dự phòng: mở giao diện bằng trình duyệt (Edge/Chrome) qua máy chủ nội bộ 127.0.0.1."""
    import webbrowser

    from .devserver import make_server

    srv = make_server(Api(ws, TkDialogs()), 0)
    webbrowser.open(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
    srv.serve_forever()


class AppApi(Api):
    """Api + việc của cửa sổ: thoát app sau khi giao diện đã hỏi lưu."""

    def __init__(self, ws: Workspace, dialogs: WebviewDialogs):
        super().__init__(ws, dialogs)
        self._win_dialogs = dialogs
        self._quitting = False

    def quit(self) -> None:
        self._quitting = True
        self._win_dialogs.window.destroy()


def run(ws: Workspace, debug: bool = False) -> None:
    if not has_webview2():
        run_in_browser(ws)
        return
    import webview

    dialogs = WebviewDialogs()
    api = AppApi(ws, dialogs)
    index = static_dir() / "index.html"
    win = webview.create_window("Điểm danh bán trú", url=str(index), js_api=api,
                                width=1366, height=800, min_size=(1000, 620), maximized=True,
                                text_select=True)
    dialogs.window = win

    def on_closing():
        # còn thay đổi chưa lưu: để giao diện hỏi (Lưu rồi thoát / Không lưu / Ở lại)
        if api._quitting or not (ws.dirty or ws.data_dirty):
            return True
        win.evaluate_js("askClose()")
        return False

    win.events.closing += on_closing
    webview.start(gui="edgechromium" if sys.platform == "win32" else None, http_server=True, debug=debug,
                  private_mode=False)
