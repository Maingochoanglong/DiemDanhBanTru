# User story: giáo vụ làm gì với app

Giao diện chỉ có những gì phục vụ các việc dưới đây. Muốn thêm nút, trang hay hộp thoại thì phải chỉ ra
nó phục vụ story nào; không có story thì không thêm. Có hai cách làm cùng một việc thì bỏ bớt một.

## Người dùng

**Giáo vụ** (1 người) làm sổ điểm danh bán trú trên máy Windows có Excel. Không rành máy tính.
Buổi sáng GVCN nhắn **Zalo** báo vắng; giáo vụ **dán từng tin** của từng GVCN vào app (để biết mình đã làm cho GVCN nào).
**8h30 chốt suất ăn**: lưu vào sổ, mở sổ Excel, chép bảng suất ăn dạng ảnh (tính năng của Excel) gửi lên Zalo.

Số liệu một ngày (đếm từ sổ tháng 10 thật, không chép tên):

| | Một ngày |
|---|---|
| Lớp | 29 |
| Lớp có em vắng | 13 tới 23 |
| Em vắng | 20 tới 79 |
| Ô ghi chú (cột H) | 8 tới 14, phần lớn chép lại từ hôm trước: "thứ 6 hàng tuần cắt…", "thêm … ghép 1.3", "vắng tới khi có thông báo mới" |
| Nhóm suất ăn | 11 |

Khoảng 1/6 số tên vắng giống hệt hôm trước (em nghỉ dài ngày). "Vắng tới khi có thông báo mới" chỉ là ghi chú,
giáo vụ vẫn tự chọn vắng mỗi ngày: app không làm việc này thay.

## Hằng ngày

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| H1 | mở app là thấy ngay ngày hôm nay, đúng sổ tháng này | bắt tay vào làm, không phải chọn gì | app tự mở ngày học hôm nay |
| H2 | GVCN nhắn Zalo "Cô ơi lớp 1D15 hôm nay vắng bé Tuấn Anh, Bảo Ngọc ạ": mở lớp, **dán nguyên tin**, bấm chọn em | ghi đúng em, không phải gõ lại hay xóa chữ thừa | bấm hàng lớp → bảng chọn tên: ô tìm tự nhặt tên trong tin (bỏ mã lớp, "vắng", "ạ"…), ô tên |
| H3 | GVCN báo "lớp đủ": một lần bấm | xong lớp đó | nút **Lớp này đủ** |
| H4 | ghi chú của lớp (cột H) như sổ giấy | ghi lý do, lịch cắt/thêm | ô **Ghi chú** trong bảng chọn tên |
| H5 | gần 8h30, biết lớp nào chưa báo | nhắc đúng GVCN | hàng **Chưa báo**: mã lớp bấm được |
| H6 | trước khi chốt, biết tổng suất ăn khớp số hiện diện | không báo sai suất | nhãn tổng suất trên bảng; trang **Suất ăn** |
| H7 | 8h30 lưu vào sổ, mở sổ Excel đúng sheet hôm nay, chép bảng suất ăn dạng ảnh gửi Zalo; in như thường lệ | báo bếp, có sổ giấy | **Lưu vào sổ**, **Mở sổ Excel** (Excel mở đúng sheet vừa lưu). Chụp ảnh làm trong Excel, app không làm thêm |
| H8 | bấm nhầm thì quay lại | không sợ sai | **Hoàn tác** |
| H9 | em "cắt thứ 6", em đã cắt / mới thêm bán trú tự được tính | không phải nhớ, không chọn lại mỗi ngày | lịch đặt ở hộp **Lịch bán trú**; app tự tính |

## Thỉnh thoảng

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| T1 | làm bù hoặc sửa ngày trước | sổ đủ ngày | lùi / tới ngày, gõ ngày, lịch, **Hôm nay** |
| T2 | đầu tháng có sổ tháng mới từ sổ tháng trước | giữ mẫu, chữ ký, ghi chú | app hỏi khi mở ngày của tháng chưa có sổ |
| T3 | đặt lịch: em bắt đầu ăn từ ngày, thôi ăn từ ngày, cắt thứ 6 | không phải nhớ, đến ngày sĩ số tự đổi; Ghi chú chỉ để ghi chú | trang **Học sinh**: bấm vào em → hộp **Lịch bán trú** (ghi vào 3 cột Ăn từ / Cắt từ / Cắt thứ 6 của file danh sách) |
| T3a | đổi cách ghép ăn, tên gọi khác; thêm / bỏ suất ăn, suất ghép ngay trong sổ | sửa ở một chỗ quen thuộc, sổ in ra vẫn đúng công thức | sửa file danh sách / sổ bằng Excel; nút mở file ở trang **Học sinh**, **Suất ăn**. App đọc dòng mới, khi lưu tự sửa công thức (ô cộng các nhóm, ô ăn tại lớp, ô em ghép lẻ) và báo đã sửa gì |
| T3b | có em chuyển đến ăn bán trú: ghi tên em vào file danh sách (lúc app đang mở cũng được) | điểm danh em đó ngay hôm đó | lưu file danh sách trong Excel; mở lớp là thấy em mới, các em đã chọn vắng vẫn giữ; ngày bắt đầu ăn đặt ở hộp **Lịch bán trú** |
| T4 | tra một em ở lớp nào, có ăn bán trú không | trả lời GVCN | trang **Học sinh** |
| T5 | em ăn ghép vắng: chọn em đó ăn nhóm nào | suất ăn đúng | trang **Suất ăn** hỏi khi cần |
| T6 | mất điện / lỡ đóng trình duyệt thì không mất việc đang làm | khỏi làm lại | sổ tạm; lần mở sau hỏi **Khôi phục** |

## Hiếm

| # | Là giáo vụ, tôi muốn… | để… | Trên app |
|---|---|---|---|
| R1 | bản app mới / máy mới: chọn sổ và file danh sách một lần | dùng được ngay | hộp **Thiết lập** |
| R2 | sổ có tên ghi tay không khớp em nào (sổ người khác ghi): thấy lớp nào, sửa | sổ đúng | hàng **Cần xem** (chỉ hiện khi có), chữ đỏ ở cột Ghi chú |
| R3 | đôi khi đã tạo sẵn sheet ngày mới trong Excel (chép từ hôm trước) nên app hiểu nhầm các lớp đã báo | làm lại từ đầu ngày đó | **Đặt lại** (nút chữ nhỏ, không đặt ngang nút Lưu) |
| R4 | đổi sổ / file danh sách, xem các file app dùng, gỡ app | biết file nằm đâu | trang **Cài đặt** |
| R5 | thoát app | tắt máy | **Thoát** (hỏi lưu nếu còn thay đổi) |

## Đã bỏ vì không phục vụ story nào (hoặc trùng việc)

- Bộ lọc bảng "Tất cả / Cần xem / Chưa báo / Có vắng": hàng **Chưa báo** và **Cần xem** đã mở thẳng được lớp; bảng 29 lớp cuộn là hết.
- Nút "Lớp cần xem tiếp" trong bảng chọn tên: trùng hàng **Cần xem**.
- Nút phóng to bảng chọn tên: bảng đã gần kín màn hình.
- Dòng "Sổ ngày …: n tên vắng đã có, đều khớp danh sách": chỉ thêm chữ, không phải làm gì.
- Đọc lịch từ chữ trong cột Ghi chú ("cắt thứ 6", "ăn từ 3/11"): giáo vụ muốn Ghi chú chỉ là ghi chú; lịch đặt ở hộp Lịch bán trú.
- Dòng đỏ "n tên chưa rõ trong sổ, bấm để xử lý": trùng hàng **Cần xem** và dòng trạng thái thanh lưu.
- Dòng TỔNG CỘNG cuối bảng: trùng dòng tổng ở đầu bảng (luôn thấy, không phải cuộn). Chú thích màu dòng: màu đã kèm chấm và chữ "(chưa báo)".
- "(mới)" trên thanh ngày: trùng dòng "Ngày này chưa có trong sổ".
- Cài đặt: nút "Thư mục" của sổ (trùng "Mở thư mục"), "Mở file" danh sách (trùng nút ở trang Học sinh), dòng nhắc đóng Excel (app báo đúng lúc gặp).
- Chân trang Suất ăn khi các lớp ghép đã ghi nhóm đủ.
- Trước đó: màn duyệt khi nhập danh sách, sửa cách ghép trong app, đọc ghi chú sổ, sao lưu.

## Không làm (giáo vụ đã nói không cần)

- Chụp / gửi bảng suất ăn: giáo vụ chép ảnh trong Excel rồi gửi Zalo.
- Tự đánh vắng em "vắng tới khi có thông báo mới": chỉ là ghi chú.

## Còn cần giáo vụ xác nhận

- Máy ở trường màn hình cỡ nào (để biết nút thu gọn thanh bên còn cần không)?
