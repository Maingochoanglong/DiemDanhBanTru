"""Mọi giá trị cố định của app ở MỘT chỗ (không viết cứng giá trị ở file khác; test_rules.py kiểm tra).

Giá trị người dùng có thể muốn đổi thì đặt trong CaiDat.txt (settings.KEYS, mặc định lấy ở đây).
Giao diện nhận phần UI qua /config.js (server.py), không tự viết cứng.
"""

APP_ID = "DiemDanhBanTru"

# ---- 4 file app được đọc / ghi (xem CLAUDE.md) ----
SETTINGS_FILE = "CaiDat.txt"  # cạnh file .exe
TEMP_TAG = "tamthoi"  # sổ tạm = "<tên sổ> tamthoi.xlsx" cạnh sổ
BOOK_SUFFIXES = (".xlsx", ".xlsm")  # sổ điểm danh: openpyxl đọc/ghi được
LIST_FILE_TYPES = ("Excel (*.xlsx;*.xls)",)  # hộp chọn file danh sách
BOOK_FILE_TYPES = ("Excel (*.xlsx)",)  # hộp chọn file sổ
SAVED_PROP = "DiemDanhBanTru_DaLuu"  # thuộc tính ẩn trong file sổ: các sheet app đã lưu

# ---- máy chủ nội bộ ----
HOST = "127.0.0.1"  # chỉ nhận kết nối từ chính máy này
HOST_NAMES = [HOST, "localhost"]  # tên miền được phép (chặn trang web lạ trỏ về máy)
DEFAULT_PORT = 47615  # cổng cố định (CaiDat.txt: cong) để lần mở sau nhận ra app đang chạy
DEV_PORT = 8765  # python -m app.web.server
API_HEADER = "X-DDBT"  # giao diện gửi kèm mọi lời gọi /api
CLIENT_HEADER = "X-Client"  # mã thẻ trình duyệt
CLIENT_ID_MAX = 64
SERVER_START_TIMEOUT = 5.0  # giây chờ máy chủ chạy
SERVER_STOP_TIMEOUT = 5.0
POLL_INTERVAL = 0.025  # giây giữa 2 lần xem máy chủ đã chạy chưa
DIALOG_POLL = 0.3  # giây giữa 2 lần xem có hộp chọn file cần mở
TAB_CLOSE_GRACE = 6.0  # giây chờ sau khi đóng thẻ cuối (tải lại trang thì kịp mở lại)
QUIT_DELAY = 0.5  # giây: trả lời giao diện xong mới tắt
PING_TIMEOUT = 2.0
QUIT_TIMEOUT = 5.0
OLD_APP_WAIT = 6.0  # giây chờ bản .exe cũ tắt hẳn

# ---- điểm danh ----
UNDO_DEPTH = 50  # số thao tác Hoàn tác được
MATCH_INITIAL_PENALTY = 2.5  # so khớp tên: chữ viết tắt là họ ("K. Bảo Ngọc" -> Kha Văn Bảo Ngọc) xếp sau khớp sát tên
FUZZY_MIN_RATIO = 0.6  # so khớp tên gõ sai: độ giống tối thiểu (difflib) để gợi ý em gần giống

# ---- lịch học ----
SCHOOL_DAYS = 5  # thứ 2..thứ 6 (weekday 0..4); thứ 7, CN nghỉ. Trường học thứ 7 thì đặt 6
FRIDAY = 4  # weekday của thứ 6 (học nửa buổi: em "cắt thứ 6" tự tính vắng)
SCHOOL_YEAR_START_MONTH = 8  # năm học từ tháng 8 tới tháng 7 năm sau (ngày ghi chú không ghi năm)

# ---- đọc file Excel ----
RED_FONT = (180, 100, 100)  # chữ đỏ (file danh sách toàn trường): R >= 180, G <= 100, B <= 100
LIST_HEADER_ROWS = 10  # dò dòng tiêu đề (Lớp, Họ tên…) trong 10 dòng đầu file danh sách
MEAL_SHEET_HEADER_ROWS = 5  # dò dòng tiêu đề sheet Nhóm ăn
MEAL_SHEET_COLS = 6
BOOK_HEADER_ROWS = 20  # dò dòng tiêu đề bảng điểm danh trong 20 dòng đầu sheet ngày
BOOK_SCAN_COLS = 30
BOOK_FOOTER_ROWS = 6  # dò dòng "ngày … tháng … năm" dưới dòng tổng
MEAL_COL_OFFSETS = (3, 4, 6)  # sổ mẫu: cột suất I -> cột L (=O-M), M (ghép vắng), O (số em ghép)
TEMP_COL_WIDTHS = (8, 8, 7, 70, 40)  # độ rộng cột sheet "Dang diem danh" của sổ tạm

# ---- so khớp tên ----
SUGGEST_MAX = 5  # số em gợi ý khi tên gõ không khớp ai
OTHER_CLASS_MAX = 8  # số em cùng tên ở lớp khác liệt kê
ERROR_TEXT_MAX = 2000  # số ký tự lỗi hiện trong hộp báo lỗi lúc mở app

# ---- giao diện (gửi sang trình duyệt qua /config.js) ----
UI = {
    "unreported_shown": 12,  # số mã lớp "Chưa báo" hiện trên thanh, còn lại ghi "và n lớp khác"
    "toast_life": 6000,  # mili giây thông báo nhỏ hiện
    "toast_life_error": 12000,
}
