"""Ghi file an toàn: sao lưu trước khi ghi, báo khi file đang mở trong Excel."""

from __future__ import annotations

import datetime as dt
import os
import shutil
from pathlib import Path

KEEP_BACKUPS = 30


class FileLockedError(Exception):
    """File đang mở trong Excel nên không ghi được."""


def lock_file(path: Path) -> Path:
    return path.with_name("~$" + path.name)


def is_locked(path: str | Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    if lock_file(path).exists():
        return True
    try:
        with open(path, "r+b"):
            pass
    except PermissionError:
        return True
    except OSError:
        return False
    return False


def backup(path: str | Path, folder: str | Path | None = None, keep: int = KEEP_BACKUPS) -> Path | None:
    path = Path(path)
    if not path.exists():
        return None
    folder = Path(folder) if folder else path.parent / "SaoLuu"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = folder / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    old = sorted(folder.glob(f"{path.stem}_*{path.suffix}"))
    for f in old[:-keep]:
        try:
            f.unlink()
        except OSError:
            pass
    return dest


def safe_save(wb, path: str | Path, backup_dir: str | Path | None = None) -> None:
    """Sao lưu bản cũ, ghi ra file tạm rồi thay thế (không làm hỏng file nếu lỗi giữa chừng)."""
    path = Path(path)
    if is_locked(path):
        raise FileLockedError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path, backup_dir)
    tmp = path.with_name(f".{path.stem}.tmp{path.suffix}")
    wb.save(str(tmp))
    try:
        os.replace(tmp, path)
    except PermissionError as e:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise FileLockedError(str(path)) from e
