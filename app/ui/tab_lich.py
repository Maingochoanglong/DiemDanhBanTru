"""Tab Lịch thêm/cắt: lên lịch cắt hoặc thêm bán trú từ một ngày, cắt thứ 6 hàng tuần."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

from ..core import schedule as sch
from ..core.text import class_sort_key, clean_spaces, fmt_date, fold, parse_date
from ..service import next_school_day
from .widgets import center, tag_colors, with_scrollbar

KIND_ORDER = [sch.CUT, sch.ADD, sch.FRIDAY]


class TabLich(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.ws = app.ws
        self.items: dict[str, sch.ScheduleItem] = {}
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Lịch thêm / cắt bán trú", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Cắt thứ 6 hàng tuần…", command=lambda: self.open_dialog(sch.FRIDAY)).pack(side="right", padx=6)
        ttk.Button(top, text="＋ Thêm bán trú…", style="Big.TButton", command=lambda: self.open_dialog(sch.ADD)).pack(side="right")
        ttk.Button(top, text="✂ Cắt bán trú…", style="Big.TButton", command=lambda: self.open_dialog(sch.CUT)).pack(side="right", padx=6)
        ttk.Label(self, style="Muted.TLabel", wraplength=1000, justify="left", text=(
            "Đặt trước ngày cắt hoặc thêm (ví dụ từ ngày mai, hay từ đầu tháng sau). Tới ngày đó app tự đổi sĩ số "
            "và danh sách tích vắng, không cần nhớ. Em \"cắt thứ 6\" (thứ 6 học nửa buổi) được tự tính vắng mỗi thứ 6.")).pack(anchor="w", pady=(4, 8))

        frame, self.tree = with_scrollbar(self, ttk.Treeview, columns=("ngay", "lop", "hs", "viec"),
                                          show="tree headings", selectmode="extended")
        frame.pack(fill="both", expand=True)
        t = self.tree
        t.heading("#0", text="Nhóm")
        t.heading("ngay", text="Ngày áp dụng")
        t.heading("lop", text="Lớp")
        t.heading("hs", text="Học sinh")
        t.heading("viec", text="Việc")
        t.column("#0", width=200)
        t.column("ngay", width=110, anchor="center")
        t.column("lop", width=70, anchor="center")
        t.column("hs", width=240)
        t.column("viec", width=360)
        tag_colors(t)
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Hủy lịch đã chọn", command=self.cancel_selected).pack(side="left")
        ttk.Label(bar, text="Chọn được nhiều dòng (giữ Ctrl).", style="Muted.TLabel").pack(side="left", padx=8)

    def refresh(self) -> None:
        t = self.tree
        t.delete(*t.get_children())
        self.items.clear()
        today = self.ws.day
        groups = {
            "soon": ("Sắp áp dụng", "warn"),
            "weekly": ("Hàng tuần – cắt thứ 6", ""),
            "done": ("Đã áp dụng (30 ngày qua)", "muted"),
        }
        buckets: dict[str, list[sch.ScheduleItem]] = {k: [] for k in groups}
        for it in self.ws.schedule_items():
            if it.kind == sch.FRIDAY:
                buckets["weekly"].append(it)
            elif it.start and it.start > today:
                buckets["soon"].append(it)
            else:
                buckets["done"].append(it)
        for key, (title, tag) in groups.items():
            lst = sorted(buckets[key], key=lambda i: (i.start or dt.date.min, class_sort_key(i.student.lop_tinh)))
            pid = t.insert("", "end", text=f"{title} ({len(lst)})", open=key != "done", tags=("bold",))
            for it in lst:
                iid = t.insert(pid, "end", values=(fmt_date(it.start) if it.start else "mỗi thứ 6" if it.kind == sch.FRIDAY else "",
                                                   it.student.lop_tinh, it.student.ho_ten, it.text), tags=(tag,) if tag else ())
                self.items[iid] = it

    def open_dialog(self, kind: str, code: str | None = None, ids: tuple[str, ...] = ()) -> None:
        code = code or self.app.tab_dd.current_class or (self.ws.roster.class_codes() or [""])[0]
        dlg = ScheduleDialog(self, self.ws, kind, code, ids)
        if not dlg.result:
            return
        r = dlg.result
        try:
            note = self.ws.schedule(r["kind"], r["code"], r["ids"], r["start"], r["end"], r["new_name"], r["new_dob"], r["note"])
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
            return
        msg = f"Đã đặt lịch: {sch.LABEL[r['kind']].lower()}"
        if r["start"]:
            msg += f" từ {fmt_date(r['start'])}"
        if note:
            msg += f". Đã thêm ghi chú cột H lớp {r['code']}: \"{note}\" — nhớ bấm Lưu vào sổ."
        self.app.flash(msg)
        self.app.refresh_days_only()
        self.refresh()

    def cancel_selected(self) -> None:
        sel = [i for i in self.tree.selection() if i in self.items]
        if not sel:
            messagebox.showinfo("Hủy lịch", "Hãy chọn dòng lịch cần hủy.", parent=self)
            return
        its = [self.items[i] for i in sel]
        lines = "\n".join(f"• {it.student.ho_ten} ({it.student.lop_tinh}): {it.text}" for it in its[:12])
        if not messagebox.askyesno("Hủy lịch", f"Hủy {len(its)} lịch sau?\n\n{lines}", parent=self):
            return
        try:
            for it in its:
                self.ws.cancel_schedule(it)
        except Exception as e:  # noqa: BLE001
            self.app.show_save_error(e, self.ws.data.path)
        self.app.flash(f"Đã hủy {len(its)} lịch. Nếu đã ghi chú ở cột H, hãy xóa ghi chú đó trong ô Ghi chú lớp.")
        self.app.refresh_days_only()
        self.refresh()


class ScheduleDialog(tk.Toplevel):
    """Hộp thoại đặt lịch: chọn việc, lớp, học sinh, ngày áp dụng."""

    NEW = "➕ Học sinh mới (chưa có trong danh sách)…"

    def __init__(self, parent, ws, kind: str, code: str, ids: tuple[str, ...] = ()):
        super().__init__(parent)
        self.title("Lên lịch thêm / cắt bán trú")
        self.transient(parent.winfo_toplevel())
        self.ws = ws
        self.result: dict | None = None
        self.shown: list = []
        self.preset = set(ids)
        base = ws.day
        self.day_next = next_school_day(base)
        self.day_month = sch.next_month_start(base)
        f = tkfont.nametofont("TkDefaultFont")

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Label(row, text="Việc:").pack(side="left")
        self.kind = tk.StringVar(value=kind)
        for k in KIND_ORDER:
            ttk.Radiobutton(row, text=sch.LABEL[k], value=k, variable=self.kind, command=self._kind_changed).pack(side="left", padx=6)

        row = ttk.Frame(body)
        row.pack(fill="x", pady=(10, 4))
        ttk.Label(row, text="Lớp:").pack(side="left")
        self.code = tk.StringVar(value=code)
        cb = ttk.Combobox(row, textvariable=self.code, values=ws.roster.class_codes(), width=8, state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._fill())
        ttk.Label(row, text="Tìm tên:").pack(side="left", padx=(12, 0))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: self._fill())
        ttk.Entry(row, textvariable=self.q, width=20).pack(side="left", padx=4)
        self.lbl_hint = ttk.Label(body, text="", style="Muted.TLabel")
        self.lbl_hint.pack(anchor="w")

        frame = ttk.Frame(body)
        frame.pack(fill="both", expand=True)
        self.lb = tk.Listbox(frame, height=12, width=60, selectmode="extended", font=f, exportselection=False)
        self.lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.bind("<<ListboxSelect>>", lambda e: self._sel_changed())

        self.new_box = ttk.Frame(body)
        ttk.Label(self.new_box, text="Họ tên em mới:").pack(side="left")
        self.new_name = tk.StringVar()
        ttk.Entry(self.new_box, textvariable=self.new_name, width=28).pack(side="left", padx=4)
        ttk.Label(self.new_box, text="Ngày sinh:").pack(side="left", padx=(8, 0))
        self.new_dob = tk.StringVar()
        ttk.Entry(self.new_box, textvariable=self.new_dob, width=12).pack(side="left", padx=4)

        self.date_box = ttk.Frame(body)
        self.date_box.pack(fill="x", pady=(10, 0))
        ttk.Label(self.date_box, text="Áp dụng từ ngày:").grid(row=0, column=0, sticky="w")
        self.start = tk.StringVar(value=fmt_date(self.day_next))
        ttk.Entry(self.date_box, textvariable=self.start, width=12).grid(row=0, column=1, padx=4)
        ttk.Button(self.date_box, text=f"Ngày học kế tiếp ({self.day_next:%d/%m})",
                   command=lambda: self.start.set(fmt_date(self.day_next))).grid(row=0, column=2, padx=2)
        ttk.Button(self.date_box, text=f"Đầu tháng sau ({self.day_month:%d/%m})",
                   command=lambda: self.start.set(fmt_date(self.day_month))).grid(row=0, column=3, padx=2)
        ttk.Button(self.date_box, text=f"Hôm nay ({base:%d/%m})",
                   command=lambda: self.start.set(fmt_date(base))).grid(row=0, column=4, padx=2)

        self.note = tk.BooleanVar(value=True)
        self.chk_note = ttk.Checkbutton(body, variable=self.note, text="Ghi chú vào cột H của lớp (như \"T11 CẮT …\")")
        self.chk_note.pack(anchor="w", pady=(10, 0))
        self.lbl_err = ttk.Label(body, text="", style="Err.TLabel")
        self.lbl_err.pack(anchor="w")
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Lưu lịch", style="Big.TButton", command=self._ok).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Hủy", command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())
        self._kind_changed()
        self.grab_set()
        center(self, parent)
        self.wait_window()

    # ------------------------------------------------------------------
    def _candidates(self):
        k, code, day = self.kind.get(), self.code.get(), self.ws.day
        roster = self.ws.roster
        if k == sch.ADD:
            pool = [s for s in roster.in_class(code) if not s.is_boarding(day) and not (s.bt_tu and s.bt_tu > day)]
        else:
            pool = roster.boarding(code, day)
            if k == sch.FRIDAY:
                pool = [s for s in pool if not s.cat_thu6]
            if k == sch.CUT:
                pool = [s for s in pool if not s.cat_tu]
        return roster.sort_like_roster(pool)

    def _fill(self) -> None:
        q = fold(self.q.get())
        self.lb.delete(0, "end")
        self.shown = []
        for s in self._candidates():
            if q and q not in fold(s.ho_ten):
                continue
            extra = "" if s.ban_tru or self.kind.get() != sch.ADD else "  (chưa ăn BT)"
            self.lb.insert("end", f"{s.ho_ten}  —  sinh {s.ngay_sinh}{extra}")
            self.shown.append(s)
            if s.id in self.preset:
                self.lb.selection_set("end")
        if self.kind.get() == sch.ADD:
            self.lb.insert("end", self.NEW)
            self.shown.append(None)
        self._sel_changed()

    def _kind_changed(self) -> None:
        k = self.kind.get()
        hints = {
            sch.CUT: "Chọn em thôi ăn bán trú (chọn được nhiều em, giữ Ctrl).",
            sch.ADD: "Chọn em trong lớp chưa ăn bán trú, hoặc dòng cuối để thêm em mới.",
            sch.FRIDAY: "Chọn em nghỉ ăn thứ 6 hàng tuần (thứ 6 học nửa buổi).",
        }
        self.lbl_hint.configure(text=hints[k])
        if k == sch.FRIDAY:
            self.date_box.pack_forget()
        else:
            self.date_box.pack(fill="x", pady=(10, 0), before=self.chk_note)
        self._fill()

    def _sel_changed(self) -> None:
        idx = self.lb.curselection()
        wants_new = any(self.shown[i] is None for i in idx)
        if wants_new:
            self.new_box.pack(fill="x", pady=(6, 0), after=self.lb.master)
        else:
            self.new_box.pack_forget()

    def _ok(self) -> None:
        k = self.kind.get()
        idx = self.lb.curselection()
        chosen = [self.shown[i] for i in idx]
        ids = [s.id for s in chosen if s is not None]
        new_name = clean_spaces(self.new_name.get()) if None in chosen else ""
        if None in chosen and not new_name:
            self.lbl_err.configure(text="Nhập họ tên em mới.")
            return
        if not ids and not new_name:
            self.lbl_err.configure(text="Chọn ít nhất một học sinh.")
            return
        start = end = None
        if k != sch.FRIDAY:
            start = parse_date(self.start.get())
            if not start:
                self.lbl_err.configure(text="Ngày áp dụng phải có dạng dd/mm/yyyy.")
                return
        dob = parse_date(self.new_dob.get())
        self.result = {"kind": k, "code": self.code.get(), "ids": ids, "start": start, "end": end,
                       "new_name": new_name, "new_dob": fmt_date(dob) if dob else "", "note": self.note.get()}
        self.destroy()
