# User story: giáo vụ làm gì với app

Giao diện chỉ có những gì phục vụ các việc dưới đây. Muốn thêm nút, trang hay hộp thoại thì phải chỉ ra
nó phục vụ story nào; không có story thì không thêm. Có hai cách làm cùng một việc thì bỏ bớt một.

## Người dùng

**Giáo vụ** (1 người) làm sổ điểm danh bán trú trên máy Windows có Excel. Không rành máy tính.
Buổi sáng vừa nhận tin giáo viên chủ nhiệm (GVCN) báo vắng, vừa làm việc khác.

Số liệu một ngày (đếm từ sổ tháng 10 thật, không chép tên):

| | Một ngày |
|---|---|
| Lớp | 29 |
| Lớp có em vắng | 13–23 |
| Em vắng | 20–79 |
| Ô ghi chú (cột H) | 8–14, phần lớn chép lại từ hôm trước: "thứ 6 hàng tuần cắt…", "thêm … ghép 1.3", "vắng tới khi có thông báo mới" |
| Nhóm suất ăn | 11 |

Khoảng 1/6 số tên vắng giống hệt hôm trước (em nghỉ dài ngày).

## Hằng ngày

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| H1 | mở app là thấy ngay ngày hôm nay, đúng sổ tháng này | bắt tay vào làm, không phải chọn gì | app tự mở ngày học hôm nay |
| H2 | GVCN nhắn "1D15 vắng Tuấn Anh, Bảo Ngọc": mở lớp, gõ hoặc dán tên (không dấu, tên gọi khác), bấm chọn em | ghi đúng em, không gõ lại họ tên | bấm hàng lớp → bảng chọn tên: ô tìm, ô tên |
| H3 | GVCN báo "lớp đủ": một lần bấm | xong lớp đó | nút **Lớp này đủ** |
| H4 | ghi chú của lớp (cột H) như sổ giấy | ghi lý do, lịch cắt/thêm | ô **Ghi chú** trong bảng chọn tên |
| H5 | gần giờ chốt, biết lớp nào chưa báo | nhắc đúng GVCN | hàng **Chưa báo**: mã lớp bấm được |
| H6 | biết tổng suất ăn và suất từng nhóm, khớp với số hiện diện | báo bếp / bảo mẫu | nhãn tổng suất trên bảng; trang **Suất ăn** |
| H7 | lưu vào sổ Excel, in như thường lệ | có sổ giấy | **Lưu vào sổ**, **Mở sổ Excel** |
| H8 | bấm nhầm thì quay lại | không sợ sai | **Hoàn tác** |
| H9 | em "cắt thứ 6", em đã cắt / mới thêm bán trú tự được tính | không phải nhớ, không chọn lại mỗi ngày | cột Ghi chú của file danh sách; app tự tính |

## Thỉnh thoảng

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| T1 | làm bù hoặc sửa ngày trước | sổ đủ ngày | lùi / tới ngày, gõ ngày, lịch, **Hôm nay** |
| T2 | đầu tháng có sổ tháng mới từ sổ tháng trước | giữ mẫu, chữ ký, ghi chú | app hỏi khi mở ngày của tháng chưa có sổ |
| T3 | thêm / cắt bán trú, đổi cách ghép ăn bằng Excel | sửa ở một chỗ quen thuộc | sửa file danh sách; app tự đọc lại; nút mở file ở trang **Học sinh**, **Suất ăn** |
| T4 | tra một em ở lớp nào, có ăn bán trú không | trả lời GVCN | trang **Học sinh** |
| T5 | em ăn ghép vắng: chọn em đó ăn nhóm nào | suất ăn đúng | trang **Suất ăn** hỏi khi cần |
| T6 | mất điện / lỡ đóng trình duyệt thì không mất việc đang làm | khỏi làm lại | sổ tạm; lần mở sau hỏi **Khôi phục** |

## Hiếm

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| R1 | bản app mới / máy mới: chọn sổ và file danh sách một lần | dùng được ngay | hộp **Thiết lập** |
| R2 | sổ có tên ghi tay không khớp em nào (sổ người khác ghi): thấy lớp nào, sửa | sổ đúng | hàng **Cần xem** (chỉ hiện khi có), chữ đỏ ở cột Ghi chú |
| R3 | sheet đã tạo sẵn trong Excel nên app hiểu nhầm các lớp đã báo | làm lại từ đầu ngày đó | **Đặt lại** (nút chữ nhỏ, không đặt ngang nút Lưu) |
| R4 | đổi sổ / file danh sách, xem các file app dùng, gỡ app | biết file nằm đâu | trang **Cài đặt** |
| R5 | thoát app | tắt máy | **Thoát** (hỏi lưu nếu còn thay đổi) |

## Đã bỏ vì không phục vụ story nào (hoặc trùng việc)

- Bộ lọc bảng "Tất cả / Cần xem / Chưa báo / Có vắng": hàng **Chưa báo** và **Cần xem** đã mở thẳng được lớp; bảng 29 lớp cuộn là hết.
- Nút "Lớp cần xem tiếp" trong bảng chọn tên: trùng hàng **Cần xem**.
- Nút phóng to bảng chọn tên: bảng đã gần kín màn hình.
- Dòng "Sổ ngày …: n tên vắng đã có, đều khớp danh sách": chỉ thêm chữ, không phải làm gì.
- Trước đó: màn duyệt khi nhập danh sách, trang Lịch, sửa cách ghép trong app, đọc ghi chú sổ, sao lưu.

## Cần giáo vụ xác nhận

1. GVCN báo vắng bằng gì (Zalo, gọi điện, giấy)? Có hay dán nguyên tin nhắn nhiều lớp một lần không?
2. Mấy giờ phải chốt suất ăn? Báo bếp bằng cách đọc số, in, hay chụp màn hình?
3. Có tạo sẵn sheet ngày trong Excel trước khi điểm danh không (để biết **Đặt lại** còn cần không)?
4. Em "vắng tới khi có thông báo mới": có muốn app tự đánh vắng mỗi ngày cho tới khi bỏ ghi chú không?
5. Máy ở trường màn hình cỡ nào (để biết thanh bên thu gọn còn cần không)?
