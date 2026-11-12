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

Cần Python 3.10 trở lên. App mở giao diện trong **trình duyệt** (Edge/Chrome) ở `http://127.0.0.1:47615` (chỉ nhận kết nối từ chính máy này). App tự thoát khi đóng thẻ trình duyệt cuối cùng hoặc bấm *Thoát*; mở app lần nữa khi đang chạy thì chỉ mở thêm thẻ.

| Phần | Framework |
|---|---|
| Máy chủ (Python) | [FastAPI](https://fastapi.tiangolo.com) chạy bằng [uvicorn](https://www.uvicorn.org) |
| Giao diện | [Vue 3](https://vuejs.org) + [PrimeVue 4](https://primevue.org) (theme Aura) + PrimeIcons — bản dựng sẵn đóng kèm trong `static/vendor/`, **không cần Node.js / bước build**, chạy không cần mạng |

PrimeVue giữ ở bản 4 (giấy phép MIT); từ bản 5 PrimeVue đổi sang giấy phép thương mại có điều kiện.

```bash
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py            # mở app trong trình duyệt
python run_app.py --no-open  # chạy máy chủ, không tự mở trình duyệt (tự vào http://127.0.0.1:47615)
python -m app.web.server    # máy chủ thử: mở http://127.0.0.1:8765 để xem/chụp giao diện, tài liệu API ở /docs
python -m pytest             # chạy test
pyinstaller --onefile --windowed --name DiemDanhBanTru --add-data "app/web/static;app/web/static" run_app.py   # dựng .exe (trên Windows)
```

Cấu trúc mã:

| Thư mục | Nội dung |
|---|---|
| `app/core/` | Xử lý không phụ thuộc Excel/giao diện: chuẩn hóa tên tiếng Việt, tên ghi sổ (`names.py`), tách tên trong ô sổ / ghi chú (`parser.py`), so khớp tên (`matcher.py`), một ngày điểm danh (`day.py`), suất ăn (`meals.py`), đọc ghi chú sổ (`notes.py`). |
| `app/excel/` | Đọc file danh sách học sinh (chữ đỏ hoặc cột Bán trú), file dữ liệu của app, sổ điểm danh tháng (`sobook.py`: tìm hàng lớp và bảng suất ăn theo nội dung, sao chép sheet, ghi số liệu, dựng lại bảng suất ăn theo bảng Nhóm ăn), sổ tạm tự lưu `… tamthoi.xlsx` (`tamthoi.py`), sao lưu, in qua Excel. |
| `app/service.py` | Điều phối các thao tác (mở ngày, dán tin, lưu, tạo sổ tháng mới). |
| `app/web/` | `api.py` (các hàm giao diện gọi: mở ngày, chọn em vắng, lưu sổ…), `server.py` (máy chủ FastAPI: trả giao diện, nhận lời gọi `POST /api/<tên hàm>`), `run.py` (mở trình duyệt, hộp chọn file của Windows, tự thoát khi đóng thẻ), `static/` (giao diện: `index.html`, `app.css`, `js/main.js` khởi động Vue + PrimeVue, `js/store.js` trạng thái và thao tác chung, `js/components/` mỗi trang / hộp thoại một file, `vendor/` thư viện đóng kèm). |
| `tests/` | Test với dữ liệu giả (không chứa thông tin thật của học sinh). |

> Không đưa file Excel thật (danh sách học sinh, sổ điểm danh) lên repo. `.gitignore` đã chặn `*.xls`, `*.xlsx`.
