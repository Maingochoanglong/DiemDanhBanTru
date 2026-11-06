"""Kiểu dáng chung: Qt Fusion + bảng màu sáng, thẻ trắng bo góc (giống ứng dụng Windows 11)."""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

ACCENT = "#0f6cbd"  # xanh kiểu Windows 11
ACCENT_DARK = "#0c5a9e"
BG = "#f3f4f6"
CARD = "#ffffff"
BORDER = "#e1e4ea"
TEXT = "#1f2328"
MUTED = "#6b7280"
OK = "#1a7f37"
OK_BG = "#e6f4ea"
WARN = "#9a5b00"
WARN_BG = "#fff4e0"
ERR = "#c42b1c"
ERR_BG = "#fde7e9"
NONE_BG = "#f1f2f4"

FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.Base, QColor(CARD))
    pal.setColor(QPalette.AlternateBase, QColor("#f7f8fa"))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(CARD))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipBase, QColor("#ffffe8"))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    app.setPalette(pal)
    app.setFont(QFont(FAMILY, 11))
    app.setStyleSheet(QSS)


QSS = f"""
QWidget {{ color: {TEXT}; }}
QToolTip {{ border: 1px solid {BORDER}; padding: 6px; }}

/* thanh điều hướng bên trái */
QFrame#nav {{ background: #eaecf0; border: none; }}
QListWidget#navList {{ background: transparent; border: none; padding: 6px 8px; outline: 0; font-size: 12pt; }}
QListWidget#navList::item {{ padding: 11px 10px; border-radius: 8px; margin: 2px 0px; color: {TEXT}; }}
QListWidget#navList::item:hover {{ background: #dfe3e8; }}
QListWidget#navList::item:selected {{ background: {CARD}; color: {ACCENT}; font-weight: 600;
                                      border-left: 3px solid {ACCENT}; }}
#appTitle {{ font-size: 15pt; font-weight: 700; color: {ACCENT}; padding: 14px 16px 6px 16px; }}

/* thẻ (vùng chức năng): nền trắng, viền mảnh, bo góc, tách khỏi nền xám */
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#cardTitle {{ font-size: 13pt; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#big {{ font-size: 14pt; font-weight: 700; }}
QLabel#warn {{ color: {WARN}; font-weight: 600; }}
QLabel#err {{ color: {ERR}; font-weight: 600; }}
QLabel#ok {{ color: {OK}; font-weight: 600; }}

/* nút */
QPushButton {{ background: {CARD}; border: 1px solid #c9ced6; border-radius: 6px; padding: 8px 16px;
              min-height: 22px; font-weight: 600; }}
QPushButton:hover {{ background: #f5f7fa; border-color: #b5bcc6; }}
QPushButton:pressed {{ background: #eceff3; }}
QPushButton:disabled {{ color: #a0a6ae; }}
QPushButton#primary {{ background: {ACCENT}; color: white; border: 1px solid {ACCENT}; }}
QPushButton#primary:hover {{ background: {ACCENT_DARK}; }}
QPushButton#flat {{ border: none; background: transparent; padding: 6px 10px; }}
QPushButton#flat:hover {{ background: #e9ecf0; }}

/* ô tên học sinh: bấm để đánh vắng */
QPushButton#student {{ text-align: left; padding: 10px 14px; font-size: 13pt; font-weight: 500;
                      border: 1px solid {BORDER}; border-radius: 8px; background: #fafbfc; }}
QPushButton#student:hover {{ border-color: {ACCENT}; background: #f2f7fd; }}
QPushButton#student:checked {{ background: {ERR_BG}; border: 2px solid {ERR}; color: {ERR}; font-weight: 700; }}

/* ô nhập */
QLineEdit, QDateEdit, QComboBox {{ background: {CARD}; border: 1px solid #c9ced6; border-radius: 6px;
                                  padding: 6px 10px; min-height: 22px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{ border: 2px solid {ACCENT}; }}
QLineEdit#search {{ font-size: 14pt; padding: 8px 12px; }}

/* bảng */
QTableView, QTableWidget, QTreeWidget, QListWidget {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px;
                                         gridline-color: #eef0f3; selection-background-color: #d6e6f7;
                                         selection-color: {TEXT}; outline: 0; }}
QHeaderView::section {{ background: #f6f7f9; border: none; border-bottom: 1px solid {BORDER}; padding: 8px 6px;
                        font-weight: 700; color: #3b4048; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* thanh trạng thái dưới cùng */
QStatusBar {{ background: {CARD}; border-top: 1px solid {BORDER}; }}
"""
