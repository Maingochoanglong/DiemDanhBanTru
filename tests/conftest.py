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


def write_list(path, roster: Roster, groups=None):
    """Ghi danh sách học sinh ra file Excel như file giáo vụ dùng (cột Ghi chú theo cách app đọc: core/notes.py).
    groups: các dòng sheet Nhóm ăn [(tên dòng, các lớp, mã ghép lẻ)]."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Lớp", "Họ tên", "Ngày sinh", "Bán trú", "Tên gọi khác", "Ăn ghép", "Ghi chú"])
    for s in roster.students:
        notes = ["cắt thứ 6"] if s.cat_thu6 else []
        if s.cat_tu:
            notes.append(f"cắt từ {s.cat_tu:%d/%m/%Y}")
        if s.bt_tu:
            notes.append(f"ăn từ {s.bt_tu:%d/%m/%Y}")
        bt = s.ban_tru and not s.bt_tu  # "ăn từ …" tự bật bán trú
        ws.append([s.lop, s.ho_ten, s.ngay_sinh, "Có" if bt else "Không", s.ten_ghi_so, s.an_ghep, ", ".join(notes + [s.ghi_chu])])
    if groups is not None:
        g = wb.create_sheet("Nhóm ăn")
        g.append(["Tên dòng", "Các lớp ăn chung", "Mã ghép lẻ"])
        for row in groups:
            g.append(list(row))
    wb.save(path)
    return path


def make_workspace(tmp_path, roster: Roster, book=None, groups=None):
    """Workspace dùng đúng 3 file: CaiDat.txt, file danh sách học sinh, sổ điểm danh."""
    from app.service import Workspace

    ws = Workspace(tmp_path / "CaiDat.txt")
    ws.set_list(write_list(tmp_path / "DanhSach.xlsx", roster, groups))
    if book is not None:
        ws.set_book(book)
    return ws
