"""Tab Học sinh: danh sách bán trú, thêm/sửa/xóa học sinh. Nhập/xuất danh sách nằm ở Cài đặt."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core.models import Student
from ..core.text import class_sort_key, clean_spaces, fmt_date, norm_class, parse_date
from ..excel.roster_import import RosterFormatError, flag_mismatches
from ..service import search_students
from .widgets import _chk, CheckListDialog, ask, center, tag_colors, with_scrollbar

ALL = "Tất cả"


class TabHocSinh(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.ws = app.ws
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Lớp:").pack(side="left")
        self.cls_var = tk.StringVar(value=ALL)
        self.cb_cls = ttk.Combobox(top, textvariable=self.cls_var, width=8, state="readonly")
        self.cb_cls.pack(side="left", padx=4)
        self.cb_cls.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        ttk.Label(top, text="Tìm tên:").pack(side="left", padx=(12, 0))
        self.q_var = tk.StringVar()
        self.q_var.trace_add("write", lambda *a: self.refresh_list())
        ttk.Entry(top, textvariable=self.q_var, width=24).pack(side="left", padx=4)
        self.bt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Chỉ em ăn bán trú", variable=self.bt_var, command=self.refresh_list).pack(side="left", padx=12)
        ttk.Button(top, text="Lưu thay đổi", style="Big.TButton", command=self.save).pack(side="right")

        left = ttk.Frame(self)
        left.pack(fill="both", expand=True, pady=(8, 0))
        cols = ("lop", "ten", "ns", "bt", "ghiso", "ghep", "db", "gc")
        frame, self.tree = with_scrollbar(left, ttk.Treeview, columns=cols, show="headings", selectmode="browse")
        frame.pack(fill="both", expand=True)
        heads = {"lop": ("Lớp", 60), "ten": ("Họ tên", 200), "ns": ("Ngày sinh", 95), "bt": ("Ăn BT", 60),
                 "ghiso": ("Tên ghi sổ", 140), "ghep": ("Ăn ghép", 70), "db": ("Đặc biệt", 220), "gc": ("Ghi chú", 160)}
        for c, (t, w) in heads.items():
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center" if c in ("lop", "ns", "bt", "ghep") else "w")
        tag_colors(self.tree)
        self.tree.bind("<Double-Button-1>", lambda e: self.edit())
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Thêm học sinh", command=self.add).pack(side="left")
        ttk.Button(bar, text="Sửa (bấm đúp)", command=self.edit).pack(side="left", padx=6)
        ttk.Button(bar, text="Xóa", command=self.delete).pack(side="left")
        self.lbl_count = ttk.Label(bar, text="", style="Muted.TLabel")
        self.lbl_count.pack(side="right")

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        codes = self.ws.roster.class_codes()
        self.cb_cls.configure(values=[ALL] + codes)
        self.refresh_list()

    def refresh_list(self) -> None:
        t = self.tree
        t.delete(*t.get_children())
        cls = self.cls_var.get()
        items = search_students(self.ws.roster, self.q_var.get(), None if cls == ALL else cls, self.bt_var.get())
        items.sort(key=lambda s: class_sort_key(s.lop_tinh))
        day = self.ws.day
        for s in items:
            special = []
            if s.lop_bt and s.lop_bt != s.lop:
                special.append(f"tính BT lớp {s.lop_bt}")
            if s.cat_thu6:
                special.append("cắt thứ 6")
            if s.bt_tu:
                special.append(f"ăn từ {fmt_date(s.bt_tu)}")
            if s.cat_tu:
                special.append(f"cắt từ {fmt_date(s.cat_tu)}")
            tag = () if s.is_boarding(day) else ("muted",)
            t.insert("", "end", iid=s.id, values=(
                s.lop, s.ho_ten, s.ngay_sinh, "x" if s.ban_tru else "",
                self.ws.roster.display_name(s) if s.ban_tru else "", s.an_ghep, "; ".join(special), s.ghi_chu), tags=tag)
        self.lbl_count.configure(text=f"{len(items)} em")

    # ------------------------------------------------------------------
    def _selected(self) -> Student | None:
        sel = self.tree.selection()
        return self.ws.roster.by_id(sel[0]) if sel else None

    def add(self) -> None:
        cls = self.cls_var.get()
        s = Student(self.ws.roster.next_id(), "" if cls == ALL else cls, "", ban_tru=True)
        if StudentDialog(self, "Thêm học sinh", s).ok:
            self.ws.roster.students.append(s)
            self._changed()

    def edit(self) -> None:
        s = self._selected()
        if s and StudentDialog(self, f"Sửa: {s.ho_ten}", s).ok:
            self._changed()

    def delete(self) -> None:
        s = self._selected()
        if not s:
            return
        if ask(self, "Xóa học sinh", f"Xóa {s.ho_ten} ({s.lop}) khỏi danh sách?\n"
               "Nếu em chỉ thôi ăn bán trú, nên sửa 'Cắt BT từ ngày' thay vì xóa.",
               [("keep", "Không xóa"), ("delete", "Xóa")], image="st_err") == "delete":
            self.ws.roster.students.remove(s)
            self._changed()

    def _changed(self) -> None:
        self.ws.roster.invalidate()
        self.ws.data_dirty = True
        self.refresh()
        self.app.refresh_days_only()

    def save(self) -> None:
        try:
            self.ws.save_data()
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        self.app.flash("Đã lưu danh sách học sinh.")

    def export(self, parent=None) -> None:
        """Xuất danh sách gọn (lớp, họ tên, ngày sinh, X ăn bán trú, ghép lớp) theo một ngày."""
        from tkinter import simpledialog

        from ..excel.files import FileLockedError
        from ..excel.roster_export import export_roster

        parent = parent or self
        raw = simpledialog.askstring("Xuất danh sách", "Đánh X cho các em ăn bán trú vào ngày (dd/mm/yyyy):",
                                     initialvalue=fmt_date(self.ws.day), parent=parent)
        if raw is None:
            return
        day = parse_date(raw)
        if not day:
            messagebox.showwarning("Ngày không đúng", "Hãy nhập ngày dạng dd/mm/yyyy.", parent=parent)
            return
        path = filedialog.asksaveasfilename(
            parent=parent, title="Lưu danh sách học sinh ăn bán trú", defaultextension=".xlsx",
            initialfile="DANH_SACH_HOC_SINH_AN_BAN_TRU.xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            n = export_roster(self.ws.roster, path, day)
        except FileLockedError:
            messagebox.showwarning("File đang mở", "File đang mở trong Excel. Hãy đóng rồi xuất lại.", parent=parent)
            return
        self.app.flash(f"Đã xuất danh sách ({n} em ăn bán trú ngày {fmt_date(day)}) ra {path}")


class StudentDialog(tk.Toplevel):
    FIELDS = [
        ("lop", "Lớp đang học (vd. 1D15)", "entry"),
        ("ho_ten", "Họ tên", "entry"),
        ("ngay_sinh", "Ngày sinh (dd/mm/yyyy)", "entry"),
        ("ban_tru", "Ăn bán trú", "check"),
        ("ten_ghi_so", "Tên ghi sổ (để trống = tự đặt)", "entry"),
        ("lop_bt", "Lớp tính bán trú (nếu khác lớp học)", "entry"),
        ("an_ghep", "Ăn ghép tại nhóm (vd. 1.2)", "entry"),
        ("cat_thu6", "Cắt thứ 6 hàng tuần (thứ 6 tự tính vắng)", "check"),
        ("bt_tu", "Bắt đầu ăn bán trú từ ngày", "date"),
        ("cat_tu", "Cắt bán trú từ ngày", "date"),
        ("ghi_chu", "Ghi chú", "entry"),
    ]

    def __init__(self, parent, title: str, student: Student):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.s = student
        self.ok = False
        self.vars: dict[str, tk.Variable] = {}
        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        for i, (f, label, kind) in enumerate(self.FIELDS):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 10))
            v = getattr(student, f)
            if kind == "check":
                var = tk.BooleanVar(value=bool(v))
                ttk.Checkbutton(body, variable=var).grid(row=i, column=1, sticky="w")
            else:
                var = tk.StringVar(value=fmt_date(v) if kind == "date" else (v or ""))
                ttk.Entry(body, textvariable=var, width=34).grid(row=i, column=1, sticky="we")
            self.vars[f] = var
        self.lbl_err = ttk.Label(body, text="", style="Err.TLabel")
        self.lbl_err.grid(row=len(self.FIELDS), column=0, columnspan=2, sticky="w", pady=(6, 0))
        bar = ttk.Frame(body)
        bar.grid(row=len(self.FIELDS) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(bar, text="Lưu", style="Big.TButton", command=self._ok).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Hủy", command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        center(self, parent)
        self.wait_window()

    def _ok(self) -> None:
        vals = {f: v.get() for f, v in self.vars.items()}
        lop = norm_class(vals["lop"])
        name = clean_spaces(vals["ho_ten"])
        if not lop or not name:
            self.lbl_err.configure(text="Cần nhập lớp (vd. 1D15) và họ tên.")
            return
        dates = {}
        for f in ("bt_tu", "cat_tu"):
            raw = clean_spaces(vals[f])
            d = parse_date(raw)
            if raw and not d:
                self.lbl_err.configure(text=f"Ngày '{raw}' không đúng dạng dd/mm/yyyy.")
                return
            dates[f] = d
        lop_bt = norm_class(vals["lop_bt"]) if clean_spaces(vals["lop_bt"]) else ""
        s = self.s
        s.lop, s.ho_ten = lop, name
        s.ngay_sinh = fmt_date(parse_date(vals["ngay_sinh"])) or clean_spaces(vals["ngay_sinh"])
        s.ban_tru, s.cat_thu6 = bool(vals["ban_tru"]), bool(vals["cat_thu6"])
        s.ten_ghi_so = clean_spaces(vals["ten_ghi_so"])
        s.lop_bt = "" if lop_bt == lop else lop_bt
        s.an_ghep = clean_spaces(vals["an_ghep"]).replace(",", ".")
        s.ghi_chu = clean_spaces(vals["ghi_chu"])
        for f, d in dates.items():
            setattr(s, f, d)
        self.ok = True
        self.destroy()


class ImportDialog(tk.Toplevel):
    """Duyệt các thay đổi khi nhập file CDHS."""

    def __init__(self, parent, changes, rows):
        super().__init__(parent)
        self.title("Nhập danh sách học sinh")
        self.transient(parent.winfo_toplevel())
        self.changes = changes
        self.ok = False
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        n_red = sum(1 for r in rows if r.red)
        ttk.Label(body, style="Title.TLabel",
                  text=f"Đọc được {len(rows)} học sinh, {n_red} em chữ đỏ (ăn bán trú).").pack(anchor="w")
        mism = flag_mismatches(rows)
        if mism:
            txt = "Lưu ý: màu chữ khác cột 'Phân loại HS' ở: " + "; ".join(
                f"{r.ho_ten} ({r.lop}, {'đỏ' if r.red else 'không đỏ'}, ghi '{r.phan_loai}')" for r in mism[:8])
            ttk.Label(body, text=txt + ". App lấy theo màu chữ.", style="Warn.TLabel", wraplength=760,
                      justify="left").pack(anchor="w", pady=(4, 0))
        ttk.Label(body, text="Bấm vào dòng để bật/tắt. Chỉ các dòng có dấu tích được áp dụng.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 4))
        frame, self.tree = with_scrollbar(body, ttk.Treeview, columns=("nd",), show="tree headings", height=16)
        frame.pack(fill="both", expand=True)
        self.tree.heading("#0", text="Áp dụng")
        self.tree.heading("nd", text="Thay đổi")
        self.tree.column("#0", width=80, anchor="center")
        self.tree.column("nd", width=680)
        tag_colors(self.tree)
        for i, c in enumerate(changes):
            self.tree.insert("", "end", iid=str(i), image=_chk(c.apply), values=(c.text,),
                             tags=("err",) if c.kind == "removed" else ())
        self.tree.bind("<ButtonRelease-1>", self._toggle)
        if not changes:
            ttk.Label(body, text="Không có thay đổi nào so với danh sách hiện tại.", style="Ok.TLabel").pack(anchor="w")
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Áp dụng", style="Big.TButton", command=self._ok).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Chọn hết", command=lambda: self._all(True)).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Bỏ hết", command=lambda: self._all(False)).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Hủy", command=self.destroy).pack(side="left")
        self.grab_set()
        center(self, parent)
        self.wait_window()

    def _toggle(self, e) -> None:
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        c = self.changes[int(iid)]
        c.apply = not c.apply
        self.tree.item(iid, image=_chk(c.apply))

    def _all(self, on: bool) -> None:
        for i, c in enumerate(self.changes):
            c.apply = on
            self.tree.item(str(i), image=_chk(on))

    def _ok(self) -> None:
        self.ok = True
        self.destroy()


def ask_import(parent, ws, path: str) -> int | None:
    try:
        changes, rows = ws.import_cdhs(path)
    except RosterFormatError as e:
        messagebox.showerror("Không đọc được file", str(e), parent=parent)
        return None
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Không đọc được file", f"Lỗi khi đọc file:\n{e}", parent=parent)
        return None
    if ws.roster.students:
        dlg = ImportDialog(parent, changes, rows)
        if not dlg.ok:
            return None
    try:
        return ws.apply_import(changes, path)
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Chưa lưu được", f"Đã nhập nhưng chưa ghi được file dữ liệu:\n{e}\n\n"
                             "Nếu file dữ liệu đang mở trong Excel, hãy đóng rồi bấm Lưu thay đổi ở tab Học sinh.",
                             parent=parent)
        ws.data_dirty = True
        return len([c for c in changes if c.apply])


def ask_notes(parent, ws, quiet: bool = False) -> int | None:
    """Đọc ghi chú cột H trong sổ và cho giáo vụ duyệt các gợi ý cập nhật danh sách."""
    try:
        sugs = ws.note_suggestions()
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Không đọc được sổ", str(e), parent=parent)
        return None
    if not sugs:
        if not quiet:
            messagebox.showinfo("Ghi chú trong sổ", "Không có gợi ý mới nào từ ghi chú trong sổ.", parent=parent)
        return 0
    dlg = CheckListDialog(
        parent, "Gợi ý từ ghi chú trong sổ",
        "App đọc các ghi chú cột H (và các chữ 'cắt …', 'thêm …' trong ô tên vắng) của sổ tháng, "
        "rồi gợi ý cập nhật danh sách để sĩ số tự khớp và thứ 6 tự tính vắng. "
        "Hãy xem từng dòng; bỏ tích dòng nào không đúng.", sugs)
    if not dlg.ok:
        return None
    try:
        return ws.apply_note_suggestions(sugs)
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Chưa lưu được", f"Đã cập nhật nhưng chưa ghi được file dữ liệu:\n{e}\n\n"
                             "Hãy đóng file dữ liệu nếu đang mở trong Excel, rồi bấm Lưu thay đổi ở tab Học sinh.",
                             parent=parent)
        ws.data_dirty = True
        return sum(1 for g in sugs if g.apply and g.changes)
