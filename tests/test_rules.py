"""Luật của app (CLAUDE.md), kiểm tra tự động:

1. App chỉ đọc / ghi 3 file trong cài đặt (CaiDat.txt, sổ điểm danh, file danh sách học sinh) và 1 sổ tạm.
   Theo dõi bằng audit hook của Python: mọi lần mở / xóa / đổi tên file, tạo thư mục, liệt kê thư mục.
2. Không viết cứng: giá trị trong app/config.py không được viết lại ở file khác (Python và JavaScript).
"""

import ast
import datetime as dt
import os
import re
import sys
from pathlib import Path

from app import config
from app.service import Workspace
from app.web.api import Api
from tests.conftest import make_workspace
from tests.test_excel import make_book

ROOT = Path(__file__).resolve().parents[1] / "app"

# ---------------------------------------------------------------- 1. chỉ 4 file
_SEEN: list | None = None  # đang theo dõi thì là danh sách (sự kiện, đường dẫn)
_EVENTS = {"open", "os.remove", "os.rename", "os.replace", "os.mkdir", "os.listdir", "os.scandir", "shutil.copyfile",
           "shutil.rmtree", "os.truncate"}


def _hook(event, args):
    if _SEEN is not None and event in _EVENTS and args and isinstance(args[0], (str, bytes, os.PathLike)):
        _SEEN.append((event, Path(os.fsdecode(args[0])).resolve()))


sys.addaudithook(_hook)  # (audit hook không gỡ được: chỉ ghi khi _SEEN đang bật)


def _watch(fn):
    global _SEEN
    _SEEN = []
    try:
        fn()
        return list(_SEEN)
    finally:
        _SEEN = None


def test_only_settings_files_and_temp_book_are_touched(tmp_path, roster):
    """Một ngày làm việc đủ việc: mở app, điểm danh, lưu, mất điện rồi khôi phục, sang tháng mới, đổi file."""
    work = tmp_path / "work"
    work.mkdir()
    ws = make_workspace(work, roster, make_book(work / "SO DIEM DANH T10.xlsx"))
    other = work / "file khac.xlsx"  # file lạ cùng thư mục: app không được đụng tới
    other.write_bytes(b"x")
    allowed = {work / "CaiDat.txt", work / "DanhSach.xlsx", work / "SO DIEM DANH T10.xlsx", work / "SO DIEM DANH T10 tamthoi.xlsx",
               work / "SO DIEM DANH T11.xlsx", work / "SO DIEM DANH T11 tamthoi.xlsx"}

    def day():
        a = Api(ws)
        a.open_day("2026-10-29", True)
        sid = next(n["id"] for n in a.class_detail("1D15")["names"])
        a.set_absent("1D15", sid, True)
        a.set_note("1D15", "ghi chú")
        a.save("keep")
        a.set_absent("1D16", next(n["id"] for n in a.class_detail("1D16")["names"]), True)  # làm dở rồi mất điện
        b = Api(Workspace(work / "CaiDat.txt"))
        b.boot()
        b.restore_temp(True)
        b.save("keep")
        b.open_day("2026-11-02", True)  # tháng mới: hỏi tạo sổ
        b.create_month_book("2026-11-02")
        b.set_absent("1D15", next(n["id"] for n in b.class_detail("1D15")["names"]), True)
        b.discard_temp()
        b.set_side_min(True)
        b.settings()
        b.choose_list(str(work / "DanhSach.xlsx"))

    seen = _watch(day)
    touched = {p for _, p in seen if p.is_relative_to(tmp_path)}
    assert touched, "audit hook không ghi được gì"
    assert touched <= {p.resolve() for p in allowed}, f"App đụng file ngoài 4 file: {sorted(map(str, touched - allowed))}"
    listed = [p for e, p in seen if e in ("os.listdir", "os.scandir") and p.is_relative_to(tmp_path)]
    assert not listed, f"App tự liệt kê thư mục (đi tìm file khác): {listed}"
    assert sorted(p.name for p in work.iterdir()) == sorted(
        ["CaiDat.txt", "DanhSach.xlsx", "SO DIEM DANH T10.xlsx", "SO DIEM DANH T11.xlsx", "file khac.xlsx"])  # sổ tạm đã xóa


# ---------------------------------------------------------------- 2. không viết cứng
_VALUES = [v for k, v in vars(config).items() if k.isupper() and isinstance(v, (str, int, float)) and not isinstance(v, bool)]
_FORBIDDEN_STR = [v for v in _VALUES if isinstance(v, str) and len(v) >= 3] + list(config.HOST_NAMES)
_FORBIDDEN_NUM = {config.DEFAULT_PORT, config.DEV_PORT}  # số đặc trưng (số nhỏ như 10 trùng ngẫu nhiên chỉ số cột…)


def _code_strings(tree):
    """Chuỗi trong mã Python, bỏ docstring (chú thích cho người đọc được nhắc tên file, cổng…)."""
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and id(n) not in docs]


def test_python_has_no_hardcoded_config_values():
    bad = []
    for p in sorted(ROOT.rglob("*.py")):
        if p.name in ("config.py", "_build.py"):
            continue
        for n in _code_strings(ast.parse(p.read_text(encoding="utf-8"))):
            v = n.value
            if isinstance(v, str) and any(f in v for f in _FORBIDDEN_STR):
                bad.append(f"{p.relative_to(ROOT)}:{n.lineno} {v!r}")
            elif type(v) in (int, float) and v in _FORBIDDEN_NUM:
                bad.append(f"{p.relative_to(ROOT)}:{n.lineno} {v!r}")
            elif type(v) is float and v not in (0.0,):
                bad.append(f"{p.relative_to(ROOT)}:{n.lineno} số {v!r} (đặt tên trong config.py)")
    assert not bad, "Giá trị viết cứng (đưa vào app/config.py):\n" + "\n".join(bad)


def test_javascript_has_no_hardcoded_config_values():
    bad = []
    for p in sorted((ROOT / "web" / "static" / "js").rglob("*.js")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            code = re.sub(r"//.*$", "", line)
            for f in _FORBIDDEN_STR + [str(v) for v in _FORBIDDEN_NUM]:
                if re.search(rf"(?<![\w.]){re.escape(f)}(?![\w.])", code):
                    bad.append(f"{p.name}:{i} {f!r}")
    assert not bad, "Giá trị viết cứng trong JavaScript (lấy từ APP_CONFIG / config.py):\n" + "\n".join(bad)


def test_school_days_from_config(monkeypatch):
    """Đổi lịch học ở config (vd. học thứ 7) thì ngày học kế tiếp đổi theo."""
    from app.service import next_school_day

    assert next_school_day(dt.date(2026, 10, 30)) == dt.date(2026, 11, 2)  # thứ 6 -> thứ 2
    monkeypatch.setattr(config, "SCHOOL_DAYS", 6)
    assert next_school_day(dt.date(2026, 10, 30)) == dt.date(2026, 10, 31)  # thứ 6 -> thứ 7
