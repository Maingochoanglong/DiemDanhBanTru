"""Cài đặt của app: file CaiDat.txt cạnh DiemDanhBanTru.exe (mở bằng Notepad sửa được).

Mỗi dòng "khóa = giá trị"; dòng bắt đầu bằng # là chú thích. Các khóa và giá trị mặc định: xem KEYS.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import config

# khóa -> (giá trị mặc định, chú thích ghi vào file)
KEYS = {
    "so_file": ("", "Sổ điểm danh tháng đang dùng (.xlsx)."),
    "cdhs_file": ("", "File Excel danh sách học sinh."),
    "cong": (str(config.DEFAULT_PORT), f"Cổng của máy chủ nội bộ (http://{config.HOST}:cổng). Chỉ đổi khi trùng chương trình khác."),
    "thanh_ben_thu_gon": ("", "x = thu gọn thanh bên trái (app tự ghi khi bấm nút « »)."),
    "build": ("", "Mã bản app đã thiết lập (app tự ghi; bản .exe mới thì bắt thiết lập lại)."),
}


def default_path() -> Path:
    """Cạnh file .exe; chạy từ mã nguồn thì ở thư mục gốc của repo."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    return base / config.SETTINGS_FILE


def load(path: Path) -> dict[str, str]:
    out = {k: default for k, (default, _) in KEYS.items()}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return out
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            out[key.strip()] = value.strip()
    return out


def save(path: Path, values: dict[str, str]) -> None:
    lines = ["# Cài đặt app Điểm danh bán trú. Mỗi dòng: khóa = giá trị."]
    for key, (default, help_text) in KEYS.items():
        lines += [f"# {help_text}", f"{key} = {values.get(key, default)}"]
    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as e:
        raise OSError(f"Không ghi được {path}. Hãy chép {config.APP_ID}.exe vào thư mục ghi được (vd. Documents) rồi mở lại.") from e


def port(values: dict[str, str]) -> int:
    try:
        return int(values.get("cong") or config.DEFAULT_PORT)
    except ValueError:
        return config.DEFAULT_PORT
