"""Kiểm tra nhanh file giao diện: các hàm được gọi phải được khai báo (tránh lỗi ReferenceError khi chạy)."""

import re
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "app" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _declared(name: str) -> bool:
    return bool(re.search(rf"(function|const|let|var)\s+{name}\b", JS))


def test_search_helpers_are_declared():
    for name in ("filterNames", "toggleName", "renderClass", "openClass"):
        assert _declared(name), f"app.js dùng {name} nhưng chưa khai báo"


def test_every_called_helper_is_declared():
    called = set(re.findall(r"\b([a-z][A-Za-z0-9]+)\(", JS))
    builtins = {"if", "for", "while", "switch", "catch", "function", "return", "matches", "esc", "api", "ask", "info",
                "form", "toast", "fetch", "setTimeout", "clearTimeout", "encodeURIComponent", "parseInt", "isNaN", "require"}
    missing = sorted(n for n in called - builtins if not _declared(n) and not re.search(rf"\.{n}\(", JS)
                     and not re.search(rf"\b{n}\s*=\s*(async\s*)?\(?", JS) and not re.search(rf"[({{,]\s*{n}\s*[,)}}=]", JS))
    assert not missing, f"Hàm được gọi nhưng chưa khai báo: {missing}"
