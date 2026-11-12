# CLAUDE.md — đọc trước khi sửa mã

App Windows (file .exe) giúp giáo vụ làm sổ điểm danh bán trú. Giao diện chạy trong trình duyệt, máy chủ Python chạy trên chính máy đó (127.0.0.1). Người dùng nói tiếng Việt: trả lời, chú thích, thông báo, commit đều viết **tiếng Việt**.

## Luật viết mã (áp dụng cho cả backend lẫn frontend)

1. **Có sẵn thì dùng, không viết lại.** Thứ tự ưu tiên:
   - hàm đã có trong repo (tìm bằng grep trước khi viết);
   - thành phần / tính năng có sẵn của thư viện đang dùng: FastAPI, openpyxl, xlrd (backend); Vue 3, PrimeVue 4 (frontend);
   - chỉ khi cả hai đều không có mới viết mới, và viết ngắn nhất có thể.

   Ví dụ đã áp dụng:
   - Hộp hỏi dùng `DynamicDialog` + `ask()` (`js/dialogs.js`), không tự dựng hộp thoại.
   - Bảng dùng `DataTable`; thông báo dùng `Toast`.
   - Ghi Excel an toàn dùng chung `excel/files.py:safe_save` (sổ chính lẫn sổ tạm).
   - Chặn tên miền lạ dùng `TrustedHostMiddleware` của FastAPI.
2. **Thêm thư viện mới chỉ khi thật cần.** Frontend phải là bản dựng sẵn đóng kèm trong `app/web/static/vendor/` (không cần Node, không có bước build, chạy không cần mạng). Không dùng PrimeVue 5 trở lên: bản 5 đổi sang giấy phép thương mại.
3. **Bỏ code thừa ngay khi bỏ tính năng**: hàm, API, thành phần Vue, lớp CSS, test, chữ trong tài liệu. Hai test giữ việc này:
   - `tests/test_static.py` báo lỗi khi có hàm Python mà giao diện không gọi, hoặc thành phần đăng ký mà không dùng;
   - `python -m vulture app --min-confidence 60` giúp tìm hàm chết. Lưu ý vulture báo nhầm các hàm của `Api` (giao diện gọi theo tên) và thuộc tính openpyxl.
4. **Mã dễ đọc cho người và AI**:
   - mỗi file một việc, có docstring/chú thích đầu file nói file đó làm gì;
   - tên hàm rõ nghĩa; mỗi trang / hộp thoại là một file trong `js/components/`;
   - không viết lớp trừu tượng "để dành". Sửa chỗ nào thì sửa đúng file của việc đó (xem bản đồ dưới).
5. **Dữ liệu thật của học sinh không bao giờ vào repo.** `.gitignore` chặn `*.xls`, `*.xlsx`, `CaiDat.txt`. Test chỉ dùng tên bịa (`tests/conftest.py`). File thật người dùng gửi chỉ để trong thư mục tạm của phiên.

## App chỉ làm việc với 3 file

| File | Ai sửa | Mã đọc/ghi |
|---|---|---|
| **Danh sách học sinh** (Excel, .xlsx/.xls) | giáo vụ, bằng Excel. App **chỉ đọc**, tự đọc lại khi mở ngày nếu file đã sửa. | `excel/roster_import.py:load_list` |
| **Sổ điểm danh tháng** (Excel, mỗi ngày 1 sheet, mỗi tháng 1 file) | app ghi sheet của ngày khi bấm Lưu | `excel/sobook.py` |
| **CaiDat.txt** (cạnh file .exe; chạy từ mã nguồn thì ở gốc repo) | app, hoặc giáo vụ sửa bằng Notepad | `settings.py` |

- **Cột của file danh sách:** Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không, hoặc chữ đỏ) · Tên gọi khác · Ăn ghép · **Ghi chú**.
  - Cột Ghi chú chứa lịch thêm/cắt: `cắt thứ 6`, `cắt từ 30/10`, `ăn từ 3/11` (bộ đọc ở `core/notes.py`).
  - Sheet **Nhóm ăn** (tùy chọn) quy định bảng suất ăn của tờ ngày mới.
- **Mã học sinh** = `lớp|họ tên|ngày sinh`: không đổi giữa các lần đọc file.
- **Sổ tạm** `… tamthoi.xlsx` cạnh sổ (`excel/tamthoi.py`):
  - ghi **ngay sau mỗi thao tác**: `Api.state()` gọi `Workspace.autosave()`;
  - khi bấm Lưu: ghi sổ tạm, ghi sheet vào sổ, rồi xóa sổ tạm;
  - mất điện thì lần mở sau app hỏi khôi phục.
- **Không có** file dữ liệu riêng, nhật ký, thư mục sao lưu.

## Bản đồ mã nguồn

```
run_app.py                điểm khởi chạy (PyInstaller)
app/main.py               main(), --selftest (CI chạy trên file .exe), ghi loi.log
app/settings.py           CaiDat.txt
app/service.py            Workspace: điều phối (mở ngày, lưu, sổ tạm, sổ tháng mới, bảng suất ăn theo Nhóm ăn)
app/core/                 xử lý thuần, không đụng file / giao diện
  models.py               Student, ClassInfo, Roster (tra theo lớp, tên ghi sổ)
  day.py                  DayState: 1 ngày điểm danh (vắng, đã báo, ghi chú, sĩ số, undo)
  matcher.py, names.py, parser.py, text.py, search.py   so khớp / chuẩn hóa tên tiếng Việt
  meals.py                bảng suất ăn, ăn ghép
  notes.py                đọc cột Ghi chú của file danh sách
app/excel/                đọc/ghi Excel
  roster_import.py        đọc file danh sách + sheet Nhóm ăn
  sobook.py               sổ tháng: tìm hàng lớp, sao chép sheet, ghi ngày, dựng bảng suất ăn
  tamthoi.py              sổ tạm
  files.py                safe_save, is_locked, open_file/open_folder
app/web/
  api.py                  Api: mọi hàm giao diện gọi (POST /api/<tên hàm>, tham số là mảng JSON)
  server.py               FastAPI + uvicorn (luồng riêng), chặn trang web lạ, /ping, /config.js
  run.py                  mở trình duyệt, hộp chọn file tkinter ở luồng chính, thoát khi đóng thẻ, BrowserApi.quit
  static/index.html       nạp vendor/ rồi js/main.js
  static/app.css          bố cục + màu trạng thái lớp (dùng biến màu --p-* của theme PrimeVue)
  static/js/main.js       khởi động Vue + PrimeVue (theme Aura, chữ tiếng Việt, đăng ký thành phần)
  static/js/api.js        api(name, ...args), conn (máy chủ đã tắt)
  static/js/store.js      trạng thái chung + thao tác dùng nhiều nơi (lưu, đổi ngày, mở lớp, chọn file, thoát)
  static/js/dialogs.js    ask / info / toast / openDialog (PrimeVue DialogService, ToastService)
  static/js/util.js       so khớp tên khi gõ, ngày
  static/js/components/   App (khung), TopBar, DiemDanhPage, ClassDialog, ResolveDialog,
                          SuatAnPage, HocSinhPage, CaiDatPage, SetupDialog, AskBody
tests/                    pytest, dữ liệu bịa; conftest.write_list / make_workspace dựng đủ 3 file
```

Thêm một thao tác mới thì:
1. thêm hàm công khai trong `Api` (`api.py`), trả về dict JSON (thường kèm `"state": self.state()`);
2. giao diện gọi `api("ten_ham", ...)`;
3. thêm test trong `tests/test_web_api.py`.

## Kiểm tra trước khi commit

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
python -m ruff check app tests
python -m app.web.server 8765 <đường dẫn CaiDat.txt>   # chạy thử giao diện: http://127.0.0.1:8765 (API: /docs)
```

Sửa giao diện thì chạy thử bằng Playwright (Chromium có sẵn) và xem ảnh chụp. CI (`.github/workflows/build-windows.yml`) chạy test, dựng `.exe` trên Windows và chạy `--selftest`.
