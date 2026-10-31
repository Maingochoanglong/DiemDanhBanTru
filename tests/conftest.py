"""Dữ liệu giả cho test. Tên học sinh/giáo viên là tên bịa, chỉ giữ cấu trúc giống thật."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import ClassInfo, Roster, Student  # noqa: E402

# (lớp, họ tên, ngày sinh, bán trú)
FAKE = [
    ("1D15", "Kha Bảo Ngọc", "02/03/2020", True),
    ("1D15", "Võ Hoàng Bảo Ngọc", "05/06/2020", True),
    ("1D15", "Đặng Bảo Ngọc", "07/08/2020", True),
    ("1D15", "Lâm Quốc Tuấn Anh", "09/10/2020", True),
    ("1D15", "Hồ Khánh Ngọc", "11/12/2020", True),
    ("1D15", "Mạc Trần Quỳnh Anh", "01/01/2020", False),
    ("1D15", "Tô Minh Khôi", "03/03/2020", True),
    ("1D16", "Lý Gia Hưng", "24/04/2020", True),
    ("1D16", "Lý Gia Hưng", "13/03/2020", True),
    ("1D16", "Kiều Thanh Vy", "15/05/2020", True),
    ("1D16", "Ông Minh Thư", "16/06/2020", True),
    ("1D16", "Âu Ngọc Khuê", "17/07/2020", True),
    ("1D16", "Doãn Thanh Vy", "18/08/2020", False),
    ("1D19", "Châu Bảo Ngọc", "01/02/2020", True),
    ("1D19", "Phùng Gia Hân", "02/02/2020", True),
    ("1D19", "Tạ Đức Anh", "03/02/2020", True),
    ("1D19", "Quách Minh Khang", "04/02/2020", True),
    ("2D17", "Viên Duy Mạnh", "01/01/2019", True),
    ("2D17", "Giang Tuấn Kiệt", "02/01/2019", True),
    ("2D17", "Khổng Hải Long", "03/01/2019", True),
    ("2D17", "Mai Phương Thanh", "04/01/2019", True),
    ("4D21", "Ninh Vũ Khoa", "01/01/2017", True),
    ("4D21", "La Thảo Vy", "02/01/2017", True),
    ("4D21", "Ung Khải Minh", "03/01/2017", True),
    ("4D19", "Lục Thảo Mi", "04/01/2017", True),
    ("4D19", "Bế Hoài Nam", "05/01/2017", True),
]


def make_roster() -> Roster:
    r = Roster()
    for i, (lop, name, dob, bt) in enumerate(FAKE, 1):
        r.students.append(Student(id=f"HS{i:04d}", lop=lop, ho_ten=name, ngay_sinh=dob, ban_tru=bt))
    for code in sorted({x[0] for x in FAKE}):
        r.classes[code] = ClassInfo(code)
    return r


@pytest.fixture
def roster() -> Roster:
    return make_roster()
