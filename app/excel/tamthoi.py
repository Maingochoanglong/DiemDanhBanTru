"""Sổ tạm: bản sao sổ điểm danh tự lưu sau mỗi thao tác, phòng mất điện / tắt máy đột ngột.

Tên file = tên sổ đang dùng + " tamthoi" (vd. "SO DIEM DANH T10 tamthoi.xlsx"), nằm cạnh sổ chính.
- Sheet của ngày đang làm được ghi như khi bấm Lưu vào sổ (mở bằng Excel xem được ngay).
- Sheet ẩn TAMTHOI ghi lại đủ thao tác của ngày đó để app khôi phục chính xác.
Bấm Lưu vào sổ thì app ghi sổ chính rồi xóa sổ tạm.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from ..core.text import fmt_date, parse_date
from .files import FileLockedError, is_locked

SHEET = "TAMTHOI"
TAG = "tamthoi"
COLS = ["Lớp", "Đã báo", "Vắng (mã HS)", "Tên ghi tay", "Bỏ vắng tự động (mã HS)", "Ghi chú",
        "Sĩ số trong sổ", "Giữ sĩ số sổ", "GV báo hiện diện", "GV báo sĩ số", "Tên không ăn BT"]
SEP = "; "


def temp_path(book: str | Path) -> Path:
    book = Path(book)
    return book.with_name(f"{book.stem} {TAG}{book.suffix}")


def is_temp(path: str | Path) -> bool:
    return Path(path).stem.lower().endswith(TAG)


def _join(items) -> str:
    return SEP.join(str(x) for x in items)


def _split(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(";") if x.strip()]


def _int(v) -> int | None:
    return int(v) if isinstance(v, (int, float)) else None


def write_state_sheet(wb, state, book: str | Path, now: dt.datetime | None = None) -> None:
    """Thêm sheet ẩn TAMTHOI ghi trạng thái ngày đang làm vào sổ (bản trong bộ nhớ)."""
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    ws = wb.create_sheet(SHEET)
    ws.sheet_state = "hidden"
    now = now or dt.datetime.now()
    ws.append(["Ngày", fmt_date(state.date), "Sổ chính", str(book), "Lưu lúc", now.strftime("%d/%m/%Y %H:%M:%S")])
    ws.append(COLS)
    for code, c in state.classes.items():
        ws.append([code, "x" if c.reported else "", _join(c.manual), _join(c.extra), _join(sorted(c.auto_off)),
                   c.note, c.sheet_si_so, "x" if c.keep_sheet_si_so else "", c.teacher_present, c.teacher_total,
                   _join(c.not_bt)])
    ws.append([])
    ws.append(["Nhóm ghép", "Số vắng nhập tay"])
    for k, v in state.manual_m.items():
        ws.append([k, v])


def save(wb, path: str | Path) -> None:
    """Ghi sổ tạm (ghi ra file phụ rồi thay thế, không sao lưu bản cũ)."""
    path = Path(path)
    if is_locked(path):
        raise FileLockedError(str(path))
    tmp = path.with_name(f".{path.stem}.ghi{path.suffix}")
    wb.save(str(tmp))
    os.replace(tmp, path)


@dataclass
class TempInfo:
    path: Path
    day: dt.date
    book: Path
    saved_at: str
    classes: dict[str, dict] = field(default_factory=dict)
    manual_m: dict[str, int] = field(default_factory=dict)


def read(path: str | Path) -> TempInfo | None:
    """Đọc sheet TAMTHOI. File hỏng / không đúng mẫu thì trả về None."""
    path = Path(path)
    try:
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        if SHEET not in wb.sheetnames:
            return None
        rows = list(wb[SHEET].iter_rows(values_only=True))
        wb.close()
    except Exception:  # noqa: BLE001
        return None
    if len(rows) < 2 or not rows[0] or len(rows[0]) < 6:
        return None
    day = parse_date(rows[0][1])
    if day is None:
        return None
    info = TempInfo(path, day, Path(str(rows[0][3] or "")), str(rows[0][5] or ""))
    i = 2
    while i < len(rows) and rows[i] and rows[i][0]:
        r = list(rows[i]) + [None] * len(COLS)
        info.classes[str(r[0])] = {
            "reported": str(r[1] or "").strip().lower() == "x", "manual": _split(r[2]), "extra": _split(r[3]),
            "auto_off": set(_split(r[4])), "note": str(r[5] or ""), "sheet_si_so": _int(r[6]),
            "keep_sheet_si_so": str(r[7] or "").strip().lower() == "x", "teacher_present": _int(r[8]),
            "teacher_total": _int(r[9]), "not_bt": _split(r[10]),
        }
        i += 1
    for r in rows[i + 2:]:
        if r and r[0] and _int(r[1]) is not None:
            info.manual_m[str(r[0])] = _int(r[1])
    return info


def apply(info: TempInfo, state) -> None:
    """Đưa thao tác đã lưu tạm vào ngày vừa mở lại (bỏ mã HS không còn trong danh sách)."""
    for code, d in info.classes.items():
        c = state.cd(code)
        for k, v in d.items():
            if k in ("manual", "auto_off"):
                v = type(v)(sid for sid in v if state.roster.by_id(sid))
            setattr(c, k, v)
    state.manual_m = dict(info.manual_m)
    state.pending = []
