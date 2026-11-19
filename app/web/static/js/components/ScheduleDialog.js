// Hộp Lịch bán trú của một em (mở từ trang Học sinh): ăn từ ngày, thôi ăn từ ngày, cắt thứ 6 hàng tuần.
// Đóng hộp với {bt_tu, cat_tu, t6} (ngày dạng "2026-12-01" hoặc ""); null = Hủy. Trang Học sinh gửi api("set_schedule").
import { dateOf, isoOf } from "../util.js";

const { inject, ref } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const s = dialogRef.value.data.s;
    const btTu = ref(dateOf(s.bt_tu)), catTu = ref(dateOf(s.cat_tu)), t6 = ref(!!s.t6);
    const save = () => dialogRef.value.close({ bt_tu: btTu.value ? isoOf(btTu.value) : "", cat_tu: catTu.value ? isoOf(catTu.value) : "", t6: t6.value });
    return { s, btTu, catTu, t6, save, cancel: () => dialogRef.value.close() };
  },
  template: /* html */`
    <p class="mt-0">Lớp <b>{{ s.lop }}</b> · sinh {{ s.ns }} · hôm nay <b>{{ s.now ? "đang ăn bán trú" : "không ăn bán trú" }}</b></p>
    <div class="sched-grid">
      <label for="schBt">Bắt đầu ăn bán trú từ ngày</label>
      <DatePicker v-model="btTu" inputId="schBt" showIcon showButtonBar placeholder="(không có)" />
      <label for="schCut">Thôi ăn (cắt) từ ngày</label>
      <DatePicker v-model="catTu" inputId="schCut" showIcon showButtonBar placeholder="(không có)" />
      <span></span>
      <label class="row-gap"><Checkbox v-model="t6" binary /> Cắt thứ 6 hàng tuần (thứ 6 app tự tính em vắng)</label>
    </div>
    <p class="text-muted small mb-0">Lưu vào file danh sách (cột Ăn từ, Cắt từ, Cắt thứ 6). Cột Ghi chú của em không đổi.
      Đến ngày đó app tự đổi sĩ số lớp.</p>
    <div class="dlg-foot">
      <Button label="Lưu lịch" icon="pi pi-check" @click="save" />
      <Button label="Hủy" severity="secondary" outlined @click="cancel" />
    </div>`,
};
