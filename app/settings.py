"""Cài đặt của app: file CaiDat.txt cạnh DiemDanhBanTru.exe (mở bằng Notepad sửa được).

Mỗi dòng "khóa = giá trị"; dòng bắt đầu bằng # là chú thích. Các khóa: xem KEYS.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FILE_NAME = "CaiDat.txt"
KEYS = {
    "so_file": "Sổ điểm danh tháng đang dùng (.xlsx). Sang tháng mới app tìm sổ tháng đó cùng thư mục.",
    "cdhs_file": "File Excel danh sách học sinh.",
    "build": "Mã bản app đã thiết lập (app tự ghi; bản .exe mới thì bắt thiết lập lại).",
}


def default_path() -> Path:
    """Cạnh file .exe; chạy từ mã nguồn thì ở thư mục gốc của repo.
    Thư mục đó không ghi được (vd. Program Files) thì dùng %APPDATA%\\DiemDanhBanTru."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    if not _writable(base):
        base = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "DiemDanhBanTru"
    return base / FILE_NAME


def _writable(folder: Path) -> bool:
    """Thử ghi thật (trên Windows os.access không xét quyền thư mục, vd. Program Files)."""
    probe = folder / ".ghi_thu"
    try:
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


def load(path: Path) -> dict[str, str]:
    out = dict.fromkeys(KEYS, "")
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
    for key, help_text in KEYS.items():
        lines += [f"# {help_text}", f"{key} = {values.get(key, '')}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
