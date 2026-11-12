# Điểm danh bán trú

App Windows nhỏ gọn giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- bấm vào lớp, tìm hoặc dán tên GV báo rồi bấm chọn từng em vắng (chỉ hiện các em ăn bán trú của lớp);
- ghi tên theo quy tắc, đếm số vắng;
- tự tính bảng suất ăn cho bảo mẫu, kể cả các lớp ghép; bảng suất ăn của tờ ngày mới dựng theo sheet *Nhóm ăn* trong file danh sách (đổi cách ghép không phải sửa công thức sổ);
- ghi vào sổ Excel giữ y mẫu cũ (mỗi ngày 1 sheet, mỗi tháng 1 file) (in bằng Excel như thường lệ).

👉 **Hướng dẫn sử dụng: [HUONG_DAN.md](HUONG_DAN.md)**

## Tải về

👉 **[Tải DiemDanhBanTru.exe](https://github.com/Maingochoanglong/DiemDanhBanTru/raw/main/tai-ve/DiemDanhBanTru.exe)** (thư mục [`tai-ve`](tai-ve) của repo).

File được GitHub Actions (`.github/workflows/build-windows.yml`) dựng trên Windows và tự commit vào `tai-ve/` mỗi khi nhánh `main` có mã mới. Cũng có ở trang **Releases** → bản *Điểm danh bán trú — bản mới nhất*. Mỗi lần cập nhật, repo nặng thêm khoảng 17 MB (dung lượng file `.exe`).

## Chạy từ mã nguồn (cho người phát triển)

Cần Python 3.10 trở lên. Giao diện là trang web (HTML + Bootstrap 5) mở trong **trình duyệt** (Edge/Chrome) qua máy chủ nội bộ `http://127.0.0.1:47615` (chỉ nhận kết nối từ chính máy này). App tự thoát khi đóng thẻ trình duyệt cuối cùng hoặc bấm *Thoát*; mở app lần nữa khi đang chạy thì chỉ mở thêm thẻ. Vẫn có thể mở trong cửa sổ app riêng nhờ pywebview (Microsoft Edge WebView2) bằng `--app`.

```bash
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py            # mở app trong trình duyệt
python run_app.py --no-open  # chạy máy chủ, không tự mở trình duyệt (tự vào http://127.0.0.1:47615)
python run_app.py --app      # mở trong cửa sổ app riêng (pywebview)
python -m app.web.devserver  # máy chủ thử: mở http://127.0.0.1:8765/index.html để xem/chụp giao diện
python -m pytest             # chạy test
pyinstaller --onefile --windowed --name DiemDanhBanTru --add-data "app/web/static;app/web/static" run_app.py   # dựng .exe (trên Windows)
```

Cấu trúc mã:

| Thư mục | Nội dung |
|---|---|
| `app/core/` | Xử lý không phụ thuộc Excel/giao diện: chuẩn hóa tên tiếng Việt, tên ghi sổ (`names.py`), tách tên trong ô sổ / ghi chú (`parser.py`), so khớp tên (`matcher.py`), một ngày điểm danh (`day.py`), suất ăn (`meals.py`), đọc ghi chú sổ (`notes.py`). |
| `app/excel/` | Đọc file danh sách học sinh (chữ đỏ hoặc cột Bán trú), file dữ liệu của app, sổ điểm danh tháng (`sobook.py`: tìm hàng lớp và bảng suất ăn theo nội dung, sao chép sheet, ghi số liệu, dựng lại bảng suất ăn theo bảng Nhóm ăn), sổ tạm tự lưu `… tamthoi.xlsx` (`tamthoi.py`), sao lưu, in qua Excel. |
| `app/service.py` | Điều phối các thao tác (mở ngày, dán tin, lưu, tạo sổ tháng mới). |
| `app/web/` | Giao diện web: `api.py` (cầu nối giao diện ↔ xử lý sổ), `static/` (HTML, JavaScript, Bootstrap 5 + Bootstrap Icons đóng kèm, chạy không cần mạng), `devserver.py` (máy chủ nội bộ 127.0.0.1: phục vụ giao diện, nhận lời gọi `/api/…`), `run.py` (mở trình duyệt, hộp chọn file, tự thoát khi đóng thẻ; hoặc cửa sổ pywebview với `--app`). |
| `tests/` | Test với dữ liệu giả (không chứa thông tin thật của học sinh). |

> Không đưa file Excel thật (danh sách học sinh, sổ điểm danh) lên repo. `.gitignore` đã chặn `*.xls`, `*.xlsx`.
