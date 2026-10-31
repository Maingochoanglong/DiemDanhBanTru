"""Thành phần giao diện dùng chung."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

OK_COLOR = "#1b7f3b"
WARN_COLOR = "#a65e00"
ERR_COLOR = "#b00020"
MUTED_COLOR = "#7a7a7a"
ACCENT = "#0b5cad"


def setup_style(root: tk.Tk) -> str:
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    else:
        style.theme_use("clam")
    family = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
    compact = root.winfo_screenheight() < 850  # laptop 1366x768: chữ nhỏ hơn 1 cỡ
    size = 10 if compact else 11
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        try:
            tkfont.nametofont(name).configure(family=family, size=size)
        except tk.TclError:
            pass
    style.configure("Treeview", rowheight=22 if compact else 26, font=(family, size))
    style.configure("Treeview.Heading", font=(family, size - 1, "bold"))
    style.configure("TLabelframe.Label", font=(family, size, "bold"), foreground=ACCENT)
    style.configure("Title.TLabel", font=(family, size + 2, "bold"))
    style.configure("Big.TButton", font=(family, size, "bold"), padding=(10, 3) if compact else (12, 5))
    style.configure("Muted.TLabel", foreground=MUTED_COLOR)
    style.configure("Ok.TLabel", foreground=OK_COLOR)
    style.configure("Warn.TLabel", foreground=WARN_COLOR)
    style.configure("Err.TLabel", foreground=ERR_COLOR)
    style.configure("TNotebook.Tab", padding=(12, 4) if compact else (14, 6), font=(family, size, "bold"))
    root.compact = compact  # type: ignore[attr-defined]
    return family


def tag_colors(tree: ttk.Treeview) -> None:
    tree.tag_configure("ok", foreground=OK_COLOR)
    tree.tag_configure("warn", foreground=WARN_COLOR)
    tree.tag_configure("err", foreground=ERR_COLOR)
    tree.tag_configure("muted", foreground=MUTED_COLOR)
    f = tkfont.nametofont("TkDefaultFont")
    tree.tag_configure("bold", font=(f.actual("family"), f.actual("size"), "bold"))
    tree.tag_configure("khoi", background="#eef3fa", font=(f.actual("family"), f.actual("size") - 1, "bold"))


def with_scrollbar(parent, widget_factory, **kw):
    """Tạo widget (Treeview/Text) kèm thanh cuộn dọc. Trả về (khung, widget)."""
    frame = ttk.Frame(parent)
    w = widget_factory(frame, **kw)
    sb = ttk.Scrollbar(frame, orient="vertical", command=w.yview)
    w.configure(yscrollcommand=sb.set)
    w.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, w


class ScrollFrame(ttk.Frame):
    """Khung cuộn dọc chứa nhiều widget con (vd. danh sách ô tích)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        bg = ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=bg)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _bind_wheel(self, on: bool) -> None:
        if on:
            self.canvas.bind_all("<MouseWheel>", self._wheel)
            self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
            self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))
        else:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

    def _wheel(self, e) -> None:
        self.canvas.yview_scroll(int(-e.delta / 120) * 2, "units")

    def clear(self) -> None:
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


class ChoiceDialog(tk.Toplevel):
    """Hộp thoại chọn 1 mục trong danh sách. result = (nút đã bấm, chỉ số mục chọn)."""

    def __init__(self, parent, title: str, message: str, options: list[str], buttons: list[tuple[str, str]],
                 need_choice: set[str] | None = None, image: str | None = None, style: str = "TLabel"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.result: tuple[str | None, int | None] = (None, None)
        self.need_choice = need_choice or set()
        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        msg = ttk.Label(body, text=message, wraplength=560, justify="left", style=style)
        if image:
            from .icons import bigger, icon

            msg.configure(image=icon(image, bigger()), compound="left")
        msg.pack(anchor="w", pady=(0, 8))
        self.lb = None
        if options:
            frame = ttk.Frame(body)
            frame.pack(fill="both", expand=True)
            self.lb = tk.Listbox(frame, height=min(10, max(3, len(options))), width=70, activestyle="dotbox",
                                 font=tkfont.nametofont("TkDefaultFont"))
            for o in options:
                self.lb.insert("end", o)
            self.lb.pack(side="left", fill="both", expand=True)
            sb = ttk.Scrollbar(frame, command=self.lb.yview)
            sb.pack(side="right", fill="y")
            self.lb.configure(yscrollcommand=sb.set)
            self.lb.selection_set(0)
            self.lb.bind("<Double-Button-1>", lambda e: self._press(buttons[0][0]))
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(10, 0))
        for i, (key, text) in enumerate(buttons):
            b = ttk.Button(bar, text=text, command=lambda k=key: self._press(k), style="Big.TButton" if i == 0 else "TButton")
            b.pack(side="left", padx=(0, 8))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._press(buttons[0][0]))
        self.grab_set()
        self.focus_set()
        center(self, parent)
        self.wait_window()

    def _press(self, key: str) -> None:
        idx = None
        if self.lb is not None and self.lb.curselection():
            idx = self.lb.curselection()[0]
        if key in self.need_choice and idx is None:
            return
        self.result = (key, idx)
        self.destroy()


def ask(parent, title: str, message: str, buttons: list[tuple[str, str]], image: str = "ask") -> str | None:
    """Hộp hỏi có nút ghi rõ việc sẽ làm bằng tiếng Việt (thay cho Yes/No).

    Nút đầu tiên là nút mặc định (Enter). Trả về khóa của nút đã bấm, None nếu đóng hộp (Esc / dấu X).
    """
    return ChoiceDialog(parent, title, message, [], buttons, image=image).result[0]


class TreeTooltip:
    """Rê chuột vào ô bị cắt chữ trong bảng: hiện ô nổi nền vàng nhạt chứa đủ nội dung."""

    def __init__(self, tree: ttk.Treeview, columns: tuple[str, ...], delay: int = 350):
        self.tree, self.columns, self.delay = tree, set(columns), delay
        self.tip: tk.Toplevel | None = None
        self.key: tuple[str, str] | None = None
        self.job: str | None = None
        tree.bind("<Motion>", self._motion, add="+")
        for ev in ("<Leave>", "<ButtonPress>", "<MouseWheel>", "<Button-4>", "<Button-5>", "<KeyPress>"):
            tree.bind(ev, lambda e: self.hide(), add="+")

    def _font(self) -> tkfont.Font:
        name = ttk.Style().lookup(str(self.tree.cget("style") or "Treeview"), "font") or "TkDefaultFont"
        try:
            return tkfont.nametofont(name)
        except tk.TclError:
            return tkfont.Font(font=name)

    def _motion(self, e) -> None:
        t = self.tree
        row, col = t.identify_row(e.y), t.identify_column(e.x)
        if (row, col) == self.key:
            return
        self.hide()
        self.key = (row, col)
        if not row or not col or col == "#0":
            return
        cid = t.column(col, "id")
        if cid not in self.columns:
            return
        text = str(t.set(row, cid)).strip()
        # chừa chỗ cho chữ đậm và lề ô
        if not text or self._font().measure(text) * 1.08 + 14 <= int(t.column(cid, "width")):
            return
        self.job = t.after(self.delay, lambda: self._show(text, e.x_root, e.y_root))

    def _show(self, text: str, x: int, y: int) -> None:
        self.job = None
        tip = self.tip = tk.Toplevel(self.tree)
        tip.overrideredirect(True)
        tk.Label(tip, text=text, background="#ffffe0", foreground="#202020", relief="solid", borderwidth=1,
                 wraplength=520, justify="left", padx=8, pady=5, font=self._font()).pack()
        tip.update_idletasks()
        sw = tip.winfo_screenwidth()
        x = min(x + 14, sw - tip.winfo_reqwidth() - 8)
        tip.geometry(f"+{max(0, x)}+{y + 20}")

    def hide(self) -> None:
        if self.job:
            self.tree.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None
        self.key = None


class TextDialog(tk.Toplevel):
    """Hộp thoại nhập nhiều dòng chữ."""

    def __init__(self, parent, title: str, message: str, initial: str = ""):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.result: str | None = None
        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=message, wraplength=560, justify="left").pack(anchor="w", pady=(0, 8))
        self.text = tk.Text(body, width=70, height=12, wrap="word", font=tkfont.nametofont("TkDefaultFont"))
        self.text.insert("1.0", initial)
        self.text.pack(fill="both", expand=True)
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text="Đồng ý", style="Big.TButton", command=self._ok).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Hủy", command=self.destroy).pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.text.focus_set()
        center(self, parent)
        self.wait_window()

    def _ok(self) -> None:
        self.result = self.text.get("1.0", "end").strip()
        self.destroy()


def center(win: tk.Toplevel, parent) -> None:
    win.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - win.winfo_width()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - win.winfo_height()) // 3
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


class CheckListDialog(tk.Toplevel):
    """Danh sách có ô tích để duyệt từng mục. items: đối tượng có .text và .apply."""

    def __init__(self, parent, title: str, intro: str, items: list, ok_text: str = "Áp dụng"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent.winfo_toplevel())
        self.items = items
        self.ok = False
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=intro, wraplength=780, justify="left").pack(anchor="w")
        ttk.Label(body, text="Bấm vào dòng để bật/tắt. Chỉ các dòng có dấu tích được áp dụng.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 4))
        frame, self.tree = with_scrollbar(body, ttk.Treeview, columns=("nd",), show="tree headings", height=16)
        frame.pack(fill="both", expand=True)
        self.tree.heading("#0", text="Áp dụng")
        self.tree.heading("nd", text="Nội dung")
        self.tree.column("#0", width=80, anchor="center", stretch=False)
        self.tree.column("nd", width=720)
        tag_colors(self.tree)
        for i, it in enumerate(items):
            self.tree.insert("", "end", iid=str(i), image=_chk(it.apply), values=(it.text,),
                             tags=() if it.apply else ("muted",))
        self.tree.bind("<ButtonRelease-1>", self._toggle)
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text=ok_text, style="Big.TButton", command=self._ok).pack(side="left", padx=(0, 8))
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
        it = self.items[int(iid)]
        it.apply = not it.apply
        self.tree.item(iid, image=_chk(it.apply), tags=() if it.apply else ("muted",))

    def _all(self, on: bool) -> None:
        for i, it in enumerate(self.items):
            it.apply = on
            self.tree.item(str(i), image=_chk(on), tags=() if on else ("muted",))

    def _ok(self) -> None:
        self.ok = True
        self.destroy()


def _chk(on: bool):
    """Ô tích dạng ảnh cho các bảng duyệt."""
    from .icons import icon

    return icon("chk_on" if on else "chk_off")
