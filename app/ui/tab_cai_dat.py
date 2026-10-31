"""Cửa sổ Cài đặt: đường dẫn file, nhập/xuất danh sách học sinh, thư mục."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import __version__
from ..excel import printing


class TabCaiDat(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self.ws = app.ws
        self.vars: dict[str, tk.StringVar] = {}
        g = ttk.Frame(self)
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)
        rows = [
            ("data", "File dữ liệu của app (danh sách HS, ghép lớp)"),
            ("so_file", "Sổ điểm danh tháng đang dùng"),
            ("cdhs_file", "File danh sách CDHS đã nhập"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(g, text=label).grid(row=i, column=0, sticky="w", pady=6, padx=(0, 10))
            var = tk.StringVar()
            self.vars[key] = var
            ttk.Entry(g, textvariable=var, state="readonly").grid(row=i, column=1, sticky="we")
            ttk.Button(g, text="Mở", command=lambda k=key: self._open(k)).grid(row=i, column=2, padx=4)
        ttk.Button(g, text="Chọn sổ khác…", command=self.app.choose_book).grid(row=1, column=3)

        # việc ít làm với danh sách học sinh (đầu năm, khi trường có danh sách mới)
        box = ttk.LabelFrame(self, text="Danh sách học sinh", padding=10)
        box.pack(fill="x", pady=(16, 0))
        ttk.Button(box, text="Nhập / cập nhật từ file CDHS…", command=self.app.ask_import_cdhs).pack(side="left")
        ttk.Button(box, text="Đọc ghi chú trong sổ…", command=self.app.ask_note_suggestions).pack(side="left", padx=6)
        ttk.Button(box, text="Xuất danh sách…", command=lambda: self.app.tab_hs.export(self)).pack(side="left")

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(16, 0))
        ttk.Button(bar, text="Mở thư mục sổ", command=lambda: self._open_folder("so_file")).pack(side="left")
        ttk.Button(bar, text="Mở thư mục sao lưu của sổ", command=self._open_backup).pack(side="left", padx=6)
        ttk.Button(bar, text="Mở thư mục dữ liệu", command=lambda: self._open_folder("data")).pack(side="left")

        ttk.Label(self, style="Muted.TLabel", justify="left", wraplength=900, text=(
            "• Mỗi lần ghi, app tự sao lưu file cũ vào thư mục SaoLuu cạnh file (giữ 30 bản gần nhất).\n"
            "• Nếu sổ đang mở trong Excel, hãy đóng Excel rồi bấm Lưu lại.\n"
            "• Có thể mở file dữ liệu bằng Excel để xem/sửa; sửa xong đóng Excel rồi khởi động lại app.\n"
            f"• Phiên bản {__version__}")).pack(anchor="w", pady=(16, 0))

    def refresh(self) -> None:
        st = self.ws.settings
        self.vars["data"].set(str(self.ws.data.path))
        self.vars["so_file"].set(st.get("so_file", ""))
        self.vars["cdhs_file"].set(st.get("cdhs_file", ""))

    def _path(self, key: str) -> Path | None:
        v = self.vars[key].get()
        return Path(v) if v else None

    def _open(self, key: str) -> None:
        p = self._path(key)
        if p and p.exists():
            printing.open_file(p)

    def _open_folder(self, key: str) -> None:
        p = self._path(key)
        if p:
            printing.open_folder(p)

    def _open_backup(self) -> None:
        p = self._path("so_file")
        if p:
            folder = p.parent / "SaoLuu"
            folder.mkdir(exist_ok=True)
            printing.open_folder(folder)
