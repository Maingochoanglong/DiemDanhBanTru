"""Dữ liệu học sinh, lớp và các quy tắc bán trú theo ngày."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .names import compute_display_names
from .text import class_sort_key, fold


@dataclass
class Student:
    id: str
    lop: str  # lớp đang học, vd. 1D15
    ho_ten: str
    ngay_sinh: str = ""  # dd/mm/yyyy
    ban_tru: bool = False
    ten_ghi_so: str = ""  # sửa tay; để trống thì dùng tên tự sinh
    lop_bt: str = ""  # lớp tính bán trú khi khác lớp học
    an_ghep: str = ""  # mã nhóm ăn ghép, vd. 1.2
    cat_thu6: bool = False
    bt_tu: dt.date | None = None  # bắt đầu ăn bán trú từ ngày
    cat_tu: dt.date | None = None  # cắt bán trú từ ngày (ngày này không ăn)
    ghi_chu: str = ""

    @property
    def lop_tinh(self) -> str:
        """Lớp dùng để tính sĩ số bán trú."""
        return self.lop_bt or self.lop

    def is_boarding(self, day: dt.date | None = None) -> bool:
        if not self.ban_tru:
            return False
        if day is None:
            return True
        if self.bt_tu and day < self.bt_tu:
            return False
        if self.cat_tu and day >= self.cat_tu:
            return False
        return True

    def auto_absent_reason(self, day: dt.date) -> str:
        """Lý do vắng tự động trong ngày, '' nếu không có."""
        if self.cat_thu6 and day.weekday() == 4:
            return "cắt thứ 6"
        return ""

    def key(self) -> tuple[str, str]:
        return fold(self.ho_ten), self.ngay_sinh


@dataclass
class ClassInfo:
    code: str  # 1D15
    gvcn: str = ""
    ma_ngan: str = ""  # 1.1

    @property
    def khoi(self) -> int:
        return int(self.code[0])


@dataclass
class Roster:
    students: list[Student] = field(default_factory=list)
    classes: dict[str, ClassInfo] = field(default_factory=dict)
    _display: dict[str, str] | None = field(default=None, repr=False)

    # ----- truy vấn -----
    def invalidate(self) -> None:
        self._display = None

    def class_codes(self) -> list[str]:
        codes = set(self.classes) | {s.lop_tinh for s in self.students if s.ban_tru}
        return sorted((c for c in codes if c), key=class_sort_key)

    def by_id(self, sid: str) -> Student | None:
        for s in self.students:
            if s.id == sid:
                return s
        return None

    def boarding(self, code: str, day: dt.date | None = None) -> list[Student]:
        """Các em ăn bán trú tính vào lớp `code` trong ngày `day`."""
        return [s for s in self.students if s.lop_tinh == code and s.is_boarding(day)]

    def in_class(self, code: str) -> list[Student]:
        """Mọi em liên quan tới lớp: học ở lớp đó hoặc tính bán trú vào lớp đó."""
        return [s for s in self.students if s.lop == code or s.lop_tinh == code]

    def si_so(self, code: str, day: dt.date | None = None) -> int:
        return len(self.boarding(code, day))

    def display_name(self, s: Student) -> str:
        if s.ten_ghi_so:
            return s.ten_ghi_so
        if self._display is None:
            self._display = self._compute_display()
        return self._display.get(s.id, s.ho_ten)

    def _compute_display(self) -> dict[str, str]:
        out: dict[str, str] = {}
        groups: dict[str, list[Student]] = {}
        for s in self.students:
            if s.ban_tru:
                groups.setdefault(s.lop_tinh, []).append(s)
        for members in groups.values():
            out.update(compute_display_names([(s.id, s.ho_ten, s.ngay_sinh) for s in members]))
        return out

    def sort_like_roster(self, items: list[Student]) -> list[Student]:
        """Sắp theo thứ tự trong danh sách trường (thứ tự lúc nhập)."""
        pos = {s.id: i for i, s in enumerate(self.students)}
        return sorted(items, key=lambda s: pos.get(s.id, 10**9))

    def ghep_codes(self) -> dict[str, list[Student]]:
        out: dict[str, list[Student]] = {}
        for s in self.students:
            if s.ban_tru and s.an_ghep:
                out.setdefault(s.an_ghep, []).append(s)
        return out

    def next_id(self) -> str:
        n = 0
        for s in self.students:
            if s.id.startswith("HS") and s.id[2:].isdigit():
                n = max(n, int(s.id[2:]))
        return f"HS{n + 1:04d}"
