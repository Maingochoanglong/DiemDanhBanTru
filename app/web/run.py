"""Mở giao diện web: mặc định trong trình duyệt (Edge/Chrome) qua máy chủ nội bộ 127.0.0.1;
hoặc (python run_app.py --app) trong cửa sổ app riêng nhờ pywebview (Microsoft Edge WebView2)."""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import urllib.request
import webbrowser

from ..build_info import BUILD
from ..service import Workspace
from .api import Api
from .devserver import APP_ID, HEADER, Clients, make_server, static_dir  # noqa: F401 (static_dir: main.py dùng)


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
    """Hộp chọn/lưu file khi chạy trong trình duyệt (tkinter, giao diện hộp chọn file của Windows)."""

    def _root(self):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)  # hiện trên cửa sổ trình duyệt
        root.lift()
        root.focus_force()
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


APP_PORT = 47615  # cổng cố định: mở app lần nữa thì nhận ra app đang chạy, chỉ mở thêm thẻ trình duyệt


class MainThreadDialogs:
    """Hộp chọn file (tkinter) chạy ở luồng chính; máy chủ web (luồng khác) gửi việc sang và chờ kết quả."""

    def __init__(self):
        self._jobs: queue.Queue = queue.Queue()
        self._tk = TkDialogs()

    def _call(self, name: str, *args):
        done, box = threading.Event(), {}
        self._jobs.put((getattr(self._tk, name), args, box, done))
        done.wait()
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        return self._call("open_file", title, types)

    def save_file(self, title: str, name: str) -> str | None:
        return self._call("save_file", title, name)

    def choose_folder(self, title: str) -> str | None:
        return self._call("choose_folder", title)

    def loop(self, stop: threading.Event) -> None:
        """Chạy ở luồng chính cho tới khi app thoát."""
        while not stop.is_set():
            try:
                fn, args, box, done = self._jobs.get(timeout=0.3)
            except queue.Empty:
                continue
            try:
                box["result"] = fn(*args)
            except Exception as e:  # noqa: BLE001
                box["error"] = e
            finally:
                done.set()


class BrowserApi(Api):
    """Api + việc của chế độ trình duyệt: nút Thoát (sau khi giao diện đã hỏi lưu) tắt máy chủ."""

    def __init__(self, ws: Workspace, dialogs, stop: threading.Event):
        super().__init__(ws, dialogs)
        self._stop = stop

    def quit(self) -> dict:
        threading.Timer(0.5, self._stop.set).start()  # trả lời giao diện xong mới tắt
        return {"ok": ""}


def _no_proxy():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def running_app(port: int) -> dict | None:
    """App đang chạy sẵn ở cổng này (mở app lần thứ hai): trả về {"app", "build"}."""
    try:
        with _no_proxy().open(f"http://127.0.0.1:{port}/ping", timeout=2) as r:
            info = json.loads(r.read())
        return info if info.get("app") == APP_ID else None
    except (OSError, ValueError):
        return None


def _ask_quit(port: int) -> None:
    """Bản cũ của app còn chạy: bảo nó thoát (thay đổi chưa lưu vẫn còn trong sổ tạm)."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/quit", data=b"[]", method="POST",
                                 headers={HEADER: "1", "Content-Type": "application/json"})
    try:
        _no_proxy().open(req, timeout=5).read()
    except OSError:
        return
    for _ in range(30):
        time.sleep(0.2)
        if running_app(port) is None:
            return


def _bind(api: Api, port: int, clients: Clients):
    try:
        return make_server(api, port, clients, dev=False)
    except OSError:  # cổng đang bị chương trình khác dùng: lấy cổng trống bất kỳ
        return make_server(api, 0, clients, dev=False)


def run_in_browser(ws: Workspace, port: int = APP_PORT, open_browser: bool = True) -> None:
    """Mở giao diện bằng trình duyệt (Edge/Chrome) qua máy chủ nội bộ 127.0.0.1.

    App tự thoát khi đóng thẻ trình duyệt cuối cùng (hoặc bấm nút Thoát trong giao diện).
    """
    other = running_app(port) if port else None
    if other is not None:
        if other.get("build") == BUILD:
            if open_browser:
                webbrowser.open(f"http://127.0.0.1:{port}/index.html")
            return
        _ask_quit(port)

    stop = threading.Event()
    dialogs = MainThreadDialogs()
    api = BrowserApi(ws, dialogs, stop)
    srv = _bind(api, port, Clients(on_empty=stop.set))
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    threading.Thread(target=srv.serve_forever, name="web", daemon=True).start()
    if sys.stdout:
        print(f"Điểm danh bán trú đang chạy tại {url}  (đóng thẻ trình duyệt để thoát)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        dialogs.loop(stop)
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()
        srv.server_close()
        ws.autosave_flush()  # thay đổi chưa lưu vào sổ: ghi nốt sổ tạm


class AppApi(Api):
    """Api + việc của cửa sổ: thoát app sau khi giao diện đã hỏi lưu."""

    def __init__(self, ws: Workspace, dialogs: WebviewDialogs):
        super().__init__(ws, dialogs)
        self._win_dialogs = dialogs
        self._quitting = False

    def quit(self) -> None:
        self._quitting = True
        self._win_dialogs.window.destroy()


def run_window(ws: Workspace, debug: bool = False) -> None:
    """Mở giao diện trong cửa sổ app riêng (pywebview)."""
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
