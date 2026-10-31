"""Tab Suất ăn: bảng suất ăn cho bảo mẫu (tự tính từ bảng điểm danh)."""

from __future__ import annotations

from tkinter import simpledialog, ttk
from tkinter import font as tkfont

from .widgets import tag_colors, with_scrollbar


class TabSuatAn(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.ws = app.ws
        self.rows: dict[str, object] = {}  # iid -> MealLine
        base = tkfont.nametofont("TkDefaultFont")
        family, size = base.actual("family"), base.actual("size")
        compact = getattr(self.winfo_toplevel(), "compact", False)
        style = ttk.Style()
        style.configure("Meal.Treeview", rowheight=28 if compact else 32, font=(family, size + 2))
        style.configure("Meal.Treeview.Heading", font=(family, size + 1, "bold"))
        style.configure("MealTotal.TLabel", font=(family, size + 4, "bold"))

        self.lbl_total = ttk.Label(self, text="", style="MealTotal.TLabel")
        self.lbl_total.pack(anchor="w")
        self.lbl_info = ttk.Label(self, text="", style="Muted.TLabel", justify="left")
        self.lbl_info.pack(side="bottom", anchor="w", fill="x", pady=(8, 0))
        self.bind("<Configure>", lambda e: self.lbl_info.configure(wraplength=max(400, e.width - 30)))
        frame, self.tree = with_scrollbar(self, ttk.Treeview, columns=("nhom", "lop", "suat"), show="headings",
                                          selectmode="browse", style="Meal.Treeview")
        frame.pack(fill="both", expand=True, pady=(8, 0))
        t = self.tree
        t.heading("nhom", text="Nhóm", anchor="w")
        t.heading("lop", text="Gồm", anchor="w")
        t.heading("suat", text="Suất")
        t.column("nhom", width=220, stretch=False)
        t.column("lop", width=600)
        t.column("suat", width=100, anchor="center", stretch=False)
        tag_colors(t)
        t.bind("<<TreeviewSelect>>", self._on_select)
        t.bind("<Double-Button-1>", self._on_double)

    def refresh(self) -> None:
        t = self.tree
        t.delete(*t.get_children())
        self.rows.clear()
        if self.ws.state is None:
            return
        layout = self.ws.layout
        if layout.is_empty:
            self.lbl_total.configure(text="Sổ chưa có bảng suất ăn", style="MealTotal.TLabel")
            self.lbl_info.configure(text="Sheet mẫu của sổ không có bảng suất ăn bên dưới bảng điểm danh.")
            return
        summary = self.ws.meals()
        manual = self.ws.state.manual_codes(layout)
        for line in summary.lines:
            r = line.row
            gom = " + ".join(r.classes)
            if r.code:
                gom += f" + ghép {line.o} em"
                if line.m:
                    gom += f" − vắng {line.m}"
                if r.code in manual:
                    gom += "  ✎"
            iid = t.insert("", "end", values=(r.label, gom, line.meals), tags=("warn",) if line.m else ())
            self.rows[iid] = line
        if layout.self_classes:
            t.insert("", "end", values=("Tự ăn tại lớp", ", ".join(layout.self_classes), summary.self_meals),
                     tags=("muted",))
        ok = summary.balanced
        self.lbl_total.configure(
            text=f"Tổng suất {summary.total_meals} {'=' if ok else '≠'} hiện diện {summary.total_present} "
                 f"{'✔' if ok else '✖'}",
            foreground="#1b7f3b" if ok else "#b00020")
        if summary.warnings:
            self.lbl_info.configure(text="\n".join("⚠ " + w for w in summary.warnings), style="Err.TLabel")
        else:
            self.lbl_info.configure(text="Bấm vào 1 nhóm để xem em ghép vắng. Nhóm có ✎: bấm đúp để nhập số em ghép vắng.",
                                    style="Muted.TLabel")

    def _on_select(self, _e=None) -> None:
        sel = self.tree.selection()
        line = self.rows.get(sel[0]) if sel else None
        if line is None:
            return
        r = line.row
        text = f"{r.label}: {' + '.join(r.classes) or '—'}"
        if r.code:
            text += f" + {line.o} em ghép"
            if line.m:
                names = f": {', '.join(line.absent_names)}" if line.absent_names else ""
                text += f", ghép vắng {line.m}{names}"
        self.lbl_info.configure(text=f"{text} → {line.meals} suất", style="TLabel")

    def _on_double(self, _e=None) -> None:
        sel = self.tree.selection()
        line = self.rows.get(sel[0]) if sel else None
        if line is None or not line.row.code:
            return
        code = line.row.code
        st = self.ws.state
        if code not in st.manual_codes(self.ws.layout):
            self.app.flash(f"Nhóm {code} tự tính theo danh sách ghép (tab Học sinh → Ghép lớp).")
            return
        val = simpledialog.askinteger("Vắng ghép", f"Số em ghép vắng ở nhóm {code}:", parent=self,
                                      initialvalue=st.manual_m.get(code, 0), minvalue=0, maxvalue=99)
        if val is None:
            return
        self.ws.push_undo()
        st.manual_m[code] = val
        self.app.tab_dd.refresh_light()
        self.refresh()
