"""Tab Điểm danh: ô dán tin Zalo + bảng điểm danh giống tờ sổ (rộng hết màn hình).

Bấm đúp vào một lớp để mở cửa sổ của lớp đó (tích vắng, tên chưa rõ, ghi chú cột H).
Bảng suất ăn nằm ở tab Suất ăn. Icon là ảnh (app/ui/icons.py), không dùng ký tự.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from ..core import matcher
from ..core.text import fold
from .icons import RESULT_ICON, STATUS_ICON, icon
from .widgets import ERR_COLOR, MUTED_COLOR, OK_COLOR, WARN_COLOR, ChoiceDialog, ScrollFrame, TreeTooltip, ask, center, dialog_body, tag_colors, with_scrollbar

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

def _msg_text(msg) -> str:
    """Nội dung ngắn của tin để hiện cho giáo vụ: các tên vắng, hoặc nguyên câu ("đủ", "32/34 đủ")."""
    if msg.names:
        return ", ".join(msg.names)
    text = " ".join(msg.raw.split())
    return text if len(text) <= 60 else text[:57] + "…"


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
        box = dialog_body(self, padding=0)
        ttk.Label(box, text="Bấm đúp: dòng có dấu cảnh báo / dấu X đỏ để chọn em đúng · dòng \"Lịch GV báo\" để áp dụng lịch · "
                       "dòng \"không rõ lớp\" để chọn lớp.",
                  style="Muted.TLabel").pack(anchor="w", padx=10, pady=(8, 2))
        bar = ttk.Frame(box, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Đóng", command=self.withdraw).pack(side="right")
        ttk.Button(bar, text="Xóa kết quả", command=tab.clear_results).pack(side="right", padx=6)
        frame, self.tree = with_scrollbar(box, ttk.Treeview, columns=("kq",), show="tree headings")
        frame.pack(fill="both", expand=True, padx=10)
        t = self.tree
        t.heading("#0", text="Lớp / tên GV ghi")
        t.heading("kq", text="Kết quả")
        t.column("#0", width=260, stretch=False)
        t.column("kq", width=640)
        tag_colors(t)
        t.bind("<Double-Button-1>", tab._on_result_double)
        TreeTooltip(t, ("kq",))

    def show(self) -> None:
        if not self.winfo_viewable():
            self.geometry("960x520")
            center(self, self.tab.winfo_toplevel())
            self.deiconify()
        self.lift()
        self.focus_set()


class TabDiemDanh(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.ws = app.ws
        self.current_class: str | None = None
        self.result_items: dict[str, tuple[str, matcher.MatchResult]] = {}
        self.sugg_items: dict[str, object] = {}  # iid -> đề nghị lịch (notes.Suggestion)
        self.check_vars: dict[str, tk.BooleanVar] = {}
        self.check_widgets: dict[str, ttk.Checkbutton] = {}
        self.unplaced_items: dict[str, object] = {}  # iid -> tin không rõ lớp (ParsedMessage)
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
        style.configure("So.Treeview", rowheight=28 if compact else 32, font=(family, size + 2))
        style.configure("So.Treeview.Heading", font=(family, size + 1, "bold"))
        style.configure("Link.TLabel", font=(family, size, "bold"))

        # Thanh dưới (đóng gói trước để luôn hiện đủ khi cửa sổ thấp)
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(bottom, text="In 2 tờ (Ctrl+P)", image=icon("print"), compound="left",
                   command=self.app.print_day).pack(side="right")
        ttk.Button(bottom, text="Lưu vào sổ (Ctrl+S)", style="Big.TButton", image=icon("save"), compound="left",
                   command=self.app.save).pack(side="right", padx=6)
        ttk.Button(bottom, text="Hoàn tác (Ctrl+Z)", image=icon("undo"), compound="left",
                   command=self.app.undo).pack(side="right", padx=6)
        ttk.Button(bottom, text="Copy lớp chưa báo", image=icon("copy"), compound="left",
                   command=self.copy_unreported).pack(side="right", padx=6)
        self.lbl_saved = ttk.Label(bottom, text="")
        self.lbl_saved.pack(side="left")
        self.lbl_saved.bind("<Button-1>", lambda e: self.ws.unresolved_count() and self.app.fix_unresolved())

        # Ô dán tin nhắn: dán vào là tự kiểm tra rồi tự xóa ô; gõ tay thì bấm Ctrl+Enter
        box = ttk.LabelFrame(self, text="Dán tin nhắn Zalo vào đây (Ctrl+V) — app tự kiểm tra ngay; "
                                        "gõ tay xong bấm Ctrl+Enter", padding=(8, 6))
        box.pack(fill="x")
        row = ttk.Frame(box)
        row.pack(fill="x")
        # ô dán chỉ cao 1 dòng khi không dùng; bấm vào thì mở ra 3 dòng
        self.paste = tk.Text(row, height=1, wrap="word", font=base, undo=True)
        self.paste.pack(side="left", fill="both", expand=True)
        self.paste.bind("<FocusIn>", lambda e: self.paste.configure(height=3))
        self.paste.bind("<FocusOut>", lambda e: self._shrink_paste())
        self.paste.bind("<<Paste>>", lambda e: self.after(80, self.analyze))
        self.paste.bind("<Control-Return>", lambda e: (self.analyze(), "break")[1])
        srow = ttk.Frame(box)
        srow.pack(fill="x", pady=(6, 0))
        ttk.Button(srow, text="Kết quả chi tiết…", image=icon("list"), compound="left",
                   command=self.show_results).pack(side="right")
        sbox = ttk.Frame(srow)
        sbox.pack(side="left", fill="x", expand=True)
        # dòng 1: việc cần xử lý (đỏ/cam) · dòng 2: thông tin (xám)
        self.lbl_summary = ttk.Label(sbox, text="", style="Link.TLabel", cursor="hand2", justify="left", compound="left")
        self.lbl_summary.pack(anchor="w")
        self.lbl_info = ttk.Label(sbox, text="", style="Muted.TLabel", cursor="hand2", justify="left")
        self.lbl_info.pack(anchor="w")
        for lbl in (self.lbl_summary, self.lbl_info):
            lbl.bind("<Button-1>", lambda e: self.show_results())
        srow.bind("<Configure>", lambda e: [lbl.configure(wraplength=max(300, e.width - 300))
                                            for lbl in (self.lbl_summary, self.lbl_info)])

        # Bảng điểm danh giống sổ, rộng hết màn hình
        left = ttk.LabelFrame(self, text="Bảng điểm danh — bấm đúp vào một lớp để tích vắng, xử lý tên", padding=6)
        left.pack(fill="both", expand=True, pady=(8, 0))
        trow = ttk.Frame(left)
        trow.pack(fill="x", pady=(0, 4))
        self.lbl_totals = ttk.Label(trow, text="", style="Title.TLabel")
        self.lbl_totals.pack(side="left")
        self.lbl_meal_total = ttk.Label(trow, text="", style="Title.TLabel", cursor="hand2", compound="left")
        self.lbl_meal_total.pack(side="left", padx=(16, 0))
        self.lbl_meal_total.bind("<Button-1>", lambda e: self.app.show_tab(self.app.tab_sa))
        legend = ttk.Frame(left)
        legend.pack(side="bottom", fill="x", pady=(4, 0))
        for text, key in (("chưa báo", "muted"), ("đủ", "ok"), ("có vắng", "warn"), ("cần xem", "err")):
            tk.Label(legend, text=f" {text} ", image=icon(STATUS_ICON[key]), compound="left", padx=4,
                     background=ROW_BG[key], foreground=ROW_FG[key]).pack(side="left", padx=(0, 6))
        ttk.Label(legend, text="[Lịch] sĩ số đổi theo lịch thêm/cắt",
                  style="Muted.TLabel").pack(side="left", padx=6)
        ttk.Button(legend, text="Mở lớp đã chọn", image=icon("open"), compound="left",
                   command=lambda: self.open_class(self.current_class)).pack(side="right")
        cols = ("gv", "siso", "vang", "hd", "ten", "note")
        frame, self.tree = with_scrollbar(left, ttk.Treeview, columns=cols, show="tree headings",
                                          selectmode="browse", style="So.Treeview")
        frame.pack(fill="both", expand=True)
        t = self.tree
        t.heading("#0", text="Lớp", anchor="w")
        t.column("#0", width=110, stretch=False, minwidth=90)
        heads = {"gv": ("GVCN", 220, "w"), "siso": ("Sĩ số", 64, "center"),
                 "vang": ("Vắng", 64, "center"), "hd": ("Hiện diện", 100, "center"),
                 "ten": ("Tên học sinh vắng", 360, "w"), "note": ("Ghi chú", 340, "w")}
        for c, (title, w, anchor) in heads.items():
            t.heading(c, text=title, anchor=anchor)
            t.column(c, width=w, anchor=anchor, stretch=c in ("ten", "note"), minwidth=50)
        for key in ROW_BG:
            t.tag_configure(key, background=ROW_BG[key], foreground=ROW_FG[key])
        t.tag_configure("sum", background="#e4ecf7", font=(family, size + 1, "bold"))
        t.tag_configure("total", background="#c9d9ef", font=(family, size + 2, "bold"))
        t.bind("<<TreeviewSelect>>", self._on_class_select)
        t.bind("<Double-Button-1>", lambda e: self._open_from_table(e))
        t.bind("<Return>", lambda e: self.open_class(self.current_class))
        t.bind("<Button-3>", self._on_table_right)
        TreeTooltip(t, ("ten", "note"))
        self._build_class_window(family, size)

    def _build_class_window(self, family: str, size: int) -> None:
        """Cửa sổ riêng của 1 lớp: tích vắng, xử lý tên chưa rõ, ghi chú. Mở bằng bấm đúp vào lớp."""
        win = self.cls_win = tk.Toplevel(self)
        win.withdraw()
        win.title("Lớp")
        win.transient(self.winfo_toplevel())
        win.protocol("WM_DELETE_WINDOW", self.close_class)
        win.bind("<Escape>", lambda e: self.close_class())
        ttk.Style().configure("Big.TCheckbutton", font=(family, size + 1))
        self.detail = dialog_body(win, "Lớp")
        bar = ttk.Frame(self.detail)
        bar.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(bar, text="Xong", style="Big.TButton", command=self.close_class).pack(side="right")
        self.lbl_cls_title = self.detail.head  # dải tiêu đề màu: "Lớp 1D15 (1.1) · GVCN …"
        self.lbl_class = ttk.Label(self.detail, text="", style="Title.TLabel")
        self.lbl_class.pack(anchor="w")
        brow = ttk.Frame(self.detail)
        brow.pack(fill="x", pady=(8, 4))
        ttk.Button(brow, text="Lớp này đủ", image=icon("st_ok"), compound="left", command=self.mark_full).pack(side="left")
        ttk.Button(brow, text="Thêm/cắt bán trú…", image=icon("calendar"), compound="left",
                   command=lambda: self._schedule_menu_for(None)).pack(side="left", padx=6)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_checks())
        ttk.Entry(brow, textvariable=self.search_var, width=16).pack(side="right")
        ttk.Label(brow, text="Tìm tên:").pack(side="right", padx=(0, 4))
        # dòng tên chưa rõ: chỉ hiện khi có
        self.pending_row = ttk.Frame(self.detail)
        self.lbl_hint = ttk.Label(self.detail, text="Tích ô = em vắng · chuột phải vào tên: cắt bán trú / cắt thứ 6",
                                  style="Muted.TLabel")
        self.lbl_hint.pack(anchor="w", pady=(4, 2))
        self.checks = ScrollFrame(self.detail, height=260)
        self.checks.pack(fill="both", expand=True)
        self.lbl_sched = ttk.Label(self.detail, text="", style="Ok.TLabel", wraplength=800, justify="left")
        self.lbl_sched.pack(anchor="w")
        self.lbl_extra = ttk.Label(self.detail, text="", style="Warn.TLabel", wraplength=800, justify="left")
        self.lbl_extra.pack(anchor="w")
        nrow = ttk.Frame(self.detail)
        nrow.pack(fill="x", pady=(6, 0))
        ttk.Label(nrow, text="Ghi chú (cột H):").pack(side="left")
        self.note_var = tk.StringVar()
        e = ttk.Entry(nrow, textvariable=self.note_var)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<FocusOut>", lambda ev: self._save_note())
        e.bind("<Return>", lambda ev: self._save_note())
        self.btn_clear_extra = ttk.Button(self.detail, text="Xóa các tên giữ tin nhắn gốc", command=self.clear_extra)
        self.lbl_warn = ttk.Label(self.detail, text="", style="Err.TLabel", wraplength=800, justify="left", compound="left")
        self.lbl_warn.pack(anchor="w")

    def _open_from_table(self, e) -> str | None:
        iid = self.tree.identify_row(e.y)
        if iid and iid in self.ws.state.classes:
            self.open_class(iid)
            return "break"
        return None

    def open_class(self, code: str | None) -> None:
        """Mở cửa sổ của lớp (dùng chung 1 cửa sổ, đổi nội dung khi chọn lớp khác)."""
        if not code or self.ws.state is None or code not in self.ws.state.classes:
            return
        self.select_class(code)
        win = self.cls_win
        if not win.winfo_viewable():
            top = self.winfo_toplevel()
            w = min(940, top.winfo_width() - 40)
            h = min(660, top.winfo_height() - 40)
            win.geometry(f"{w}x{h}")
            center(win, top)
            win.deiconify()
        self._build_checks()
        self._refresh_detail_labels()
        win.lift()
        win.focus_set()

    def close_class(self) -> None:
        self._save_note()
        self.cls_win.withdraw()
        self.tree.focus_set()

    def _shrink_paste(self) -> None:
        if not self.paste.get("1.0", "end").strip():
            self.paste.configure(height=1)

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

    def _class_status(self, code: str) -> str:
        """Mức màu của 1 lớp: muted (chưa báo) / ok (đủ) / warn (có vắng) / err (cần xem)."""
        st = self.ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        problem = bool(c.extra) or any(p[0] == code for p in st.pending) or bool(st.class_warnings(code))
        if problem:
            return "err"
        if not c.reported and not n:
            return "muted"
        if n:
            return "warn"
        return "ok"

    def _class_values(self, code: str) -> tuple[tuple, str]:
        st = self.ws.state
        c = st.cd(code)
        tag = self._class_status(code)
        info = self.ws.roster.classes.get(code)
        n = st.absent_count(code)
        names = ", ".join(st.absent_names(code))
        if not c.reported and not n:
            names = "(chưa báo)"
        note = c.note
        warns = st.class_warnings(code)
        if warns:
            note = warns[0] + (f" · {note}" if note else "")
        if st.scheduled_changes(code):
            note = "[Lịch] " + note
        vals = (info.gvcn if info else "", st.si_so(code), n, st.present(code), names, note)
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
                t.item(code, text=f" {code}", image=icon(STATUS_ICON[tag]), values=vals, tags=(tag,))
            si = sum(st.si_so(c) for c in codes)
            ab = sum(st.absent_count(c) for c in codes)
            t.item(f"khoi{k}", text=f"KHỐI {k}", values=("", si, ab, si - ab, "", ""), tags=("sum",))
        si, ab, pr = st.totals()
        n_rep = sum(1 for c in st.classes.values() if c.reported)
        t.item("tong", text="TỔNG CỘNG", values=(f"đã báo {n_rep}/{len(st.classes)} lớp", si, ab, pr, "", ""),
               tags=("total",))
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
        for s in students:
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
            cb = ttk.Checkbutton(self.checks.inner, text=label, variable=var, style="Big.TCheckbutton",
                                 command=lambda sid=s.id, v=var: self._toggle(sid, v.get()))
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
        w = self.cls_win.winfo_width() if self.cls_win.winfo_viewable() else 940
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
        """Xếp các ô tích thành cột, đọc dọc A→Z (hết cột 1 mới sang cột 2) như danh sách giấy."""
        q = fold(self.search_var.get())
        cols = self._check_cols()
        shown = []
        for cb in self.check_widgets.values():
            if q and q not in cb._search:  # type: ignore[attr-defined]
                cb.grid_remove()
            else:
                shown.append(cb)
        rows = max(1, -(-len(shown) // cols))
        for i, cb in enumerate(shown):
            cb.grid(row=i % rows, column=i // rows, sticky="w", padx=(4, 14), pady=1)

    def _refresh_detail_labels(self) -> None:
        st = self.ws.state
        code = self.current_class
        if not code:
            return
        info = self.ws.roster.classes.get(code)
        gv = f" · GVCN {info.gvcn}" if info and info.gvcn else ""
        ma = f" ({info.ma_ngan})" if info and info.ma_ngan else ""
        self.lbl_cls_title.configure(text=f"Lớp {code}{ma}{gv}")
        self.cls_win.title(f"Lớp {code}")
        c = st.cd(code)
        state = "chưa báo" if not c.reported else ("đủ" if not st.absent_count(code) else "đã báo")
        self.lbl_class.configure(
            text=f"Sĩ số {st.si_so(code)} · Vắng {st.absent_count(code)} · Hiện diện {st.present(code)} · {state}")
        # tên chưa rõ của lớp: mỗi tên 1 nút để chọn em đúng
        for w in self.pending_row.winfo_children():
            w.destroy()
        # khung trống vẫn giữ chiều cao cũ -> ẩn hẳn khi không có gì, hiện lại khi có
        self.pending_row.pack_forget()
        pend = [res for p_code, res in st.pending if p_code == code]
        if pend:
            ttk.Label(self.pending_row, text="Tên chưa rõ:", style="Err.TLabel").pack(side="left")
            for res in pend[:6]:
                ttk.Button(self.pending_row, text=f"{res.query}…", image=icon(RESULT_ICON[res.status]), compound="left",
                           command=lambda r=res: self._resolve_from_detail(code, r)).pack(side="left", padx=2, pady=2)
            self.pending_row.pack(fill="x", before=self.lbl_hint)
        sched = []
        for it in st.scheduled_changes(code):
            what = "cắt" if it.kind == "cat" else "thêm"
            sched.append(f"{what} {it.student.ho_ten} (từ {it.start:%d/%m})")
        upcoming = [s for s in self.ws.roster.in_class(code)
                    if (s.cat_tu and s.cat_tu > st.date) or (s.ban_tru and s.bt_tu and s.bt_tu > st.date)]
        txt = ""
        if sched:
            txt = f"Sĩ số đổi theo lịch ({c.sheet_si_so} → {st.si_so(code)}): " + "; ".join(sched)
        if upcoming:
            nxt = "; ".join(
                f"{'cắt' if s.cat_tu and s.cat_tu > st.date else 'thêm'} {s.ho_ten} từ "
                f"{(s.cat_tu if s.cat_tu and s.cat_tu > st.date else s.bt_tu):%d/%m}" for s in upcoming)
            txt += ("\n" if txt else "") + "Sắp tới: " + nxt
        self.lbl_sched.configure(text=txt)
        if c.extra:
            self.lbl_extra.configure(text="Giữ tin nhắn gốc (tên chưa khớp danh sách): " + ", ".join(c.extra))
            self.btn_clear_extra.pack(anchor="w", before=self.lbl_warn)
        else:
            self.lbl_extra.configure(text="")
            self.btn_clear_extra.pack_forget()
        self.note_var.set(c.note)
        warns = st.class_warnings(code)
        self.lbl_warn.configure(text="\n".join(warns), image=icon("st_err") if warns else "")

    def _refresh_meals(self) -> None:
        """Dòng "Tổng suất = hiện diện" trên màn Điểm danh; bảng đầy đủ ở tab Suất ăn."""
        tab = getattr(self.app, "tab_sa", None)
        if tab is not None:
            tab.refresh()
        if self.ws.layout.is_empty:
            self.lbl_meal_total.configure(text="")
            return
        summary = self.ws.meals()
        ok = summary.balanced
        self.lbl_meal_total.configure(
            text=f"Tổng suất {summary.total_meals} {'=' if ok else '≠'} hiện diện {summary.total_present}"
                 f"{'' if ok else ' (xem tab Suất ăn)'}",
            image=icon("st_ok" if ok else "st_err"), foreground=OK_COLOR if ok else ERR_COLOR)

    def _refresh_totals(self) -> None:
        st = self.ws.state
        si, ab, pr = st.totals()
        n_rep = sum(1 for c in st.classes.values() if c.reported)
        wd = WEEKDAYS[st.date.weekday()]
        self.lbl_totals.configure(
            text=f"{wd} {st.date:%d/%m/%Y}  ·  Đã báo {n_rep}/{len(st.classes)} lớp  ·  Sĩ số {si}  ·  "
                 f"Vắng {ab}  ·  Hiện diện {pr}")
        n_block = self.ws.unresolved_count()
        if n_block:  # chưa cho lưu: bấm vào để tới chỗ cần xử lý
            self.lbl_saved.configure(text=f" Còn {n_block} tên chưa rõ — xử lý xong mới lưu được", style="Err.TLabel",
                                     image=icon("st_err"), compound="left", cursor="hand2")
        else:
            saved = "Có thay đổi chưa lưu vào sổ" if self.ws.dirty else (
                "Đã có trong sổ" if st.exists_in_book else "Ngày này chưa có trong sổ")
            self.lbl_saved.configure(text=saved, style="Warn.TLabel" if self.ws.dirty else "Muted.TLabel",
                                     image=icon("pencil") if self.ws.dirty else "", compound="left", cursor="")
        self._show_summary()

    # ------------------------------------------------------------------ tóm tắt kết quả
    def _set_summary(self, parts: list[tuple[str, str]]) -> None:
        self._summary = parts
        self._show_summary()

    def _show_summary(self) -> None:
        """Dòng 1: việc cần xử lý (đỏ/cam, bấm để xem). Dòng 2: thông tin (xám)."""
        st = self.ws.state
        todo = [(t, k) for t, k in self._summary if k != "ok"]
        info = [t for t, k in self._summary if k == "ok"]
        n_pending = len(st.pending) if st else 0
        if n_pending:
            todo.append((f"{n_pending} tên chưa rõ", "err"))
        if st and self.ws.unplaced:
            todo.append((f"{len(self.ws.unplaced)} tin không rõ lớp", "err"))
        n_sug = len(self.sugg_items)
        if n_sug:
            todo.append((f"{n_sug} lịch GV báo chưa áp dụng", "warn"))
        if not todo:
            self.lbl_info.configure(text="")
            if info:
                self.lbl_summary.configure(text=" " + "  ·  ".join(info), foreground=OK_COLOR, image=icon("st_ok"))
            else:
                self.lbl_summary.configure(text="Chưa dán tin nào.", foreground=MUTED_COLOR, image="")
            return
        worst = "err" if any(k == "err" for _, k in todo) else "warn"
        self.lbl_summary.configure(
            text=" Cần xử lý: " + "  ·  ".join(t for t, _ in todo) + "  — bấm để xem",
            foreground=ERR_COLOR if worst == "err" else WARN_COLOR,
            image=icon("st_err" if worst == "err" else "res_ambiguous"))
        self.lbl_info.configure(text="  ·  ".join(info))

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
            self._schedule_menu_for(None, e, from_table=True)

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
                self.tree.item(code, image=icon(STATUS_ICON[tag]), values=vals, tags=(tag,))

    def _schedule_menu_for(self, student, event=None, from_table: bool = False) -> None:
        """Menu đặt lịch nhanh cho 1 em (chuột phải) hoặc cho cả lớp (nút Thêm/cắt BT…, chuột phải trên bảng)."""
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
        if from_table:
            menu.add_command(label=" Mở lớp này (tích vắng, xử lý tên)", image=icon("open"), compound="left",
                             command=lambda: self.open_class(code))
            menu.add_separator()
        menu.add_command(label=" Cắt bán trú từ ngày…", image=icon("cut"), compound="left",
                         command=lambda: tab.open_dialog(sch.CUT, code, ids))
        if student is None:
            menu.add_command(label=" Thêm em vào bán trú…", image=icon("add"), compound="left",
                             command=lambda: tab.open_dialog(sch.ADD, code))
        if student is not None and student.cat_thu6:
            menu.add_command(label=" Bỏ cắt thứ 6", image=icon("undo"), compound="left",
                             command=lambda: self._undo_friday(student))
        else:
            menu.add_command(label=" Cắt thứ 6 hàng tuần…", image=icon("friday"), compound="left",
                             command=lambda: tab.open_dialog(sch.FRIDAY, code, ids))
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
        pid = r.insert("", 0, text=" Lịch thêm/cắt", image=icon("res_schedule"), values=(f"{len(changes)} thay đổi bán trú có hiệu lực từ hôm nay — sĩ số đã tự cập nhật",),
                       tags=("ok", "bold"), open=True)
        for it in changes:
            what = "cắt bán trú" if it.kind == "cat" else "thêm bán trú"
            r.insert(pid, "end", text=it.student.lop_tinh, values=(f"{what}: {it.student.ho_ten} (từ {it.start:%d/%m})",))
        self._summary.append((f"{len(changes)} em thêm/cắt từ hôm nay (sĩ số đã tự đổi)", "ok"))
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
        self.paste.configure(height=1)
        self.tree.focus_set()
        before = set(self.unplaced_items)
        r = self.tree_res
        if skipped:
            days = ", ".join(f"{d:%d/%m} ({n})" for d, n in sorted(skipped.items()))
            r.insert("", 0, text="Bỏ qua", values=(f"{sum(skipped.values())} tin của ngày khác: {days} — "
                                                     "mở đúng ngày rồi dán lại nếu cần",), tags=("muted",))
        last = None
        classes, not_bt = set(), 0
        for po in outcomes:
            code = self._show_outcome(po)
            if code and po.message.is_report:
                classes.add(code)
                last = code
            not_bt += sum(1 for x in po.results if x.status == matcher.NOT_BT)
        st = self.ws.state
        parts = []
        if classes:
            parts.append((f"Vừa dán {len(classes)} lớp ({st.date:%d/%m})", "ok"))
        elif skipped:
            parts.append((f"Không có tin nào của ngày {st.date:%d/%m}", "warn"))
        if not_bt:
            parts.append((f"{not_bt} tên không ăn BT (không tính vắng)", "warn"))
        if skipped:
            parts.append((f"bỏ qua {sum(skipped.values())} tin ngày khác", "ok"))
        self._summary = parts
        self.refresh()
        if last:
            self.select_class(last)
        # tin không ghi lớp (vd. tin nhắn riêng "đủ", "Vắng Minh Khôi"): hỏi chọn lớp ngay
        for iid in [i for i in self.unplaced_items if i not in before]:
            if self._place_message(iid, now=True) == "later":
                break
        if self.sugg_items and any(po.suggestions for po in outcomes):
            self.show_results()  # đề nghị thêm/cắt cần giáo vụ xác nhận

    def _show_outcome(self, po) -> str | None:
        r = self.tree_res
        msg = po.message
        st = self.ws.state
        if msg.cls is None:
            who = f" ({msg.sender})" if msg.sender else ""
            if not msg.is_report:  # chỉ báo thêm/cắt, không rõ lớp: không tính gì, chỉ hiện để biết
                r.insert("", 0, text=f" Lịch GV báo{who}", image=icon("res_schedule"),
                         values=(f"\"{msg.schedule or _msg_text(msg)}\" — không ghi mã lớp, không tính là vắng",),
                         tags=("muted",))
                return None
            why = ("gợi ý lớp " + ", ".join(po.guessed_from)) if po.guessed_from else "chưa rõ lớp"
            iid = r.insert("", 0, text=f" không rõ lớp{who}", image=icon("res_unknown"),
                           values=(f"{_msg_text(msg)} — {why} — bấm đúp để chọn lớp",), tags=("err",))
            self.unplaced_items[iid] = (msg, po.guessed_from)
            return None
        code = msg.cls
        if msg.schedule:
            self._show_schedule(po)
        if not msg.is_report:
            return code
        count = f"báo {msg.present}/{msg.total} · " if msg.total is not None else ""
        when = f"{msg.when:%H:%M} " if msg.when else ""
        if msg.full:
            head = f"{when}{count}đủ"
        else:
            head = f"{when}{count}ghi {st.absent_count(code)} tên vắng: {', '.join(st.absent_names(code))}"
        warns = st.class_warnings(code)
        tag = "err" if warns else ("ok" if msg.full else "warn")
        pid = r.insert("", 0, text=code, values=(head,), tags=(tag, "bold"), open=True)
        for w in warns:
            r.insert(pid, "end", text="", image=icon("res_ambiguous"), values=(w,), tags=("err",))
        for res in po.results:
            self._insert_result(pid, code, res)
        return code

    def _show_schedule(self, po) -> None:
        r = self.tree_res
        msg = po.message
        src = f"{msg.cls}: \"{msg.schedule}\"" + (f" ({msg.sender} {msg.when:%d/%m %H:%M})" if msg.when else "")
        if po.schedule_known:
            r.insert("", 0, text=f" Lịch GV báo {msg.cls}", image=icon("res_schedule"),
                     values=(f"{src} — không tính là vắng; nếu chưa làm thì đặt ở tab Học sinh → Lịch thêm/cắt",),
                     tags=("muted",))
            return
        for sug in po.suggestions:
            if not sug.apply or not sug.changes:
                r.insert("", 0, text=f" Lịch GV báo {msg.cls}", image=icon("res_unknown"), values=(f"{src} — {sug.text}",),
                         tags=("err",))
                continue
            what = sug.text.split(" — ", 1)[-1]
            who = sug.student.ho_ten if sug.student else sug.new_name
            iid = r.insert("", 0, text=f" Lịch GV báo {msg.cls}", image=icon("res_schedule"),
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
        iid = r.insert(parent, "end", text=f" {res.query}", image=icon(RESULT_ICON[res.status]), values=(text,), tags=(tag,))
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
            r.insert("", 0, text="Sổ", image=icon("res_ok"), values=(head + " — tất cả đều đúng",), tags=("ok", "bold"))
            self._summary = [(f"Sổ ngày {st.date:%d/%m}: {n} tên vắng, tất cả đều đúng", "ok")]
        else:
            pid = r.insert("", 0, text="Sổ", values=(head + f" — {len(bad)} tên cần xem",), tags=("err", "bold"), open=True)
            for code, res in bad:
                sub = r.insert(pid, "end", text=code, values=("",), open=True)
                self._insert_result(sub, code, res)
            self._summary = [(f"sổ ngày {st.date:%d/%m} có {len(bad)}/{n} tên cần xem", "err")]
        self._show_summary()

    def clear_results(self) -> None:
        self.tree_res.delete(*self.tree_res.get_children())
        self.result_items.clear()
        self.sugg_items.clear()
        self.unplaced_items.clear()
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
        if iid in self.unplaced_items:
            self._place_message(iid)
            return
        if iid not in self.result_items:
            code = self.tree_res.item(iid, "text").strip().split(" ")[0]
            if code in self.ws.state.classes:
                self.select_class(code)
            return
        code, res = self.result_items[iid]
        self._resolve(code, res)

    def _apply_suggestion(self, iid: str) -> None:
        sug = self.sugg_items[iid]
        who = sug.student.ho_ten if sug.student else sug.new_name
        what = sug.text.split(" — ", 1)[-1]
        if ask(self.results, "Áp dụng lịch GV báo",
               f"Lớp {sug.code}: {who} — {what}.\n\nÁp dụng vào danh sách bán trú?",
               [("apply", "Áp dụng"), ("no", "Không")]) != "apply":
            return
        try:
            note = self.ws.apply_paste_suggestion(sug)
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        del self.sugg_items[iid]
        done = f"Đã áp dụng: {who} — {what}" + (f" · ghi chú cột H: \"{note}\"" if note else "")
        self.tree_res.item(iid, text=f" {sug.code}", image=icon("res_ok"), values=(done,), tags=("ok",))
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
                   "Nếu em này mới chuyển vào lớp, hãy sửa ở tab Học sinh. Hoặc chọn \"Giữ tin nhắn gốc\".")
        elif cands:
            msg = f"Lớp {code}: tên '{res.query}' — chọn em đúng:"
        else:
            msg = f"Lớp {code}: không tìm thấy '{res.query}' trong danh sách bán trú."
        buttons = ([("pick", "Chọn em này")] if cands else []) + [("raw", "Giữ tin nhắn gốc"), ("skip", "Bỏ qua tên này")]
        dlg = ChoiceDialog(self, "Chọn học sinh", msg, options, buttons, need_choice={"pick"})
        key, idx = dlg.result
        if key is None:
            return
        self.ws.push_undo()
        if key == "pick" and idx is not None:
            st.resolve_pending(code, res, cands[idx])
            row = (res.query, f"→ {roster.display_name(cands[idx])}  (đã chọn)", "ok", "res_ok")
        elif key == "raw":
            st.resolve_pending(code, res, None, keep_raw=True)
            row = (res.query, "Giữ tin nhắn gốc: ghi vào sổ đúng chữ GV gõ", "warn", "res_raw")
        else:
            st.resolve_pending(code, res, None)
            row = (res.query, "Đã bỏ qua", "muted", "res_skip")
        for iid, (_, r) in list(self.result_items.items()):
            if r is res:
                self.tree_res.item(iid, text=f" {row[0]}", image=icon(row[3]), values=(row[1],), tags=(row[2],))
                del self.result_items[iid]
        if code in st.classes:
            st.cd(code).reported = True
        self.refresh_light()
        self.select_class(code)

    def _resolve_from_detail(self, code: str, res: matcher.MatchResult) -> None:
        self._resolve(code, res)

    def focus_problem(self) -> None:
        """Sau hộp "Còn tên chưa rõ": đưa giáo vụ tới chỗ cần xử lý."""
        st = self.ws.state
        codes = [c for c in st.classes if c in self.ws.pending_names()]
        if codes:
            self.open_class(codes[0])
            self.app.flash(f"Lớp {codes[0]}: bấm vào tên chưa rõ để chọn em đúng.", error=True)
        if self.ws.unplaced:
            self.show_results()

    def _place_message(self, iid: str, now: bool = False) -> str | None:
        """Chọn lớp cho tin không rõ lớp. now=True: hỏi ngay khi vừa dán (có nút "Để sau")."""
        msg, guesses = self.unplaced_items[iid]
        codes = list(self.ws.state.classes)
        order = [c for c in guesses if c in codes] + [c for c in codes if c not in guesses]
        options = []
        for c in order:
            info = self.ws.roster.classes.get(c)
            hint = "  (gợi ý)" if c in guesses else ""
            options.append(f"{c}  —  GVCN {info.gvcn if info and info.gvcn else '?'}{hint}")
        who = f" của {msg.sender}" if msg.sender else ""
        buttons = [("pick", "Ghi vào lớp này"), ("skip", "Bỏ tin này")] + ([("later", "Để sau")] if now else [])
        parent = self.results if self.results.winfo_viewable() else self.winfo_toplevel()
        dlg = ChoiceDialog(parent, "Tin này của lớp nào?",
                           f"Tin{who}: \"{_msg_text(msg)}\" không ghi mã lớp. Tin này của lớp nào?",
                           options, buttons, need_choice={"pick"})
        key, idx = dlg.result
        if key in (None, "later"):
            return "later"
        if key == "skip":
            self.ws.dismiss_unplaced(msg)
            self.tree_res.item(iid, values=("Đã bỏ tin này",), tags=("muted",))
        else:
            code = order[idx]
            results = self.ws.assign_unplaced(msg, code)
            self.tree_res.item(iid, text=f"{code} (giáo vụ chọn lớp)", values=(f"Đã ghi vào lớp {code}",),
                               tags=("ok", "bold"), open=True)
            for res in results:
                self._insert_result(iid, code, res)
            self.select_class(code)
        del self.unplaced_items[iid]
        self.refresh_light()
        return key
