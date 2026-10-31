"""Cửa sổ chính: chọn ngày, các tab, lưu/in, hướng dẫn lần đầu."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..core.text import parse_date
from ..excel import printing
from ..excel.files import FileLockedError
from ..service import NeedMonthBook, Workspace, next_school_day
from .tab_cai_dat import TabCaiDat
from .tab_diem_danh import WEEKDAYS, TabDiemDanh
from .tab_ghep_lop import TabGhepLop
from .tab_hoc_sinh import TabHocSinh, ask_import, ask_notes
from .tab_lich import TabLich
from .icons import icon, set_app_icon
from .tab_suat_an import TabSuatAn
from .widgets import ChoiceDialog, ask


class _TabGroup(ttk.Frame):
    """Tab chứa các tab con (dùng cho tab Học sinh: danh sách + ghép lớp)."""

    def __init__(self, parent):
        super().__init__(parent, padding=(0, 4, 0, 0))
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)


class MainWindow:
    def __init__(self, root: tk.Tk, ws: Workspace):
        self.root = root
        self.ws = ws
        root.title("Điểm danh bán trú")
        set_app_icon(root)
        root.minsize(1100, 680)

        top = ttk.Frame(root, padding=(10, 8, 10, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Ngày:", style="Title.TLabel").pack(side="left")
        ttk.Button(top, image=icon("prev"), command=lambda: self.step_day(-1)).pack(side="left", padx=(6, 2))
        self.date_var = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.date_var, width=11, font=("TkDefaultFont", 12, "bold"), justify="center")
        e.pack(side="left")
        e.bind("<Return>", lambda ev: self.open_typed_day())
        ttk.Button(top, image=icon("next"), command=lambda: self.step_day(1)).pack(side="left", padx=(2, 4))
        ttk.Button(top, text="Hôm nay", image=icon("today"), compound="left",
                   command=lambda: self.open_day(dt.date.today())).pack(side="left", padx=4)
        self.lbl_wd = ttk.Label(top, text="", style="Title.TLabel")
        self.lbl_wd.pack(side="left", padx=8)
        ttk.Button(top, text="Cài đặt", image=icon("settings"), compound="left",
                   command=self.show_settings).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Mở sổ trong Excel", image=icon("excel"), compound="left",
                   command=self.open_book_in_excel).pack(side="right")
        self.lbl_book = ttk.Label(top, text="", style="Muted.TLabel")
        self.lbl_book.pack(side="right", padx=8)

        self.status = ttk.Label(root, text="", padding=(10, 2, 10, 6))
        self.status.pack(side="bottom", fill="x")
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=8)
        self.tab_dd = TabDiemDanh(self.nb, self)
        self.tab_sa = TabSuatAn(self.nb, self)
        # Tab "Học sinh" gồm 3 tab con ít dùng hằng ngày: danh sách, lịch thêm/cắt, ghép lớp
        self.tab_hs_group = _TabGroup(self.nb)
        self.tab_hs = TabHocSinh(self.tab_hs_group.nb, self)
        self.tab_lich = TabLich(self.tab_hs_group.nb, self)
        self.tab_ghep = TabGhepLop(self.tab_hs_group.nb, self)
        self.tab_hs_group.nb.add(self.tab_hs, text="  Danh sách học sinh  ")
        self.tab_hs_group.nb.add(self.tab_lich, text="  Lịch thêm/cắt  ")
        self.tab_hs_group.nb.add(self.tab_ghep, text="  Ghép lớp  ")
        self.nb.add(self.tab_dd, text="  Điểm danh  ")
        self.nb.add(self.tab_sa, text="  Suất ăn  ")
        self.nb.add(self.tab_hs_group, text="  Học sinh  ")
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)
        self.tab_hs_group.nb.bind("<<NotebookTabChanged>>", self._on_tab)
        # Cài đặt: cửa sổ riêng, mở bằng nút Cài đặt
        self.cd_win = tk.Toplevel(root)
        self.cd_win.withdraw()
        self.cd_win.title("Cài đặt")
        self.cd_win.transient(root)
        self.cd_win.protocol("WM_DELETE_WINDOW", self.cd_win.withdraw)
        self.tab_cd = TabCaiDat(self.cd_win, self)
        self.tab_cd.pack(fill="both", expand=True)
        ttk.Button(self.tab_cd, text="Đóng", command=self.cd_win.withdraw).pack(anchor="e", pady=(12, 0))

        self._flash_job = None

        root.bind_all("<Control-s>", lambda e: self.save())
        root.bind_all("<Control-p>", lambda e: self.print_day())
        root.bind_all("<Control-z>", self._ctrl_z)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(150, self.startup)

    # ------------------------------------------------------------------ khởi động
    def startup(self) -> None:
        self._first_run = False
        if self.ws.needs_setup:
            self.setup_wizard()
        today = dt.date.today()
        self.open_day(today if today.weekday() < 5 else next_school_day(today), ask=False)
        if self._first_run and self.ws.book_path and self.ws.roster.students:
            if ask_notes(self.root, self.ws, quiet=True):
                self.open_day(self.ws.day, ask=False)

    def setup_wizard(self) -> None:
        messagebox.showinfo(
            "Bắt đầu sử dụng",
            "Chào bạn! Lần đầu dùng cần 2 bước:\n\n"
            "1. Chọn file danh sách học sinh (file CDHS, em tô chữ ĐỎ là có ăn bán trú).\n"
            "2. Chọn sổ điểm danh bán trú của tháng hiện tại (file .xlsx, mỗi ngày 1 sheet).\n\n"
            f"Dữ liệu của app sẽ lưu tại:\n{self.ws.data.path}", parent=self.root)
        path = filedialog.askopenfilename(
            parent=self.root, title="Bước 1: chọn file danh sách học sinh (CDHS)",
            filetypes=[("Excel", "*.xls *.xlsx"), ("Tất cả", "*.*")])
        if path:
            n = ask_import(self.root, self.ws, path)
            if n is not None:
                n_bt = sum(1 for s in self.ws.roster.students if s.ban_tru)
                messagebox.showinfo("Đã nhập danh sách",
                                    f"Đã nhập {len(self.ws.roster.students)} học sinh, {n_bt} em ăn bán trú.",
                                    parent=self.root)
        if not self.ws.settings.get("so_file"):
            self.choose_book(title="Bước 2: chọn sổ điểm danh tháng hiện tại", reopen=False)
        self._first_run = True

    # ------------------------------------------------------------------ chọn ngày
    def open_typed_day(self) -> None:
        d = parse_date(self.date_var.get())
        if not d:
            messagebox.showwarning("Ngày không đúng", "Hãy nhập ngày dạng dd/mm/yyyy, ví dụ 29/10/2026.", parent=self.root)
            return
        self.open_day(d)

    def step_day(self, step: int) -> None:
        self.open_day(next_school_day(self.ws.day, step))

    def confirm_discard(self, then: str = "chuyển ngày") -> bool:
        """Hỏi lưu khi ngày đang mở có thay đổi. Trả về False nếu người dùng muốn ở lại."""
        if not self.ws.dirty:
            return True
        ans = ask(self.root, "Chưa lưu", f"Ngày {self.ws.day:%d/%m/%Y} có thay đổi chưa lưu vào sổ.",
                  [("save", f"Lưu rồi {then}"), ("discard", "Không lưu"), ("stay", "Ở lại")])
        if ans == "save":
            return self.save()
        return ans == "discard"

    def open_day(self, day: dt.date, ask: bool = True) -> None:
        if ask and not self.confirm_discard():
            self.date_var.set(f"{self.ws.day:%d/%m/%Y}")
            return
        try:
            self.ws.load_day(day)
        except NeedMonthBook as e:
            if not self._handle_new_month(day, e):
                self._after_load()
                return
            try:
                self.ws.load_day(day)
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Lỗi mở sổ", str(ex), parent=self.root)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Lỗi mở sổ", f"Không mở được sổ điểm danh:\n{e}", parent=self.root)
        self._after_load()

    def _handle_new_month(self, day: dt.date, e: NeedMonthBook) -> bool:
        if e.prev is None:
            self.flash("Chưa chọn sổ điểm danh. Bấm nút Cài đặt → Chọn sổ khác…", error=True)
            return False
        dlg = ChoiceDialog(
            self.root, "Sổ tháng mới",
            f"Chưa có sổ điểm danh tháng {e.month}/{e.year} trong thư mục\n{e.prev.parent}.\n\n"
            f"Tạo sổ mới từ sheet cuối cùng của sổ '{e.prev.name}'? (giữ nguyên mẫu, chữ ký, ghi chú)",
            [], [("new", "Tạo sổ tháng mới"), ("pick", "Chọn file sổ có sẵn…"), ("cancel", "Để sau")])
        key = dlg.result[0]
        if key == "new":
            try:
                new = self.ws.create_month_book(day)
            except FileExistsError as ex:
                self.ws.set_book(ex.args[0])
                return True
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Không tạo được sổ mới", str(ex), parent=self.root)
                return False
            self.flash(f"Đã tạo sổ mới: {new.name}")
            return True
        if key == "pick":
            return self.choose_book(reopen=False)
        return False

    def _after_load(self) -> None:
        st = self.ws.state
        self.date_var.set(f"{self.ws.day:%d/%m/%Y}")
        self.lbl_wd.configure(text=WEEKDAYS[self.ws.day.weekday()])
        bp = self.ws.book_path
        if bp:
            sheet = self.ws.sheet_name or str(self.ws.day.day)
            where = f"sheet {sheet}" if st and st.exists_in_book else f"sẽ tạo sheet {sheet} (mẫu: sheet {self.ws.template_name})"
            self.lbl_book.configure(text=f"Sổ: {bp.name} · {where}")
        else:
            self.lbl_book.configure(text="Chưa có sổ cho tháng này")
        self.tab_dd.clear_results()
        self.refresh_all()
        self.tab_dd.show_sheet_checks()
        self.tab_dd.show_scheduled_changes()

    # ------------------------------------------------------------------ làm mới
    def refresh_all(self) -> None:
        if self.ws.state is None:
            return
        self.tab_dd.refresh()
        self.tab_sa.refresh()
        self.tab_lich.refresh()
        self.tab_ghep.refresh()
        self.tab_hs.refresh()
        self.tab_cd.refresh()

    def refresh_days_only(self) -> None:
        if self.ws.state is None:
            return
        self.ws.roster.invalidate()
        self.tab_dd.refresh()

    def _on_tab(self, _e=None) -> None:
        tab = self.nb.nametowidget(self.nb.select())
        if isinstance(tab, _TabGroup):
            tab = tab.nb.nametowidget(tab.nb.select())
        if hasattr(tab, "refresh") and self.ws.state is not None:
            tab.refresh()

    def show_tab(self, tab) -> None:
        """Chuyển tới một tab (kể cả tab con trong tab Học sinh)."""
        if tab in (self.tab_hs, self.tab_lich, self.tab_ghep):
            self.nb.select(self.tab_hs_group)
            self.tab_hs_group.nb.select(tab)
        else:
            self.nb.select(tab)

    def show_settings(self) -> None:
        if self.ws.state is not None:
            self.tab_cd.refresh()
        w = self.cd_win
        if not w.winfo_viewable():
            w.update_idletasks()  # cao vừa nội dung, rộng đủ hiện đường dẫn file
            w.geometry(f"{max(980, w.winfo_reqwidth())}x{w.winfo_reqheight()}")
            from .widgets import center

            center(w, self.root)
            w.deiconify()
        w.lift()
        w.focus_set()

    def flash(self, text: str, error: bool = False) -> None:
        self.status.configure(text=text, style="Err.TLabel" if error else "Ok.TLabel")
        if self._flash_job:
            self.root.after_cancel(self._flash_job)
        self._flash_job = self.root.after(12000, lambda: self.status.configure(text=""))

    # ------------------------------------------------------------------ lưu / in
    def save(self) -> bool:
        if self.ws.state is None:
            return False
        if not self.ws.book_path:
            messagebox.showwarning("Chưa có sổ", "Chưa có sổ điểm danh cho tháng này. Bấm nút Cài đặt để chọn sổ.",
                                   parent=self.root)
            return False
        self.tab_dd._save_note()
        if not self._check_unresolved():
            return False
        conflicts = self.ws.si_so_conflicts()
        if conflicts:
            lines = [f"{c}: theo danh sách {ds} em, trong sổ đang ghi {so} em" for c, ds, so in conflicts]
            dlg = ChoiceDialog(
                self.root, "Sĩ số khác nhau",
                "Các lớp sau có sĩ số theo danh sách bán trú khác sĩ số đang ghi trong sổ "
                "(có thể do thêm/cắt em chưa cập nhật ở tab Học sinh). Ghi sĩ số nào vào sổ?",
                lines, [("keep", "Giữ sĩ số như trong sổ"), ("list", "Dùng sĩ số theo danh sách"), ("cancel", "Hủy")])
            key = dlg.result[0]
            if key in (None, "cancel"):
                return False
            if key == "keep":
                self.ws.keep_sheet_si_so([c for c, _, _ in conflicts])
        while True:
            try:
                sheet = self.ws.save()
                break
            except FileLockedError as e:
                if ask(self.root, "File đang mở", f"File đang mở trong Excel nên chưa ghi được:\n{e}\n\n"
                       "Hãy đóng file đó trong Excel rồi bấm Thử lại.",
                       [("retry", "Thử lại"), ("cancel", "Hủy")], image="st_err") != "retry":
                    return False
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Lỗi khi lưu", f"Không lưu được:\n{e}", parent=self.root)
                return False
        if self.ws.warning:
            self.flash(self.ws.warning, error=True)
        else:
            self.flash(f"Đã lưu vào sổ {self.ws.book_path.name}, sheet {sheet}. Bản cũ đã sao lưu trong thư mục SaoLuu.")
        self._after_load_light()
        return True

    def _check_unresolved(self) -> bool:
        """Chốt chặn: còn tên chưa rõ / tin không rõ lớp (chưa tính vắng) thì CHƯA cho lưu, in.

        Không bị kẹt: mỗi tên chưa rõ đều chọn được "Chọn em này", "Giữ nguyên chữ GV ghi" hoặc "Bỏ qua tên này";
        tin không rõ lớp chọn được "Ghi vào lớp này" hoặc "Bỏ tin này".
        """
        n = self.ws.unresolved_count()
        if not n:
            return True
        lines = [f"Lớp {code}: {', '.join(names)}" for code, names in self.ws.pending_names().items()]
        for m in self.ws.unplaced:
            who = f" (người gửi {m.sender})" if m.sender else ""
            lines.append(f"Tin không rõ lớp{who}: {', '.join(m.names)}")
        ChoiceDialog(
            self.root, "Chưa lưu được",
            f"Còn {n} tên GV báo vắng chưa rõ là em nào, nên chưa tính vắng.\n"
            "Với mỗi tên: chọn em đúng, giữ nguyên chữ GV ghi, hoặc bỏ qua tên đó. Xử lý xong mới lưu được.",
            lines, [("fix", "Xử lý ngay")], image="st_err", style="Err.TLabel")
        self.fix_unresolved()
        return False

    def fix_unresolved(self) -> None:
        """Đưa giáo vụ tới chỗ cần xử lý (cửa sổ lớp có tên chưa rõ, hoặc Kết quả chi tiết)."""
        self.show_tab(self.tab_dd)
        self.tab_dd.focus_problem()

    def _after_load_light(self) -> None:
        bp = self.ws.book_path
        if bp:
            self.lbl_book.configure(text=f"Sổ: {bp.name} · sheet {self.ws.sheet_name}")
        self.tab_dd.refresh_light()

    def print_day(self) -> None:
        st = self.ws.state
        if st is None or not self.ws.book_path:
            return
        if self.ws.dirty or not st.exists_in_book:
            if self.ws.unresolved_count():
                self._check_unresolved()
                return
            if ask(self.root, "Lưu trước khi in", "Cần lưu ngày này vào sổ trước khi in.",
                   [("save", "Lưu rồi in"), ("cancel", "Hủy")]) != "save":
                return
            if not self.save():
                return
        areas = self.ws.print_areas()
        self.flash("Đang gửi lệnh tới Excel…")
        self.root.update_idletasks()
        try:
            printing.print_areas(self.ws.book_path, self.ws.sheet_name, areas)
        except printing.PrintError as e:
            if ask(self.root, "Không in trực tiếp được",
                   f"{e}\n\nCó thể mở sổ bằng Excel để in tay (vùng in: {' và '.join(areas)}).",
                   [("open", "Mở sổ bằng Excel"), ("close", "Đóng")], image="st_err") == "open":
                printing.open_file(self.ws.book_path)
            return
        self.flash("Đã gửi lệnh in 2 tờ.")

    def undo(self) -> None:
        if self.ws.undo():
            self.tab_dd.refresh()
            self.flash("Đã hoàn tác.")

    def _ctrl_z(self, e) -> None:
        if isinstance(e.widget, (tk.Text, ttk.Entry, tk.Entry)):
            return  # để ô chữ tự hoàn tác
        self.undo()

    def show_save_error(self, e: Exception, path) -> None:
        if isinstance(e, FileLockedError):
            messagebox.showwarning("File đang mở", f"File đang mở trong Excel:\n{path}\nHãy đóng Excel rồi lưu lại.",
                                   parent=self.root)
        else:
            messagebox.showerror("Lỗi khi lưu", str(e), parent=self.root)

    # ------------------------------------------------------------------ file
    def choose_book(self, title: str = "Chọn sổ điểm danh tháng (.xlsx)", reopen: bool = True) -> bool:
        path = filedialog.askopenfilename(parent=self.root, title=title, filetypes=[("Excel", "*.xlsx"), ("Tất cả", "*.*")])
        if not path:
            return False
        self.ws.set_book(path)
        if reopen:
            self.open_day(self.ws.day)
        return True

    def ask_import_cdhs(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Chọn file danh sách học sinh (CDHS)",
                                          filetypes=[("Excel", "*.xls *.xlsx"), ("Tất cả", "*.*")])
        if path:
            self.import_cdhs(path)

    def import_cdhs(self, path: str) -> None:
        n = ask_import(self.root, self.ws, path)
        if n is None:
            return
        self.flash(f"Đã áp dụng {n} thay đổi từ {Path(path).name}.")
        self.refresh_days_only()
        self.tab_hs.refresh()
        self.tab_ghep.refresh()

    def ask_note_suggestions(self) -> None:
        n = ask_notes(self.root, self.ws)
        if n:
            self.flash(f"Đã cập nhật {n} học sinh theo ghi chú trong sổ.")
            if not self.ws.dirty:
                self.open_day(self.ws.day, ask=False)
            else:
                self.refresh_days_only()
            self.tab_hs.refresh()

    def open_book_in_excel(self) -> None:
        if self.ws.book_path:
            printing.open_file(self.ws.book_path)

    # ------------------------------------------------------------------ đóng app
    def on_close(self) -> None:
        if not self.confirm_discard("thoát"):
            return
        if self.ws.data_dirty:
            ans = ask(self.root, "Chưa lưu", "Danh sách học sinh / ghép lớp có thay đổi chưa lưu.",
                      [("save", "Lưu rồi thoát"), ("discard", "Không lưu"), ("stay", "Ở lại")])
            if ans in (None, "stay"):
                return
            if ans == "save":
                try:
                    self.ws.save_data()
                except Exception as e:  # noqa: BLE001
                    self.show_save_error(e, self.ws.data.path)
                    return
        self.root.destroy()
