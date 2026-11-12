"""Làm việc với file: ghi Excel an toàn (không tạo file phụ), báo khi file đang mở trong Excel, mở file / thư mục."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path


class FileLockedError(Exception):
    """File đang mở trong Excel nên không ghi được."""


def is_locked(path: str | Path) -> bool:
    """Excel giữ file đang mở (không cho ghi): thử mở để ghi là biết, không đụng file nào khác."""
    try:
        with open(path, "r+b"):
            return False
    except FileNotFoundError:
        return False
    except PermissionError:
        return True


def safe_save(wb, path: str | Path) -> None:
    """Dựng file Excel trong bộ nhớ trước (lỗi lúc dựng thì file cũ còn nguyên), xong mới ghi đè 1 lần.
    Không tạo file phụ: app chỉ đụng sổ, sổ tạm, file danh sách, CaiDat.txt."""
    if is_locked(path):
        raise FileLockedError(str(path))
    buf = io.BytesIO()
    wb.save(buf)
    try:
        Path(path).write_bytes(buf.getvalue())
    except PermissionError as e:
        raise FileLockedError(str(path)) from e


def open_file(path: str | Path) -> None:
    """Mở file bằng chương trình mặc định (Excel, Notepad…)."""
    path = str(Path(path).resolve())
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])  # noqa: S603


def open_folder(path: str | Path) -> None:
    p = Path(path)
    open_file(p if p.is_dir() else p.parent)
