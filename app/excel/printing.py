"""In 2 tờ bằng Microsoft Excel trên máy (Windows). Không có Excel thì mở file để in tay."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class PrintError(Exception):
    pass


def _abs_area(area: str) -> str:
    """'A1:G46' -> '$A$1:$G$46'."""
    import re

    def fix(ref: str) -> str:
        m = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", ref.strip())
        return f"${m.group(1).upper()}${m.group(2)}" if m else ref

    return ":".join(fix(p) for p in area.split(":"))


def print_areas(path: str | Path, sheet_name: str, areas: list[str], preview: bool = False) -> None:
    """In từng vùng thành 1 trang A4 ngang (vừa khít 1 trang). File không bị sửa."""
    if sys.platform != "win32":
        raise PrintError("Chỉ in trực tiếp được trên Windows có cài Microsoft Excel.")
    try:
        import pythoncom
        import win32com.client
    except ImportError as e:  # pragma: no cover - chỉ có trên Windows
        raise PrintError("Thiếu thư viện điều khiển Excel (pywin32).") from e

    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx("Excel.Application")
        xl.DisplayAlerts = False
        xl.Visible = bool(preview)
        wb = xl.Workbooks.Open(str(Path(path).resolve()), ReadOnly=True)
        ws = wb.Worksheets(sheet_name)
        ws.Activate()
        for area in areas:
            if not area:
                continue
            ps = ws.PageSetup
            ps.PrintArea = _abs_area(area)
            ps.Orientation = 2  # ngang
            ps.Zoom = False
            ps.FitToPagesWide = 1
            ps.FitToPagesTall = 1
            ps.CenterHorizontally = True
            if preview:
                ws.PrintPreview()
            else:
                ws.PrintOut()
    except Exception as e:  # noqa: BLE001 - lỗi COM rất đa dạng
        raise PrintError(f"Excel báo lỗi khi in: {e}") from e
    finally:
        try:
            if wb is not None:
                wb.Close(SaveChanges=False)
            if xl is not None:
                xl.Quit()
        finally:
            pythoncom.CoUninitialize()


def open_file(path: str | Path) -> None:
    """Mở file bằng chương trình mặc định (Excel)."""
    path = str(Path(path).resolve())
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])  # noqa: S603, S607
    else:
        subprocess.Popen(["xdg-open", path])  # noqa: S603, S607


def open_folder(path: str | Path) -> None:
    p = Path(path)
    open_file(p if p.is_dir() else p.parent)
