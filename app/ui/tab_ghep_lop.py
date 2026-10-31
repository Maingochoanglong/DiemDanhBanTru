"""Tab Ghép lớp: gán từng em lớp ghép (1.5, 4.4…) vào nhóm ăn (1.1, 1.2…)."""

from __future__ import annotations

from tkinter import messagebox, ttk

from .widgets import ScrollFrame, TextDialog, tag_colors, with_scrollbar


class TabGhepLop(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.ws = app.ws
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Danh sách học sinh ăn ghép", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Lưu danh sách ghép", style="Big.TButton", command=self.save).pack(side="right")
        ttk.Label(self, style="Muted.TLabel", wraplength=900, justify="left", text=(
            "Lớp ghép là lớp không có hàng riêng trong bảng suất ăn; các em được chia sang ăn cùng lớp khác. "
            "Chọn một hoặc nhiều em (giữ Ctrl để chọn nhiều) rồi bấm nút nhóm. Khi em vắng, app tự điền ô "
            "\"vắng\" đúng hàng trong bảng suất ăn.")).pack(anchor="w", pady=(4, 8))
        self.body = ScrollFrame(self)
        self.body.pack(fill="both", expand=True)
        self.trees: dict[str, ttk.Treeview] = {}

    def refresh(self) -> None:
        self.body.clear()
        self.trees.clear()
        layout = self.ws.layout
        if layout.is_empty or not layout.ghep_classes:
            ttk.Label(self.body.inner, text="Sổ đang mở không có lớp ghép (bảng suất ăn không có hàng \"… ghép\" nhận học sinh lẻ).",
                      style="Muted.TLabel").pack(anchor="w")
            return
        o_now = self.ws.state.o_values(layout) if self.ws.state else layout.o_values
        for code in layout.ghep_classes:
            khoi = int(code[0])
            groups = layout.ghep_codes(khoi)
            students = self.ws.ghep_students(code)
            info = self.ws.roster.classes.get(code)
            ma = f" ({info.ma_ngan})" if info and info.ma_ngan else ""
            box = ttk.LabelFrame(self.body.inner, text=f"Lớp {code}{ma} — {len(students)} em ăn bán trú", padding=6)
            box.pack(fill="x", pady=(0, 10), padx=2)
            frame, tree = with_scrollbar(box, ttk.Treeview, columns=("ht", "ns", "nhom"), show="tree headings",
                                         height=min(14, max(3, len(students))), selectmode="extended")
            frame.pack(side="left", fill="both", expand=True)
            tree.heading("#0", text="Tên ghi sổ")
            tree.heading("ht", text="Họ tên")
            tree.heading("ns", text="Ngày sinh")
            tree.heading("nhom", text="Ăn ghép tại")
            tree.column("#0", width=150)
            tree.column("ht", width=220)
            tree.column("ns", width=100, anchor="center")
            tree.column("nhom", width=100, anchor="center")
            tag_colors(tree)
            for s in students:
                ok = s.an_ghep in groups
                tree.insert("", "end", iid=s.id, text=self.ws.roster.display_name(s),
                            values=(s.ho_ten, s.ngay_sinh, s.an_ghep or "chưa gán"), tags=() if ok else ("err",))
            self.trees[code] = tree
            side = ttk.Frame(box)
            side.pack(side="left", fill="y", padx=(10, 0))
            for g in groups:
                n = sum(1 for s in students if s.an_ghep == g)
                in_book = layout.o_values.get(g)
                txt = f"→ Ăn ở {g}   ({n} em"
                txt += f", sổ ghi {in_book})" if in_book is not None else ")"
                ttk.Button(side, text=txt, command=lambda c=code, gg=g: self.assign(c, gg)).pack(fill="x", pady=2)
            ttk.Button(side, text="Bỏ gán", command=lambda c=code: self.assign(c, "")).pack(fill="x", pady=(8, 2))
            ttk.Button(side, text="Dán danh sách ghép…", command=lambda c=code: self.paste_list(c)).pack(fill="x", pady=2)
            total = sum(o_now.get(g, 0) for g in groups)
            style = "Ok.TLabel" if total == len(students) else "Err.TLabel"
            ttk.Label(side, text=f"Tổng ghép: {total}/{len(students)} em", style=style).pack(anchor="w", pady=(8, 0))
            unassigned = sum(1 for s in students if s.an_ghep not in groups)
            if unassigned:
                ttk.Label(side, text=f"{unassigned} em chưa gán nhóm", style="Err.TLabel").pack(anchor="w")

    def assign(self, code: str, group: str) -> None:
        tree = self.trees.get(code)
        ids = list(tree.selection()) if tree else []
        if not ids:
            messagebox.showinfo("Ghép lớp", "Hãy chọn một hoặc nhiều em trong danh sách trước.", parent=self)
            return
        self.ws.assign_ghep(ids, group)
        self._changed = True
        self.refresh()
        self.app.refresh_days_only()

    def paste_list(self, code: str) -> None:
        dlg = TextDialog(self, f"Dán danh sách ghép lớp {code}",
                         "Mỗi dòng ghi mã nhóm rồi tên các em, ví dụ:\n"
                         "1.1: Bảo Ngọc, Gia Hân, Minh Khôi\n1.2: Đức Anh, Thảo Vy")
        if not dlg.result:
            return
        n, problems = self.ws.assign_ghep_text(code, dlg.result)
        self.refresh()
        self.app.refresh_days_only()
        msg = f"Đã gán {n} em."
        if problems:
            msg += "\n\nCần xem lại:\n" + "\n".join(problems[:20])
        messagebox.showinfo("Ghép lớp", msg, parent=self)

    def save(self) -> None:
        try:
            self.ws.save_data()
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        self.app.flash("Đã lưu danh sách ghép vào file dữ liệu.")
