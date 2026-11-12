// Trang Suất ăn: bảng suất ăn như trong sổ (cột suất, tên ghép, gồm), em ghép vắng chưa rõ nhóm.
import { api } from "../api.js";
import { store } from "../store.js";
import { mealDiff } from "../util.js";
import MealEditor from "./MealEditor.js";

const { computed, onActivated, ref } = Vue;

export default {
  components: { MealEditor },
  setup() {
    const m = ref(null), editing = ref(false);
    const load = async () => { m.value = await api("meals"); };
    onActivated(() => { editing.value = false; load(); });

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
    const rowClass = r => r.gap ? "gap" : r.self ? "text-muted" : r.m ? "warn-row" : "";
    async function pick(sid, g) { const r = await api("pick_ghep", sid, g); store.S = r.state; load(); }
    function students(code) { store.hsPreset = code; store.page = "hs"; }
    function closeEditor(saved) { editing.value = false; if (saved) load(); }
    return { m, editing, rows, title, rowClass, pick, students, closeEditor };
  },
  template: /* html */`
  <section class="page">
    <MealEditor v-if="editing" @close="closeEditor" />
    <div v-else-if="m" class="sheet">
      <div class="sheet-head">
        <div class="grow">
          <template v-if="m.empty"><div class="fs-5 fw-bold">Sổ chưa có bảng suất ăn</div></template>
          <template v-else>
            <div :class="['fs-5 fw-bold', m.ok ? 'text-success' : 'text-danger']">
              <i :class="['pi', m.ok ? 'pi-check-circle' : 'pi-exclamation-triangle']"></i> {{ title }}</div>
            <div class="small text-muted">{{ m.self ? "Các nhóm " + m.groups_total + " + tự ăn tại lớp " + m.self.meals + " = " + m.total + " suất" : "Các nhóm: " + m.groups_total + " suất" }}</div>
          </template>
        </div>
        <Button label="Sửa cách ghép" icon="pi pi-sitemap" outlined title="Lớp nào ăn chung dòng nào trong bảng suất ăn của sổ" @click="editing = true" />
      </div>
      <div v-if="!m.empty" class="px-3 pt-2">
        <Message v-if="m.ask.length" severity="warn" class="mb-2">
          <div class="mb-1"><b><i class="pi pi-question-circle me-2"></i>Em ăn ghép vắng — chọn nhóm em đó ăn:</b>
            <span class="small text-muted ms-2">chỉ cho ngày này; muốn app tự biết thì ghi cột <b>Ăn ghép</b> trong file Excel danh sách</span></div>
          <div v-for="x in m.ask" :key="x.sid" class="row-gap flex-wrap mb-1">
            <span class="ask-name"><b>{{ x.name }}</b> <span class="text-muted">lớp {{ x.cls }}</span></span>
            <Button v-for="g in x.groups" :key="g" :label="'Nhóm ' + g" size="small" severity="contrast" outlined class="py-0" @click="pick(x.sid, g)" />
          </div>
        </Message>
        <Message v-for="w in m.warnings" severity="error" icon="pi pi-exclamation-triangle" class="mb-2">{{ w }}</Message>
        <Message v-if="m.note" severity="info" class="mb-2">{{ m.note }}</Message>
      </div>
      <DataTable v-if="!m.empty" :value="rows" dataKey="k" scrollable scrollHeight="flex" :rowClass="rowClass" size="small" class="meal">
        <Column header="Suất" class="text-center w-suat" headerClass="center"><template #body="{ data: l }">
          <b v-if="!l.gap" :class="{ 'text-danger': !l.self }">{{ l.meals }}</b></template></Column>
        <Column field="label" header="Tên ghép" class="fw-semibold w-label" />
        <Column header="Gồm"><template #body="{ data: l }">{{ l.gom }}
          <span v-if="l.absent && l.absent.length" class="text-danger"> − vắng {{ l.absent.length }}:
            <template v-for="(x, i) in l.absent" :key="x.sid">{{ i ? ", " : "" }}<a v-if="x.picked" href="#" class="link-danger"
              title="Bấm để chọn lại nhóm" @click.prevent="pick(x.sid, '')">{{ x.name }}</a><template v-else>{{ x.name }}</template></template>
          </span></template></Column>
      </DataTable>
      <div v-if="m.empty" class="p-3 text-muted">Sheet mẫu của sổ không có bảng suất ăn bên dưới bảng điểm danh.</div>
      <div v-if="m.ghep && m.ghep.length" class="sheet-foot small">
        <span v-for="g in m.ghep" :key="g.code" class="me-3 text-nowrap"><i class="pi pi-sitemap me-1"></i>Lớp ghép <b>{{ g.code }}</b>:
          đã ghi nhóm <b :class="g.done < g.n ? 'text-warn' : 'text-success'">{{ g.done }}/{{ g.n }} em</b> ·
          <a href="#" @click.prevent="students(g.code)">Xem các em</a></span>
        <span v-if="m.ghep.some(g => g.done < g.n)" class="text-muted">(ghi nhóm ở cột <b>Ăn ghép</b> trong Excel)</span>
      </div>
    </div>
  </section>`,
};
