// Trang Học sinh: tra cứu danh sách (sửa thì sửa file Excel rồi nhập lại).
import { api } from "../api.js";
import { openPath, store } from "../store.js";

const { computed, onActivated, ref, watch } = Vue;

export default {
  setup() {
    const cls = ref(""), q = ref(""), bt = ref(true), HS = ref({ rows: [], classes: [] });
    const load = async () => { HS.value = await api("students", q.value, cls.value || "", bt.value); };
    watch([cls, q, bt], load);
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
    return { cls, q, bt, HS, options, openPath };
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
      <DataTable :value="HS.rows" scrollable scrollHeight="flex" size="small" stripedRows :rowClass="s => s.now ? '' : 'text-muted'">
        <Column field="lop" header="Lớp" />
        <Column field="ten" header="Họ tên" class="fw-semibold" />
        <Column field="ns" header="Ngày sinh" />
        <Column header="Ăn BT" class="text-center"><template #body="{ data: s }"><i v-if="s.bt" class="pi pi-check text-success"></i></template></Column>
        <Column field="goi" header="Tên gọi khác" />
        <Column field="ghep" header="Ăn ghép" />
        <Column field="db" header="App hiểu là" />
        <Column field="gc" header="Ghi chú" />
      </DataTable>
    </div>
    <div class="text-muted small">Trang này chỉ để tra cứu. Thêm, sửa học sinh, cắt / thêm bán trú: sửa file Excel danh sách
      (cột <b>Ghi chú</b>: <i>cắt thứ 6</i>, <i>cắt từ 30/10</i>, <i>ăn từ 3/11</i>), lưu file, app tự đọc lại khi mở ngày.</div>
  </section>`,
};
