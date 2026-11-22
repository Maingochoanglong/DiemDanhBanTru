# Điểm danh bán trú

App Windows nhỏ gọn giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- bấm vào lớp, tìm hoặc dán tên GV báo rồi bấm chọn từng em vắng (chỉ hiện các em ăn bán trú của lớp);
- ghi tên theo quy tắc, đếm số vắng;
- tự tính bảng suất ăn cho bảo mẫu, kể cả các lớp ghép; bảng suất ăn của tờ ngày mới dựng theo sheet *Nhóm ăn* trong file danh sách (đổi cách ghép không phải sửa công thức sổ);
- ghi vào sổ Excel giữ y mẫu cũ (mỗi ngày 1 sheet, mỗi tháng 1 file) (in bằng Excel như thường lệ);
- chỉ làm việc với 3 file: **danh sách học sinh** (Excel; lịch thêm/cắt đặt trên app, lưu vào 3 cột Ăn từ / Cắt từ / Cắt thứ 6), **sổ điểm danh tháng**, **CaiDat.txt** cạnh file .exe. Đang làm dở thì có thêm sổ tạm `… tamthoi.xlsx` cạnh file .exe, ghi sau mỗi thao tác, xóa khi đã lưu vào sổ.
- mọi thứ nằm trong thư mục chứa file .exe (không ghi gì vào `%APPDATA%`, `%TEMP%`): gỡ app chỉ cần xóa thư mục đó.

👉 **Hướng dẫn sử dụng: [HUONG_DAN.md](HUONG_DAN.md)**

## Tải về

👉 **[Tải DiemDanhBanTru.exe](https://github.com/Maingochoanglong/DiemDanhBanTru/raw/main/tai-ve/DiemDanhBanTru.exe)** (thư mục [`tai-ve`](tai-ve) của repo).

File được GitHub Actions (`.github/workflows/build-windows.yml`) dựng trên Windows và tự commit vào `tai-ve/` mỗi khi nhánh `main` có mã mới. Cũng có ở trang **Releases** → bản *Điểm danh bán trú, bản mới nhất*. Mỗi lần cập nhật, repo nặng thêm khoảng 20 MB (dung lượng file `.exe`, dựng bằng Nuitka).

## Chạy từ mã nguồn (cho người phát triển)

Cần Python 3.10 trở lên. App mở giao diện trong **trình duyệt** (Edge/Chrome) ở `http://127.0.0.1:47615` (chỉ nhận kết nối từ chính máy này). App tự thoát khi đóng thẻ trình duyệt cuối cùng hoặc bấm *Thoát*; mở app lần nữa khi đang chạy thì chỉ mở thêm thẻ.

| Phần | Framework |
|---|---|
| Máy chủ (Python) | [FastAPI](https://fastapi.tiangolo.com) chạy bằng [uvicorn](https://www.uvicorn.org) |
| Giao diện | [Vue 3](https://vuejs.org) + [PrimeVue 4](https://primevue.org) (theme Aura) + PrimeIcons: bản dựng sẵn đóng kèm trong `static/vendor/`, **không cần Node.js / bước build**, chạy không cần mạng |

PrimeVue giữ ở bản 4 (giấy phép MIT); từ bản 5 PrimeVue đổi sang giấy phép thương mại có điều kiện.

```bash
pip install -r requirements.txt -r requirements-dev.txt
python run_app.py            # mở app trong trình duyệt
python run_app.py --no-open  # chạy máy chủ, không tự mở trình duyệt (tự vào http://127.0.0.1:47615)
python -m app.web.server    # máy chủ thử: mở http://127.0.0.1:8765 để xem/chụp giao diện, tài liệu API ở /docs
python -m pytest             # chạy test
python -m nuitka run_app.py --file-version=2.0.0 --product-version=2.0.0   # dựng dist/DiemDanhBanTru.exe bằng Nuitka (tùy chọn ở đầu run_app.py)
```

Cấu trúc mã:

| Thư mục | Nội dung |
|---|---|
| `app/core/` | Xử lý không phụ thuộc Excel/giao diện: chuẩn hóa tên tiếng Việt, tên ghi sổ (`names.py`), tách tên trong ô sổ (`parser.py`), so khớp tên (`matcher.py`), một ngày điểm danh (`day.py`), suất ăn (`meals.py`). |
| `app/excel/` | Đọc file danh sách học sinh + sheet Nhóm ăn (`roster_import.py`), ghi 3 cột lịch bán trú (`roster_schedule.py`), sổ điểm danh tháng (`sobook.py`: tìm hàng lớp và bảng suất ăn theo nội dung, sao chép sheet, ghi số liệu, dựng lại bảng suất ăn theo Nhóm ăn), sổ tạm `… tamthoi.xlsx` (`tamthoi.py`), ghi file an toàn / mở file (`files.py`). |
| `app/settings.py` | CaiDat.txt (cạnh file .exe). |
| `app/config.py` | Mọi giá trị cố định (cổng, tên file, thời gian chờ, lịch học…), không viết cứng ở chỗ khác. |
| `app/service.py` | Điều phối các thao tác (mở ngày, lưu, sổ tạm, tạo sổ tháng mới). |
| `app/web/` | `api.py` (các hàm giao diện gọi: mở ngày, chọn em vắng, lưu sổ…), `server.py` (máy chủ FastAPI: trả giao diện, nhận lời gọi `POST /api/<tên hàm>`), `run.py` (mở trình duyệt, hộp chọn file của Windows, tự thoát khi đóng thẻ), `static/` (giao diện: `index.html`, `app.css`, `js/main.js` khởi động Vue + PrimeVue, `js/store.js` trạng thái và thao tác chung, `js/components/` mỗi trang / hộp thoại một file, `vendor/` thư viện đóng kèm). |
| `tests/` | Test với dữ liệu giả (không chứa thông tin thật của học sinh). |

Luật viết mã và bản đồ chi tiết cho người / AI sửa mã: **[CLAUDE.md](CLAUDE.md)**. Giáo vụ dùng app làm gì (căn cứ để sửa giao diện): **[USER_STORIES.md](USER_STORIES.md)**.

> Không đưa file Excel thật (danh sách học sinh, sổ điểm danh) lên repo. `.gitignore` đã chặn `*.xls`, `*.xlsx`.
