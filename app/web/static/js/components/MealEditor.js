// Sửa cách ghép: mỗi dòng = 1 dòng bảng suất ăn trong sổ (tên ghép + các lớp ăn chung), kéo thả để đổi thứ tự.
import { api } from "../api.js";
import { openDialog, toast } from "../dialogs.js";
import { store } from "../store.js";
import MealClassPicker from "./MealClassPicker.js";

const { computed, onMounted, ref } = Vue;

export default {
  emits: ["close"],
  setup(_, { emit }) {
    const MG = ref(null), today = ref(false), errors = ref([]);
    let seq = 0;
    const row = (g = {}, gap = false) => ({ k: ++seq, label: g.label || "", classes: [...(g.classes || [])], code: g.code || "", gap });
    onMounted(async () => {
      const r = await api("meal_groups");
      r.groups = r.groups.map(g => row(g, !g.label && !g.classes.length && !g.code));
      MG.value = r;
    });
    const ma = computed(() => Object.fromEntries(MG.value.classes.map(c => [c.code, c.ma])));
    const free = computed(() => {
      const used = new Set(MG.value.groups.flatMap(g => g.classes));
      return MG.value.classes.map(c => c.code).filter(c => !used.has(c));
    });
    async function pickClasses(g) {
      const pick = await openDialog(MealClassPicker, { header: `Chọn lớp ăn chung dòng "${g.label || "mới"}"`, width: "60rem",
        data: { groups: MG.value.groups, classes: MG.value.classes, g } });
      if (!pick) return;
      MG.value.groups.forEach(x => { if (x !== g) x.classes = x.classes.filter(c => !pick.includes(c)); });  // lớp chỉ ở 1 dòng
      g.classes = MG.value.classes.map(c => c.code).filter(c => pick.includes(c));
    }
    async function save() {
      const bad = MG.value.groups.findIndex(g => !g.gap && !g.label.trim() && !g.code);
      if (bad >= 0) { errors.value = [`Dòng ${bad + 1} chưa có tên ghép.`]; return; }
      const groups = MG.value.groups.map(g => g.gap ? { label: "", classes: [], code: "" } : { label: g.label, classes: g.classes, code: g.code.trim() });
      const r = await api("save_meal_groups", groups, today.value);
      if (r.errors) { errors.value = r.errors; return; }
      store.S = r.state;
      toast(r.flash);
      emit("close", true);
    }
    return { MG, today, errors, ma, free, row, pickClasses, save, close: () => emit("close", false) };
  },
  template: /* html */`
  <div v-if="MG" class="sheet p-3 overflow-auto">
    <Message severity="secondary" class="mb-2">Mỗi dòng ở đây = 1 dòng bảng suất ăn trong sổ (cột suất + cột tên ghép), đúng thứ tự từ trên xuống
      (kéo biểu tượng <i class="pi pi-bars"></i> để đổi thứ tự). Lớp không thuộc dòng nào thì <b>ăn tại lớp</b>.
      <b>Mã ghép lẻ</b>: chỉ ghi ở dòng nhận em ghép lẻ từ lớp chia nhóm (vd. 1.2); em nào ăn dòng đó thì cột <b>Ăn ghép</b> trong file danh sách ghi đúng mã này.</Message>
    <Message v-if="errors.length" severity="error" class="mb-2"><b>Chưa lưu được:</b><ul class="mb-0"><li v-for="e in errors">{{ e }}</li></ul></Message>
    <DataTable :value="MG.groups" dataKey="k" size="small" class="mb-2" @rowReorder="e => MG.groups = e.value">
      <Column rowReorder class="w-drag" />
      <Column header="Tên ghép (in ở sổ)" class="w-label"><template #body="{ data: g }">
        <span v-if="g.gap" class="text-muted small fst-italic text-nowrap">— dòng trống (cách dòng trong sổ) —</span>
        <InputText v-else v-model="g.label" placeholder="vd. 1.2 ghép" class="fw-semibold" fluid /></template></Column>
      <Column header="Các lớp ăn chung"><template #body="{ data: g }"><div v-if="!g.gap" class="row-gap flex-wrap">
        <Tag v-for="c in g.classes" :key="c" severity="secondary" :value="c + (ma[c] ? ' (' + ma[c] + ')' : '')" />
        <span v-if="!g.classes.length" class="text-muted small">chưa có lớp</span>
        <Button label="Chọn lớp" icon="pi pi-pencil" size="small" outlined class="py-0" @click="pickClasses(g)" /></div></template></Column>
      <Column header="Mã ghép lẻ" class="w-code"><template #body="{ data: g }">
        <InputText v-if="!g.gap" v-model="g.code" placeholder="—" class="text-center" fluid title="Chỉ ghi khi dòng này nhận em ghép lẻ (vd. 1.2)" /></template></Column>
      <Column class="w-del"><template #body="{ index }">
        <Button icon="pi pi-times" severity="danger" text rounded title="Xóa dòng" @click="MG.groups.splice(index, 1)" /></template></Column>
    </DataTable>
    <div class="row-gap mb-2">
      <Button label="Thêm dòng" icon="pi pi-plus" outlined @click="MG.groups.push(row())" />
      <Button label="Thêm dòng trống" icon="pi pi-minus" severity="secondary" outlined @click="MG.groups.push(row({}, true))" />
    </div>
    <div class="mb-2"><b>Ăn tại lớp:</b> {{ free.join(", ") || "—" }}</div>
    <div class="row-gap flex-wrap border-top pt-2">
      <template v-if="MG.exists"><Checkbox v-model="today" binary inputId="mgToday" />
        <label for="mgToday">Dựng lại bảng suất ăn cả tờ ngày đang mở (tờ này đã có trong sổ)</label></template>
      <span v-else class="text-muted">Áp dụng từ tờ ngày đang mở (chưa có trong sổ) và các ngày sau.</span>
      <div class="row-gap ms-auto">
        <Button label="Lưu cách ghép" icon="pi pi-check" @click="save" />
        <Button label="Hủy" severity="secondary" outlined @click="close" />
      </div>
    </div>
  </div>`,
};
