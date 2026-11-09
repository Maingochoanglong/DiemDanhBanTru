"""Tạo file thông tin phiên bản cho DiemDanhBanTru.exe (tên app, phiên bản, mô tả).

File .exe có thông tin này (Chuột phải → Properties → Details) thì Windows Defender
và phần mềm diệt virus ít nhận nhầm hơn. Chạy: python packaging/make_version_file.py <file ra>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import __version__  # noqa: E402

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('042a04b0', [
      StringStruct('CompanyName', 'DiemDanhBanTru'),
      StringStruct('FileDescription', 'Điểm danh bán trú'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'DiemDanhBanTru'),
      StringStruct('LegalCopyright', 'Điểm danh bán trú'),
      StringStruct('OriginalFilename', 'DiemDanhBanTru.exe'),
      StringStruct('ProductName', 'Điểm danh bán trú'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [0x042a, 1200])])
  ]
)
"""


def main(out: str) -> None:
    parts = [int(x) for x in __version__.split(".")][:4]
    parts += [0] * (4 - len(parts))
    Path(out).write_text(TEMPLATE.format(t=tuple(parts), v=__version__), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "version_info.txt")
