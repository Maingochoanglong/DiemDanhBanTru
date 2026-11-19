// Trang Học sinh: tra cứu danh sách; bấm vào em để đặt lịch bán trú (ScheduleDialog). Thêm / sửa học sinh: sửa file Excel.
import { api } from "../api.js";
import { openDialog } from "../dialogs.js";
import { handle, openPath, store } from "../store.js";
import ScheduleDialog from "./ScheduleDialog.js";

const { computed, onActivated, ref, watch } = Vue;

export default {
  setup() {
    const cls = ref(""), q = ref(""), bt = ref(true), HS = ref({ rows: [], classes: [] });
    const load = async () => { HS.value = await api("students", q.value, cls.value || "", bt.value); };
    watch([cls, q, bt], load);
    watch(() => store.S, () => { if (store.page === "hs") load(); });  // vd. quay lại từ Excel vừa sửa danh sách
    onActivated(() => {
      if (store.hsPreset !== null) {  // mở từ trang Suất ăn: lọc sẵn 1 lớp
        const preset = store.hsPreset;
        store.hsPreset = null;
        if (cls.value !== preset || q.value) { q.value = ""; cls.value = preset; return; }  // watch tải lại
      }
      load();
    });
    // lớp lọc sẵn (vd. lớp ghép) có thể không nằm trong danh sách lớp: vẫn hiện trong ô chọn
    const options = computed(() => !cls.value || HS.value.classes.includes(cls.value) ? HS.value.classes : [...HS.value.classes, cls.value]);
    async function schedule(s) {
      const r = await openDialog(ScheduleDialog, { header: `Lịch bán trú — ${s.ten}`, width: "34rem", data: { s } });
      if (r) handle(await api("set_schedule", s.id, r.bt_tu, r.cat_tu, r.t6));  // xong thì store.S đổi → watch tải lại bảng
    }
    return { cls, q, bt, HS, options, openPath, schedule };
  },
  template: /* html */`
  <section class="page">
    <div class="toolbar">
      <Select v-model="cls" :options="options" placeholder="Tất cả lớp" showClear class="w-11rem" />
      <IconField><InputIcon class="pi pi-search" /><InputText v-model="q" placeholder="Tìm tên (không cần dấu)" /></IconField>
      <Checkbox v-model="bt" binary inputId="hsBt" /><label for="hsBt">Chỉ em ăn bán trú</label>
      <span class="text-muted ms-2">{{ HS.rows.length }} em</span>
      <Button label="Sửa danh sách" icon="pi pi-external-link" severity="secondary" outlined class="ms-auto" @click="openPath('cdhs_file')" />
    </div>
    <div class="sheet">
      <DataTable :value="HS.rows" scrollable scrollHeight="flex" size="small" stripedRows :rowClass="s => s.now ? 'clickable' : 'clickable text-muted'"
        @row-click="e => schedule(e.data)">
        <Column field="lop" header="Lớp" />
        <Column field="ten" header="Họ tên" class="fw-semibold" />
        <Column field="ns" header="Ngày sinh" />
        <Column header="Ăn BT" class="text-center"><template #body="{ data: s }"><i v-if="s.bt" class="pi pi-check text-success"></i></template></Column>
        <Column field="goi" header="Tên gọi khác" />
        <Column field="ghep" header="Ăn ghép" />
        <Column field="lich" header="Lịch" />
        <Column field="gc" header="Ghi chú" />
      </DataTable>
    </div>
    <div class="text-muted small"><b>Bấm vào một em</b> để đặt lịch: bắt đầu ăn từ ngày, thôi ăn từ ngày, cắt thứ 6.
      Thêm / sửa học sinh: bấm <b>Sửa danh sách</b> (mở file Excel), lưu file là app đọc lại ngay.</div>
  </section>`,
};
