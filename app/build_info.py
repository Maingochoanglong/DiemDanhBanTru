"""Mã bản dựng của file .exe (máy dựng ghi vào app/_build.py). Chạy từ mã nguồn thì là "dev".

Mỗi bản .exe tải về có mã riêng: lần đầu mở một bản mới, app bắt thiết lập lại
(nơi đặt file, sổ điểm danh, danh sách học sinh) thay vì dùng lại cài đặt cũ.
"""

try:
    from ._build import BUILD  # type: ignore[import-not-found]
except ImportError:  # chạy từ mã nguồn / test
    BUILD = "dev"
