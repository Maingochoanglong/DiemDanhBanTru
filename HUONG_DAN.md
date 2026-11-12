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
4. App mở giao diện trong **trình duyệt** của máy (Edge/Chrome), ở địa chỉ `http://127.0.0.1:47615`. Mọi thứ vẫn chạy trên máy này, không cần mạng, không gửi dữ liệu đi đâu.
   - **Thoát app**: bấm **Thoát** ở góc dưới thanh bên trái (app hỏi lưu nếu còn thay đổi), hoặc đóng thẻ trình duyệt đó (trình duyệt hỏi lại nếu còn thay đổi chưa lưu vào sổ).
   - Lỡ đóng thẻ khi đang làm dở: mở lại app, app hỏi **Khôi phục** từ sổ tạm (mục 8).
   - Bấm đúp mở app lần nữa khi app đang chạy: chỉ mở thêm thẻ trình duyệt, không chạy 2 app cùng lúc. Tải lại trang (F5) không làm mất thay đổi.

Máy cần Windows 10/11 và Microsoft Excel (để mở, in sổ). Không cần cài Python.

## 2. App làm việc với 3 file

| File | Dùng để | Ai sửa |
|---|---|---|
| **Danh sách học sinh** (Excel) | biết em nào ăn bán trú, tên gọi khác, ăn ghép, lịch thêm/cắt (cột Ghi chú), cách ghép ăn (sheet Nhóm ăn) | **bạn, bằng Excel**. App chỉ đọc; sửa file xong, mở ngày là app đọc lại |
| **Sổ điểm danh tháng** (Excel) | sổ như thường lệ, mỗi ngày 1 sheet, mỗi tháng 1 file | app ghi sheet của ngày khi bấm **Lưu vào sổ** |
| **CaiDat.txt** (cạnh file `DiemDanhBanTru.exe`) | nhớ đang dùng sổ nào, file danh sách nào, cổng của app (`cong`, chỉ đổi khi trùng chương trình khác), thanh bên thu gọn | app tự ghi; mở bằng Notepad sửa được |

Ngoài ra chỉ có **sổ tạm** (mục 8): file nhỏ cạnh sổ, có khi đang làm dở và tự xóa khi đã lưu vào sổ.

**File danh sách học sinh** có các cột (tên cột viết như dưới, thứ tự tùy ý):

| Lớp | Họ tên | Ngày sinh | Bán trú | Tên gọi khác | Ăn ghép | Ghi chú |
|---|---|---|---|---|---|---|
| 1D15 | Kha Bảo Ngọc | 02/03/2020 | Có | | | cắt thứ 6 |
| 1D15 | Tô Minh Khôi | 03/03/2020 | Có | | | cắt từ 30/10 |
| 1D19 | Phùng Gia Hân | 02/02/2020 | Có | | 1.2 | |
| 2D17 | Viên Duy Mạnh | 01/01/2019 | Không | | | ăn từ 3/11 |

- **Bán trú**: *Có* / *Không*. Dùng file danh sách học sinh toàn trường cũng được, khi đó **em tô chữ đỏ là có ăn bán trú**.
- **Tên gọi khác**: tên GV hay báo khác tên thật (vd. *Mi Mi*). Nhiều tên thì cách nhau dấu phẩy, tên đầu được ghi vào sổ. Em **trùng cả họ và tên** trong cùng lớp thì ghi *Gia Hưng A*, *Gia Hưng B*; để trống thì app tự đặt A/B theo ngày sinh.
- **Ăn ghép**: nhóm ăn của em lớp ghép (mục 5).
- **Lớp tính BT** (cột tùy chọn): em học lớp này nhưng tính bán trú ở lớp khác thì ghi lớp đó (vd. *1D16*).
- **Ghi chú**: lịch thêm / cắt bán trú, ghi ngắn, nhiều ý cách nhau dấu phẩy:
  - `cắt thứ 6`: mỗi thứ 6 em tự được tính vắng (kể cả khi GV báo "đủ");
  - `cắt từ 30/10` (hoặc `thôi ăn từ 30/10`, `nghỉ ăn từ 30/10`): từ ngày 30/10 em thôi ăn, sĩ số tự giảm;
  - `ăn từ 3/11`: từ ngày 3/11 em bắt đầu ăn, sĩ số tự tăng (cột Bán trú ghi *Không* cũng được).

  Ghi kiểu *T11 cắt*, *tháng 11 ăn BT*, *30/10/2026* hay không dấu đều được. Chữ khác (vd. *dị ứng tôm*) app bỏ qua. Trang **Học sinh**, cột **App hiểu là**, cho biết app đã hiểu ghi chú thế nào.

**Mỗi lần tải bản app mới về**, lần đầu mở app hiện màn **Thiết lập trước khi điểm danh**: **chọn sổ điểm danh** của tháng đang làm, **chọn file danh sách học sinh**, rồi bấm **Bắt đầu điểm danh**. Mở lại cùng bản thì không hỏi nữa. Đổi file sau này: trang **Cài đặt** → **Chọn sổ khác…** / **Chọn file khác…**.

## 3. Mỗi sáng

Thanh bên trái có các trang: **Điểm danh** (dùng hằng ngày), **Suất ăn**, **Học sinh**, **Cài đặt**. Thanh trên cùng để chọn ngày: gõ ngày dạng `dd/mm/yyyy` rồi Enter, hoặc bấm nút lịch, 2 nút mũi tên, **Hôm nay**; nút **Mở sổ Excel** mở sổ đang dùng.

Trang **Điểm danh**:

| Phần | Dùng để |
|---|---|
| **Bảng điểm danh** | Có các cột như sổ: **Lớp · GVCN · Sĩ số · Vắng · Hiện diện · Tên học sinh vắng · Ghi chú**, dòng cộng từng khối và **TỔNG CỘNG**. Màu dòng: xám = chưa báo, xanh = đủ, cam = có vắng, đỏ = cần xem (tên chưa rõ, sĩ số khác sổ). Thứ 6, lớp chưa báo vẫn ghi *(chưa báo)* kèm dòng xám *nghỉ T6: …* (các em cắt thứ 6 đã tự tính vắng). Lớp **đủ hay vắng luôn do bạn bấm**: app không tự tính đủ (kể cả lớp có ghi chú kiểu *Không nói gì là đủ*). Phía trên bảng có dòng **Chưa báo (n): 1D15 · 4D21 …** — bấm mã lớp để mở lớp đó; nút lọc **Tất cả / Chưa báo / Có vắng** ở góc phải để bảng chỉ hiện các lớp cần xem. Ghi chú và danh sách tên dài tự xuống dòng; bấm nút **«** ở góc trên thanh bên để thu gọn thanh bên, bảng rộng hơn. Phía trên bảng có **Tổng suất = hiện diện** (xanh khi khớp, đỏ khi lệch — bấm để xem trang Suất ăn). |
| **Bảng chọn tên** (**bấm vào 1 lớp**) | Hiện tên các em ăn bán trú của lớp dạng **ô chữ to**. **Bấm vào ô tên = vắng** (ô chuyển đỏ), bấm lại để bỏ. Ô **Tìm tên** to ở trên, gõ không cần dấu (`long`, `hai long`, `h long` đều ra *Hải Long*); ô tìm **chỉ để lọc** tên (không tự chọn, Enter cũng không chọn); chọn vắng = **bấm vào ô tên**. Gõ hoặc **dán nhiều tên cách nhau dấu phẩy** (vd. `Gia Huy, Bảo Anh, Minh`) thì hiện các em có các tên đó để bấm chọn. Gõ đủ chữ thì chỉ hiện em có đủ các chữ đó (gõ `gia huy` không ra *Huỳnh Gia Lộc*); gõ có dấu thì ưu tiên em đúng dấu (`Nguyên Vũ` không ra *Nguyễn Vũ Khang*); em có tên cuối khớp đứng trước (`Thư` → *Minh Thư* trước *Thư Kỳ*); tên nào không có trong bảng thì hiện thành **ô viền đứt** ghi lý do: *Không ăn bán trú* (ô xám) hoặc *Không có trong danh sách* (ô vàng, nên xem lại tên) — các ô này không bấm được, không tính. Nút **Lớp này đủ** (lớp có em nghỉ thứ 6 thì nút ghi **Đủ (trừ em nghỉ thứ 6)**), ô **Ghi chú (cột H)**. Bấm **Xong** (hoặc Esc) để đóng. |

Hộp hỏi và bảng chọn tên luôn hiện **giữa màn hình**, nền phía sau tối đi.


Trang **Suất ăn**: bảng suất ăn cho từng nhóm bảo mẫu, tính như công thức trong sổ (hiện diện các lớp + em ghép − em ghép vắng), ghi tên em ghép vắng ngay trong dòng. Dòng trên cùng phải là **Tổng suất = hiện diện**; khi lệch app ghi rõ **thừa / thiếu bao nhiêu suất** và lý do ở ngay dưới. Em ăn ghép vắng mà danh sách chưa ghi nhóm: app hỏi **em đó ăn nhóm nào** (bấm nút nhóm; bấm tên em trong dòng để chọn lại). Bấm **Lưu vào sổ** khi suất ăn còn lệch thì app hỏi lại trước khi lưu.

### Kiểm tra tên trong sổ

Mở một ngày **đã có trong sổ**, app đối chiếu mọi ô tên vắng (kể cả gõ tay trong Excel). Tên không khớp danh sách hiện dòng đỏ phía trên bảng (bấm vào để mở lớp đó) và thành nút đỏ trong bảng chọn tên: bấm vào để **chọn em đúng**, **giữ nguyên chữ đã ghi**, hoặc **bỏ qua tên này**. Không có em nào tên gần giống thì app cho chọn trong cả lớp. Muốn lần sau app tự nhận ra tên đó: ghi tên vào cột *Tên gọi khác* trong file Excel danh sách (lưu file, app tự đọc lại khi mở ngày).

App còn đối chiếu số trong sổ: lớp lệch sĩ số hoặc thiếu/thừa tên vắng thì dòng lớp tô đỏ và ghi lý do ở cột Ghi chú (vd. "Thiếu 1 tên (GV báo vắng 3 em, mới ghi 2)").

### Lưu vào sổ

1. Bấm **Lưu vào sổ** (Ctrl+S). Nếu chưa có sheet ngày hôm nay, app sao chép sheet hôm trước rồi điền số liệu.
   - Còn **tên chưa rõ** thì app **chưa cho lưu**; bấm **Xử lý ngay** để app mở lớp cần xử lý.
   - Còn điều cần biết thì app hỏi **một lần** trong hộp **Kiểm tra trước khi lưu**: **lớp chưa báo** (lưu thì tính **đủ**),
     **suất ăn thừa/thiếu** (nút **Xem trang Suất ăn**), **sĩ số danh sách khác sổ** (chọn **giữ sĩ số như sổ** hay **dùng sĩ số theo danh sách**).
     Bấm **Hủy** để ở lại sửa.
2. In: bấm **Mở sổ Excel** rồi in trong Excel như thường lệ (tờ 1 bảng điểm danh, tờ 2 bảng suất ăn).

Nút **Hoàn tác** (Ctrl+Z) bỏ thao tác vừa làm.

Nút **Đặt lại** đưa mọi lớp của ngày đang mở về *chưa báo* và bỏ hết tên vắng đã chọn (ghi chú, sĩ số giữ nguyên). Dùng khi sheet của ngày đó đã được tạo sẵn trong sổ nên app hiểu nhầm là đã điểm danh. Sổ chỉ đổi khi bấm **Lưu vào sổ**. (Sheet tạo sẵn mà còn trống — chưa có tên vắng nào — thì app đã tự coi các lớp là *chưa báo*.)

## 4. Lịch thêm / cắt bán trú, nghỉ thứ 6

Ghi ở cột **Ghi chú** trong file Excel danh sách (mục 2): `cắt từ 30/10`, `ăn từ 3/11`, `cắt thứ 6`. Lưu file Excel, rồi mở ngày trong app (hoặc bấm **Hôm nay**): app đọc lại danh sách.

- Từ ngày đó app tự đổi sĩ số và danh sách tên của lớp. Trên trang Điểm danh, cột Ghi chú của lớp có chữ **[Lịch]**. Sĩ số đổi theo lịch thì app không hỏi "sĩ số khác nhau" khi lưu.
- Bảng chọn tên ghi *Sắp tới: cắt … từ …* cho các em sắp đổi; ô tên có nhãn nhỏ *nghỉ T6* nếu em cắt thứ 6.
- Muốn ghi vào sổ như cách vẫn viết (vd. "Từ 30/10 cắt bán trú …"): gõ vào ô **Ghi chú (cột H)** trong bảng chọn tên của lớp.
- Bỏ lịch: xóa chữ trong ô Ghi chú của file danh sách.

## 5. Ghép lớp (lớp 1.5, 4.4 …)

Lớp ghép là lớp không có hàng riêng trong bảng suất ăn: các em chia sang ăn ở nhóm khác (1.1, 1.2 …).

- Nhóm ăn của từng em ghi ở cột **Ăn ghép** trong file Excel danh sách (vd. *1.3*; để trống = không ăn ghép). Đây là chỗ duy nhất ghi nhóm ghép.
- Chân trang **Suất ăn** ghi mỗi lớp ghép đã ghi nhóm cho bao nhiêu em (vd. *1D19: 1/29 em*); bấm **Xem các em** để mở trang **Học sinh** lọc sẵn lớp đó (cột **Ăn ghép**).
- Em đã có nhóm mà vắng: app tự trừ đúng nhóm, tự điền ô **vắng** trong bảng suất ăn của sổ.
- Em chưa có nhóm mà vắng: trang **Suất ăn** hỏi em đó ăn nhóm nào (chỉ cho ngày đó). Mở lại ngày đã lưu, app đọc lại ô **vắng** trong sổ; chỉ hỏi lại khi không chắc em nào ở nhóm nào.
- Lớp ghép chưa ghi nhóm cho đủ mọi em thì số em ghép mỗi nhóm giữ như sổ hôm trước.
- Em có thể ghép sang nhóm khác khối (vd. em lớp 1 ăn cùng nhóm 2.1): cột **Ăn ghép** ghi mã nhóm đó là được.

### Đổi cách ghép (đầu năm học, hoặc giữa năm)

Trang **Suất ăn** trình bày như bảng trong sổ: cột **Suất** và cột **Tên ghép** (dòng trống cách nhóm giữ nguyên). Cách ghép khai báo ở sheet **Nhóm ăn** trong file Excel danh sách (nút **Sửa cách ghép** mở file đó):

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
- Sửa xong lưu file Excel. Sheet ghi sai (lớp không có, một lớp ở 2 dòng, mã trùng…) thì trang **Cài đặt** báo lỗi và app giữ bảng suất ăn như sổ.
- **Từ tờ ngày mới** (kể cả tờ đầu tháng của sổ tháng mới), app tự dựng bảng suất ăn theo sheet này: dòng, nhãn, công thức, ô số em ghép, ô cộng các nhóm, ô cộng các lớp ăn tại lớp, vùng in. **Các tờ đã có trong sổ giữ nguyên.** Trang **Suất ăn** ghi rõ khi bảng của ngày đang mở khác sheet Nhóm ăn.
- File danh sách không có sheet Nhóm ăn thì app giữ bảng suất ăn như sổ (như trước).

## 6. Học sinh

Trang **Học sinh** chỉ để **tra cứu**: tìm em, lọc theo lớp, xem em nào ăn bán trú, **tên gọi khác**, ăn ghép, **Ghi chú** và cột **App hiểu là** (cắt thứ 6, cắt từ…, ăn từ…).

- Muốn **thêm, sửa, xóa học sinh**, đặt **lịch thêm / cắt**: sửa **file Excel danh sách** (nút **Sửa danh sách** mở file), lưu lại. App đọc lại khi mở ngày.
- Đổi sang file danh sách khác: **Cài đặt → Chọn file khác…**.

Lớp có sĩ số theo danh sách khác sĩ số trong sổ được tô đỏ ở bảng điểm danh. Khi lưu, nếu còn lệch, app hỏi: **giữ sĩ số như trong sổ** hay **dùng sĩ số theo danh sách**.

## 7. Ngày cũ, tháng mới

- Đổi ngày: gõ vào ô ngày (`dd/mm/yyyy`) rồi Enter, bấm nút lịch, 2 nút mũi tên hoặc **Hôm nay**. Ngày đang mở có thay đổi chưa lưu thì app hỏi **Lưu rồi chuyển ngày / Không lưu / Ở lại**.
- Mở một ngày **đã có trong sổ**: app đọc lại và **kiểm tra mọi ô tên vắng** (kể cả gõ tay trong Excel), báo tên sai hoặc không ăn bán trú.
- Sang tháng mới (hoặc mở ngày của tháng khác sổ đang chọn): app hỏi **Tạo sổ tháng mới** hoặc **Chọn file sổ có sẵn**. Sổ mới (vd. `… T11.xlsx`) được làm từ sheet cuối của sổ đang chọn, giữ nguyên mẫu, chữ ký, ghi chú; đã có file cùng tên thì app dùng file đó. App không tự đi tìm sổ khác trong thư mục.

## 8. An toàn dữ liệu & lỗi thường gặp

- App **không tạo bản sao lưu**. Sổ chính chỉ thay đổi khi bấm **Lưu vào sổ**; lúc ghi, app ghi ra file phụ rồi mới thay sổ, nên lỗi giữa chừng không làm hỏng sổ.
- **Sổ tạm (phòng mất điện)**: **ngay sau mỗi thao tác**, app tự lưu một file nhỏ (vài KB, không chép cả cuốn sổ nên rất nhẹ), tên là tên sổ thêm chữ `tamthoi`, nằm cạnh sổ chính (vd. `SO DIEM DANH T10 tamthoi.xlsx`). Dòng trạng thái dưới bảng ghi *"đã lưu tạm lúc …"*.
  - Bấm **Lưu vào sổ** thì app chép vào sheet của ngày trong sổ chính rồi xóa sổ tạm.
  - Nếu máy tắt đột ngột khi chưa lưu, lần mở app sau sẽ hỏi **Khôi phục**. Chọn Khôi phục để làm tiếp, rồi nhớ bấm Lưu vào sổ.
  - Thoát app và chọn *Không lưu*, hoặc đổi ngày và chọn *Không lưu*, thì sổ tạm cũng bị xóa.
  - Có thể mở sổ tạm bằng Excel để xem: sheet *Dang diem danh* ghi từng lớp đã báo chưa, số vắng, tên vắng, ghi chú.
- **"File đang mở trong Excel"**: đóng file đó trong Excel, rồi bấm *Thử lại*.
- **In sổ**: bấm **Mở sổ Excel** rồi in trong Excel như thường lệ.
- App **chỉ đọc / ghi 4 file**: CaiDat.txt, file danh sách học sinh, sổ đang chọn và sổ tạm của sổ đó. Không ghi file nhật ký, không tạo file nào khác, không tự mở các file khác trong thư mục. Lỗi hiện ngay trên màn hình (lỗi lúc mở app hiện hộp thông báo).
- **Thư mục đặt app không ghi được** (vd. Program Files): app báo không ghi được CaiDat.txt; chép `DiemDanhBanTru.exe` vào thư mục khác (vd. Documents).
- **Bấm mở app mà không thấy trình duyệt hiện lên**: mở Edge/Chrome rồi gõ địa chỉ `127.0.0.1:47615`.
- Hộp **chọn file** (chọn sổ, chọn file danh sách) là cửa sổ riêng của app; nếu không thấy, tìm nó trên thanh tác vụ (taskbar).
- **Windows cảnh báo khi tải hoặc mở app**: app chưa có *chữ ký số* (chứng thư mua của hãng chứng thực) nên mỗi bản mới Windows chưa "quen", trình duyệt và SmartScreen sẽ hỏi lại. App không có gì nguy hiểm; làm một lần cho mỗi bản mới:
  - **Edge**: ở danh sách tải về, rê chuột lên file → **…** → **Giữ lại** → **Hiện thêm** → **Vẫn giữ**. **Chrome**: bấm **Giữ lại**.
  - Màn xanh **"Windows đã bảo vệ PC của bạn"**: bấm **Thông tin bổ sung** → **Vẫn chạy**.
  - Hoặc trước khi mở: chuột phải file `DiemDanhBanTru.exe` → **Properties** → tích **Bỏ chặn (Unblock)** → **OK**.
  - Nếu **Windows Defender** xóa / chặn file: mở **Bảo mật Windows → Bảo vệ khỏi vi-rút và mối đe dọa → Lịch sử bảo vệ**, chọn mục bị chặn → **Cho phép**. Có thể gửi file cho Microsoft xem lại (microsoft.com/wdsi/filesubmission, chọn *Software developer*/*Home customer*, ghi "false positive") để các máy khác không bị chặn nữa.
  - Thông tin phiên bản của file: chuột phải → **Properties → Details** (tên *Điểm danh bán trú*, số phiên bản).
- **Cập nhật app lên bản mới**: tải lại `DiemDanhBanTru.exe` trong thư mục `tai-ve` của repo, chép đè lên file cũ (thoát app trước: bấm **Thoát** trong giao diện). Danh sách học sinh, lịch, cách ghép nằm trong file Excel danh sách nên vẫn giữ nguyên; lần đầu mở bản mới app hỏi chọn lại sổ và file danh sách.

## 9. Phím tắt

| Phím | Việc |
|---|---|
| Esc | Đóng bảng chọn tên / hộp đang mở |
| Ctrl+S | Lưu vào sổ |
| Ctrl+Z | Hoàn tác thao tác vừa làm |
