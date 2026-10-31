"""Icon ảnh: mọi tên icon giao diện dùng đều có dữ liệu PNG hợp lệ."""

import base64
import re
from pathlib import Path

from app.ui.icons_data import ICONS

PNG = b"\x89PNG\r\n\x1a\n"


def test_icon_data_is_png():
    for name, sizes in ICONS.items():
        assert sizes, name
        for s, data in sizes.items():
            raw = base64.b64decode(data)
            assert raw.startswith(PNG), (name, s)
            w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
            assert (w, h) == (s, s), (name, s, w, h)


def test_every_icon_used_in_ui_exists():
    ui = Path(__file__).resolve().parents[1] / "app" / "ui"
    used = set()
    for f in ui.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        used |= set(re.findall(r"""icon\(\s*["']([a-z_]+)["']""", text))
        # tên icon truyền cho hộp hỏi: ask(..., image="st_err"), ChoiceDialog(..., image="...")
        used |= set(re.findall(r"""\bimage(?::\s*str(?:\s*\|\s*None)?)?\s*=\s*["']([a-z_]+)["']""", text))
    # bảng tên icon trong app/ui/icons.py (đọc bằng ast để không cần tkinter khi chạy test)
    import ast

    tree = ast.parse((ui / "icons.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            used |= {v.value for v in node.value.values if isinstance(v, ast.Constant)}
    assert used, "không thấy chỗ nào dùng icon"
    assert used <= set(ICONS), used - set(ICONS)
