// Lên lịch thêm / cắt bán trú / cắt thứ 6. Đóng hộp với true khi đã lưu lịch.
import { api } from "../api.js";
import { toast } from "../dialogs.js";
import { store } from "../store.js";
import { dateOf, dmyOf } from "../util.js";

const { inject, ref, watch } = Vue;
const KINDS = [{ label: "Cắt bán trú", value: "cat" }, { label: "Thêm bán trú", value: "them" }, { label: "Cắt thứ 6 hàng tuần", value: "thu6" }];
const HINTS = { cat: "Tích các em thôi ăn bán trú.", them: "Tích em trong lớp chưa ăn bán trú, hoặc tích Học sinh mới.", thu6: "Tích các em nghỉ ăn thứ 6 hàng tuần." };

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const data = dialogRef.value.data;
    const kind = ref(data.kind), code = ref(data.code), q = ref("");
    const opt = ref(null), chosen = ref([...data.ids]), start = ref(null), note = ref(true);
    const addNew = ref(false), newName = ref(""), newDob = ref(""), err = ref(""), busy = ref(false);

    watch([kind, code, q], async () => {
      opt.value = await api("schedule_options", kind.value || "cat", code.value, q.value);
      if (!start.value) start.value = dateOf(opt.value.next);
    }, { immediate: true });

    async function save() {
      busy.value = true;
      const r = await api("add_schedule", kind.value, code.value, chosen.value, start.value ? dmyOf(start.value) : "",
        addNew.value ? newName.value : "", addNew.value ? newDob.value : "", note.value);
      busy.value = false;
      if (r.error) { err.value = r.error; return; }
      store.S = r.state;
      toast(r.ok);
      dialogRef.value.close(true);
    }
    const quick = () => opt.value ? [["Ngày học kế tiếp", opt.value.next], ["Đầu tháng sau", opt.value.month], ["Hôm nay", opt.value.today]] : [];
    return { KINDS, HINTS, kind, code, q, opt, chosen, start, note, addNew, newName, newDob, err, busy, save, quick, dateOf,
      close: () => dialogRef.value.close(false) };
  },
  template: /* html */`
    <SelectButton v-model="kind" :options="KINDS" optionLabel="label" optionValue="value" :allowEmpty="false" class="mb-3" />
    <div class="row-gap mb-2">
      <Select v-if="opt" v-model="code" :options="opt.classes" class="w-9rem" />
      <IconField class="grow"><InputIcon class="pi pi-search" /><InputText v-model="q" placeholder="Tìm tên…" fluid /></IconField>
    </div>
    <div class="text-muted small mb-1">{{ HINTS[kind] }}</div>
    <Listbox v-if="opt" v-model="chosen" :options="opt.students" optionValue="id" multiple listStyle="max-height: 34vh"
      emptyMessage="Không có em nào phù hợp.">
      <template #option="{ option: s, selected }"><Checkbox :modelValue="selected" binary readonly class="me-2" />{{ s.ten }} <span class="text-muted ms-1">— sinh {{ s.ns }}{{ kind === 'them' && !s.bt ? " (chưa ăn BT)" : "" }}</span></template>
    </Listbox>
    <template v-if="kind === 'them'">
      <div class="row-gap mt-2"><Checkbox v-model="addNew" binary inputId="snew" /><label for="snew"><b>Học sinh mới</b> (chưa có trong danh sách)</label></div>
      <div v-if="addNew" class="row-gap mt-2">
        <InputText v-model="newName" placeholder="Họ tên em mới" class="grow" />
        <InputText v-model="newDob" placeholder="Ngày sinh" class="w-9rem" />
      </div>
    </template>
    <div v-if="kind !== 'thu6'" class="mt-3">
      <label class="d-block mb-1">Áp dụng từ ngày:</label>
      <div class="row-gap flex-wrap">
        <DatePicker v-model="start" dateFormat="dd/mm/yy" showIcon class="w-11rem" />
        <Button v-for="[label, d] in quick()" :key="label" :label="label + ' (' + d.slice(0, 5) + ')'" size="small" severity="secondary" outlined
          @click="start = dateOf(d)" />
      </div>
    </div>
    <div class="row-gap mt-3"><Checkbox v-model="note" binary inputId="snote" />
      <label for="snote">Ghi chú vào cột H của lớp (như "Tháng 11 cắt bán trú …")</label></div>
    <div class="dlg-foot">
      <span class="text-danger me-auto pre-line">{{ err }}</span>
      <Button label="Lưu lịch" icon="pi pi-check" :loading="busy" @click="save" />
      <Button label="Hủy" severity="secondary" outlined @click="close" />
    </div>`,
};
