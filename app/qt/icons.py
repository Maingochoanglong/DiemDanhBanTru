"""Icon (Tabler, PNG nhúng sẵn trong app/ui/icons_data.py) dùng cho Qt."""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

from ..ui.icons_data import ICONS

_cache: dict[str, QIcon] = {}


def qicon(name: str) -> QIcon:
    if name not in _cache:
        ic = QIcon()
        for _size, data in sorted(ICONS.get(name, {}).items()):
            pm = QPixmap()
            pm.loadFromData(QByteArray.fromBase64(data.encode()), "PNG")
            ic.addPixmap(pm)
        _cache[name] = ic
    return _cache[name]
