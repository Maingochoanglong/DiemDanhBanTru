"""Kiểm tra nhanh giao diện (static/): file được nạp có thật, import đúng, lời gọi Python có thật, thành phần đã đăng ký."""

import inspect
import re
from pathlib import Path

from app.web.api import Api
from app.web.run import BrowserApi

STATIC = Path(__file__).resolve().parents[1] / "app" / "web" / "static"
JS = {p: p.read_text(encoding="utf-8") for p in (STATIC / "js").rglob("*.js")}
ALL = "\n".join(JS.values())


def test_index_loads_existing_files():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    missing = [r for r in refs if r != "config.js" and not (STATIC / r).exists()]  # config.js do máy chủ trả về
    assert refs and not missing, f"index.html nạp file không có: {missing}"


def test_imports_resolve_and_names_are_exported():
    for path, src in JS.items():
        for names, target in re.findall(r'import\s+(.+?)\s+from\s+"(\.[^"]+)"', src):
            dep = (path.parent / target).resolve()
            assert dep.exists(), f"{path.name}: import {target} không có"
            dsrc = JS[dep]
            if names.startswith("{"):
                for n in re.findall(r"\w+", names):
                    assert re.search(rf"export\s+(async\s+)?(function|const|let)\s+{n}\b", dsrc), f"{path.name}: {dep.name} không có {n}"
            else:
                assert "export default" in dsrc, f"{path.name}: {dep.name} không có export default"


def test_ui_calls_only_existing_python_functions():
    called = set(re.findall(r'api\("([a-z_]+)"', ALL))
    methods = {n for n, _ in inspect.getmembers(BrowserApi, inspect.isfunction) if not n.startswith("_")}
    assert called - methods == set(), f"Giao diện gọi hàm Python không có: {called - methods}"
    unused = {n for n, _ in inspect.getmembers(Api, inspect.isfunction) if not n.startswith("_")} - called - {"state"}
    assert not unused, f"Hàm Python không còn ai gọi (code thừa?): {unused}"


def test_components_used_in_templates_are_registered():
    main = JS[STATIC / "js" / "main.js"]
    registered = set(re.findall(r'"([A-Z]\w+)"', main.split("for (const name of", 1)[1].split("]", 1)[0]))
    for path, src in JS.items():
        local = set(re.findall(r"components:\s*\{([^}]*)\}", src) and re.findall(r"\w+", re.findall(r"components:\s*\{([^}]*)\}", src)[0]))
        used = set(re.findall(r"<([A-Z]\w+)", src)) - {"KeepAlive"}
        missing = used - registered - local
        assert not missing, f"{path.name} dùng thành phần chưa đăng ký: {missing}"
