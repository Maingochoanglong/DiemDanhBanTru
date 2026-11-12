"""Làm việc với file: ghi Excel an toàn (ghi ra file phụ rồi thay thế, báo khi file đang mở), mở file / thư mục."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class FileLockedError(Exception):
    """File đang mở trong Excel nên không ghi được."""


def is_locked(path: str | Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    if path.with_name("~$" + path.name).exists():  # file khóa Excel tạo khi đang mở
        return True
    try:
        with open(path, "r+b"):
            pass
    except PermissionError:
        return True
    except OSError:
        return False
    return False


def safe_save(wb, path: str | Path) -> None:
    path = Path(path)
    if is_locked(path):
        raise FileLockedError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.ghi{path.suffix}")
    wb.save(str(tmp))
    try:
        os.replace(tmp, path)
    except PermissionError as e:
        tmp.unlink(missing_ok=True)
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
