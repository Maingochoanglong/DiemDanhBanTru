# Hướng dẫn sử dụng app Điểm danh bán trú

App giúp giáo vụ làm sổ điểm danh bán trú hằng ngày:

- bấm vào lớp để tích em vắng (tên chữ to, có ô tìm tên không cần gõ dấu);
- ghi tên đúng quy tắc;
- tự đếm số vắng;
- tự tính bảng suất ăn (kể cả các em ăn ghép);
- ghi vào sổ để in bằng Excel như thường lệ (2 tờ).

Kết quả ghi vào **chính file sổ Excel đang dùng**, giữ y kiểu cũ: mỗi ngày 1 sheet, mỗi tháng 1 file.

---

## 1. Cài đặt

1. Trên trang repo GitHub, mở thư mục **`tai-ve`** → bấm **`DiemDanhBanTru.exe`** → nút **Download** (hoặc tải ở trang **Releases**).
2. Chép file vào một thư mục cố định (ví dụ `Documents\DiemDanhBanTru`), rồi bấm đúp để mở.
3. Lần đầu mở, Windows có thể báo *"Windows protected your PC"*. Bấm **More info → Run anyway**. Lý do: app không mua chữ ký số, file vẫn an toàn.

Máy cần Windows 10/11. In trực tiếp cần Microsoft Excel. Không cần cài Python.

## 2. Lần đầu sử dụng (khoảng 5 phút)

Mở app lần đầu, app **không hỏi chọn file**. Màn chính hiện dòng nhắc màu vàng; bạn tự làm khi sẵn sàng. Bấm **Cài đặt** ở thanh bên trái:

1. **Nhập danh sách…**: chọn file Excel danh sách. Dùng được 2 dạng:
   - **file đơn giản**: các cột *Lớp · Họ tên · Ngày sinh (hoặc Ngày tháng năm sinh) · Bán trú*, cột Bán trú ghi **Có** / **Không**. Có thể thêm cột **Tên gọi khác** (chỉ sửa trong file Excel này, app đọc khi nhập danh sách; ô trống = không có tên gọi khác): tên GV hay báo khác tên thật, vd. em có tên nước ngoài thường gọi là *Mi Mi*; nhiều tên thì cách nhau dấu phẩy, tên đầu là tên ghi vào sổ. Cột Họ tên chỉ ghi họ và tên thật. Em **trùng cả họ và tên** trong cùng lớp thì ghi chữ A/B ở cột Tên gọi khác (vd. *Gia Hưng A*, *Gia Hưng B*); để trống thì app tự đặt A/B theo ngày sinh (em sinh trước là A). Em **trùng tên nhưng khác họ** thì app hiện cả họ lẫn tên (vd. *Lò Gia Hân*, *Vi Gia Hân*);
   - file danh sách học sinh toàn trường, trong đó **em tô chữ đỏ là có ăn bán trú**.

   App liệt kê các thay đổi để bạn duyệt rồi bấm **Áp dụng**.
2. **Chọn sổ khác…** (lần đầu: chọn sổ): chọn sổ của tháng hiện tại (ví dụ `PH3.SỔ ĐIỂM DANH T11.xlsx`).
3. Nếu muốn, bấm **Đọc ghi chú sổ…**: app đọc ghi chú cột H và đề xuất cập nhật danh sách, ví dụ:
   - "Thứ 6 hàng tuần cắt 2 em …" → đánh dấu **cắt thứ 6**: thứ 6 các em tự được tính vắng.
   - "Tháng 11 cắt …" (hoặc "T11 CẮT …") → **cắt bán trú từ 01/11**; "Từ 12/10 cắt bán trú …" → cắt từ 12/10.
   - "thêm … ghép 1.3" → thêm em vào bán trú lớp đó, ăn ghép ở nhóm 1.3.

   Bỏ tích dòng nào không đúng rồi bấm **Áp dụng**.

Dữ liệu riêng của app (danh sách HS, ghép lớp, cài đặt) lưu ở `Documents\DiemDanhBanTru\DuLieu_BanTru.xlsx`. File này mở được bằng Excel để xem.

## 3. Mỗi sáng

Thanh bên trái có các trang: **Điểm danh** (dùng hằng ngày), **Suất ăn**, **Học sinh**, **Lịch thêm/cắt**, **Cài đặt**. Thanh trên cùng để chọn ngày: gõ ngày dạng `dd/mm/yyyy` rồi Enter, hoặc bấm nút lịch, 2 nút mũi tên, **Hôm nay**; nút **Mở sổ Excel** mở sổ đang dùng.

Trang **Điểm danh**:

| Phần | Dùng để |
|---|---|
| **Bảng điểm danh** | Có các cột như sổ: **Lớp · GVCN · Sĩ số · Vắng · Hiện diện · Tên học sinh vắng · Ghi chú**, dòng cộng từng khối và **TỔNG CỘNG**. Màu dòng: xám = chưa báo, xanh = đủ, cam = có vắng, đỏ = cần xem (tên chưa rõ, sĩ số khác sổ). Thứ 6, lớp chưa báo vẫn ghi *(chưa báo)* kèm dòng xám *nghỉ T6: …* (các em cắt thứ 6 đã tự tính vắng). Lớp có ghi chú trong sổ kiểu *Không nói gì là đủ* thì GV không nhắn app vẫn tính là **đủ**. Phía trên bảng có dòng **Chưa báo (n): 1D15 · 4D21 …** — bấm mã lớp để mở lớp đó; nút lọc **Tất cả / Chưa báo / Có vắng** ở góc phải để bảng chỉ hiện các lớp cần xem. Ghi chú dài: rê chuột để xem đủ. Phía trên bảng có **Tổng suất = hiện diện** (xanh khi khớp, đỏ khi lệch — bấm để xem trang Suất ăn). |
| **Bảng chọn tên** (**bấm vào 1 lớp**) | Hiện tên các em ăn bán trú của lớp dạng **ô chữ to**. **Bấm vào ô tên = vắng** (ô chuyển đỏ), bấm lại để bỏ. Ô **Tìm tên** to ở trên, gõ không cần dấu (`long`, `hai long`, `h long` đều ra *Hải Long*); ô tìm **chỉ để lọc** tên (không tự chọn, Enter cũng không chọn); chọn vắng = **bấm vào ô tên**. Gõ hoặc **dán nhiều tên cách nhau dấu phẩy** (vd. `Gia Huy, Bảo Anh, Minh`) thì hiện các em có các tên đó để bấm chọn. Gõ đủ chữ thì chỉ hiện em có đủ các chữ đó (gõ `gia huy` không ra *Huỳnh Gia Lộc*); gõ có dấu thì ưu tiên em đúng dấu (`Nguyên Vũ` không ra *Nguyễn Vũ Khang*); em có tên cuối khớp đứng trước (`Thư` → *Minh Thư* trước *Thư Kỳ*); tên nào không có trong bảng thì hiện thành **ô viền đứt** ghi lý do: *Không ăn bán trú* (ô xám) hoặc *Không có trong danh sách* (ô vàng, nên xem lại tên) — các ô này không bấm được, không tính. Nút **Lớp này đủ** (lớp có em nghỉ thứ 6 thì nút ghi **Đủ (trừ em nghỉ thứ 6)**), ô **Ghi chú (cột H)**, nút **Thêm/cắt bán trú**. Bấm **Xong** (hoặc Esc) để đóng. |

Hộp hỏi và bảng chọn tên luôn hiện **giữa màn hình**, nền phía sau tối đi.


Trang **Suất ăn**: bảng suất ăn cho từng nhóm bảo mẫu, tính như công thức trong sổ (hiện diện các lớp + em ghép − em ghép vắng), ghi tên em ghép vắng ngay trong dòng. Dòng trên cùng phải là **Tổng suất = hiện diện**; khi lệch app ghi rõ **thừa / thiếu bao nhiêu suất** và lý do ở ngay dưới. Em ăn ghép vắng mà danh sách chưa ghi nhóm: app hỏi **em đó ăn nhóm nào** (bấm nút nhóm; bấm tên em trong dòng để chọn lại). Bấm **Lưu vào sổ** khi suất ăn còn lệch thì app hỏi lại trước khi lưu.

### Kiểm tra tên trong sổ

Mở một ngày **đã có trong sổ**, app đối chiếu mọi ô tên vắng (kể cả gõ tay trong Excel). Tên không khớp danh sách hiện dòng đỏ phía trên bảng (bấm vào để mở lớp đó) và thành nút đỏ trong bảng chọn tên: bấm vào để **chọn em đúng**, **giữ nguyên chữ đã ghi**, hoặc **bỏ qua tên này**. Không có em nào tên gần giống thì app cho chọn trong cả lớp. Muốn lần sau app tự nhận ra tên đó: ghi tên vào cột *Tên gọi khác* trong file Excel danh sách rồi nhập lại danh sách.

App còn đối chiếu số trong sổ: lớp lệch sĩ số hoặc thiếu/thừa tên vắng thì dòng lớp tô đỏ và ghi lý do ở cột Ghi chú (vd. "Thiếu 1 tên (GV báo vắng 3 em, mới ghi 2)").

### Lưu vào sổ

1. Bấm **Lưu vào sổ** (Ctrl+S). Nếu chưa có sheet ngày hôm nay, app sao chép sheet hôm trước rồi điền số liệu.
   - Còn **tên chưa rõ** thì app **chưa cho lưu**; bấm **Xử lý ngay** để app mở lớp cần xử lý.
   - Còn điều cần biết thì app hỏi **một lần** trong hộp **Kiểm tra trước khi lưu**: **lớp chưa báo** (lưu thì tính **đủ**),
     **suất ăn thừa/thiếu** (nút **Xem trang Suất ăn**), **sĩ số danh sách khác sổ** (chọn **giữ sĩ số như sổ** hay **dùng sĩ số theo danh sách**).
     Bấm **Hủy** để ở lại sửa.
2. In: bấm **Mở sổ Excel** rồi in trong Excel như thường lệ (tờ 1 bảng điểm danh, tờ 2 bảng suất ăn).

Nút **Hoàn tác** (Ctrl+Z) bỏ thao tác vừa làm.

## 4. Lịch thêm / cắt bán trú, nghỉ thứ 6

Trang **Lịch thêm/cắt** dùng khi biết trước một em sẽ thôi ăn hoặc bắt đầu ăn, ví dụ từ ngày mai hay từ đầu tháng sau:

1. Bấm **Cắt bán trú…**, **Thêm bán trú…** hoặc **Cắt thứ 6…**.
2. Chọn lớp, rồi **tích** các em. Muốn thêm em chưa có trong danh sách: tích dòng cuối *Học sinh mới…* rồi gõ họ tên.
3. Chọn ngày áp dụng: bấm **Ngày học kế tiếp**, **Đầu tháng sau**, hoặc gõ ngày.
4. Bấm **Lưu lịch**.

Từ ngày đó app tự đổi sĩ số và danh sách tên của lớp. Trên trang Điểm danh, cột Ghi chú của lớp đó có chữ **[Lịch]**. Sĩ số đổi theo lịch đã đặt thì app không hỏi "sĩ số khác nhau" khi lưu.

Nếu để tích ô *Ghi chú vào cột H*, app tự ghi chú vào cột H như cách bạn vẫn viết, ví dụ "Tháng 11 cắt bán trú Hồ Khánh Ngọc" hoặc "Từ 30/10 cắt bán trú …". Ghi chú tự mang sang các ngày sau. Nhớ bấm **Lưu vào sổ** để ghi chú vào sổ.

**Thứ 6 học nửa buổi**: em nào nghỉ ăn thứ 6 hàng tuần thì bấm **Cắt thứ 6…**. Mỗi thứ 6, app tự tính các em này vắng, kể cả khi GV báo "đủ".

Danh sách lịch chia nhóm: *Sắp áp dụng*, *Hàng tuần – cắt thứ 6*, *Đã áp dụng (30 ngày qua)*. Tích dòng rồi bấm **Hủy lịch đã tích** để hủy.

Nút **Thêm/cắt bán trú** ở cuối bảng chọn tên đặt lịch cho lớp đó. Bỏ lịch (kể cả *cắt thứ 6 hàng tuần*): trang **Lịch thêm/cắt**, tích dòng lịch rồi bấm **Hủy lịch đã tích**. Ô tên có nhãn nhỏ *nghỉ T6* hoặc *cắt từ 01/11* nếu em đã có lịch.

## 5. Ghép lớp (lớp 1.5, 4.4 …)

Lớp ghép là lớp không có hàng riêng trong bảng suất ăn: các em chia sang ăn ở nhóm khác (1.1, 1.2 …).

- Nhóm ăn của từng em ghi ở cột **Ăn ghép** trong file Excel danh sách (vd. *1.3*; để trống = không ăn ghép), rồi vào **Cài đặt → Nhập danh sách học sinh**. Đây là chỗ duy nhất ghi nhóm ghép.
- Chân trang **Suất ăn** ghi mỗi lớp ghép đã ghi nhóm cho bao nhiêu em (vd. *1D19: 1/29 em*); bấm **Xem các em** để mở trang **Học sinh** lọc sẵn lớp đó (cột **Ăn ghép**).
- Em đã có nhóm mà vắng: app tự trừ đúng nhóm, tự điền ô **vắng** trong bảng suất ăn của sổ.
- Em chưa có nhóm mà vắng: trang **Suất ăn** hỏi em đó ăn nhóm nào (chỉ cho ngày đó). Mở lại ngày đã lưu, app đọc lại ô **vắng** trong sổ; chỉ hỏi lại khi không chắc em nào ở nhóm nào.
- Lớp ghép chưa ghi nhóm cho đủ mọi em thì số em ghép mỗi nhóm giữ như sổ hôm trước.
- Em có thể ghép sang nhóm khác khối (vd. em lớp 1 ăn cùng nhóm 2.1): cột **Ăn ghép** ghi mã nhóm đó là được.

### Đổi cách ghép (đầu năm học, hoặc giữa năm): sheet "Nhóm ăn"

Bảng suất ăn cuối mỗi tờ điểm danh (lớp nào ăn chung dòng nào) khai báo ở sheet **Nhóm ăn** trong file Excel danh sách, không cần sửa công thức trong sổ:

| Tên dòng (in ở sổ) | Các lớp ăn chung | Mã ghép lẻ |
|---|---|---|
| cô Lan | 1D20, 3D22, 5D22 | |
| cô Mai | 2D21, 3D23, 4D22 | |
| *(dòng trống = cách dòng)* | | |
| 1.1 ghép | 1D15 | 1.1 |
| 2.4 ghép 2.5 | 2D19, 2D20 | |
| 4.2 ghép 4.4 | 4D19 | 4.2 |

- Mỗi dòng của sheet = một dòng bảng suất ăn, đúng thứ tự. **Các lớp ăn chung** là các lớp ăn cả lớp ở dòng đó (ghi *2D19* hay *2.4* đều được).
- **Mã ghép lẻ**: chỉ ghi khi dòng nhận em ghép lẻ từ lớp chia nhóm (như 1D19, 4D21). Em ăn dòng nào thì cột **Ăn ghép** của em ghi đúng mã đó. Tên dòng phải bắt đầu bằng mã (vd. *1.2 ghép*).
- Lớp không có ở sheet và không có em ghi **Ăn ghép** = **ăn tại lớp**.
- Sửa xong: **Cài đặt → Nhập danh sách…**. Hộp duyệt có dòng *Bảng Nhóm ăn: …* ghi rõ thay đổi; sheet ghi sai (lớp không có, một lớp ở 2 dòng, mã trùng…) thì app báo lỗi và giữ bảng cũ.
- **Từ tờ ngày mới** (kể cả tờ đầu tháng của sổ tháng mới), app tự dựng bảng suất ăn theo sheet này: dòng, nhãn, công thức, ô số em ghép, ô cộng các nhóm, ô cộng các lớp ăn tại lớp, vùng in. **Các tờ đã có trong sổ giữ nguyên.** Trang **Suất ăn** ghi rõ khi bảng của ngày đang mở khác sheet Nhóm ăn.
- File danh sách không có sheet Nhóm ăn thì app giữ bảng suất ăn như sổ (như trước).

## 6. Học sinh

Trang **Học sinh** chỉ để **tra cứu**: tìm em, lọc theo lớp, xem em nào ăn bán trú, **tên gọi khác** (như cột trong file Excel), ăn ghép, lịch cắt/thêm.

- Muốn **thêm, sửa, xóa học sinh** (kể cả tên gọi khác): sửa trong **file Excel danh sách** rồi vào Cài đặt → **Nhập danh sách…**.
- Lịch **cắt bán trú từ ngày**, **ăn từ ngày**, **cắt thứ 6**: đặt ở trang **Lịch thêm/cắt** hoặc menu *Thêm/cắt bán trú* trong bảng tên của lớp.

Việc ít làm với danh sách nằm trong trang **Cài đặt**:

- **Nhập danh sách…** khi có danh sách mới (file đơn giản *Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không) · Tên gọi khác · Ăn ghép*, có thể kèm sheet **Nhóm ăn** — xem mục 5; hoặc file danh sách học sinh toàn trường tô đỏ). App liệt kê từng thay đổi (em mới, đổi lớp, thôi/bắt đầu ăn) để bạn duyệt. Thông tin cắt thứ 6, ăn ghép… vẫn giữ nguyên.
- Sửa file Excel danh sách xong, lần mở app sau app tự thấy file đã sửa và hỏi **Nhập lại** (hoặc *Để sau*).
- **Đọc ghi chú sổ…**: app đọc ghi chú cột H của sổ (vd. "Tháng 11 cắt …", "Thứ 6 hàng tuần cắt …") để gợi ý cập nhật danh sách.

Lớp có sĩ số theo danh sách khác sĩ số trong sổ được tô đỏ ở bảng điểm danh. Khi lưu, nếu còn lệch, app hỏi: **giữ sĩ số như trong sổ** hay **dùng sĩ số theo danh sách**.

## 7. Ngày cũ, tháng mới

- Đổi ngày: gõ vào ô ngày (`dd/mm/yyyy`) rồi Enter, bấm nút lịch, 2 nút mũi tên hoặc **Hôm nay**. Ngày đang mở có thay đổi chưa lưu thì app hỏi **Lưu rồi chuyển ngày / Không lưu / Ở lại**.
- Mở một ngày **đã có trong sổ**: app đọc lại và **kiểm tra mọi ô tên vắng** (kể cả gõ tay trong Excel), báo tên sai hoặc không ăn bán trú.
- Sang tháng mới: app hỏi **Tạo sổ tháng mới**. Sổ mới (vd. `… T11.xlsx`) được làm từ sheet cuối của tháng trước, giữ nguyên mẫu, chữ ký, ghi chú.

## 8. An toàn dữ liệu & lỗi thường gặp

- Trước mỗi lần ghi, app **sao lưu** file cũ vào thư mục `SaoLuu` cạnh file (giữ 30 bản gần nhất).
- **Sổ tạm (phòng mất điện)**: sau mỗi thao tác, app tự lưu một bản sao của sổ, tên là tên sổ thêm chữ `tamthoi`, nằm cạnh sổ chính (vd. `SO DIEM DANH T10 tamthoi.xlsx`). Dòng trạng thái dưới bảng ghi *"đã lưu tạm lúc …"*.
  - Bấm **Lưu vào sổ** thì app ghi vào sổ chính và xóa sổ tạm.
  - Nếu máy tắt đột ngột khi chưa lưu, lần mở app sau sẽ hỏi **Khôi phục**. Chọn Khôi phục để làm tiếp, rồi nhớ bấm Lưu vào sổ.
  - Thoát app và chọn *Không lưu*, hoặc đổi ngày và chọn *Không lưu*, thì sổ tạm cũng bị xóa.
  - Có thể mở sổ tạm bằng Excel để xem: sheet của ngày đang làm đã được điền sẵn.
- **"File đang mở trong Excel"**: đóng file đó trong Excel, rồi bấm *Thử lại*.
- **Không in trực tiếp được**: app báo vùng in và mở sổ bằng Excel để bạn in tay. App tự tính vùng in theo mẫu sổ:
  - tờ 1: A1 tới hết phần chữ ký (thường là A1:G46);
  - tờ 2: bảng suất ăn (thường là G68:O80).
- Khi app gặp lỗi, chi tiết được ghi vào `%APPDATA%\DiemDanhBanTru\loi.log`.
- Máy chưa có **Microsoft Edge WebView2** (hiếm, Windows 11 có sẵn): app tự mở giao diện bằng trình duyệt Edge, vẫn dùng bình thường. Muốn mở trong cửa sổ riêng thì cài WebView2 Runtime miễn phí của Microsoft.
- **Cập nhật app lên bản mới**: tải lại `DiemDanhBanTru.exe` trong thư mục `tai-ve` của repo, chép đè lên file cũ (đóng app trước). Danh sách học sinh, ghép lớp, lịch và cài đặt nằm trong file dữ liệu `DuLieu_BanTru.xlsx` nên vẫn giữ nguyên.

## 9. Phím tắt

| Phím | Việc |
|---|---|
| Esc | Đóng bảng chọn tên / hộp đang mở |
| Ctrl+S | Lưu vào sổ |
| Ctrl+Z | Hoàn tác thao tác vừa làm |
