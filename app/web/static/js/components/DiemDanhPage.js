// Trang Điểm danh: bảng như tờ sổ (lớp, sĩ số, vắng, hiện diện, tên vắng, ghi chú) + thanh lưu.
import { api } from "../api.js";
import { ask } from "../dialogs.js";
import { doSave, handle, openClass, store } from "../store.js";
import { mealDiff } from "../util.js";

const { computed, ref } = Vue;

export default {
  setup() {
    const filter = ref("all");  // all | unrep (chưa báo) | absent (có vắng)
    const S = computed(() => store.S);
    const classes = computed(() => S.value.rows.filter(r => r.kind === "class"));
    const filters = computed(() => {
      const c = classes.value;
      return [["all", "Tất cả", c.length], ["unrep", "Chưa báo", c.filter(r => !r.reported).length], ["absent", "Có vắng", c.filter(r => r.vang > 0).length]]
        .map(([value, label, n]) => ({ value, label: `${label} (${n})` }));
    });
    const keep = r => filter.value === "all" || (filter.value === "unrep" ? !r.reported : r.vang > 0);
    const rows = computed(() => {
      const t = S.value.totals;
      const out = S.value.rows.filter(r => r.kind === "class" ? keep(r) : filter.value === "all");
      if (t) out.push({ kind: "tong", code: "TỔNG CỘNG", ...t });
      return out;
    });
    const empty = computed(() => !classes.value.length ? "Chưa có danh sách học sinh. Vào Cài đặt để nhập."
      : !classes.value.some(keep) ? (filter.value === "unrep" ? "Các lớp đều đã báo." : "Không lớp nào có em vắng.") : "");
    const note = r => [r.sched ? "[Lịch]" : "", r.warn, r.not_bt ? `Không ăn BT: ${r.not_bt}` : "", r.note].filter(Boolean).join(" · ");
    const tip = r => (r.sched ? "[Lịch] = sĩ số đổi theo lịch thêm/cắt. " : "") + [r.warn, r.note].filter(Boolean).join(" · ");
    const rowClass = r => r.kind === "class" ? `cls st-${r.status}` : r.kind;
    const meal = computed(() => {
      const m = S.value.meal;
      return m && { ok: m.ok, text: m.ok ? `Tổng suất ${m.total} = hiện diện ${m.present}` : `Suất ăn ${mealDiff(m)}${m.ask ? ` · ${m.ask} em ghép chưa rõ nhóm` : ""}` };
    });
    const saveState = computed(() => {
      const s = S.value;
      if (s.unresolved) return { cls: "err", icon: "pi-exclamation-triangle", text: `Còn ${s.unresolved} tên chưa rõ — xử lý xong mới lưu được` };
      if (s.dirty) return { cls: "dirty", icon: "pi-pencil", text: "Có thay đổi chưa lưu vào sổ",
        sub: s.temp_error ? ` — ${s.temp_error}` : (s.temp_at ? ` (đã lưu tạm lúc ${s.temp_at})` : ""), subErr: !!s.temp_error };
      return { cls: "", text: s.exists ? "Đã có trong sổ" : (s.book ? "Ngày này chưa có trong sổ" : "") };
    });
    function gotoUnresolved() { const t = S.value.unresolved && S.value.todo.find(x => x.code); if (t) openClass(t.code); }
    async function reset() {
      const k = await ask("Đặt lại điểm danh ngày này?", `<p>Mọi lớp về <b>chưa báo</b>, bỏ hết tên vắng đã chọn. Ghi chú và sĩ số giữ nguyên.</p>
        <p class="text-muted mb-0">Dùng khi sheet trong sổ đã tạo sẵn nên app hiểu nhầm là các lớp đã điểm danh. Sổ chỉ thay đổi khi bấm <b>Lưu vào sổ</b>; bấm <b>Hoàn tác</b> nếu nhầm.</p>`,
      [{ key: "ok", label: "Đặt lại", severity: "danger", outlined: false }, { key: "no", label: "Thôi" }], { icon: "pi-refresh" });
      if (k === "ok") handle(await api("reset_day"));
    }
    const undo = async () => handle(await api("undo"));
    return { store, S, filter, filters, rows, empty, note, tip, rowClass, meal, saveState, openClass, gotoUnresolved, reset, undo, doSave };
  },
  template: /* html */`
  <section class="page" id="page-dd">
    <Message v-if="S.hint" severity="warn" icon="pi pi-cog" class="clickable" @click="store.page = 'cd'">{{ S.hint }}</Message>
    <Message v-for="t in S.todo" severity="error" icon="pi pi-exclamation-triangle" class="clickable" @click="openClass(t.code)">{{ t.text }}</Message>
    <div v-if="S.info.length" class="text-muted small"><i class="pi pi-info-circle me-1"></i>{{ S.info.join(" · ") }}</div>

    <div class="row-gap flex-wrap">
      <span v-if="!S.unreported.length" class="text-success small"><i class="pi pi-check-circle me-1"></i>Các lớp đều đã báo</span>
      <template v-else>
        <span class="text-muted"><i class="pi pi-hourglass me-1"></i>Chưa báo ({{ S.unreported.length }}):</span>
        <Button v-for="c in S.unreported.slice(0, 12)" :key="c" :label="c" size="small" severity="secondary" outlined class="py-0" @click="openClass(c)" />
        <span v-if="S.unreported.length > 12" class="text-muted small">và {{ S.unreported.length - 12 }} lớp khác</span>
      </template>
      <SelectButton v-model="filter" :options="filters" optionLabel="label" optionValue="value" :allowEmpty="false" size="small" class="ms-auto" />
    </div>

    <div class="sheet">
      <div class="sheet-head">
        <b v-if="S.totals">Sĩ số {{ S.totals.si }} · Vắng {{ S.totals.vang }} · Hiện diện {{ S.totals.hd }}</b>
        <Tag v-if="meal" :severity="meal.ok ? 'success' : 'danger'" :icon="meal.ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"
          :value="meal.text" class="clickable" @click="store.page = 'sa'" />
        <span class="legend ms-auto" title="Bấm vào một lớp để chọn em vắng">
          <span><span class="dot muted"></span>chưa báo</span><span><span class="dot ok"></span>đủ</span>
          <span><span class="dot warn"></span>có vắng</span><span><span class="dot err"></span>cần xem</span>
        </span>
      </div>
      <DataTable :value="rows" scrollable scrollHeight="flex" :rowClass="rowClass" class="so" size="small"
        @row-click="e => e.data.kind === 'class' && openClass(e.data.code)">
        <template #empty><div class="text-center text-muted py-5">{{ empty }}</div></template>
        <Column header="Lớp" class="w-lop"><template #body="{ data: r }">
          <span v-if="r.kind === 'class'" :class="['dot', r.status]"></span>{{ r.code }}
          <span v-if="r.ma" class="text-muted small fw-normal"> ({{ r.ma }})</span></template></Column>
        <Column header="GVCN" class="gv"><template #body="{ data: r }"><div class="cut" :title="r.gvcn">{{ r.gvcn }}</div></template></Column>
        <Column field="si" header="Sĩ số" class="num" />
        <Column header="Vắng" class="num fw-bold"><template #body="{ data: r }">{{ r.vang || 0 }}</template></Column>
        <Column field="hd" header="Hiện diện" class="num" />
        <Column header="Tên học sinh vắng" class="ten"><template #body="{ data: r }">
          <template v-if="r.kind === 'class'">
            <template v-if="r.reported">{{ r.ten }}</template>
            <template v-else><span class="text-muted fst-italic">(chưa báo)</span>
              <span v-if="r.auto" class="text-muted small"> · nghỉ T6: {{ r.auto }}</span></template>
          </template></template></Column>
        <Column header="Ghi chú" class="note"><template #body="{ data: r }">
          <div v-if="r.kind === 'class'" class="cut" :title="tip(r)">{{ note(r) }}</div></template></Column>
      </DataTable>
    </div>

    <div class="actionbar">
      <span :class="['state', saveState.cls]" @click="gotoUnresolved">
        <i v-if="saveState.icon" :class="['pi', saveState.icon]"></i> {{ saveState.text }}<span v-if="saveState.sub" :class="{ 'text-danger': saveState.subErr }">{{ saveState.sub }}</span>
      </span>
      <Button label="Đặt lại" icon="pi pi-refresh" severity="danger" outlined @click="reset"
        title='Mọi lớp về "chưa báo", bỏ hết tên vắng đã chọn (dùng khi sheet trong sổ đã tạo sẵn)' />
      <Button label="Hoàn tác" icon="pi pi-undo" severity="secondary" outlined @click="undo" />
      <Button label="Lưu vào sổ" icon="pi pi-save" @click="doSave" />
    </div>
  </section>`,
};
