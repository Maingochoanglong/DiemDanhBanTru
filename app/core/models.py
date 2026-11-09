"""Dữ liệu học sinh, lớp và các quy tắc bán trú theo ngày."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from .names import compute_display_names
from .text import class_sort_key, clean_spaces, fold


@dataclass
class Student:
    id: str
    lop: str  # lớp đang học, vd. 1D15
    ho_ten: str
    ngay_sinh: str = ""  # dd/mm/yyyy
    ban_tru: bool = False
    ten_ghi_so: str = ""  # tên gọi khác (vd. "Mi Mi"), cách nhau dấu phẩy; tên đầu ghi vào sổ. Trống = tên tự sinh
    lop_bt: str = ""  # lớp tính bán trú khi khác lớp học
    an_ghep: str = ""  # mã nhóm ăn ghép, vd. 1.2
    cat_thu6: bool = False
    bt_tu: dt.date | None = None  # bắt đầu ăn bán trú từ ngày
    cat_tu: dt.date | None = None  # cắt bán trú từ ngày (ngày này không ăn)
    ghi_chu: str = ""

    def aliases(self) -> list[str]:
        """Các tên gọi khác (GV hay báo bằng tên này)."""
        return [clean_spaces(x) for x in re.split(r"[,;]", self.ten_ghi_so) if clean_spaces(x)]

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
    _by_class: dict[str, list[Student]] | None = field(default=None, repr=False, compare=False)
    _by_id: dict[str, Student] | None = field(default=None, repr=False, compare=False)
    _n: int = field(default=-1, repr=False, compare=False)

    # ----- truy vấn -----
    def invalidate(self) -> None:
        """Gọi sau khi thêm/bớt em hoặc đổi lớp của em (các bảng tra nhanh được dựng lại)."""
        self._display = None
        self._by_class = self._by_id = None

    def _index(self) -> dict[str, list[Student]]:
        """Bảng tra em theo lớp tính bán trú (dựng 1 lần; thêm/bớt em thì tự dựng lại)."""
        if self._by_class is None or self._n != len(self.students):
            idx: dict[str, list[Student]] = {}
            for s in self.students:
                idx.setdefault(s.lop_tinh, []).append(s)
            self._by_class, self._by_id, self._n = idx, {s.id: s for s in self.students}, len(self.students)
        return self._by_class

    def class_codes(self) -> list[str]:
        codes = set(self.classes) | {s.lop_tinh for s in self.students if s.ban_tru}
        return sorted((c for c in codes if c), key=class_sort_key)

    def by_id(self, sid: str) -> Student | None:
        self._index()
        s = self._by_id.get(sid) if self._by_id is not None else None
        return s if s is not None and s.id == sid else next((x for x in self.students if x.id == sid), None)

    def boarding(self, code: str, day: dt.date | None = None) -> list[Student]:
        """Các em ăn bán trú tính vào lớp `code` trong ngày `day`."""
        return [s for s in self._index().get(code, ()) if s.lop_tinh == code and s.is_boarding(day)]

    def in_class(self, code: str) -> list[Student]:
        """Mọi em liên quan tới lớp: học ở lớp đó hoặc tính bán trú vào lớp đó."""
        return [s for s in self.students if s.lop == code or s.lop_tinh == code]

    def si_so(self, code: str, day: dt.date | None = None) -> int:
        return len(self.boarding(code, day))

    def display_name(self, s: Student) -> str:
        if s.ten_ghi_so:
            return s.aliases()[0] if s.aliases() else s.ten_ghi_so
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
