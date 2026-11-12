// Trang Lịch thêm/cắt: các lịch đã đặt (sắp áp dụng / hàng tuần / đã áp dụng), tích để hủy.
import { api } from "../api.js";
import { ask, info, toast } from "../dialogs.js";
import { handle, scheduleDialog, store } from "../store.js";

const { onActivated, ref, watch } = Vue;
const GROUPS = [["soon", "Sắp áp dụng"], ["weekly", "Hàng tuần – cắt thứ 6"], ["done", "Đã áp dụng (30 ngày qua)"]];

export default {
  setup() {
    const rows = ref([]), counts = ref({}), selected = ref([]);
    async function load() {
      const g = await api("schedules");
      rows.value = GROUPS.flatMap(([k]) => g[k].map(it => ({ ...it, group: k })));
      counts.value = Object.fromEntries(GROUPS.map(([k]) => [k, g[k].length]));
      selected.value = [];
    }
    onActivated(load);
    watch(() => store.schedTick, load);
    async function cancel() {
      const keys = selected.value.map(x => x.key);
      if (!keys.length) return info("Hủy lịch", "Hãy tích các dòng lịch cần hủy.");
      const k = await ask("Hủy lịch", `Hủy ${keys.length} lịch đã tích?`, [{ key: "keep", label: "Giữ lại" }, { key: "cancel", label: "Hủy các lịch này", severity: "danger", outlined: false }]);
      if (k !== "cancel") return;
      const r = handle(await api("cancel_schedules", keys));
      if (r.ok) toast(r.ok);
      load();
    }
    const title = k => GROUPS.find(g => g[0] === k)[1];
    return { rows, counts, selected, cancel, title, scheduleDialog, rowClass: r => r.group === "soon" ? "warn-row" : r.group === "done" ? "text-muted" : "" };
  },
  template: /* html */`
  <section class="page">
    <div class="toolbar">
      <span class="text-muted small me-auto">Đặt trước ngày cắt / thêm, tới ngày đó app tự đổi sĩ số.</span>
      <Button label="Cắt bán trú…" icon="pi pi-minus-circle" severity="danger" @click="scheduleDialog('cat')" />
      <Button label="Thêm bán trú…" icon="pi pi-user-plus" severity="success" @click="scheduleDialog('them')" />
      <Button label="Cắt thứ 6…" icon="pi pi-calendar-minus" severity="secondary" outlined @click="scheduleDialog('thu6')" />
      <Button label="Hủy lịch đã tích" icon="pi pi-times-circle" severity="danger" outlined @click="cancel" />
    </div>
    <div class="sheet">
      <DataTable v-model:selection="selected" :value="rows" dataKey="key" rowGroupMode="subheader" groupRowsBy="group"
        scrollable scrollHeight="flex" size="small" :rowClass="rowClass">
        <template #groupheader="{ data }"><b>{{ title(data.group) }} ({{ counts[data.group] }})</b></template>
        <template #empty><div class="text-muted py-3">Chưa có lịch nào.</div></template>
        <Column selectionMode="multiple" class="w-check" />
        <Column field="ngay" header="Ngày áp dụng" />
        <Column field="lop" header="Lớp" />
        <Column field="hs" header="Học sinh" />
        <Column field="viec" header="Việc" />
      </DataTable>
    </div>
  </section>`,
};
