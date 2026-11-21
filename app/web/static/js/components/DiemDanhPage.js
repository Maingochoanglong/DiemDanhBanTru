// Trang Điểm danh: bảng như tờ sổ (lớp, sĩ số, vắng, hiện diện, tên vắng, ghi chú) + thanh lưu.
import { api, CONFIG } from "../api.js";
import { ask } from "../dialogs.js";
import { doSave, gotoDay, handle, openClass, store } from "../store.js";
import { mealDiff } from "../util.js";

const { computed } = Vue;

export default {
  setup() {
    const S = computed(() => store.S);
    const rows = computed(() => S.value.rows);
    const note = r => [r.sched ? "[Lịch]" : "", r.warn, r.not_bt ? `Không ăn BT: ${r.not_bt}` : "", r.note].filter(Boolean).join(" · ");
    const tip = r => (r.sched ? "[Lịch] = sĩ số đổi theo lịch thêm/cắt. " : "") + [r.warn, r.note].filter(Boolean).join(" · ");
    const rowClass = r => r.kind === "class" ? `cls st-${r.status}` : r.kind;
    const meal = computed(() => {
      const m = S.value.meal;
      return m && { ok: m.ok, text: m.ok ? `Tổng suất ${m.total} = hiện diện ${m.present}` : `Suất ăn ${mealDiff(m)}${m.ask ? ` · ${m.ask} em ghép chưa rõ nhóm` : ""}` };
    });
    const saveState = computed(() => {
      const s = S.value;
      if (s.unresolved) return { cls: "err", icon: "pi-exclamation-triangle", text: `Còn ${s.unresolved} tên chưa rõ, xử lý xong mới lưu được` };
      if (s.dirty) return { cls: "dirty", icon: "pi-pencil", text: "Có thay đổi chưa lưu vào sổ",
        sub: s.temp_error ? `. ${s.temp_error}` : (s.temp_at ? ` (đã lưu tạm lúc ${s.temp_at})` : ""), subErr: !!s.temp_error };
      return { cls: "", text: s.exists ? "Đã có trong sổ" : (s.book ? "Ngày này chưa có trong sổ" : "") };
    });
    function gotoUnresolved() { if (S.value.unresolved) openClass(S.value.need_look[0]); }
    async function reset() {
      const k = await ask("Đặt lại điểm danh ngày này?", `<p>Mọi lớp về <b>chưa báo</b>, bỏ hết tên vắng đã chọn. Ghi chú và sĩ số giữ nguyên.</p>
        <p class="text-muted">Dùng khi sheet trong sổ đã tạo sẵn nên app hiểu nhầm là các lớp đã điểm danh. Sổ chỉ thay đổi khi bấm <b>Lưu vào sổ</b>; bấm <b>Hoàn tác</b> nếu nhầm.</p>`,
      [{ key: "ok", label: "Đặt lại", severity: "danger", outlined: false }, { key: "no", label: "Thôi" }], { icon: "pi-refresh" });
      if (k === "ok") handle(await api("reset_day"));
    }
    const undo = async () => handle(await api("undo"));
    const shown = CONFIG.unreported_shown;  // số mã lớp "Chưa báo" hiện trên thanh
    // chưa có sổ tháng này: mở lại ngày để app hỏi tạo sổ tháng mới; còn lại thì vào Cài đặt
    const hintClick = () => S.value.hint_month ? gotoDay(f => api("open_day", S.value.date, f)) : (store.page = "cd");
    return { store, shown, S, rows, note, tip, rowClass, meal, saveState, openClass, gotoUnresolved, reset, undo, doSave, hintClick };
  },
  template: /* html */`
  <section class="page" id="page-dd">
    <div class="page-top notes">
      <Message v-if="S.hint" severity="warn" :icon="S.hint_month ? 'pi pi-calendar-plus' : 'pi pi-cog'" class="full clickable" @click="hintClick">{{ S.hint }}</Message>
      <div v-if="S.info.length" class="full label text-muted small"><i class="pi pi-info-circle"></i>{{ S.info.join(" · ") }}</div>
      <template v-if="S.need_look.length">
        <span class="label text-danger fw-semibold" title="Lớp có tên trong sổ chưa xác định hoặc sĩ số lệch: xem chữ đỏ ở cột Ghi chú">
          <i class="pi pi-exclamation-triangle"></i>Cần xem ({{ S.need_look.length }}):</span>
        <div class="chips">
          <Button v-for="c in S.need_look.slice(0, shown)" :key="c" :label="c" size="small" severity="danger" outlined @click="openClass(c)" />
          <span v-if="S.need_look.length > shown" class="more text-muted small">và {{ S.need_look.length - shown }} lớp khác</span>
        </div>
      </template>
      <span v-if="!S.unreported.length && rows.length" class="full label text-success small"><i class="pi pi-check-circle"></i>Các lớp đều đã báo</span>
      <template v-else-if="S.unreported.length">
        <span class="label text-muted"><i class="pi pi-hourglass"></i>Chưa báo ({{ S.unreported.length }}):</span>
        <div class="chips">
          <Button v-for="c in S.unreported.slice(0, shown)" :key="c" :label="c" size="small" severity="secondary" outlined @click="openClass(c)" />
          <span v-if="S.unreported.length > shown" class="more text-muted small">và {{ S.unreported.length - shown }} lớp khác</span>
        </div>
      </template>
    </div>

    <div class="sheet box">
      <div class="sheet-head">
        <b v-if="S.totals">Sĩ số {{ S.totals.si }} · Vắng {{ S.totals.vang }} · Hiện diện {{ S.totals.hd }}</b>
        <Tag v-if="meal" :severity="meal.ok ? 'success' : 'danger'" :icon="meal.ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"
          :value="meal.text" class="clickable" @click="store.page = 'sa'" />
      </div>
      <DataTable :value="rows" scrollable scrollHeight="flex" :rowClass="rowClass" class="so" size="small"
        @row-click="e => e.data.kind === 'class' && openClass(e.data.code)">
        <template #empty><div class="text-center text-muted">Chưa có danh sách học sinh. Vào Cài đặt để chọn file.</div></template>
        <Column header="Lớp"><template #body="{ data: r }">
          <span v-if="r.kind === 'class'" :class="['dot', r.status]"></span>{{ r.code }}
          <span v-if="r.ma" class="text-muted small fw-normal"> ({{ r.ma }})</span></template></Column>
        <Column header="GVCN" class="gv"><template #body="{ data: r }"><div class="cut" :title="r.gvcn">{{ r.gvcn }}</div></template></Column>
        <Column field="si" header="Sĩ số" class="num" />
        <Column header="Vắng" class="num fw-bold vang"><template #body="{ data: r }">{{ r.vang || 0 }}</template></Column>
        <Column field="hd" header="Hiện diện" class="num" />
        <Column header="Tên học sinh vắng" class="ten"><template #body="{ data: r }">
          <template v-if="r.kind === 'class'">
            <template v-if="r.reported">{{ r.ten }}</template>
            <template v-else><span class="text-muted fst-italic">(chưa báo)</span>
              <span v-if="r.auto" class="text-muted small"> · cắt thứ 6: {{ r.auto }}</span></template>
          </template></template></Column>
        <Column header="Ghi chú" class="note"><template #body="{ data: r }">
          <div v-if="r.kind === 'class'" class="cut" :title="tip(r)">{{ note(r) }}</div></template></Column>
      </DataTable>
    </div>

    <div class="page-bottom actionbar">
      <span :class="['state', saveState.cls]" @click="gotoUnresolved">
        <i v-if="saveState.icon" :class="['pi', saveState.icon]"></i> {{ saveState.text }}<span v-if="saveState.sub" :class="{ 'text-danger': saveState.subErr }">{{ saveState.sub }}</span>
      </span>
      <Button label="Đặt lại" icon="pi pi-refresh" severity="secondary" text size="small" @click="reset"
        title='Mọi lớp về "chưa báo", bỏ hết tên vắng đã chọn (dùng khi sheet trong sổ đã tạo sẵn)' />
      <Button label="Hoàn tác" icon="pi pi-undo" severity="secondary" outlined @click="undo" />
      <Button label="Lưu vào sổ" icon="pi pi-save" :disabled="!S.book" @click="doSave" />
    </div>
  </section>`,
};
