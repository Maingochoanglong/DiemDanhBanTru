"""Trang Điểm danh: bên trái danh sách lớp, bên phải tên các em của lớp đang chọn.

Bấm vào lớp → hiện tên các em (ô to). Bấm vào ô tên → vắng (ô đỏ), bấm lại → bỏ vắng.
Không có cửa sổ bật lên: mọi thứ nằm trên cùng một màn.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.search import matches
from . import theme as T
from .icons import qicon

STATUS = {  # mức → (chữ, màu chữ, màu nền, icon)
    "muted": ("chưa báo", T.MUTED, T.NONE_BG, "st_none"),
    "ok": ("đủ", T.OK, T.OK_BG, "st_ok"),
    "warn": ("có vắng", T.WARN, T.WARN_BG, "st_absent"),
    "err": ("cần xem", T.ERR, T.ERR_BG, "st_err"),
}


def card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    """Thẻ trắng bo góc chứa một vùng chức năng."""
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    if title:
        t = QLabel(title)
        t.setObjectName("cardTitle")
        lay.addWidget(t)
    return f, lay


class PageDiemDanh(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ws = app.ws
        self.code: str | None = None
        self.buttons: dict[str, QPushButton] = {}
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # ---- trái: danh sách lớp
        left, ll = card("Lớp")
        left.setMinimumWidth(330)
        left.setMaximumWidth(400)
        self.classes = QTableWidget(0, 4)
        self.classes.setHorizontalHeaderLabels(["Lớp", "Sĩ số", "Vắng", "Có mặt"])
        self.classes.verticalHeader().setVisible(False)
        self.classes.setShowGrid(False)
        self.classes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.classes.setSelectionMode(QAbstractItemView.SingleSelection)
        self.classes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.classes.verticalHeader().setDefaultSectionSize(40)
        h = self.classes.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2, 3):
            h.setSectionResizeMode(c, QHeaderView.Fixed)
            self.classes.setColumnWidth(c, 62 if c < 3 else 76)
        self.classes.itemSelectionChanged.connect(self._on_select)
        ll.addWidget(self.classes, 1)
        self.lbl_total = QLabel("")
        self.lbl_total.setObjectName("big")
        ll.addWidget(self.lbl_total)
        root.addWidget(left)

        # ---- phải: tên các em của lớp đang chọn
        right, rl = card()
        # dòng 1: tên lớp + GVCN (trái) · sĩ số, vắng, hiện diện (phải)
        self.head = head = QBoxLayout(QBoxLayout.LeftToRight)
        self.lbl_class = QLabel("")
        self.lbl_class.setStyleSheet("font-size: 16pt; font-weight: 700;")
        self.lbl_class.setTextFormat(Qt.RichText)
        head.addWidget(self.lbl_class, 1)
        self.lbl_counts = QLabel("")
        self.lbl_counts.setStyleSheet("font-size: 13pt; font-weight: 600;")
        head.addWidget(self.lbl_counts)
        rl.addLayout(head)

        self.lbl_warn = QLabel("")
        self.lbl_warn.setObjectName("err")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.hide()
        rl.addWidget(self.lbl_warn)

        # dòng 2: ô tìm tên (to) · nút Lớp này đủ
        srow = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Tìm tên trong lớp (không cần dấu)")
        self.search.setToolTip("Gõ đầu chữ, vd: h long. Còn 1 em khớp thì Enter để đánh vắng. Esc để xóa.")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._layout_names)
        self.search.returnPressed.connect(self._enter)
        srow.addWidget(self.search, 1)
        self.btn_full = QPushButton(qicon("st_ok"), "  Lớp này đủ")
        self.btn_full.setToolTip("Lớp không có em nào vắng")
        self.btn_full.setMinimumHeight(44)
        self.btn_full.clicked.connect(self.mark_full)
        srow.addWidget(self.btn_full)
        rl.addLayout(srow)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.grid_host)
        rl.addWidget(self.scroll, 1)

        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Ghi chú (cột H):"))
        self.note = QLineEdit()
        self.note.editingFinished.connect(self._save_note)
        note_row.addWidget(self.note, 1)
        rl.addLayout(note_row)
        root.addWidget(right, 1)

        self._relayout = QTimer(self, singleShot=True, interval=60, timeout=self._layout_names)

    # ------------------------------------------------------------------ làm mới
    def refresh(self) -> None:
        st = self.ws.state
        if st is None:
            return
        codes = list(st.classes)
        if self.code not in st.classes:
            self.code = codes[0] if codes else None
        self._fill_classes()
        self._build_names()
        self._refresh_header()

    def _status(self, code: str) -> str:
        st = self.ws.state
        c = st.cd(code)
        n = st.absent_count(code)
        if c.extra or any(p[0] == code for p in st.pending) or st.class_warnings(code):
            return "err"
        if not c.reported and not n:
            return "muted"
        return "warn" if n else "ok"

    def _fill_classes(self) -> None:
        st = self.ws.state
        t = self.classes
        t.blockSignals(True)
        codes = list(st.classes)
        t.setRowCount(len(codes))
        bold = QFont()
        bold.setBold(True)
        for r, code in enumerate(codes):
            key = self._status(code)
            text, fg, bg, ic = STATUS[key]
            vals = [code, str(st.si_so(code)), str(st.absent_count(code)), str(st.present(code))]
            for c, v in enumerate(vals):
                it = t.item(r, c)
                if it is None:
                    it = QTableWidgetItem()
                    t.setItem(r, c, it)
                it.setText(("  " if c == 0 else "") + v)
                it.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if c == 0 else Qt.AlignCenter))
                it.setBackground(QBrush(QColor(bg)))
                it.setForeground(QBrush(QColor(fg if c != 0 else T.TEXT)))
                if c == 0:
                    it.setIcon(qicon(ic))
                    it.setFont(bold)
                    it.setData(Qt.UserRole, code)
                    it.setToolTip(text)
            if code == self.code:
                t.selectRow(r)
        t.blockSignals(False)
        si, ab, pr = st.totals()
        n_rep = sum(1 for c in st.classes.values() if c.reported)
        self.lbl_total.setText(f"Đã báo {n_rep}/{len(codes)} lớp · Sĩ số {si}\nVắng {ab} · Hiện diện {pr}")

    def _on_select(self) -> None:
        rows = self.classes.selectionModel().selectedRows()
        if not rows:
            return
        code = self.classes.item(rows[0].row(), 0).data(Qt.UserRole)
        if code != self.code:
            self._save_note()
            self.code = code
            self.search.clear()
            self._build_names()
            self._refresh_header()
            self.search.setFocus()

    def _refresh_header(self) -> None:
        st = self.ws.state
        code = self.code
        if not code:
            self.lbl_class.setText("Chưa có lớp")
            return
        info = self.ws.roster.classes.get(code)
        ma = f" ({info.ma_ngan})" if info and info.ma_ngan else ""
        gv = (f"  <span style='font-size:11pt; font-weight:400; color:{T.MUTED}'>GVCN {info.gvcn}</span>"
              if info and info.gvcn else "")
        self.lbl_class.setText(f"Lớp {code}{ma}{gv}")
        n = st.absent_count(code)
        self.lbl_counts.setText(f"Sĩ số {st.si_so(code)}  ·  Vắng {n}  ·  Hiện diện {st.present(code)}")
        warns = st.class_warnings(code)
        self.lbl_warn.setText("⚠ " + "\n⚠ ".join(warns) if warns else "")
        self.lbl_warn.setVisible(bool(warns))
        self.note.setText(st.cd(code).note)

    def _build_names(self) -> None:
        for b in self.buttons.values():
            b.deleteLater()
        self.buttons.clear()
        st = self.ws.state
        code = self.code
        if not code:
            return
        students = self.ws.roster.sort_like_roster(self.ws.roster.boarding(code, st.date))
        auto = st.auto_absent(code)
        for s in students:
            label = self.ws.roster.display_name(s)
            extra = auto.get(s.id) or ("nghỉ T6" if s.cat_thu6 else "")
            b = QPushButton(label + (f"   ({extra})" if extra else ""))
            b.setObjectName("student")
            b.setCheckable(True)
            b.setChecked(st.is_absent(code, s.id))
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(46)
            b.setToolTip(f"{s.ho_ten} · {s.ngay_sinh}")
            b._search = s.ho_ten + " " + label  # type: ignore[attr-defined]
            b.toggled.connect(lambda on, sid=s.id: self._toggle(sid, on))
            self.buttons[s.id] = b
        self._layout_names()

    def _layout_names(self) -> None:
        """Xếp ô tên thành cột, đọc dọc A→Z như danh sách giấy; ô tìm lọc theo đầu chữ."""
        while self.grid.count():
            self.grid.takeAt(0)
        q = self.search.text()
        shown = []
        for b in self.buttons.values():
            ok = matches(q, b._search)  # type: ignore[attr-defined]
            b.setVisible(ok)
            if ok:
                shown.append(b)
        w = self.scroll.viewport().width() or 900
        cols = max(1, min(4, w // 200))
        rows = max(1, -(-len(shown) // cols))
        for i, b in enumerate(shown):
            self.grid.addWidget(b, i % rows, i // rows)
        for c in range(4):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)
        self.grid.setRowStretch(rows, 1)

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        # màn hẹp: sĩ số / vắng / có mặt xuống dòng dưới tên lớp
        self.head.setDirection(QBoxLayout.TopToBottom if self.width() < 980 else QBoxLayout.LeftToRight)
        self._relayout.start()

    # ------------------------------------------------------------------ thao tác
    def _toggle(self, sid: str, absent: bool) -> None:
        st = self.ws.state
        if st.is_absent(self.code, sid) == absent:
            return
        self.ws.push_undo()
        st.set_absent(self.code, sid, absent)
        self._after_change()

    def _enter(self) -> None:
        shown = [b for b in self.buttons.values() if b.isVisible()]
        if len(shown) == 1:
            shown[0].toggle()
            self.search.selectAll()

    def mark_full(self) -> None:
        if not self.code:
            return
        self.ws.push_undo()
        self.ws.state.mark_full(self.code)
        self._build_names()
        self._after_change()

    def _save_note(self) -> None:
        st = self.ws.state
        if st is None or not self.code:
            return
        c = st.cd(self.code)
        val = self.note.text().strip()
        if val != c.note:
            self.ws.push_undo()
            c.note = val
            self.app.mark_changed()

    def _after_change(self) -> None:
        self._fill_classes()
        self._refresh_header()
        self.app.mark_changed()
