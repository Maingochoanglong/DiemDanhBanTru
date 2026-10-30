"""Tab Điểm danh: bảng giống tờ sổ, dán tin Zalo, tích vắng theo lớp, bảng suất ăn.

Bố cục:
    ① ô dán tin Zalo + dòng tóm tắt kết quả (bấm để xem chi tiết)
    ② bảng điểm danh giống sổ (trái)      ③ lớp đang chọn: tích vắng (phải, trên)
                                           ④ bảng suất ăn (phải, dưới)
    thanh nút: Copy lớp chưa báo · Hoàn tác · Lưu vào sổ · Xem trước · In 2 tờ
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

from ..core import matcher
from ..core.text import fold
from .widgets import ERR_COLOR, MUTED_COLOR, OK_COLOR, WARN_COLOR, ChoiceDialog, ScrollFrame, center, tag_colors, with_scrollbar

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

# màu nền từng dòng lớp trong bảng: chưa báo / đủ / có vắng / cần xem
ROW_BG = {"muted": "#f2f2f2", "ok": "#e5f4e9", "warn": "#fff0d9", "err": "#fde2e2"}
ROW_FG = {"muted": MUTED_COLOR, "ok": "#145c2c", "warn": "#7a4300", "err": ERR_COLOR}
PROBLEM = (matcher.AMBIGUOUS, matcher.OTHER_CLASS, matcher.NOT_FOUND)


class ResultWindow(tk.Toplevel):
    """Cửa sổ "Kết quả kiểm tra": từng tên GV ghi và kết quả so với danh sách, đề nghị lịch thêm/cắt."""

    def __init__(self, tab: TabDiemDanh):
        super().__init__(tab)
        self.withdraw()
        self.tab = tab
        self.title("Kết quả kiểm tra tin nhắn")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.transient(tab.winfo_toplevel())
        ttk.Label(self, text="Bấm đúp vào dòng ⚠ / ✖ để chọn em đúng · dòng 📅 Đề nghị để áp dụng lịch.",
                  style="Muted.TLabel").pack(anchor="w", padx=10, pady=(8, 2))
        bar = ttk.Frame(self, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Đóng", command=self.withdraw).pack(side="right")
        ttk.Button(bar, text="Xóa kết quả", command=tab.clear_results).pack(side="right", padx=6)
        frame, self.tree = with_scrollbar(self, ttk.Treeview, columns=("kq",), show="tree headings")
        frame.pack(fill="both", expand=True, padx=10)
        t = self.tree
        t.heading("#0", text="Lớp / tên GV ghi")
        t.heading("kq", text="Kết quả")
        t.column("#0", width=260, stretch=False)
        t.column("kq", width=640)
        tag_colors(t)
        t.bind("<Double-Button-1>", tab._on_result_double)

    def show(self) -> None:
        if not self.winfo_viewable():
            self.geometry("960x520")
            center(self, self.tab.winfo_toplevel())
            self.deiconify()
        self.lift()
        self.focus_set()


class TabDiemDanh(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=6)
        self.app = app
        self.ws = app.ws
        self.current_class: str | None = None
        self.result_items: dict[str, tuple[str, matcher.MatchResult]] = {}
        self.sugg_items: dict[str, object] = {}  # iid -> đề nghị lịch (notes.Suggestion)
        self.check_vars: dict[str, tk.BooleanVar] = {}
        self.check_widgets: dict[str, ttk.Checkbutton] = {}
        self.meal_rows: dict[str, object] = {}  # iid -> MealLine
        self._summary: list[tuple[str, str]] = []  # (chữ, mức: ok/warn/err)
        self._build()
        self.results = ResultWindow(self)
        self.tree_res = self.results.tree

    # ------------------------------------------------------------------ dựng giao diện
    def _build(self) -> None:
        compact = getattr(self.winfo_toplevel(), "compact", False)
        base = tkfont.nametofont("TkDefaultFont")
        family, size = base.actual("family"), base.actual("size")
        style = ttk.Style()
        style.configure("So.Treeview", rowheight=23 if compact else 30, font=(family, size + 1))
        style.configure("So.Treeview.Heading", font=(family, size, "bold"))
        style.configure("Link.TLabel", font=(family, size, "bold"))

        # Thanh dưới (đóng gói trước để luôn hiện đủ khi cửa sổ thấp)
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Button(bottom, text="In 2 tờ (Ctrl+P)", style="Big.TButton", command=lambda: self.app.print_day(False)).pack(side="right")
        ttk.Button(bottom, text="Xem trước", command=lambda: self.app.print_day(True)).pack(side="right", padx=6)
        ttk.Button(bottom, text="Lưu vào sổ (Ctrl+S)", style="Big.TButton", command=self.app.save).pack(side="right", padx=6)
        ttk.Button(bottom, text="Hoàn tác (Ctrl+Z)", command=self.app.undo).pack(side="right", padx=6)
        ttk.Button(bottom, text="Copy lớp chưa báo", command=self.copy_unreported).pack(side="right", padx=6)
        self.lbl_saved = ttk.Label(bottom, text="")
        self.lbl_saved.pack(side="left")

        # ① Ô dán tin nhắn
        box = ttk.LabelFrame(self, text="① Dán tin nhắn Zalo vào đây (Ctrl+V) — dán cả đoạn chép từ Zalo máy tính, "
                                        "app tự lấy đúng tin của ngày đang mở", padding=(6, 4))
        box.pack(fill="x")
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Button(row, text="Xóa ô", command=lambda: self.paste.delete("1.0", "end")).pack(side="right", padx=(6, 0))
        ttk.Button(row, text="Kiểm tra (Ctrl+Enter)", style="Big.TButton", command=self.analyze).pack(side="right", padx=(6, 0))
        self.paste = tk.Text(row, height=2 if compact else 3, wrap="word", font=base, undo=True)
        self.paste.pack(side="left", fill="both", expand=True)
        self.paste.bind("<<Paste>>", lambda e: self.after(80, self.analyze))
        self.paste.bind("<Control-Return>", lambda e: (self.analyze(), "break")[1])
        srow = ttk.Frame(box)
        srow.pack(fill="x", pady=(4, 0))
        ttk.Button(srow, text="Kiểm tra lại sổ", command=self.app.recheck_day).pack(side="right")
        ttk.Button(srow, text="Kết quả chi tiết…", command=self.show_results).pack(side="right", padx=6)
        self.lbl_summary = ttk.Label(srow, text="", style="Link.TLabel", cursor="hand2")
        self.lbl_summary.pack(side="left", fill="x", expand=True)
        self.lbl_summary.bind("<Button-1>", lambda e: self.show_results())

        self.paned = paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(6, 0))

        # ② Bảng điểm danh giống sổ
        left = ttk.LabelFrame(paned, text="② Bảng điểm danh — bấm vào một lớp để xem, tích vắng", padding=4)
        paned.add(left, weight=3)
        self.lbl_totals = ttk.Label(left, text="", style="Title.TLabel")
        self.lbl_totals.pack(anchor="w", pady=(0, 4))
        legend = ttk.Frame(left)
        legend.pack(side="bottom", fill="x", pady=(4, 0))
        for text, key in (("○ chưa báo", "muted"), ("✔ đủ", "ok"), ("● có vắng", "warn"), ("⚠ cần xem", "err")):
            tk.Label(legend, text=f" {text} ", background=ROW_BG[key], foreground=ROW_FG[key]).pack(side="left", padx=(0, 6))
        ttk.Label(legend, text="📅 sĩ số đổi theo lịch thêm/cắt", style="Muted.TLabel").pack(side="left", padx=6)
        cols = ("lop", "gv", "siso", "vang", "hd", "ten", "note")
        frame, self.tree = with_scrollbar(left, ttk.Treeview, columns=cols, show="headings",
                                          selectmode="browse", style="So.Treeview")
        frame.pack(fill="both", expand=True)
        t = self.tree
        heads = {"lop": ("Lớp", 74, "w"), "gv": ("GVCN", 150 if compact else 190, "w"), "siso": ("Sĩ số", 50, "center"),
                 "vang": ("Vắng", 48, "center"), "hd": ("Hiện diện", 84, "center"),
                 "ten": ("Tên học sinh vắng", 250, "w"), "note": ("Ghi chú", 150, "w")}
        for c, (title, w, anchor) in heads.items():
            t.heading(c, text=title, anchor=anchor)
            t.column(c, width=w, anchor=anchor, stretch=c in ("ten", "note"), minwidth=40)
        for key in ROW_BG:
            t.tag_configure(key, background=ROW_BG[key], foreground=ROW_FG[key])
        t.tag_configure("sum", background="#e4ecf7", font=(family, size, "bold"))
        t.tag_configure("total", background="#c9d9ef", font=(family, size + 1, "bold"))
        t.bind("<<TreeviewSelect>>", self._on_class_select)
        t.bind("<Button-3>", self._on_table_right)

        right = ttk.PanedWindow(paned, orient="vertical")
        paned.add(right, weight=2)
        self.right = right

        # ③ Lớp đang chọn
        self.detail = ttk.LabelFrame(right, text="③ Lớp", padding=6)
        right.add(self.detail, weight=3)
        self.lbl_class = ttk.Label(self.detail, text="Chọn một lớp trong bảng", style="Title.TLabel")
        self.lbl_class.pack(anchor="w")
        brow = ttk.Frame(self.detail)
        brow.pack(fill="x", pady=(4, 2))
        ttk.Button(brow, text="Lớp này đủ", command=self.mark_full).pack(side="left")
        ttk.Button(brow, text="Bỏ đã báo", command=self.unmark_reported).pack(side="left", padx=4)
        ttk.Button(brow, text="Thêm/cắt…", command=lambda: self._schedule_menu_for(None)).pack(side="left")
        frow = ttk.Frame(self.detail)
        frow.pack(fill="x", pady=(2, 2))
        ttk.Label(frow, text="Tìm tên:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_checks())
        ttk.Entry(frow, textvariable=self.search_var, width=12).pack(side="left", padx=4)
        self.lbl_hint = ttk.Label(frow, text="tích ô = vắng · chuột phải vào tên: cắt / thứ 6", style="Muted.TLabel")
        self.lbl_hint.pack(side="left", padx=4)
        self.pending_row = ttk.Frame(self.detail)
        self.pending_row.pack(fill="x")
        self.checks = ScrollFrame(self.detail, height=120)
        self.checks.pack(fill="both", expand=True)
        self.lbl_sched = ttk.Label(self.detail, text="", style="Ok.TLabel", wraplength=300, justify="left")
        self.lbl_sched.pack(anchor="w")
        self.lbl_extra = ttk.Label(self.detail, text="", style="Warn.TLabel", wraplength=300, justify="left")
        self.lbl_extra.pack(anchor="w")
        nrow = ttk.Frame(self.detail)
        nrow.pack(fill="x", pady=(4, 0))
        ttk.Label(nrow, text="Ghi chú (cột H):").pack(side="left")
        self.note_var = tk.StringVar()
        e = ttk.Entry(nrow, textvariable=self.note_var)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<FocusOut>", lambda ev: self._save_note())
        e.bind("<Return>", lambda ev: self._save_note())
        self.btn_clear_extra = ttk.Button(self.detail, text="Xóa tên ghi nguyên văn", command=self.clear_extra)
        self.lbl_warn = ttk.Label(self.detail, text="", style="Err.TLabel", wraplength=300, justify="left")
        self.lbl_warn.pack(anchor="w")

        # ④ Bảng suất ăn
        meal = ttk.LabelFrame(right, text="④ Bảng suất ăn (tự tính)", padding=4)
        right.add(meal, weight=2)
        self.lbl_meal_total = ttk.Label(meal, text="", style="Title.TLabel")
        self.lbl_meal_total.pack(side="bottom", anchor="w", pady=(4, 0))
        self.lbl_meal_info = ttk.Label(meal, text="", style="Muted.TLabel", wraplength=300, justify="left")
        self.lbl_meal_info.pack(side="bottom", anchor="w", fill="x")
        frame, self.tree_meal = with_scrollbar(meal, ttk.Treeview, columns=("nhom", "lop", "suat"), show="headings",
                                               selectmode="browse", height=6)
        frame.pack(fill="both", expand=True)
        m = self.tree_meal
        m.heading("nhom", text="Nhóm", anchor="w")
        m.heading("lop", text="Gồm", anchor="w")
        m.heading("suat", text="Suất")
        m.column("nhom", width=110, stretch=False)
        m.column("lop", width=200)
        m.column("suat", width=56, anchor="center", stretch=False)
        tag_colors(m)
        m.bind("<<TreeviewSelect>>", self._on_meal_select)
        m.bind("<Double-Button-1>", self._on_meal_double)

        def wrap(e, widgets):
            for w in widgets:
                w.configure(wraplength=max(220, e.width - 20))

        self.detail.bind("<Configure>", lambda e: wrap(e, (self.lbl_warn, self.lbl_extra, self.lbl_sched)))
        meal.bind("<Configure>", lambda e: wrap(e, (self.lbl_meal_info,)))
        self.after(300, self._init_sashes)

    def _init_sashes(self) -> None:
        w = self.paned.winfo_width()
        if w < 200:
            self.after(300, self._init_sashes)
            return
        try:
            self.paned.sashpos(0, w - (470 if w < 1500 else 540))
            h = self.right.winfo_height()
            if h > 200:
                self.right.sashpos(0, int(h * (0.5 if h < 500 else 0.56)))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ làm mới
    def refresh(self) -> None:
        st = self.ws.state
        if st is None:
            return
        if self.current_class not in st.classes:
            self.current_class = next(iter(st.classes), None)
        self._refresh_table()
        self._build_checks()
        self._refresh_detail_labels()
        self._refresh_meals()
        self._refresh_totals()

    def refresh_light(self) -> None:
        """Làm mới số liệu, không dựng lại danh sách ô tích (giữ vị trí cuộn)."""
        self._refresh_table()
        self._sync_checks()
        self._refresh_detail_labels()
        self._refresh_meals()
        self._refresh_totals()

    def _class_status(self, code: str) -> tuple[str, str]:
        """(ký hiệu, mức màu) của 1 lớp."""
        st = self.ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        problem = bool(c.extra) or any(p[0] == code for p in st.pending) or bool(st.class_warnings(code))
        if problem:
            return "⚠", "err"
        if not c.reported and not n:
            return "○", "muted"
        if n:
            return "●", "warn"
        return "✔", "ok"

    def _class_values(self, code: str) -> tuple[tuple, str]:
        st = self.ws.state
        c = st.cd(code)
        icon, tag = self._class_status(code)
        info = self.ws.roster.classes.get(code)
        n = st.absent_count(code)
        names = ", ".join(st.absent_names(code))
        if not c.reported and not n:
            names = "(chưa báo)"
        note = c.note
        warns = st.class_warnings(code)
        if warns:
            note = "⚠ " + warns[0] + (f" · {note}" if note else "")
        if st.scheduled_changes(code):
            note = "📅 " + note
        vals = (f"{icon} {code}", info.gvcn if info else "", st.si_so(code), n, st.present(code), names, note)
        return vals, tag

    def _refresh_table(self) -> None:
        t = self.tree
        st = self.ws.state
        by_khoi: dict[int, list[str]] = {}
        for code in st.classes:
            by_khoi.setdefault(int(code[0]), []).append(code)
        order: list[str] = []
        for k, codes in sorted(by_khoi.items()):
            order += codes + [f"khoi{k}"]
        order.append("tong")
        if list(t.get_children()) != order:
            t.delete(*t.get_children())
            for iid in order:
                t.insert("", "end", iid=iid)
        for k, codes in sorted(by_khoi.items()):
            for code in codes:
                vals, tag = self._class_values(code)
                t.item(code, values=vals, tags=(tag,))
            si = sum(st.si_so(c) for c in codes)
            ab = sum(st.absent_count(c) for c in codes)
            t.item(f"khoi{k}", values=(f"KHỐI {k}", "", si, ab, si - ab, "", ""), tags=("sum",))
        si, ab, pr = st.totals()
        n_rep = sum(1 for c in st.classes.values() if c.reported)
        t.item("tong", values=("TỔNG CỘNG", f"đã báo {n_rep}/{len(st.classes)} lớp", si, ab, pr, "", ""), tags=("total",))
        sel = self.current_class
        if sel and t.exists(sel) and t.selection() != (sel,):
            t.selection_set(sel)
            t.see(sel)

    def _build_checks(self) -> None:
        self.checks.clear()
        self.check_vars.clear()
        self.check_widgets.clear()
        st = self.ws.state
        code = self.current_class
        if not code:
            return
        students = self.ws.roster.sort_like_roster(self.ws.roster.boarding(code, st.date))
        auto = st.auto_absent(code)
        cols = self._check_cols()
        for i, s in enumerate(students):
            var = tk.BooleanVar(value=st.is_absent(code, s.id))
            label = self.ws.roster.display_name(s)
            if s.id in auto:
                label += f"  ({auto[s.id]})"
            elif s.cat_thu6:
                label += "  (nghỉ T6)"
            if s.cat_tu and s.cat_tu > st.date:
                label += f"  (cắt từ {s.cat_tu:%d/%m})"
            if s.an_ghep:
                label += f"  [ăn {s.an_ghep}]"
            cb = ttk.Checkbutton(self.checks.inner, text=label, variable=var,
                                 command=lambda sid=s.id, v=var: self._toggle(sid, v.get()))
            cb.grid(row=i // cols, column=i % cols, sticky="w", padx=(4, 14), pady=1)
            cb.bind("<Button-3>", lambda e, st_=s: self._schedule_menu_for(st_, e))
            cb._search = fold(s.ho_ten + " " + label)  # type: ignore[attr-defined]
            self.check_vars[s.id] = var
            self.check_widgets[s.id] = cb
        for c in range(cols):
            self.checks.inner.columnconfigure(c, weight=1)
        if not students:
            ttk.Label(self.checks.inner, text="Lớp này chưa có em nào ăn bán trú trong danh sách.",
                      style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self._filter_checks()

    def _check_cols(self) -> int:
        w = self.detail.winfo_width()
        return 3 if w > 620 else 2

    def _sync_checks(self) -> None:
        st = self.ws.state
        code = self.current_class
        if not code:
            return
        boarding = {s.id for s in self.ws.roster.boarding(code, st.date)}
        if boarding != set(self.check_vars):
            self._build_checks()
            return
        for sid, var in self.check_vars.items():
            var.set(st.is_absent(code, sid))

    def _filter_checks(self) -> None:
        q = fold(self.search_var.get())
        cols = self._check_cols()
        i = 0
        for cb in self.check_widgets.values():
            if q and q not in cb._search:  # type: ignore[attr-defined]
                cb.grid_remove()
            else:
                cb.grid(row=i // cols, column=i % cols)
                i += 1

    def _refresh_detail_labels(self) -> None:
        st = self.ws.state
        code = self.current_class
        if not code:
            return
        info = self.ws.roster.classes.get(code)
        gv = f" · GVCN {info.gvcn}" if info and info.gvcn else ""
        ma = f" ({info.ma_ngan})" if info and info.ma_ngan else ""
        self.detail.configure(text=f"③ Lớp {code}{ma}{gv}")
        c = st.cd(code)
        state = "chưa báo" if not c.reported else ("đủ" if not st.absent_count(code) else "đã báo")
        self.lbl_class.configure(
            text=f"Sĩ số {st.si_so(code)} · Vắng {st.absent_count(code)} · Hiện diện {st.present(code)} · {state}")
        # tên chưa rõ của lớp: mỗi tên 1 nút để chọn em đúng
        for w in self.pending_row.winfo_children():
            w.destroy()
        pend = [res for p_code, res in st.pending if p_code == code]
        if pend:
            ttk.Label(self.pending_row, text="Tên chưa rõ:", style="Err.TLabel").pack(side="left")
            for res in pend[:6]:
                ttk.Button(self.pending_row, text=f"{res.icon} {res.query}…",
                           command=lambda r=res: self._resolve_from_detail(code, r)).pack(side="left", padx=2, pady=2)
        sched = []
        for it in st.scheduled_changes(code):
            what = "cắt" if it.kind == "cat" else "thêm"
            sched.append(f"{what} {it.student.ho_ten} (từ {it.start:%d/%m})")
        upcoming = [s for s in self.ws.roster.in_class(code)
                    if (s.cat_tu and s.cat_tu > st.date) or (s.ban_tru and s.bt_tu and s.bt_tu > st.date)]
        txt = ""
        if sched:
            txt = f"📅 Sĩ số đổi theo lịch ({c.sheet_si_so} → {st.si_so(code)}): " + "; ".join(sched)
        if upcoming:
            nxt = "; ".join(
                f"{'cắt' if s.cat_tu and s.cat_tu > st.date else 'thêm'} {s.ho_ten} từ "
                f"{(s.cat_tu if s.cat_tu and s.cat_tu > st.date else s.bt_tu):%d/%m}" for s in upcoming)
            txt += ("\n" if txt else "") + "Sắp tới: " + nxt
        self.lbl_sched.configure(text=txt)
        if c.extra:
            self.lbl_extra.configure(text="Tên ghi nguyên văn (chưa khớp danh sách): " + ", ".join(c.extra))
            self.btn_clear_extra.pack(anchor="w", before=self.lbl_warn)
        else:
            self.lbl_extra.configure(text="")
            self.btn_clear_extra.pack_forget()
        self.note_var.set(c.note)
        warns = st.class_warnings(code)
        self.lbl_warn.configure(text="\n".join("⚠ " + w for w in warns))

    def _refresh_meals(self) -> None:
        m = self.tree_meal
        m.delete(*m.get_children())
        self.meal_rows.clear()
        layout = self.ws.layout
        if layout.is_empty:
            self.lbl_meal_total.configure(text="")
            self.lbl_meal_info.configure(text="Sổ chưa có bảng suất ăn bên dưới (như sheet ngày 21–28/10).",
                                         style="Err.TLabel")
            return
        summary = self.ws.meals()
        manual = self.ws.state.manual_codes(layout)
        for line in summary.lines:
            r = line.row
            gom = " + ".join(r.classes)
            if r.code:
                gom += f" + ghép {line.o}"
                if line.m:
                    gom += f" − vắng {line.m}"
                if r.code in manual:
                    gom += " ✎"
            iid = m.insert("", "end", values=(r.label, gom, line.meals), tags=("warn",) if line.m else ())
            self.meal_rows[iid] = line
        if layout.self_classes:
            m.insert("", "end", values=("Tự ăn tại lớp", ", ".join(layout.self_classes), summary.self_meals),
                     tags=("muted",))
        ok = summary.balanced
        self.lbl_meal_total.configure(
            text=f"Tổng suất {summary.total_meals} {'=' if ok else '≠'} hiện diện {summary.total_present} {'✔' if ok else '✖'}",
            style="Ok.TLabel" if ok else "Err.TLabel")
        info = "Bấm vào 1 nhóm để xem chi tiết · nhóm có ✎: bấm đúp để nhập số em ghép vắng."
        if summary.warnings:
            self.lbl_meal_info.configure(text="\n".join("⚠ " + w for w in summary.warnings), style="Err.TLabel")
        else:
            self.lbl_meal_info.configure(text=info, style="Muted.TLabel")

    def _on_meal_select(self, _e=None) -> None:
        sel = self.tree_meal.selection()
        line = self.meal_rows.get(sel[0]) if sel else None
        if line is None:
            return
        r = line.row
        text = f"{r.label}: {' + '.join(r.classes) or '—'}"
        if r.code:
            text += f" + {line.o} em ghép"
            if line.m:
                names = f": {', '.join(line.absent_names)}" if line.absent_names else ""
                text += f", ghép vắng {line.m}{names}"
        text += f" → {line.meals} suất"
        self.lbl_meal_info.configure(text=text, style="TLabel")

    def _on_meal_double(self, _e=None) -> None:
        from tkinter import simpledialog

        sel = self.tree_meal.selection()
        line = self.meal_rows.get(sel[0]) if sel else None
        if line is None or not line.row.code:
            return
        code = line.row.code
        st = self.ws.state
        if code not in st.manual_codes(self.ws.layout):
            self.app.flash(f"Nhóm {code} tự tính theo danh sách ghép (tab Ghép lớp).")
            return
        val = simpledialog.askinteger("Vắng ghép", f"Số em ghép vắng ở nhóm {code}:", parent=self,
                                      initialvalue=st.manual_m.get(code, 0), minvalue=0, maxvalue=99)
        if val is None:
            return
        self.ws.push_undo()
        st.manual_m[code] = val
        self.refresh_light()

    def _refresh_totals(self) -> None:
        st = self.ws.state
        si, ab, pr = st.totals()
        n_rep = sum(1 for c in st.classes.values() if c.reported)
        wd = WEEKDAYS[st.date.weekday()]
        self.lbl_totals.configure(
            text=f"{wd} {st.date:%d/%m/%Y}  ·  Đã báo {n_rep}/{len(st.classes)} lớp  ·  Sĩ số {si}  ·  "
                 f"Vắng {ab}  ·  Hiện diện {pr}")
        saved = "● Có thay đổi chưa lưu vào sổ" if self.ws.dirty else (
            "Đã có trong sổ" if st.exists_in_book else "Ngày này chưa có trong sổ")
        self.lbl_saved.configure(text=saved, style="Warn.TLabel" if self.ws.dirty else "Muted.TLabel")
        self._show_summary()

    # ------------------------------------------------------------------ tóm tắt kết quả
    def _set_summary(self, parts: list[tuple[str, str]]) -> None:
        self._summary = parts
        self._show_summary()

    def _show_summary(self) -> None:
        st = self.ws.state
        parts = list(self._summary)
        n_pending = len(st.pending) if st else 0
        if n_pending:
            parts.append((f"⚠ còn {n_pending} tên chưa rõ — bấm để xử lý", "err"))
        n_sug = len(self.sugg_items)
        if n_sug:
            parts.append((f"📅 {n_sug} đề nghị thêm/cắt bán trú — bấm để xem", "warn"))
        if not parts:
            self.lbl_summary.configure(text="Chưa dán tin nào.", foreground=MUTED_COLOR)
            return
        worst = "err" if any(k == "err" for _, k in parts) else ("warn" if any(k == "warn" for _, k in parts) else "ok")
        color = {"ok": OK_COLOR, "warn": WARN_COLOR, "err": ERR_COLOR}[worst]
        self.lbl_summary.configure(text="  ·  ".join(t for t, _ in parts), foreground=color)

    def show_results(self) -> None:
        self.results.show()

    # ------------------------------------------------------------------ thao tác
    def _on_class_select(self, _e=None) -> None:
        sel = self.tree.selection()
        if not sel or sel[0].startswith("khoi") or sel[0] == "tong":
            return
        if sel[0] != self.current_class:
            self._save_note()
            self.current_class = sel[0]
            self.search_var.set("")
            self._build_checks()
            self._refresh_detail_labels()

    def _on_table_right(self, e) -> None:
        iid = self.tree.identify_row(e.y)
        if iid and iid in self.ws.state.classes:
            self.tree.selection_set(iid)
            self._on_class_select()
            self._schedule_menu_for(None, e)

    def select_class(self, code: str) -> None:
        if self.tree.exists(code):
            self.tree.selection_set(code)
            self.tree.see(code)
            self._on_class_select()

    def _toggle(self, sid: str, absent: bool) -> None:
        self.ws.push_undo()
        self.ws.state.set_absent(self.current_class, sid, absent)
        self.refresh_light()

    def mark_full(self) -> None:
        if not self.current_class:
            return
        self.ws.push_undo()
        self.ws.state.mark_full(self.current_class)  # em cắt thứ 6 vẫn tính vắng vào thứ 6
        self.refresh_light()

    def unmark_reported(self) -> None:
        if not self.current_class:
            return
        self.ws.push_undo()
        self.ws.state.cd(self.current_class).reported = False
        self.refresh_light()

    def clear_extra(self) -> None:
        if not self.current_class:
            return
        self.ws.push_undo()
        self.ws.state.cd(self.current_class).extra.clear()
        self.refresh_light()

    def _save_note(self) -> None:
        code = self.current_class
        if not code or self.ws.state is None:
            return
        c = self.ws.state.cd(code)
        val = self.note_var.get().strip()
        if val != c.note:
            self.ws.push_undo()
            c.note = val
            self._refresh_totals()
            if self.tree.exists(code):
                vals, tag = self._class_values(code)
                self.tree.item(code, values=vals, tags=(tag,))

    def _schedule_menu_for(self, student, event=None) -> None:
        """Menu đặt lịch nhanh cho 1 em (chuột phải) hoặc cho cả lớp (nút Thêm/cắt BT…)."""
        from ..core import schedule as sch

        code = self.current_class
        if not code:
            return
        tab = self.app.tab_lich
        ids = (student.id,) if student else ()
        menu = tk.Menu(self, tearoff=0)
        title = student.ho_ten if student else f"Lớp {code}"
        menu.add_command(label=title, state="disabled")
        menu.add_separator()
        menu.add_command(label="✂ Cắt bán trú từ ngày…", command=lambda: tab.open_dialog(sch.CUT, code, ids))
        if student is None:
            menu.add_command(label="＋ Thêm em vào bán trú…", command=lambda: tab.open_dialog(sch.ADD, code))
        if student is not None and student.cat_thu6:
            menu.add_command(label="Bỏ cắt thứ 6", command=lambda: self._undo_friday(student))
        else:
            menu.add_command(label="Cắt thứ 6 hàng tuần…", command=lambda: tab.open_dialog(sch.FRIDAY, code, ids))
        if event is not None:
            x, y = event.x_root, event.y_root
        else:
            x, y = self.winfo_pointerx(), self.winfo_pointery()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _undo_friday(self, student) -> None:
        from ..core import schedule as sch

        try:
            self.ws.cancel_schedule(sch.ScheduleItem(sch.FRIDAY, student))
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
        self.app.flash(f"Đã bỏ cắt thứ 6 cho {student.ho_ten}.")
        self.app.refresh_days_only()
        self.app.tab_lich.refresh()

    def show_scheduled_changes(self) -> None:
        """Báo các em thêm/cắt có hiệu lực từ hôm nay (so với sổ hôm trước)."""
        st = self.ws.state
        if st is None:
            return
        changes = st.scheduled_changes()
        if not changes:
            return
        r = self.tree_res
        pid = r.insert("", 0, text="📅 Lịch", values=(f"{len(changes)} thay đổi bán trú có hiệu lực từ hôm nay — sĩ số đã tự cập nhật",),
                       tags=("ok", "bold"), open=True)
        for it in changes:
            what = "cắt bán trú" if it.kind == "cat" else "thêm bán trú"
            r.insert(pid, "end", text=it.student.lop_tinh, values=(f"{what}: {it.student.ho_ten} (từ {it.start:%d/%m})",))
        self._summary.append((f"📅 {len(changes)} em thêm/cắt từ hôm nay (sĩ số đã tự đổi)", "ok"))
        self._show_summary()

    def copy_unreported(self) -> None:
        st = self.ws.state
        codes = st.unreported()
        if not codes:
            self.app.flash("Tất cả các lớp đã báo.")
            return
        parts = []
        for c in codes:
            info = self.ws.roster.classes.get(c)
            parts.append(f"{c} ({info.gvcn})" if info and info.gvcn else c)
        text = "Các lớp chưa báo sĩ số bán trú: " + ", ".join(parts)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.flash(f"Đã copy {len(codes)} lớp chưa báo — dán vào Zalo để nhắc.")

    # ------------------------------------------------------------------ dán tin nhắn
    def analyze(self) -> None:
        text = self.paste.get("1.0", "end").strip()
        if not text or self.ws.state is None:
            return
        outcomes = self.ws.paste(text)
        skipped = self.ws.paste_skipped
        if not outcomes and not skipped:
            self.app.flash("Không đọc được tin nhắn nào (không thấy mã lớp hoặc tên).", error=True)
            return
        self.paste.delete("1.0", "end")
        r = self.tree_res
        if skipped:
            days = ", ".join(f"{d:%d/%m} ({n})" for d, n in sorted(skipped.items()))
            r.insert("", 0, text="Bỏ qua", values=(f"{sum(skipped.values())} tin của ngày khác: {days} — "
                                                     "mở đúng ngày rồi dán lại nếu cần",), tags=("muted",))
        last = None
        classes, unknown, not_bt = set(), 0, 0
        for po in outcomes:
            code = self._show_outcome(po)
            if code and po.message.is_report:
                classes.add(code)
                last = code
            unknown += po.message.cls is None
            not_bt += sum(1 for x in po.results if x.status == matcher.NOT_BT)
        st = self.ws.state
        parts = []
        if classes:
            parts.append((f"Vừa dán: {len(classes)} lớp ngày {st.date:%d/%m}", "ok"))
        elif skipped:
            parts.append((f"Không có tin nào của ngày {st.date:%d/%m}", "warn"))
        if unknown:
            parts.append((f"⚠ {unknown} tin không rõ lớp — bấm để xem", "err"))
        if not_bt:
            parts.append((f"⛔ {not_bt} tên không ăn bán trú (đã bỏ qua)", "ok"))
        if skipped:
            parts.append((f"bỏ qua {sum(skipped.values())} tin ngày khác", "ok"))
        self._summary = parts
        self.refresh()
        if last:
            self.select_class(last)
        if self.sugg_items and any(po.suggestions for po in outcomes):
            self.show_results()  # đề nghị thêm/cắt cần giáo vụ xác nhận

    def _show_outcome(self, po) -> str | None:
        r = self.tree_res
        msg = po.message
        st = self.ws.state
        if msg.cls is None:
            if po.guessed_from:
                why = "nhiều lớp cùng có các tên này: " + ", ".join(po.guessed_from)
            else:
                why = "không đoán được lớp — hãy dán kèm mã lớp (vd. 2D17) hoặc tích tay"
            who = f" ({msg.sender})" if msg.sender else ""
            r.insert("", 0, text=f"? không rõ lớp{who}", values=(f"{', '.join(msg.names)} — {why}",), tags=("err",))
            return None
        code = msg.cls
        if msg.schedule:
            self._show_schedule(po)
        if not msg.is_report:
            return code
        count = f"báo {msg.present}/{msg.total} · " if msg.total is not None else ""
        if po.class_by == "sender":
            guess = f" (theo người gửi {msg.sender})"
        elif msg.guessed:
            guess = " (app đoán lớp)"
        else:
            guess = ""
        when = f"{msg.when:%H:%M} " if msg.when else ""
        if msg.full:
            head = f"{when}{count}đủ"
        else:
            head = f"{when}{count}ghi {st.absent_count(code)} tên vắng: {', '.join(st.absent_names(code))}"
        warns = st.class_warnings(code)
        tag = "err" if warns else ("ok" if msg.full else "warn")
        pid = r.insert("", 0, text=f"{code}{guess}", values=(head,), tags=(tag, "bold"), open=True)
        for w in warns:
            r.insert(pid, "end", text="  ⚠", values=(w,), tags=("err",))
        for res in po.results:
            self._insert_result(pid, code, res)
        return code

    def _show_schedule(self, po) -> None:
        r = self.tree_res
        msg = po.message
        src = f"{msg.cls}: \"{msg.schedule}\"" + (f" ({msg.sender} {msg.when:%d/%m %H:%M})" if msg.when else "")
        if po.schedule_known:
            r.insert("", 0, text=f"📅 {msg.cls}", values=(f"{src} — lịch này đã có, không cần làm gì",), tags=("muted",))
            return
        for sug in po.suggestions:
            if not sug.apply or not sug.changes:
                r.insert("", 0, text=f"📅 {msg.cls}", values=(f"{src} — {sug.text}",), tags=("err",))
                continue
            what = sug.text.split(" — ", 1)[-1]
            who = sug.student.ho_ten if sug.student else sug.new_name
            iid = r.insert("", 0, text=f"📅 Đề nghị {msg.cls}",
                           values=(f"{who}: {what} — bấm đúp để áp dụng · tin {src}",), tags=("warn", "bold"))
            self.sugg_items[iid] = sug

    def _insert_result(self, parent: str, code: str, res: matcher.MatchResult) -> None:
        r = self.tree_res
        roster = self.ws.roster
        if res.status == matcher.OK:
            text = f"→ {roster.display_name(res.student)}  ({res.student.ho_ten})"
            tag = "ok"
        elif res.status == matcher.AMBIGUOUS:
            text = f"{len(res.candidates)} em trùng tên: " + ", ".join(c.ho_ten for c in res.candidates) + " — bấm đúp để chọn"
            tag = "warn"
        elif res.status == matcher.NOT_BT:
            text = f"{res.student.ho_ten} KHÔNG ăn bán trú — bỏ qua, không ghi"
            tag = "muted"
        elif res.status == matcher.OTHER_CLASS:
            where = ", ".join(f"{c.ho_ten} ({c.lop})" for c in res.candidates[:3])
            text = f"Không có trong lớp {code}. Có em cùng tên ở: {where} — bấm đúp"
            tag = "err"
        else:
            sug = ", ".join(roster.display_name(c) for c in res.candidates[:3])
            text = "Không tìm thấy trong lớp" + (f". Gần giống: {sug}" if sug else "") + " — bấm đúp"
            tag = "err"
        iid = r.insert(parent, "end", text=f"{res.icon} {res.query}", values=(text,), tags=(tag,))
        if res.status in PROBLEM:
            self.result_items[iid] = (code, res)

    def show_sheet_checks(self) -> None:
        """Hiện kết quả kiểm tra các ô tên vắng đã có trong sổ (gõ tay hoặc app ghi trước đó)."""
        checks = self.ws.sheet_checks
        if not checks:
            return
        r = self.tree_res
        bad = [(code, res) for code, lst in checks.items() for res in lst if res.status != matcher.OK]
        st = self.ws.state
        n = sum(len(v) for v in checks.values())
        head = f"Kiểm tra sổ ngày {st.date:%d/%m}: {n} tên"
        if not bad:
            r.insert("", 0, text="Sổ", values=(head + " — tất cả đều đúng ✔",), tags=("ok", "bold"))
            self._summary = [(f"Sổ ngày {st.date:%d/%m}: {n} tên vắng, tất cả đều đúng ✔", "ok")]
        else:
            pid = r.insert("", 0, text="Sổ", values=(head + f" — {len(bad)} tên cần xem",), tags=("err", "bold"), open=True)
            for code, res in bad:
                sub = r.insert(pid, "end", text=code, values=("",), open=True)
                self._insert_result(sub, code, res)
            self._summary = [(f"Sổ ngày {st.date:%d/%m}: {len(bad)}/{n} tên cần xem — bấm để xem", "err")]
        self._show_summary()

    def clear_results(self) -> None:
        self.tree_res.delete(*self.tree_res.get_children())
        self.result_items.clear()
        self.sugg_items.clear()
        self._summary = []
        if self.ws.state is not None:
            self._show_summary()

    def _on_result_double(self, _e=None) -> None:
        sel = self.tree_res.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in self.sugg_items:
            self._apply_suggestion(iid)
            return
        if iid not in self.result_items:
            code = self.tree_res.item(iid, "text").split(" ")[0]
            if code in self.ws.state.classes:
                self.select_class(code)
            return
        code, res = self.result_items[iid]
        self._resolve(code, res)

    def _apply_suggestion(self, iid: str) -> None:
        sug = self.sugg_items[iid]
        who = sug.student.ho_ten if sug.student else sug.new_name
        what = sug.text.split(" — ", 1)[-1]
        if not messagebox.askyesno("Áp dụng lịch", f"Lớp {sug.code}: {who} — {what}.\n\nÁp dụng vào danh sách bán trú?",
                                   parent=self.results):
            return
        try:
            note = self.ws.apply_paste_suggestion(sug)
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        del self.sugg_items[iid]
        done = f"Đã áp dụng: {who} — {what}" + (f" · ghi chú cột H: \"{note}\"" if note else "")
        self.tree_res.item(iid, text=f"✔ {sug.code}", values=(done,), tags=("ok",))
        self.app.flash(done)
        self.app.refresh_days_only()
        self.app.tab_lich.refresh()

    def _resolve(self, code: str, res: matcher.MatchResult) -> None:
        """Hộp chọn em đúng cho 1 tên chưa rõ; cập nhật dòng kết quả tương ứng."""
        roster = self.ws.roster
        st = self.ws.state
        boarding_ids = {s.id for s in roster.boarding(code, st.date)}
        cands = [c for c in res.candidates if c.id in boarding_ids]
        options = [f"{roster.display_name(c)}  —  {c.ho_ten}  —  sinh {c.ngay_sinh}" for c in cands]
        if res.status == matcher.OTHER_CLASS:
            where = "; ".join(f"{c.ho_ten} lớp {c.lop}{' (ăn BT)' if c.ban_tru else ''}" for c in res.candidates)
            msg = (f"'{res.query}' không có trong danh sách bán trú lớp {code}.\nCó em cùng tên ở: {where}.\n\n"
                   "Nếu em này mới chuyển vào lớp, hãy sửa ở tab Học sinh. Hoặc chọn ghi nguyên văn vào sổ.")
        elif cands:
            msg = f"Lớp {code}: tên '{res.query}' — chọn em đúng:"
        else:
            msg = f"Lớp {code}: không tìm thấy '{res.query}' trong danh sách bán trú."
        buttons = ([("pick", "Chọn em này")] if cands else []) + [("raw", "Ghi nguyên văn"), ("skip", "Bỏ qua tên này")]
        dlg = ChoiceDialog(self, "Chọn học sinh", msg, options, buttons, need_choice={"pick"})
        key, idx = dlg.result
        if key is None:
            return
        self.ws.push_undo()
        if key == "pick" and idx is not None:
            st.resolve_pending(code, res, cands[idx])
            row = (f"✔ {res.query}", f"→ {roster.display_name(cands[idx])}  (đã chọn)", "ok")
        elif key == "raw":
            st.resolve_pending(code, res, None, keep_raw=True)
            row = (f"✎ {res.query}", "Ghi nguyên văn vào sổ", "warn")
        else:
            st.resolve_pending(code, res, None)
            row = (f"– {res.query}", "Đã bỏ qua", "muted")
        for iid, (_, r) in list(self.result_items.items()):
            if r is res:
                self.tree_res.item(iid, text=row[0], values=(row[1],), tags=(row[2],))
                del self.result_items[iid]
        if code in st.classes:
            st.cd(code).reported = True
        self.refresh_light()
        self.select_class(code)

    def _resolve_from_detail(self, code: str, res: matcher.MatchResult) -> None:
        self._resolve(code, res)
