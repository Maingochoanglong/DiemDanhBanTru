// Trang Suất ăn: bảng suất ăn như trong sổ (cột suất, tên ghép, gồm), em ghép vắng chưa rõ nhóm.
import { api } from "../api.js";
import { openPath, store } from "../store.js";
import { mealDiff } from "../util.js";

const { computed, onActivated, ref, watch } = Vue;

export default {
  setup() {
    const m = ref(null);
    const load = async () => { m.value = await api("meals"); };
    onActivated(load);
    watch(() => store.S, () => { if (store.page === "sa") load(); });  // vd. quay lại từ Excel vừa sửa cột Ăn ghép

    // như bảng trong sổ: dòng trống giữ chỗ cách dòng
    const rows = computed(() => {
      if (!m.value || m.value.empty) return [];
      const out = [];
      let prev = null, k = 0;
      for (const l of m.value.lines) {
        for (let r = prev === null ? l.row : prev + 1; r < l.row; r++) out.push({ k: k++, gap: true });
        prev = l.row;
        out.push({ k: k++, ...l });
      }
      if (m.value.self) out.push({ k: k++, self: true, absent: [], ...m.value.self });
      return out;
    });
    const title = computed(() => {
      const d = mealDiff(m.value);
      return m.value.ok ? `Tổng suất ${m.value.total} = hiện diện ${m.value.present}`
        : `${d[0].toUpperCase() + d.slice(1)}: tổng suất ${m.value.total}, hiện diện ${m.value.present}`;
    });
    const rowClass = r => r.gap ? "gap" : r.self ? "text-muted" : r.m ? "absent-row" : ""  // dòng có em ghép vắng;
    async function pick(sid, g) { const r = await api("pick_ghep", sid, g); store.S = r.state; load(); }
    function students(code) { store.hsPreset = code; store.page = "hs"; }
    const missing = computed(() => (m.value?.ghep || []).filter(g => g.done < g.n));  // lớp ghép còn em chưa ghi nhóm
    return { m, rows, title, rowClass, pick, students, openPath, missing };
  },
  template: /* html */`
  <section class="page">
    <div v-if="m" class="sheet box">
      <div class="sheet-head split">
        <div v-if="m.empty" class="fs-5 fw-bold">Sổ chưa có bảng suất ăn</div>
        <div v-else>
          <div :class="['fs-5 fw-bold', m.ok ? 'text-success' : 'text-danger']">
            <i :class="['pi', m.ok ? 'pi-check-circle' : 'pi-exclamation-triangle']"></i> {{ title }}</div>
          <div class="small text-muted">{{ m.self ? "Các nhóm " + m.groups_total + " + tự ăn tại lớp " + m.self.meals + " = " + m.total + " suất" : "Các nhóm: " + m.groups_total + " suất" }}</div>
        </div>
        <Button label="Sửa cột Ăn ghép" icon="pi pi-external-link" severity="secondary" outlined @click="openPath('cdhs_file')"
          title="Mở file danh sách học sinh: cột Ăn ghép (em ăn nhóm nào), sheet Nhóm ăn. Thêm / bỏ dòng suất ăn thì sửa trong sổ (Mở sổ Excel)." />
      </div>
      <div v-if="!m.empty && (m.ask.length || m.warnings.length || m.note)" class="sheet-notes">
        <Message v-if="m.ask.length" severity="warn">
          <div class="ask-grid">
            <div class="full"><b><i class="pi pi-question-circle"></i> Em ăn ghép vắng: chọn nhóm em đó ăn</b>
              <span class="small text-muted"> (chỉ cho ngày này; muốn app tự biết thì ghi cột <b>Ăn ghép</b> trong file Excel danh sách)</span></div>
            <template v-for="x in m.ask" :key="x.sid">
              <span><b>{{ x.name }}</b> <span class="text-muted">lớp {{ x.cls }}</span></span>
              <div class="chips wide"><Button v-for="g in x.groups" :key="g" :label="'Nhóm ' + g" size="small" outlined @click="pick(x.sid, g)" /></div>
            </template>
          </div>
        </Message>
        <Message v-for="w in m.warnings" severity="error" icon="pi pi-exclamation-triangle">{{ w }}</Message>
        <Message v-if="m.note" severity="info">{{ m.note }}</Message>
      </div>
      <DataTable v-if="!m.empty" :value="rows" dataKey="k" scrollable scrollHeight="flex" :rowClass="rowClass" size="small" class="meal">
        <Column header="Suất" class="text-center w-suat" headerClass="center"><template #body="{ data: l }">
          <b v-if="!l.gap">{{ l.meals }}</b></template></Column>
        <Column field="label" header="Tên ghép" class="fw-semibold w-label" />
        <Column header="Gồm"><template #body="{ data: l }">{{ l.gom }}
          <span v-if="l.absent && l.absent.length" class="text-absent">; vắng {{ l.absent.length }}:
            <template v-for="(x, i) in l.absent" :key="x.sid">{{ i ? ", " : "" }}<a v-if="x.picked" href="#" class="text-absent"
              title="Bấm để chọn lại nhóm" @click.prevent="pick(x.sid, '')">{{ x.name }}</a><template v-else>{{ x.name }}</template></template>
          </span></template></Column>
      </DataTable>
      <div v-else class="sheet-notes text-muted">Sheet mẫu của sổ không có bảng suất ăn bên dưới bảng điểm danh.</div>
      <div v-if="missing.length" class="sheet-foot small">
        <span v-for="g in missing" :key="g.code"><i class="pi pi-sitemap"></i> Lớp ghép <b>{{ g.code }}</b>:
          mới ghi nhóm <b class="text-remind">{{ g.done }}/{{ g.n }} em</b>, <a href="#" @click.prevent="students(g.code)">xem các em</a></span>
        <span class="text-muted">Ghi nhóm ở cột <b>Ăn ghép</b> trong file danh sách.</span>
      </div>
    </div>
  </section>`,
};
