"""Dán nguyên tin Zalo của GVCN vào ô tìm của bảng chọn tên (USER_STORIES H2): app nhặt đúng tên các em.

Chạy hàm namesIn / searchTerms của giao diện (static/js/util.js) bằng Node; máy không có Node thì bỏ qua.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import config

UTIL = Path(__file__).resolve().parents[1] / "app" / "web" / "static" / "js" / "util.js"
CLASS = ["Kha Bảo Ngọc Bé Na", "Võ Hoàng Bảo Ngọc", "Lâm Quốc Tuấn Anh", "Hồ Khánh Ngọc", "Tô Minh Khôi", "Mạc Trần Quỳnh Anh"]


def found(tmp_path, message: str) -> list[str]:
    script = tmp_path / "t.mjs"
    script.write_text(
        f'import {{ namesIn, searchTerms }} from {json.dumps(UTIL.as_uri())};\n'
        f'console.log(JSON.stringify(searchTerms({json.dumps(message)}).flatMap(t => namesIn(t, {json.dumps(CLASS)}, {config.UI["name_words_max"]}))));\n',
        encoding="utf-8")
    out = subprocess.run(["node", str(script)], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(out)


pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="máy không có Node")


@pytest.mark.parametrize(("message", "names"), [
    ("Tuấn Anh, Khánh Ngọc", ["Tuấn Anh", "Khánh Ngọc"]),
    ("tua", ["tua"]),  # đang gõ dở: giữ nguyên để lọc như cũ
    ("1D15 vắng Tuấn Anh, Khánh Ngọc", ["Tuấn Anh", "Khánh Ngọc"]),
    ("Lớp 1D15 hôm nay vắng 2 bạn: Tuấn Anh và Khánh Ngọc ạ", ["Tuấn Anh", "Khánh Ngọc"]),
    ("Cô ơi lớp 1/1 nghỉ bé Minh Khôi (bệnh) ạ", ["Minh Khôi"]),
    ("1D15 vắng Tuấn Anh Khánh Ngọc Quỳnh Anh", ["Tuấn Anh", "Khánh Ngọc", "Quỳnh Anh"]),  # không có dấu phẩy
    ("Báo cơm 1D15: vắng 1 - Tuấn Anh", ["Tuấn Anh"]),  # "Báo" không phải "Bảo"
    ("1D15 vắng Tuấn Anh, Khán Ngọc", ["Tuấn Anh", "Khán Ngọc"]),  # tên gõ sai vẫn hiện để giáo vụ xem
    ("1D15 đủ ạ", []),  # lời nhắn không có tên: bỏ qua
    ("Cô ơi lớp 1D15 hôm nay vắng:\nbé Tuấn Anh", ["Tuấn Anh"]),  # dòng chào đầu tin bỏ qua
    ("Khán Ngọc", ["Khán Ngọc"]),  # tên gõ tay không khớp ai: vẫn hiện để giáo vụ xem lại
])
def test_names_picked_from_zalo_message(tmp_path, message, names):
    assert found(tmp_path, message) == names
