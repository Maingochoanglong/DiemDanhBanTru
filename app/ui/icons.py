"""Icon ảnh (vẽ từ vector Tabler Icons) thay cho icon dạng ký tự.

`icon("st_ok")` trả về PhotoImage đúng cỡ chữ của máy (màn 125–150% tự dùng cỡ lớn hơn).
Ảnh được giữ trong bộ nhớ để Tk không xóa mất.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from .icons_data import ICONS

_cache: dict[tuple[str, int], tk.PhotoImage] = {}
_base: list[int] = []


def base_size() -> int:
    """Cỡ icon hợp với chữ: gần bằng chiều cao dòng chữ."""
    if not _base:
        try:
            line = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        except tk.TclError:
            line = 17
        sizes = sorted(next(iter(ICONS.values())))
        _base.append(min(sizes, key=lambda s: abs(s - line * 0.95)))
    return _base[0]


def icon(name: str, size: int | None = None) -> tk.PhotoImage:
    sizes = ICONS[name]
    want = size or base_size()
    s = want if want in sizes else min(sizes, key=lambda x: abs(x - want))
    key = (name, s)
    if key not in _cache:
        _cache[key] = tk.PhotoImage(data=sizes[s], format="png")
    return _cache[key]


def bigger() -> int:
    """Cỡ lớn hơn 1 bậc (cho nút chính, dòng tổng)."""
    sizes = sorted(next(iter(ICONS.values())))
    b = base_size()
    return next((s for s in sizes if s > b), b)


def set_app_icon(root: tk.Tk) -> None:
    try:
        root.iconphoto(True, *(icon("app", s) for s in (64, 48, 32, 16)))
    except tk.TclError:
        pass


def reset() -> None:
    """Dùng khi tạo lại cửa sổ Tk (vd. trong test)."""
    _cache.clear()
    _base.clear()


# Kết quả kiểm tra tên (matcher) -> icon
RESULT_ICON = {
    "ok": "res_ok",
    "ambiguous": "res_ambiguous",
    "not_bt": "res_not_bt",
    "other_class": "res_err",
    "not_found": "res_err",
}
# Trạng thái lớp (mức màu) -> icon
STATUS_ICON = {"muted": "st_none", "ok": "st_ok", "warn": "st_absent", "err": "st_err"}
