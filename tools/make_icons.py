"""Tạo app/ui/icons_data.py từ icon vector Tabler Icons (MIT).

Chạy lúc phát triển (không cần khi dùng app):

    pip download --no-deps pytablericons==1.0.1 && python -m zipfile -e pytablericons-1.0.1-py3-none-any.whl tabler
    pip install cairosvg
    python tools/make_icons.py tabler/pytablericons/icons

Mỗi icon được tô màu rồi chuyển SVG -> PNG ở nhiều cỡ, lưu dạng base64 để file .exe tự có icon.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import cairosvg

SIZES = (16, 20, 24, 32)
APP_SIZES = (16, 32, 48, 64)

GREEN, ORANGE, RED, GREY, BLUE, DARK = "#1b7f3b", "#c26a00", "#c62828", "#8a8a8a", "#0b5cad", "#3c4a55"

# tên trong app: (kiểu outline/filled, file SVG Tabler, màu)
ICONS = {
    # trạng thái lớp trong bảng điểm danh
    "st_none": ("outline", "circle", GREY),
    "st_ok": ("filled", "circle-check", GREEN),
    "st_absent": ("filled", "circle", ORANGE),
    "st_err": ("filled", "alert-triangle", RED),
    # kết quả kiểm tra từng tên
    "res_ok": ("outline", "circle-check", GREEN),
    "res_ambiguous": ("filled", "alert-triangle", ORANGE),
    "res_not_bt": ("outline", "ban", GREY),
    "res_err": ("filled", "circle-x", RED),
    "res_raw": ("outline", "pencil", ORANGE),
    "res_skip": ("outline", "minus", GREY),
    "res_schedule": ("outline", "calendar-event", BLUE),
    "res_unknown": ("outline", "help-circle", RED),
    # ô tích trong hộp duyệt
    "chk_on": ("filled", "square-check", BLUE),
    "chk_off": ("outline", "square", GREY),
    # nút
    "prev": ("outline", "chevron-left", DARK),
    "next": ("outline", "chevron-right", DARK),
    "settings": ("outline", "settings", DARK),
    "cut": ("outline", "scissors", DARK),
    "add": ("outline", "plus", DARK),
    "save": ("outline", "device-floppy", BLUE),
    "print": ("outline", "printer", DARK),
    "undo": ("outline", "arrow-back-up", DARK),
    "copy": ("outline", "copy", DARK),
    "pencil": ("outline", "pencil", ORANGE),
    "calendar": ("outline", "calendar-event", DARK),
    "excel": ("outline", "file-spreadsheet", GREEN),
    "today": ("outline", "calendar-check", DARK),
    "list": ("outline", "list-details", DARK),
    "friday": ("outline", "calendar-minus", DARK),  # cắt thứ 6 hàng tuần
    "open": ("outline", "app-window", BLUE),  # mở cửa sổ lớp
    "ask": ("outline", "help-circle", BLUE),  # hộp hỏi
}
APP_ICON = ("outline", "calendar-check", BLUE)  # biểu tượng cửa sổ app


def _svg(root: Path, kind: str, name: str, color: str) -> bytes:
    text = (root / kind / f"{name}.svg").read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text.replace("currentColor", color).encode("utf-8")


def _png(svg: bytes, size: int) -> str:
    return base64.b64encode(cairosvg.svg2png(bytestring=svg, output_width=size, output_height=size)).decode("ascii")


def main(root: Path, out: Path) -> None:
    lines = ['"""Icon PNG (base64) tạo từ Tabler Icons (MIT, xem LICENSE-tabler-icons.txt) bằng tools/make_icons.py.',
             "", 'Không sửa tay: chạy lại tools/make_icons.py để cập nhật."""', "", "ICONS = {"]
    for key, (kind, name, color) in {**ICONS, "app": APP_ICON}.items():
        svg = _svg(root, kind, name, color)
        sizes = APP_SIZES if key == "app" else SIZES
        lines.append(f"    {key!r}: {{")
        for s in sizes:
            lines.append(f"        {s}: {_png(svg, s)!r},")
        lines.append("    },")
    lines.append("}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Đã ghi {out} ({len(ICONS) + 1} icon)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(__file__).resolve().parents[1] / "app" / "ui" / "icons_data.py")
