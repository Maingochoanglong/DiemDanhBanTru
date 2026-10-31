# Điểm danh bán trú

App Windows nhỏ gọn giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- dán tin nhắn Zalo của GVCN, app kiểm tra từng tên (có trong lớp không, có ăn bán trú không);
- ghi tên theo quy tắc, đếm số vắng;
- tự tính bảng suất ăn cho bảo mẫu, kể cả các lớp ghép;
- ghi vào sổ Excel giữ y mẫu cũ (mỗi ngày 1 sheet, mỗi tháng 1 file) và in 2 tờ.

👉 **Hướng dẫn sử dụng: [HUONG_DAN.md](HUONG_DAN.md)**

## Tải về

Trang **Releases** → bản *Điểm danh bán trú — bản mới nhất* → tải `DiemDanhBanTru.exe`. File được dựng tự động bởi GitHub Actions (`.github/workflows/build-windows.yml`) sau mỗi lần cập nhật mã.

## Chạy từ mã nguồn (cho người phát triển)

Cần Python 3.10 trở lên, có Tkinter.

```bash
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py            # mở app
python -m pytest             # chạy test
pyinstaller --onefile --windowed --name DiemDanhBanTru run_app.py   # dựng .exe (trên Windows)
```

Cấu trúc mã:

| Thư mục | Nội dung |
|---|---|
| `app/core/` | Xử lý không phụ thuộc Excel/giao diện: chuẩn hóa tên tiếng Việt, tên ghi sổ (`names.py`), đọc tin Zalo (`parser.py`), so khớp tên (`matcher.py`), một ngày điểm danh (`day.py`), suất ăn (`meals.py`), đọc ghi chú sổ (`notes.py`). |
| `app/excel/` | Đọc file CDHS (chữ đỏ), file dữ liệu của app, sổ điểm danh tháng (`sobook.py`: tìm hàng lớp và bảng suất ăn theo nội dung, sao chép sheet, ghi số liệu), sao lưu, in qua Excel. |
| `app/service.py` | Điều phối các thao tác (mở ngày, dán tin, lưu, tạo sổ tháng mới). |
| `app/ui/` | Giao diện Tkinter: tab Điểm danh, Ghép lớp, Học sinh, Cài đặt. |
| `tests/` | Test với dữ liệu giả (không chứa thông tin thật của học sinh). |

> Không đưa file Excel thật (danh sách học sinh, sổ điểm danh) lên repo. `.gitignore` đã chặn `*.xls`, `*.xlsx`.
