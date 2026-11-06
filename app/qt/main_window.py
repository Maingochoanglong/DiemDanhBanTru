"""Cửa sổ chính (Qt): thanh điều hướng bên trái, thanh ngày ở trên, nội dung ở giữa, nút Lưu/In ở dưới."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..service import NeedMonthBook, Workspace, next_school_day
from .icons import qicon
from .page_diem_danh import PageDiemDanh, card

WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


class MainWindow(QMainWindow):
    def __init__(self, ws: Workspace):
        super().__init__()
        self.ws = ws
        self.setWindowTitle("Điểm danh bán trú")
        self.setMinimumSize(980, 560)  # laptop 1366x768 phóng chữ 125% ≈ 1093x614
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- thanh điều hướng bên trái
        side = QFrame()
        side.setObjectName("nav")
        side.setFixedWidth(196)
        self.side = side
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        self.app_title = QLabel("Điểm danh\nbán trú")
        self.app_title.setObjectName("appTitle")
        sl.addWidget(self.app_title)
        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        for text, ic in (("Điểm danh", "list"), ("Suất ăn", "today"), ("Học sinh", "pencil"),
                         ("Lịch thêm/cắt", "calendar"), ("Ghép lớp", "copy"), ("Cài đặt", "settings")):
            QListWidgetItem(qicon(ic), "  " + text, self.nav)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.currentRowChanged.connect(self._go)
        sl.addWidget(self.nav, 1)
        outer.addWidget(side)

        # ---- phần chính
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(12)
        outer.addWidget(main, 1)

        top, tl = card()
        tl.setContentsMargins(12, 8, 12, 8)
        row = QHBoxLayout()
        tl.addLayout(row)
        b_prev = QPushButton(qicon("prev"), "")
        b_prev.setToolTip("Ngày học trước")
        b_prev.clicked.connect(lambda: self.open_day(next_school_day(self.ws.day, -1)))
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy")
        self.date.setStyleSheet("font-size: 14pt; font-weight: 700; min-width: 150px;")
        self.date.dateChanged.connect(self._date_edited)
        b_next = QPushButton(qicon("next"), "")
        b_next.setToolTip("Ngày học sau")
        b_next.clicked.connect(lambda: self.open_day(next_school_day(self.ws.day, 1)))
        b_today = QPushButton(qicon("today"), "  Hôm nay")
        b_today.clicked.connect(lambda: self.open_day(dt.date.today()))
        self.lbl_wd = QLabel("")
        self.lbl_wd.setStyleSheet("font-size: 14pt; font-weight: 700; padding-left: 8px;")
        for w in (b_prev, self.date, b_next, b_today, self.lbl_wd):
            row.addWidget(w)
        row.addStretch(1)
        self.lbl_book = QLabel("")
        self.lbl_book.setObjectName("muted")
        row.addWidget(self.lbl_book)
        self.b_excel = QPushButton(qicon("excel"), "  Mở sổ Excel")
        row.addWidget(self.b_excel)
        ml.addWidget(top)

        self.pages = QStackedWidget()
        self.page_dd = PageDiemDanh(self)
        self.pages.addWidget(self.page_dd)
        for text in ("Suất ăn", "Học sinh", "Lịch thêm/cắt", "Ghép lớp", "Cài đặt"):
            p, pl = card(text)
            pl.addWidget(QLabel("(đang chuyển sang giao diện mới)"))
            pl.addStretch(1)
            self.pages.addWidget(p)
        ml.addWidget(self.pages, 1)

        bottom = QHBoxLayout()
        self.lbl_state = QLabel("")
        self.lbl_state.setObjectName("muted")
        bottom.addWidget(self.lbl_state, 1)
        self.b_undo = QPushButton(qicon("undo"), "  Hoàn tác")
        self.b_undo.setShortcut("Ctrl+Z")
        self.b_undo.clicked.connect(self.undo)
        b_save = QPushButton(qicon("save"), "  Lưu vào sổ")
        b_save.setObjectName("primary")
        b_save.setShortcut("Ctrl+S")
        b_print = QPushButton(qicon("print"), "  In 2 tờ")
        b_print.setShortcut("Ctrl+P")
        for b in (self.b_undo, b_save, b_print):
            b.setMinimumHeight(42)
            bottom.addWidget(b)
        ml.addLayout(bottom)

        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------------ điều hướng
    def _go(self, row: int) -> None:
        self.pages.setCurrentIndex(row)

    def _date_edited(self, q: QDate) -> None:
        d = dt.date(q.year(), q.month(), q.day())
        if d != self.ws.day:
            self.open_day(d)

    def open_day(self, day: dt.date) -> None:
        try:
            self.ws.load_day(day)
        except NeedMonthBook:
            pass
        self.date.blockSignals(True)
        self.date.setDate(QDate(day.year, day.month, day.day))
        self.date.blockSignals(False)
        self.lbl_wd.setText(WEEKDAYS[day.weekday()])
        bp = self.ws.book_path
        st = self.ws.state
        if bp:
            where = "sheet có sẵn" if st and st.exists_in_book else "sheet mới"
            self.lbl_book.setText(f"{bp.stem} · {where}")
            self.b_excel.setToolTip(f"Mở {bp.name} ({where})")
        else:
            self.lbl_book.setText("Chưa chọn sổ tháng này")
        self.page_dd.refresh()
        self.mark_changed()

    def mark_changed(self) -> None:
        st = self.ws.state
        if st is None:
            return
        self.lbl_state.setText("Có thay đổi chưa lưu vào sổ" if self.ws.dirty else (
            "Đã có trong sổ" if st.exists_in_book else "Ngày này chưa có trong sổ"))

    def undo(self) -> None:
        if self.ws.undo():
            self.page_dd.refresh()
            self.mark_changed()

    def resizeEvent(self, e) -> None:  # noqa: N802
        """Màn nhỏ (laptop phóng chữ 125%): thu hẹp menu trái, ẩn tên sổ (vẫn xem được khi rê chuột)."""
        super().resizeEvent(e)
        small = self.width() < 1250
        self.side.setFixedWidth(178 if small else 196)
        self.app_title.setVisible(not small)
        self.lbl_book.setVisible(self.width() >= 1300)

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key_Escape and self.page_dd.search.hasFocus():
            self.page_dd.search.clear()
            return
        super().keyPressEvent(e)
