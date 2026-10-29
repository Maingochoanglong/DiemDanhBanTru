"""Tab Điểm danh: dán tin Zalo, kiểm tra tên, tích vắng theo lớp, xem bảng suất ăn."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from ..core import matcher
from ..core.text import fold
from .widgets import ChoiceDialog, ScrollFrame, tag_colors, with_scrollbar

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


class TabDiemDanh(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=6)
        self.app = app
        self.ws = app.ws
        self.current_class: str | None = None
        self.result_items: dict[str, tuple[str, matcher.MatchResult]] = {}
        self.check_vars: dict[str, tk.BooleanVar] = {}
        self.check_widgets: dict[str, ttk.Checkbutton] = {}
        self._build()

    # ------------------------------------------------------------------ dựng giao diện
    def _build(self) -> None:
        # Thanh dưới
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(6, 0))
        # nút đóng gói trước để luôn hiện đủ khi cửa sổ hẹp
        ttk.Button(bottom, text="In 2 tờ (Ctrl+P)", style="Big.TButton", command=lambda: self.app.print_day(False)).pack(side="right")
        ttk.Button(bottom, text="Xem trước", command=lambda: self.app.print_day(True)).pack(side="right", padx=6)
        ttk.Button(bottom, text="Lưu vào sổ (Ctrl+S)", style="Big.TButton", command=self.app.save).pack(side="right", padx=6)
        ttk.Button(bottom, text="Hoàn tác (Ctrl+Z)", command=self.app.undo).pack(side="right", padx=6)
        ttk.Button(bottom, text="Copy lớp chưa báo", command=self.copy_unreported).pack(side="right", padx=6)
        self.lbl_totals = ttk.Label(bottom, text="", style="Title.TLabel")
        self.lbl_totals.pack(side="left", fill="x", expand=True)

        self.paned = paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ① Cột trái: danh sách lớp
        left = ttk.LabelFrame(paned, text="Các lớp", padding=4)
        frame, self.tree_cls = with_scrollbar(left, ttk.Treeview, columns=("siso", "vang", "tt"),
                                             show="tree headings", selectmode="browse")
        frame.pack(fill="both", expand=True)
        t = self.tree_cls
        t.heading("#0", text="Lớp")
        t.heading("siso", text="Sĩ số")
        t.heading("vang", text="Vắng")
        t.heading("tt", text="Trạng thái")
        t.column("#0", width=78, stretch=False)
        t.column("siso", width=54, anchor="center", stretch=False)
        t.column("vang", width=50, anchor="center", stretch=False)
        t.column("tt", width=96)
        tag_colors(t)
        t.bind("<<TreeviewSelect>>", self._on_class_select)
        ttk.Label(left, text="○ chưa báo   ● đủ   ● có vắng", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        paned.add(left, weight=0)

        # Cột giữa: chia trên/dưới, kéo được đường chia
        mid = ttk.Frame(paned)
        paned.add(mid, weight=3)
        self.vpaned = ttk.PanedWindow(mid, orient="vertical")
        self.vpaned.pack(fill="both", expand=True)
        upper = ttk.Frame(self.vpaned)
        lower = ttk.Frame(self.vpaned)
        self.vpaned.add(upper, weight=1)
        self.vpaned.add(lower, weight=2)

        box = ttk.LabelFrame(upper, text="① Dán tin nhắn Zalo vào đây (Ctrl+V) — app tự kiểm tra tên", padding=6)
        box.pack(fill="x")
        compact = getattr(self.winfo_toplevel(), "compact", False)
        self.paste = tk.Text(box, height=2 if compact else 3, wrap="word", font=tkfont.nametofont("TkDefaultFont"), undo=True)
        self.paste.pack(fill="x")
        self.paste.bind("<<Paste>>", lambda e: self.after(80, self.analyze))
        self.paste.bind("<Control-Return>", lambda e: (self.analyze(), "break")[1])
        bar = ttk.Frame(box)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Kiểm tra (Ctrl+Enter)", command=self.analyze).pack(side="left")
        ttk.Button(bar, text="Xóa ô", command=lambda: self.paste.delete("1.0", "end")).pack(side="left", padx=6)
        ttk.Button(bar, text="Kiểm tra lại sổ", command=self.app.recheck_day).pack(side="right")
        ttk.Button(bar, text="Xóa kết quả", command=self.clear_results).pack(side="right", padx=6)

        res = ttk.LabelFrame(upper, text="Kết quả kiểm tra tên  (bấm đúp vào dòng ⚠ / ✖ để chọn em đúng)", padding=4)
        res.pack(fill="both", expand=True, pady=(6, 0))
        frame, self.tree_res = with_scrollbar(res, ttk.Treeview, columns=("kq",), show="tree headings", height=4)
        frame.pack(fill="both", expand=True)
        r = self.tree_res
        r.heading("#0", text="Lớp / tên GV ghi")
        r.heading("kq", text="Kết quả")
        r.column("#0", width=230, stretch=False)
        r.column("kq", width=420)
        tag_colors(r)
        r.bind("<Double-Button-1>", self._on_result_double)

        self.detail = ttk.LabelFrame(lower, text="② Lớp", padding=6)
        self.detail.pack(fill="both", expand=True, pady=(6, 0))
        self.lbl_class = ttk.Label(self.detail, text="Chọn một lớp ở cột bên trái", style="Title.TLabel")
        self.lbl_class.pack(anchor="w")
        srow = ttk.Frame(self.detail)
        srow.pack(fill="x", pady=(4, 2))
        ttk.Button(srow, text="Lớp này đủ", command=self.mark_full).pack(side="right")
        ttk.Button(srow, text="Bỏ dấu đã báo", command=self.unmark_reported).pack(side="right", padx=6)
        ttk.Button(srow, text="Thêm/cắt BT…", command=lambda: self._schedule_menu_for(None)).pack(side="right")
        ttk.Label(srow, text="Tìm tên:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_checks())
        ttk.Entry(srow, textvariable=self.search_var, width=18).pack(side="left", padx=4)
        ttk.Label(srow, text="Tích = vắng · chuột phải: cắt/thứ 6", style="Muted.TLabel").pack(side="left", padx=4)
        self.checks = ScrollFrame(self.detail, height=120)
        self.checks.pack(fill="both", expand=True)
        self.lbl_sched = ttk.Label(self.detail, text="", style="Ok.TLabel", wraplength=640, justify="left")
        self.lbl_sched.pack(anchor="w")
        self.lbl_extra = ttk.Label(self.detail, text="", style="Warn.TLabel", wraplength=640, justify="left")
        self.lbl_extra.pack(anchor="w")
        nrow = ttk.Frame(self.detail)
        nrow.pack(fill="x", pady=(4, 0))
        ttk.Label(nrow, text="Ghi chú lớp (cột H):").pack(side="left")
        self.note_var = tk.StringVar()
        e = ttk.Entry(nrow, textvariable=self.note_var)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<FocusOut>", lambda ev: self._save_note())
        e.bind("<Return>", lambda ev: self._save_note())
        self.btn_clear_extra = ttk.Button(nrow, text="Xóa tên ghi nguyên văn", command=self.clear_extra)
        self.lbl_warn = ttk.Label(self.detail, text="", style="Err.TLabel", wraplength=640, justify="left")
        self.lbl_warn.pack(anchor="w")

        # ③ Cột phải: bảng suất ăn
        right = ttk.LabelFrame(paned, text="③ Bảng suất ăn (tự tính)", padding=4)
        paned.add(right, weight=2)
        frame, self.tree_meal = with_scrollbar(right, ttk.Treeview, columns=("suat", "chi"), show="headings")
        frame.pack(fill="both", expand=True)
        m = self.tree_meal
        m.heading("suat", text="Suất")
        m.heading("chi", text="Nhóm · chi tiết")
        m.column("suat", width=56, anchor="center", stretch=False)
        m.column("chi", width=430)
        tag_colors(m)
        m.bind("<Double-Button-1>", self._on_meal_double)
        self.meal_rows: dict[str, str] = {}  # iid -> mã nhóm ghép
        self.lbl_meal_total = ttk.Label(right, text="", style="Title.TLabel")
        self.lbl_meal_total.pack(anchor="w", pady=(6, 0))
        self.lbl_meal_warn = ttk.Label(right, text="", style="Err.TLabel", wraplength=360, justify="left")
        self.lbl_meal_warn.pack(anchor="w", fill="x")
        right.bind("<Configure>", lambda e: self.lbl_meal_warn.configure(wraplength=max(200, e.width - 16)))
        self.detail.bind("<Configure>", lambda e: [w.configure(wraplength=max(300, e.width - 20))
                                                   for w in (self.lbl_warn, self.lbl_extra, self.lbl_sched)])
        self.after(300, self._init_sashes)

    def _init_sashes(self) -> None:
        w = self.paned.winfo_width()
        if w < 200:
            self.after(300, self._init_sashes)
            return
        try:
            self.paned.sashpos(0, 330 if w > 1500 else 305)
            self.paned.sashpos(1, int(w * 0.65))
            h = self.vpaned.winfo_height()
            if h > 200:
                self.vpaned.sashpos(0, int(h * 0.47))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ làm mới
    def refresh(self) -> None:
        st = self.ws.state
        if st is None:
            return
        self._refresh_classes()
        if self.current_class not in st.classes:
            self.current_class = next(iter(st.classes), None)
        self._build_checks()
        self._refresh_detail_labels()
        self._refresh_meals()
        self._refresh_totals()

    def refresh_light(self) -> None:
        """Làm mới số liệu, không dựng lại danh sách ô tích (giữ vị trí cuộn)."""
        self._refresh_classes()
        self._sync_checks()
        self._refresh_detail_labels()
        self._refresh_meals()
        self._refresh_totals()

    def _class_status(self, code: str) -> tuple[str, str]:
        st = self.ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        has_problem = bool(c.extra) or any(p[0] == code for p in st.pending) or bool(st.class_warnings(code))
        if not c.reported and not n:
            return "○ chưa báo", "muted"
        if has_problem:
            return f"● {n} vắng ⚠" if n else "● cần xem ⚠", "err"
        if n:
            return f"● vắng {n}", "warn"
        return "● đủ", "ok"

    def _refresh_classes(self) -> None:
        t = self.tree_cls
        st = self.ws.state
        sel = self.current_class
        existing = set(t.get_children())
        by_khoi: dict[int, list[str]] = {}
        for code in st.classes:
            by_khoi.setdefault(int(code[0]), []).append(code)
        for k, codes in sorted(by_khoi.items()):
            kid = f"khoi{k}"
            si = sum(st.si_so(c) for c in codes)
            ab = sum(st.absent_count(c) for c in codes)
            if kid not in existing:
                t.insert("", "end", iid=kid, text=f"KHỐI {k}", open=True, tags=("khoi",))
            t.item(kid, values=(si, ab, ""))
            for code in codes:
                tt, tag = self._class_status(code)
                vals = (st.si_so(code), st.absent_count(code), tt)
                if t.exists(code):
                    t.item(code, values=vals, tags=(tag,))
                else:
                    t.insert(kid, "end", iid=code, text=code, values=vals, tags=(tag,))
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
        cols = 3
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
            cb.grid(row=i // cols, column=i % cols, sticky="w", padx=(4, 18), pady=1)
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
        cols = 3
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
        self.detail.configure(text=f"② Lớp {code}{ma}{gv}")
        self.lbl_class.configure(
            text=f"{code} · Sĩ số {st.si_so(code)} · Vắng {st.absent_count(code)} · Hiện diện {st.present(code)}")
        c = st.cd(code)
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
            self.btn_clear_extra.pack(side="right")
        else:
            self.lbl_extra.configure(text="")
            self.btn_clear_extra.pack_forget()
        self.note_var.set(c.note)
        warns = st.class_warnings(code)
        self.lbl_warn.configure(text="\n".join("⚠ " + w for w in warns))

    def _refresh_meals(self) -> None:
        m = self.tree_meal
        m.delete(*m.get_children())
        layout = self.ws.layout
        if layout.is_empty:
            self.lbl_meal_total.configure(text="")
            self.lbl_meal_warn.configure(text="Sổ chưa có bảng suất ăn bên dưới (như sheet ngày 21–28/10).")
            return
        summary = self.ws.meals()
        manual = self.ws.state.manual_codes(layout)
        self.meal_rows.clear()
        for line in summary.lines:
            r = line.row
            if r.code:
                detail = f"{r.label}: {' + '.join(r.classes)} + ghép {line.o} em"
                if line.m:
                    names = f" ({', '.join(line.absent_names)})" if line.absent_names else ""
                    detail += f" − vắng {line.m}{names}"
                if r.code in manual:
                    detail += "  ✎"
            else:
                detail = f"{r.label}: {' + '.join(r.classes)}"
            iid = m.insert("", "end", values=(line.meals, detail), tags=("warn",) if line.m else ())
            if r.code:
                self.meal_rows[iid] = r.code
        if layout.self_classes:
            m.insert("", "end", values=(summary.self_meals, "Tự ăn tại lớp: " + ", ".join(layout.self_classes)),
                     tags=("muted",))
        ok = summary.balanced
        self.lbl_meal_total.configure(
            text=f"Tổng suất {summary.total_meals} {'=' if ok else '≠'} hiện diện {summary.total_present} {'✔' if ok else '✖'}",
            style="Ok.TLabel" if ok else "Err.TLabel")
        self.lbl_meal_warn.configure(text="\n".join("⚠ " + w for w in summary.warnings))

    def _on_meal_double(self, _e=None) -> None:
        from tkinter import simpledialog

        sel = self.tree_meal.selection()
        if not sel or sel[0] not in self.meal_rows:
            return
        code = self.meal_rows[sel[0]]
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
        saved = "chưa lưu" if self.ws.dirty else ("đã có trong sổ" if st.exists_in_book else "chưa có trong sổ")
        self.lbl_totals.configure(
            text=f"{wd} {st.date:%d/%m/%Y} · Đã báo {n_rep}/{len(st.classes)} lớp · Sĩ số {si} · Vắng {ab} · Hiện diện {pr} · ({saved})",
            style="Warn.TLabel" if self.ws.dirty else "TLabel")

    # ------------------------------------------------------------------ thao tác
    def _on_class_select(self, _e=None) -> None:
        sel = self.tree_cls.selection()
        if not sel or sel[0].startswith("khoi"):
            return
        if sel[0] != self.current_class:
            self._save_note()
            self.current_class = sel[0]
            self.search_var.set("")
            self._build_checks()
            self._refresh_detail_labels()

    def select_class(self, code: str) -> None:
        if self.tree_cls.exists(code):
            self.tree_cls.selection_set(code)
            self.tree_cls.see(code)
            self._on_class_select()

    def _toggle(self, sid: str, absent: bool) -> None:
        self.ws.push_undo()
        self.ws.state.set_absent(self.current_class, sid, absent)
        self.refresh_light()

    def mark_full(self) -> None:
        if not self.current_class:
            return
        self.ws.push_undo()
        self.ws.state.mark_full(self.current_class)  # em cắt thứ 6 / vắng dài hạn vẫn tính vắng
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
        menu.add_command(label="Vắng dài hạn…", command=lambda: tab.open_dialog(sch.LONG, code, ids))
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
        if not outcomes:
            self.app.flash("Không đọc được tin nhắn nào (không thấy mã lớp hoặc tên).", error=True)
            return
        self.paste.delete("1.0", "end")
        last = None
        for po in outcomes:
            last = self._show_outcome(po) or last
        self.refresh()
        if last:
            self.select_class(last)

    def _show_outcome(self, po) -> str | None:
        r = self.tree_res
        msg = po.message
        st = self.ws.state
        if msg.cls is None:
            if po.guessed_from:
                why = "nhiều lớp cùng có các tên này: " + ", ".join(po.guessed_from)
            else:
                why = "không đoán được lớp — hãy dán kèm mã lớp (vd. 2D17) hoặc tích tay"
            r.insert("", 0, text="? (không rõ lớp)", values=(f"{', '.join(msg.names)} — {why}",), tags=("err",))
            return None
        code = msg.cls
        count = f"báo {msg.present}/{msg.total} · " if msg.total is not None else ""
        guess = " (app đoán lớp)" if msg.guessed else ""
        if msg.full:
            head = f"{count}đủ"
        else:
            head = f"{count}ghi {st.absent_count(code)} tên vắng: {', '.join(st.absent_names(code))}"
        warns = st.class_warnings(code)
        tag = "err" if warns else ("ok" if msg.full else "warn")
        pid = r.insert("", 0, text=f"{code}{guess}", values=(head,), tags=(tag, "bold"), open=True)
        for w in warns:
            r.insert(pid, "end", text="  ⚠", values=(w,), tags=("err",))
        for res in po.results:
            self._insert_result(pid, code, res)
        return code

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
        if res.status in (matcher.AMBIGUOUS, matcher.OTHER_CLASS, matcher.NOT_FOUND):
            self.result_items[iid] = (code, res)

    def show_sheet_checks(self) -> None:
        """Hiện kết quả kiểm tra các ô tên vắng đã có trong sổ (gõ tay hoặc app ghi trước đó)."""
        checks = self.ws.sheet_checks
        if not checks:
            return
        r = self.tree_res
        bad = [(code, res) for code, lst in checks.items() for res in lst if res.status != matcher.OK]
        st = self.ws.state
        head = f"Kiểm tra sổ ngày {st.date:%d/%m}: {sum(len(v) for v in checks.values())} tên"
        if not bad:
            r.insert("", 0, text="Sổ", values=(head + " — tất cả đều đúng ✔",), tags=("ok", "bold"))
            return
        pid = r.insert("", 0, text="Sổ", values=(head + f" — {len(bad)} tên cần xem",), tags=("err", "bold"), open=True)
        for code, res in bad:
            sub = r.insert(pid, "end", text=code, values=("",), open=True)
            self._insert_result(sub, code, res)

    def clear_results(self) -> None:
        self.tree_res.delete(*self.tree_res.get_children())
        self.result_items.clear()

    def _on_result_double(self, _e=None) -> None:
        sel = self.tree_res.selection()
        if not sel:
            return
        iid = sel[0]
        if iid not in self.result_items:
            parent_text = self.tree_res.item(iid, "text")
            code = parent_text.split(" ")[0]
            if code in self.ws.state.classes:
                self.select_class(code)
            return
        code, res = self.result_items[iid]
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
            self.tree_res.item(iid, text=f"✔ {res.query}", values=(f"→ {roster.display_name(cands[idx])}  (đã chọn)",), tags=("ok",))
        elif key == "raw":
            st.resolve_pending(code, res, None, keep_raw=True)
            self.tree_res.item(iid, text=f"✎ {res.query}", values=("Ghi nguyên văn vào sổ",), tags=("warn",))
        else:
            st.resolve_pending(code, res, None)
            self.tree_res.item(iid, text=f"– {res.query}", values=("Đã bỏ qua",), tags=("muted",))
        if code in st.classes:
            st.cd(code).reported = True
        del self.result_items[iid]
        self.refresh_light()
        self.select_class(code)
