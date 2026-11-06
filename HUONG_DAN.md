# Hướng dẫn sử dụng app Điểm danh bán trú

App giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- bấm vào lớp để tích em vắng (tên chữ to, có ô tìm tên không cần gõ dấu);
- ghi tên đúng quy tắc;
- tự đếm số vắng;
- tự tính bảng suất ăn (kể cả các em ăn ghép);
- in 2 tờ.

Kết quả ghi vào **chính file sổ Excel đang dùng**, giữ y kiểu cũ: mỗi ngày 1 sheet, mỗi tháng 1 file.

---

## 1. Cài đặt

1. Trên trang repo GitHub, mở thư mục **`tai-ve`** → bấm **`DiemDanhBanTru.exe`** → nút **Download** (hoặc tải ở trang **Releases**).
2. Chép file vào một thư mục cố định (ví dụ `Documents\DiemDanhBanTru`), rồi bấm đúp để mở.
3. Lần đầu mở, Windows có thể báo *"Windows protected your PC"*. Bấm **More info → Run anyway**. Lý do: app không mua chữ ký số, file vẫn an toàn.

Máy cần Windows 10/11. In trực tiếp cần Microsoft Excel. Không cần cài Python.

## 2. Lần đầu sử dụng (khoảng 5 phút)

Mở app lần đầu, app **không hỏi chọn file**. Màn chính hiện dòng nhắc màu cam; bạn tự làm khi sẵn sàng:

1. Bấm **Cài đặt** (góc trên bên phải) → **Nhập danh sách học sinh (file Excel)…**. Dùng được 2 dạng file:
   - **file đơn giản 4 cột**: *Lớp · Họ và tên · Ngày sinh · Ăn bán trú*, cột **Ăn bán trú** ghi **có** hoặc **không** (một sheet, không cần cố định dòng hay lọc);
   - file CDHS của trường, trong đó **em tô chữ đỏ là có ăn bán trú**.

   App liệt kê các em đọc được để bạn duyệt rồi bấm **Áp dụng**.
2. Trong Cài đặt, bấm **Chọn sổ khác…** để chọn **sổ điểm danh tháng hiện tại** (ví dụ `PH3.SỔ ĐIỂM DANH T10.xlsx`).
3. Nếu muốn, bấm **Đọc ghi chú trong sổ…**: app đọc ghi chú cột H và đề xuất cập nhật danh sách, ví dụ:
   - "Thứ 6 hàng tuần cắt 2 em …" → đánh dấu **cắt thứ 6**: thứ 6 các em tự được tính vắng.
   - "Tháng 11 cắt …" (hoặc "T11 CẮT …") → **cắt bán trú từ 01/11**; "Từ 12/10 cắt bán trú …" → cắt từ 12/10. Sĩ số tự giảm từ ngày đó.
   - "thêm … ghép 1.3" → thêm em vào bán trú lớp đó, ăn ghép ở nhóm 1.3.

   Bỏ tích dòng nào không đúng rồi bấm **Áp dụng**.

Dữ liệu riêng của app (danh sách HS, ghép lớp, cài đặt) lưu ở `Documents\DiemDanhBanTru\DuLieu_BanTru.xlsx`. File này mở được bằng Excel để xem.

## 3. Mỗi sáng

App có 3 tab: **Điểm danh** (dùng hằng ngày), **Suất ăn**, **Học sinh** (trong đó có 3 tab con ít dùng: **Danh sách học sinh**, **Lịch thêm/cắt**, **Ghép lớp**). Cài đặt mở bằng nút **Cài đặt** ở góc trên bên phải.

Màn hình **Điểm danh** gồm:

| Phần | Dùng để |
|---|---|
| **Bảng điểm danh** | Giống tờ sổ: Lớp · GVCN · Sĩ số · Vắng · Hiện diện · Tên học sinh vắng · Ghi chú, có dòng cộng từng khối và **TỔNG CỘNG**. Mỗi dòng có icon và màu: **vòng tròn xám** = chưa báo, **tích xanh** = đủ, **chấm cam** = có vắng, **tam giác đỏ** = cần xem. Cột Ghi chú: **[Lịch]** = sĩ số đổi theo lịch thêm/cắt. Chữ dài bị cắt: rê chuột vào ô để xem đủ. Dòng trên bảng có **Tổng suất = hiện diện** kèm dấu tích xanh (đỏ khi lệch, bấm vào để xem tab Suất ăn). |
| **Cửa sổ lớp** (**bấm vào 1 lớp** trong bảng) | Hiện danh sách em ăn bán trú của lớp, **chữ to**, đọc dọc A→Z. **Tích = vắng.** Ô **Tìm tên** to ở góc phải, con trỏ đặt sẵn ở đó: gõ tên không cần dấu (`long`, `hai long`, `h long` đều ra *Hải Long*); còn đúng 1 em khớp thì bấm **Enter** là tích luôn, rồi gõ tên tiếp. **Esc** xóa ô tìm (bấm lần nữa để đóng). Có nút *Lớp này đủ*, ô ghi chú cột H. Bấm **Xong** để đóng. |

Tab **Suất ăn**: bảng suất ăn cho từng nhóm bảo mẫu, tự trừ các em ghép vắng. Dòng trên cùng phải là **Tổng suất = hiện diện** kèm dấu tích xanh. Bấm vào 1 nhóm để xem tên em ghép vắng.

Các cửa sổ con (cửa sổ lớp, Cài đặt, hộp hỏi) luôn mở **giữa màn hình** và tự co lại cho vừa màn hình nhỏ.

> Đọc tin nhắn Zalo **tạm ẩn**, sẽ phát triển sau.

### Kiểm tra tên trong sổ

Mở một ngày **đã có trong sổ**, app đối chiếu mọi ô tên vắng (kể cả gõ tay trong Excel). Tên không khớp danh sách hiện thành dòng **"Cần xử lý: …"** ở bảng điểm danh (bấm vào để xem chi tiết) và thành nút trong **cửa sổ lớp**: chọn em đúng, **giữ nguyên chữ trong sổ**, hoặc bỏ qua.

App còn đối chiếu số trong sổ: lớp lệch sĩ số hoặc thiếu/thừa tên vắng thì dòng lớp tô đỏ và ghi lý do ở cột Ghi chú (vd. "Thiếu 1 tên (GV báo vắng 3 em, mới ghi 2)").

### Lưu và in

Khi các lớp đã báo xong:

1. Bấm **Lưu vào sổ** (Ctrl+S). Nếu chưa có sheet ngày hôm nay, app sao chép sheet hôm trước rồi điền số liệu.
   - Nếu còn **tên chưa rõ**, app **chưa cho lưu và in** (các tên đó chưa được tính vắng nên suất ăn sẽ sai). Cạnh nút Lưu hiện chữ đỏ "Còn … tên chưa rõ"; bấm **Xử lý ngay** để app đưa bạn tới lớp cần xử lý. Với mỗi tên: **chọn em đúng**, **giữ tin nhắn gốc**, hoặc **bỏ qua tên này** — xử lý hết là lưu được.
2. Bấm **In 2 tờ** (Ctrl+P): tờ 1 là bảng điểm danh, tờ 2 là bảng suất ăn.
   - Nếu còn **lớp chưa báo**, app nhắc trước khi in: các lớp đó đang được **tính đủ** (không em nào vắng). Bấm **Vẫn in** (hoặc **Lưu rồi in**) nếu đúng vậy, hoặc **Ở lại** để chờ GV báo.

Nút **Copy lớp chưa báo** chép danh sách lớp (kèm tên GVCN) chưa báo để dán vào Zalo nhắc GV.

## 4. Lịch thêm / cắt bán trú, nghỉ thứ 6

Tab **Học sinh → Lịch thêm/cắt** dùng khi biết trước một em sẽ thôi ăn hoặc bắt đầu ăn, ví dụ từ ngày mai hay từ đầu tháng sau:

1. Bấm **Cắt bán trú…** (hình cây kéo) hoặc **Thêm bán trú…** (dấu cộng).
2. Chọn lớp, rồi chọn em (giữ Ctrl để chọn nhiều em). Muốn thêm em chưa có trong danh sách: chọn dòng cuối *Học sinh mới…* rồi gõ họ tên.
3. Chọn ngày áp dụng: bấm **Ngày học kế tiếp**, **Đầu tháng sau**, hoặc gõ ngày.
4. Bấm **Lưu lịch**.

Từ ngày đó app tự đổi sĩ số và danh sách tích vắng của lớp. Trên màn Điểm danh, cột Ghi chú của lớp đó có chữ **[Lịch]** và cửa sổ lớp ghi "Sĩ số đổi theo lịch (3 → 2): …". Sĩ số đổi theo lịch đã đặt thì app không hỏi "sĩ số khác nhau" khi lưu.

Nếu để tích ô *Ghi chú vào cột H*, app tự ghi chú vào cột H như cách bạn vẫn viết, ví dụ "Tháng 11 cắt bán trú Hồ Khánh Ngọc" hoặc "Từ 30/10 cắt bán trú …". Ghi chú tự mang sang các ngày sau. Nhớ bấm **Lưu vào sổ** để ghi chú vào sổ.

**Thứ 6 học nửa buổi**: em nào nghỉ ăn thứ 6 hàng tuần thì bấm **Cắt thứ 6 hàng tuần…**. Mỗi thứ 6, app tự tính các em này vắng, kể cả khi GV báo "đủ".

Danh sách lịch chia nhóm: *Sắp áp dụng*, *Hàng tuần – cắt thứ 6*, *Đã áp dụng (30 ngày qua)*. Chọn dòng rồi bấm **Hủy lịch đã chọn** để hủy.

Làm nhanh ngay trên màn Điểm danh: **bấm chuột phải vào tên em** trong cửa sổ lớp để chọn *Cắt bán trú từ ngày…* hoặc *Cắt thứ 6 hàng tuần…*. Nút **Thêm/cắt…** (hoặc chuột phải vào dòng lớp trong bảng) đặt lịch cho cả lớp. Bên cạnh tên em có nhãn *(nghỉ T6)* hoặc *(cắt từ 01/11)* nếu em đã có lịch.

## 5. Ghép lớp (lớp 1.5, 4.4 …)

Tab **Học sinh → Ghép lớp** liệt kê các em ăn bán trú của lớp ghép (lớp không có hàng riêng trong bảng suất ăn).

- Chọn một hoặc nhiều em (giữ Ctrl), rồi bấm **→ Ăn ở 1.1**, **→ Ăn ở 1.2**…
- Hoặc bấm **Dán danh sách ghép…** và gõ mỗi dòng: `1.1: Bảo Ngọc, Gia Hân, Minh Khôi`.
- Bấm **Lưu danh sách ghép**.

Khi đã gán đủ cả lớp, mỗi lần em ghép vắng, app tự điền ô **vắng** đúng hàng trong bảng suất ăn. Khi chưa gán đủ, app giữ số em ghép như sổ cũ; bạn **bấm đúp vào hàng nhóm** (có hình bút chì) trong tab Suất ăn để nhập số em ghép vắng.

Nếu nhập danh sách từ file có cột **Ghép lớp**, app tự gán nhóm ghép theo cột đó.

## 6. Học sinh

Tab **Học sinh** dùng để:

- tìm em, lọc theo lớp;
- **Thêm học sinh**, hoặc **Sửa** (bấm đúp) các thông tin: ăn bán trú, *cắt bán trú từ ngày*, *bắt đầu ăn từ ngày*, *cắt thứ 6*, *ăn ghép tại*, *tên ghi sổ* (nếu muốn ghi khác tên tự đặt);
- bấm **Lưu thay đổi** sau khi sửa.

Việc ít làm với danh sách nằm trong **Cài đặt → Danh sách học sinh**:

- **Nhập danh sách học sinh (file Excel)…** khi có danh sách mới (file đơn giản 4 cột *Lớp · Họ và tên · Ngày sinh · Ăn bán trú (có/không)*, hoặc file CDHS tô đỏ). App liệt kê từng thay đổi (em mới, đổi lớp, thôi/bắt đầu ăn) để bạn duyệt. Thông tin cắt thứ 6, ăn ghép… vẫn giữ nguyên.
- **Đọc ghi chú trong sổ…**: app đọc ghi chú cột H của sổ (vd. "Tháng 11 cắt …", "Thứ 6 hàng tuần cắt …") để gợi ý cập nhật danh sách.
- **Xuất danh sách…**: ghi ra file đơn giản 4 cột *Lớp · Họ và tên · Ngày sinh · Ăn bán trú (có/không)*, tính theo ngày bạn chọn (vd. ngày đầu tháng sau). File này gửi cho người khác xem, sửa bằng Excel, hoặc nhập lại vào app.

Lớp có sĩ số theo danh sách khác sĩ số trong sổ được tô đỏ ở bảng điểm danh. Khi lưu, nếu còn lệch, app hỏi: **giữ sĩ số như trong sổ** hay **dùng sĩ số theo danh sách**.

## 7. Ngày cũ, tháng mới

- Đổi ngày bằng ô **Ngày**, 2 nút mũi tên trái/phải hoặc **Hôm nay**.
- Mở một ngày **đã có trong sổ**: app đọc lại và **kiểm tra mọi ô tên vắng** (kể cả gõ tay trong Excel), báo tên sai hoặc không ăn bán trú.
- Sang tháng mới: app hỏi **Tạo sổ tháng mới**. Sổ mới (vd. `… T11.xlsx`) được làm từ sheet cuối của tháng trước, giữ nguyên mẫu, chữ ký, ghi chú.

## 8. An toàn dữ liệu & lỗi thường gặp

- Trước mỗi lần ghi, app **sao lưu** file cũ vào thư mục `SaoLuu` cạnh file (giữ 30 bản gần nhất).
- **"File đang mở trong Excel"**: đóng file đó trong Excel, rồi bấm *Thử lại*.
- **Không in trực tiếp được**: app báo vùng in và mở sổ bằng Excel để bạn in tay. App tự tính vùng in theo mẫu sổ:
  - tờ 1: A1 tới hết phần chữ ký (thường là A1:G46);
  - tờ 2: bảng suất ăn (thường là G68:O80).
- Khi app gặp lỗi, chi tiết được ghi vào `%APPDATA%\DiemDanhBanTru\loi.log`.
- **Cập nhật app lên bản mới**: tải lại `DiemDanhBanTru.exe` trong thư mục `tai-ve` của repo, chép đè lên file cũ (đóng app trước). Danh sách học sinh, ghép lớp, lịch và cài đặt nằm trong file dữ liệu `DuLieu_BanTru.xlsx` nên vẫn giữ nguyên.

## 9. Phím tắt

| Phím | Việc |
|---|---|
| Enter (ô tìm trong cửa sổ lớp) | Chỉ còn 1 em khớp thì tích / bỏ tích em đó |
| Esc (ô tìm trong cửa sổ lớp) | Xóa ô tìm; bấm lần nữa để đóng cửa sổ lớp |
| Ctrl+S | Lưu vào sổ |
| Ctrl+P | In 2 tờ |
| Ctrl+Z | Hoàn tác thao tác vừa làm |
