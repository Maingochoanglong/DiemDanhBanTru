"""Tab Cài đặt: đường dẫn file, vùng in."""

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
        ttk.Button(g, text="Nhập lại…", command=self.app.ask_import_cdhs).grid(row=2, column=3)

        box = ttk.LabelFrame(self, text="Vùng in (mỗi vùng in thành 1 tờ A4 ngang)", padding=10)
        box.pack(fill="x", pady=(16, 0))
        for i, (key, label) in enumerate([("vung_in_1", "Tờ 1 – bảng điểm danh (trống = tự tính, thường là A1:G46)"),
                                          ("vung_in_2", "Tờ 2 – bảng suất ăn (trống = tự tìm, thường là G68:O80)")]):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            var = tk.StringVar()
            self.vars[key] = var
            ttk.Entry(box, textvariable=var, width=16).grid(row=i, column=1, sticky="w")
        ttk.Button(box, text="Lưu vùng in", command=self.save_areas).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.lbl_auto = ttk.Label(box, text="", style="Muted.TLabel")
        self.lbl_auto.grid(row=2, column=1, sticky="w", pady=(8, 0))

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
        self.vars["vung_in_1"].set(st.get("vung_in_1", ""))
        self.vars["vung_in_2"].set(st.get("vung_in_2", ""))
        try:
            auto = self.ws.print_areas() if self.ws.book_path else []
        except Exception:  # noqa: BLE001
            auto = []
        self.lbl_auto.configure(text=("Đang dùng: " + " và ".join(auto)) if auto else "")

    def save_areas(self) -> None:
        for k in ("vung_in_1", "vung_in_2"):
            self.ws.settings[k] = self.vars[k].get().strip().upper().replace("$", "")
        try:
            self.ws.save_data()
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        self.refresh()
        self.app.flash("Đã lưu vùng in.")

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
