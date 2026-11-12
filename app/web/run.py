"""Mở app: chạy máy chủ nội bộ (server.py) rồi mở giao diện trong trình duyệt (Edge/Chrome).

App tự thoát khi đóng thẻ trình duyệt cuối cùng, hoặc bấm nút Thoát trong giao diện.
Mở app lần nữa khi đang chạy: chỉ mở thêm thẻ trình duyệt.
"""

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
from .server import APP_ID, HEADER, Clients, Server, create_app

APP_PORT = 47615  # cổng cố định: mở app lần nữa thì nhận ra app đang chạy


class TkDialogs:
    """Hộp chọn/lưu file của Windows (tkinter). Chỉ gọi ở luồng chính (xem MainThreadDialogs)."""

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


class MainThreadDialogs:
    """Hộp chọn file chạy ở luồng chính; máy chủ web (luồng khác) gửi việc sang và chờ kết quả."""

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
    """Api + nút Thoát (giao diện đã hỏi lưu trước): tắt máy chủ."""

    def __init__(self, ws: Workspace, dialogs, stop: threading.Event):
        super().__init__(ws, dialogs)
        self._stop = stop

    def quit(self) -> dict:
        threading.Timer(0.5, self._stop.set).start()  # trả lời giao diện xong mới tắt
        return {"ok": ""}


def _open(req, timeout: float):
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)


def running_app(port: int) -> dict | None:
    """App đang chạy sẵn ở cổng này (mở app lần thứ hai): trả về {"app", "build"}."""
    try:
        with _open(f"http://127.0.0.1:{port}/ping", 2) as r:
            info = json.loads(r.read())
        return info if info.get("app") == APP_ID else None
    except (OSError, ValueError):
        return None


def _ask_quit(port: int) -> None:
    """Bản .exe khác còn chạy: bảo nó thoát (thay đổi chưa lưu vẫn còn trong sổ tạm)."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/quit", data=b"[]", method="POST",
                                 headers={HEADER: "1", "Content-Type": "application/json"})
    try:
        _open(req, 5).read()
    except OSError:
        return
    for _ in range(30):
        time.sleep(0.2)
        if running_app(port) is None:
            return


def run(ws: Workspace, port: int = APP_PORT, open_browser: bool = True) -> None:
    other = running_app(port)
    if other is not None:
        if other.get("build") == BUILD:
            if open_browser:
                webbrowser.open(f"http://127.0.0.1:{port}/")
            return
        _ask_quit(port)

    stop = threading.Event()
    dialogs = MainThreadDialogs()
    srv = Server(create_app(BrowserApi(ws, dialogs, stop), Clients(on_empty=stop.set)), port).start()
    if sys.stdout:
        print(f"Điểm danh bán trú đang chạy tại {srv.url}  (đóng thẻ trình duyệt để thoát)", flush=True)
    if open_browser:
        webbrowser.open(srv.url)
    try:
        dialogs.loop(stop)
    except KeyboardInterrupt:
        pass
    finally:
        srv.stop()
        ws.autosave_flush()  # thay đổi chưa lưu vào sổ: ghi nốt sổ tạm
