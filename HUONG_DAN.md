# Hướng dẫn sử dụng app Điểm danh bán trú

App giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- kiểm tra tên học sinh vắng mà GVCN nhắn qua Zalo;
- ghi tên đúng quy tắc;
- tự đếm số vắng;
- tự tính bảng suất ăn (kể cả các em ăn ghép);
- in 2 tờ.

Kết quả ghi vào **chính file sổ Excel đang dùng**, giữ y kiểu cũ: mỗi ngày 1 sheet, mỗi tháng 1 file.

---

## 1. Cài đặt

1. Vào trang **Releases** của repo trên GitHub, tải file **`DiemDanhBanTru.exe`**.
2. Chép file vào một thư mục cố định (ví dụ `Documents\DiemDanhBanTru`), rồi bấm đúp để mở.
3. Lần đầu mở, Windows có thể báo *"Windows protected your PC"*. Bấm **More info → Run anyway**. Lý do: app không mua chữ ký số, file vẫn an toàn.

Máy cần Windows 10/11. In trực tiếp cần Microsoft Excel. Không cần cài Python.

## 2. Lần đầu sử dụng (khoảng 5 phút)

App hỏi lần lượt:

1. **Chọn file danh sách học sinh**: file `.xls`/`.xlsx`, dùng được 2 dạng:
   - file CDHS của trường, trong đó **em tô chữ đỏ là có ăn bán trú**;
   - file gọn 5 cột *Tên lớp học · Họ tên · Ngày sinh · Ăn bán trú · Ghép lớp*, trong đó cột **Ăn bán trú** ghi **X** nếu em có ăn, cột **Ghép lớp** ghi nhóm ăn ghép (vd. `1.2`).

   App báo số em đọc được. Với file CDHS, app chỉ ra các em có màu chữ không khớp cột "Phân loại HS" để bạn xem lại.
2. **Chọn sổ điểm danh tháng hiện tại** (ví dụ `PH3.SỔ ĐIỂM DANH T10.xlsx`).
3. **Gợi ý từ ghi chú trong sổ**: app đọc các ghi chú cột H và đề xuất cập nhật danh sách, ví dụ:
   - "Thứ 6 hàng tuần cắt 2 em …" → đánh dấu **cắt thứ 6**: thứ 6 các em tự được tính vắng.
   - "Tháng 11 cắt …" (hoặc "T11 CẮT …") → **cắt bán trú từ 01/11**; "Từ 12/10 cắt bán trú …" → cắt từ 12/10. Sĩ số tự giảm từ ngày đó.
   - "Cắt …" không ghi ngày → cắt từ ngày của sheet đầu tiên có ghi chú đó.
   - "thêm … ghép 1.3" → thêm em vào bán trú lớp đó, ăn ghép ở nhóm 1.3.
   - Cùng một em có nhiều ghi chú → lấy ngày sớm nhất.

   Bỏ tích dòng nào không đúng rồi bấm **Áp dụng**.

Dữ liệu riêng của app (danh sách HS, ghép lớp, cài đặt) lưu ở `Documents\DiemDanhBanTru\DuLieu_BanTru.xlsx`. File này mở được bằng Excel để xem.

## 3. Mỗi sáng

Màn hình **Điểm danh** gồm:

| Phần | Dùng để |
|---|---|
| **① Dán tin nhắn Zalo** (trên cùng) | Copy tin nhắn của GVCN trong Zalo, bấm vào ô rồi **Ctrl+V**. Dán 1 tin hay cả đoạn nhiều tin đều được. Dòng chữ bên dưới tóm tắt kết quả; bấm vào đó (hoặc nút **Kết quả chi tiết…**) để xem từng tên. |
| **② Bảng điểm danh** (trái) | Giống tờ sổ: Lớp · GVCN · Sĩ số · Vắng · Hiện diện · Tên học sinh vắng · Ghi chú, có dòng cộng từng khối và **TỔNG CỘNG**. Mỗi dòng tô màu: **xám** = chưa báo, **xanh** = đủ, **cam** = có vắng, **đỏ** = cần xem. 📅 ở cột Ghi chú: sĩ số đổi theo lịch thêm/cắt. |
| **③ Lớp đang chọn** (phải, trên) | Bấm 1 dòng lớp trong bảng: hiện danh sách em ăn bán trú của lớp, **tích = vắng**. Dùng khi đọc tin trên điện thoại, hoặc để sửa. Có nút *Lớp này đủ*, ô tìm tên, ô ghi chú cột H. |
| **④ Bảng suất ăn** (phải, dưới) | App tự tính số suất cho từng nhóm bảo mẫu, tự trừ các em ghép vắng. Dòng cuối phải là **Tổng suất = hiện diện ✔**. Bấm vào 1 nhóm để xem chi tiết. |

### Dán tin chép từ Zalo trên máy tính

Có thể chép **cả đoạn tin nhắn** trong nhóm Zalo trên máy tính, mỗi tin có dạng:

```
[29/10/2026 07:29:43] Tên Zalo người gửi: 2D19: 30/31( Bảo Long)
```

- App **chỉ lấy tin của ngày đang mở**. Tin của ngày khác được bỏ qua và báo lại (vd. "bỏ qua 50 tin ngày khác"). Muốn nhập ngày khác thì mở ngày đó rồi dán lại cùng đoạn tin.
- Tin được đọc **theo giờ gửi**: GV nhắn sửa thì tin sau thay cho tin trước của cùng lớp.
- Tin **không ghi mã lớp** (vd. "Vắng Hải Long và Tuấn Anh"): app tìm lớp theo **tên Zalo người gửi** so với cột GVCN của sổ (vd. tên Zalo "Lan Nguyễn" là cô Nguyễn Thị Ngọc Lan, "Phamthanhtam" là thầy Phạm Thanh Tâm). Người gửi đã từng nhắn kèm mã lớp thì app nhớ lớp của người đó. Nếu vẫn không biết, app đoán theo tên học sinh.
- Lời chào, "dạ", "ok cô"… không có chữ "vắng/nghỉ/đủ" hay sĩ số thì app bỏ qua.
- **Tin báo lịch** (vd. "Lớp 5D21: tháng 11 cắt bán trú Gia Huy") không tính là vắng. App hiện dòng **📅 Đề nghị**: bấm đúp để áp dụng, app tự cắt/thêm em đó và ghi chú cột H ("Tháng 11 cắt bán trú …"). Nếu lịch đó đã có sẵn, app chỉ báo "đã có".

### Kiểm tra tên

Mỗi tên GV ghi được kiểm tra (xem trong **Kết quả chi tiết…**):

- ✔ **xanh**: đúng em trong lớp, có ăn bán trú. Tên được ghi theo quy tắc (tên đệm + tên; trùng thì họ tên đầy đủ; trùng cả họ tên thì thêm A/B theo ngày sinh).
- ⚠ **cam**: nhiều em trùng tên. **Bấm đúp** để chọn đúng em.
- ⛔ **xám**: em có trong lớp nhưng **không ăn bán trú**, app bỏ qua, không ghi.
- ✖ **đỏ**: không tìm thấy trong lớp (có gợi ý tên gần giống, hoặc báo em học lớp khác). Bấm đúp để chọn, ghi nguyên văn, hoặc bỏ qua.

Tên chưa rõ cũng hiện thành nút ở phần **③** khi chọn lớp đó, bấm vào để xử lý.

App còn đối chiếu số GV báo: nếu GV ghi "38/41" mà sĩ số là 40, hoặc ghi 3 tên nhưng số vắng là 2, dòng lớp đó tô đỏ và ghi lý do ở cột Ghi chú.

### Lưu và in

Khi các lớp đã báo xong:

1. Bấm **Lưu vào sổ** (Ctrl+S). Nếu chưa có sheet ngày hôm nay, app sao chép sheet hôm trước rồi điền số liệu.
2. Bấm **In 2 tờ** (Ctrl+P): tờ 1 là bảng điểm danh, tờ 2 là bảng suất ăn. Bấm **Xem trước** nếu muốn xem trước khi in.

Nút **Copy lớp chưa báo** chép danh sách lớp (kèm tên GVCN) chưa báo để dán vào Zalo nhắc.

## 4. Lịch thêm / cắt bán trú, nghỉ thứ 6

Tab **Lịch thêm/cắt** dùng khi biết trước một em sẽ thôi ăn hoặc bắt đầu ăn, ví dụ từ ngày mai hay từ đầu tháng sau:

1. Bấm **✂ Cắt bán trú…** hoặc **＋ Thêm bán trú…**.
2. Chọn lớp, rồi chọn em (giữ Ctrl để chọn nhiều em). Muốn thêm em chưa có trong danh sách: chọn dòng cuối *Học sinh mới…* rồi gõ họ tên.
3. Chọn ngày áp dụng: bấm **Ngày học kế tiếp**, **Đầu tháng sau**, hoặc gõ ngày.
4. Bấm **Lưu lịch**.

Từ ngày đó app tự đổi sĩ số và danh sách tích vắng của lớp. Trên màn Điểm danh hiện dòng "📅 Lịch … có hiệu lực từ hôm nay". Sĩ số đổi theo lịch đã đặt thì app không hỏi "sĩ số khác nhau" khi lưu.

Nếu để tích ô *Ghi chú vào cột H*, app tự ghi chú vào cột H như cách bạn vẫn viết, ví dụ "Tháng 11 cắt bán trú Hồ Khánh Ngọc" hoặc "Từ 30/10 cắt bán trú …". Ghi chú tự mang sang các ngày sau. Nhớ bấm **Lưu vào sổ** để ghi chú vào sổ.

**Thứ 6 học nửa buổi**: em nào nghỉ ăn thứ 6 hàng tuần thì bấm **Cắt thứ 6 hàng tuần…**. Mỗi thứ 6, app tự tính các em này vắng, kể cả khi GV báo "đủ".

Danh sách lịch chia nhóm: *Sắp áp dụng*, *Hàng tuần – cắt thứ 6*, *Đã áp dụng (30 ngày qua)*. Chọn dòng rồi bấm **Hủy lịch đã chọn** để hủy.

Làm nhanh ngay trên màn Điểm danh: **bấm chuột phải vào tên em** ở phần ③ để chọn *Cắt bán trú từ ngày…* hoặc *Cắt thứ 6 hàng tuần…*. Nút **Thêm/cắt…** (hoặc chuột phải vào dòng lớp trong bảng) đặt lịch cho cả lớp. Bên cạnh tên em có nhãn *(nghỉ T6)* hoặc *(cắt từ 01/11)* nếu em đã có lịch.

## 5. Ghép lớp (lớp 1.5, 4.4 …)

Tab **Ghép lớp** liệt kê các em ăn bán trú của lớp ghép (lớp không có hàng riêng trong bảng suất ăn).

- Chọn một hoặc nhiều em (giữ Ctrl), rồi bấm **→ Ăn ở 1.1**, **→ Ăn ở 1.2**…
- Hoặc bấm **Dán danh sách ghép…** và gõ mỗi dòng: `1.1: Bảo Ngọc, Gia Hân, Minh Khôi`.
- Bấm **Lưu danh sách ghép**.

Khi đã gán đủ cả lớp, mỗi lần em ghép vắng, app tự điền ô **vắng** đúng hàng trong bảng suất ăn. Khi chưa gán đủ, app giữ số em ghép như sổ cũ; bạn **bấm đúp vào hàng nhóm** (có dấu ✎) trong bảng suất ăn để nhập số em ghép vắng.

Nếu nhập danh sách từ file có cột **Ghép lớp**, app tự gán nhóm ghép theo cột đó.

## 6. Học sinh

Tab **Học sinh** dùng để:

- tìm em, lọc theo lớp;
- **Thêm học sinh**, hoặc **Sửa** (bấm đúp) các thông tin: ăn bán trú, *cắt bán trú từ ngày*, *bắt đầu ăn từ ngày*, *cắt thứ 6*, *ăn ghép tại*, *tên ghi sổ* (nếu muốn ghi khác tên tự đặt);
- **Nhập / cập nhật từ file CDHS…** khi trường có danh sách mới (file CDHS tô đỏ, hoặc file 5 cột có X). App liệt kê từng thay đổi (em mới, đổi lớp, thôi/bắt đầu ăn, đổi nhóm ghép) để bạn duyệt. Thông tin cắt thứ 6… vẫn giữ nguyên.
- **Xuất danh sách…**: ghi ra file 5 cột *Tên lớp học · Họ tên · Ngày sinh · Ăn bán trú (X) · Ghép lớp*, tính theo ngày bạn chọn (vd. ngày đầu tháng sau). File này gửi cho người khác xem, hoặc nhập lại vào app.

Bảng **Sĩ số bán trú từng lớp** bên phải tô đỏ lớp có sĩ số theo danh sách khác sĩ số trong sổ. Khi lưu, nếu còn lệch, app hỏi: **giữ sĩ số như trong sổ** hay **dùng sĩ số theo danh sách**.

## 7. Ngày cũ, tháng mới

- Đổi ngày bằng ô **Ngày**, nút ◀ ▶ hoặc **Hôm nay**.
- Mở một ngày **đã có trong sổ**: app đọc lại và **kiểm tra mọi ô tên vắng** (kể cả gõ tay trong Excel), báo tên sai hoặc không ăn bán trú.
- Sang tháng mới: app hỏi **Tạo sổ tháng mới**. Sổ mới (vd. `… T11.xlsx`) được làm từ sheet cuối của tháng trước, giữ nguyên mẫu, chữ ký, ghi chú.

## 8. An toàn dữ liệu & lỗi thường gặp

- Trước mỗi lần ghi, app **sao lưu** file cũ vào thư mục `SaoLuu` cạnh file (giữ 30 bản gần nhất).
- **"File đang mở trong Excel"**: đóng file đó trong Excel, rồi bấm *Thử lại*.
- **Không in trực tiếp được**: app mở sổ bằng Excel để bạn in tay (vùng in hiện trong tab *Cài đặt*).
- Sửa vùng in ở tab **Cài đặt**, mặc định:
  - tờ 1: A1 tới hết phần chữ ký (A1:G46);
  - tờ 2: bảng suất ăn (G68:O80).
- Khi app gặp lỗi, chi tiết được ghi vào `%APPDATA%\DiemDanhBanTru\loi.log`.

## 9. Phím tắt

| Phím | Việc |
|---|---|
| Ctrl+V (trong ô dán) | Dán và kiểm tra tin nhắn |
| Ctrl+Enter | Kiểm tra lại nội dung ô dán |
| Ctrl+S | Lưu vào sổ |
| Ctrl+P | In 2 tờ |
| Ctrl+Z | Hoàn tác thao tác vừa làm |
