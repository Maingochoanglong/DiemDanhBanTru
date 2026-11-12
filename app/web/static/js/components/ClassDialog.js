// Bảng chọn tên của 1 lớp: bấm tên em để đánh vắng; ô tìm (gõ không dấu, dán nhiều tên) chỉ để lọc.
import { api } from "../api.js";
import { openDialog } from "../dialogs.js";
import { applyClass, store } from "../store.js";
import { matches, matchLevel, searchTerms, tailMatch } from "../util.js";
import ResolveDialog from "./ResolveDialog.js";

const { computed, nextTick, ref, watch } = Vue;

export default {
  setup() {
    const cls = store.cls;
    const q = ref(""), note = ref(""), search = ref(null);
    watch(() => cls.D, D => { note.value = D ? D.note : ""; });
    watch(() => cls.open, open => { if (open) q.value = ""; });

    // lọc theo các tên đã gõ / dán: mỗi tên chỉ hiện các em khớp tốt nhất
    // (đủ chữ, đúng dấu trước; khớp đầu chữ khi đang gõ dở); tên không khớp em nào hiện ô viền đứt
    const view = computed(() => {
      const D = cls.D;
      if (!D) return { tiles: [], miss: [], hint: false };
      const terms = searchTerms(q.value), found = new Set(), rank = new Map();
      const names = D.names.map(n => ({ n, s: `${n.full} ${n.name} ${n.alias || ""}` }));
      for (const t of terms) {
        const lv = names.map(x => matchLevel(t, x.s));
        const best = Math.max(0, ...lv);
        if (!best) continue;
        found.add(t);
        names.forEach((x, i) => { if (lv[i] === best) rank.set(x.n.id, Math.min(rank.get(x.n.id) ?? 1, tailMatch(t, x.n.full, x.n.name) ? 0 : 1)); });
      }
      const tiles = names.map(({ n }) => ({ n, show: !terms.length || rank.has(n.id), order: rank.get(n.id) ?? 0 }));
      const miss = terms.filter(t => !found.has(t)).map(t => ({ t, o: (D.others || []).find(x => matches(t, x.s)) }));
      const hint = !tiles.some(x => x.show) && miss.some(m => !m.o);
      return { tiles, miss, hint };
    });
    const friday = computed(() => cls.D?.names.some(n => n.absent && n.tags.includes("cắt thứ 6")));

    const toggle = async n => applyClass(await api("set_absent", cls.code, n.id, !n.absent));
    const full = async () => applyClass(await api("mark_full", cls.code));
    const clearExtra = async () => applyClass(await api("clear_extra", cls.code));
    const saveNote = async () => { if (note.value !== cls.D.note) applyClass(await api("set_note", cls.code, note.value)); };
    async function resolve(p) {
      const r = await openDialog(ResolveDialog, { header: "Chọn học sinh", width: "40rem", data: { D: cls.D, p } });
      if (r) applyClass(await api("resolve", cls.code, p.idx, r.key, r.sid));
    }
    // dán tên nhiều dòng: ô một dòng sẽ dính các dòng lại, nên đổi xuống dòng thành dấu phẩy
    function paste(e) {
      const t = e.clipboardData.getData("text");
      if (!/[\r\n]/.test(t)) return;
      e.preventDefault();
      const el = e.target;
      el.setRangeText(t.trim().replace(/\s*[\r\n]+\s*/g, ", "), el.selectionStart, el.selectionEnd, "end");
      q.value = el.value;
    }
    const focus = () => nextTick(() => search.value?.$el.focus());
    return { cls, q, note, search, view, friday, toggle, full, clearExtra, saveNote, resolve, paste, focus };
  },
  template: /* html */`
  <Dialog v-model:visible="cls.open" modal maximizable :draggable="false" class="cls-dialog" @show="focus">
    <template #header>
      <div v-if="cls.D" class="cls-head">
        <div><div class="p-dialog-title">Lớp {{ cls.D.code }}{{ cls.D.ma ? " (" + cls.D.ma + ")" : "" }}</div>
          <div class="text-muted">{{ cls.D.gvcn ? "GVCN " + cls.D.gvcn : "" }}</div></div>
        <div class="row-gap ms-auto me-3">
          <Tag severity="secondary" :value="'Sĩ số ' + cls.D.si" /><Tag severity="danger" :value="'Vắng ' + cls.D.vang" />
          <Tag severity="success" :value="'Hiện diện ' + cls.D.hd" />
        </div>
      </div>
    </template>
    <template v-if="cls.D">
      <Message v-for="w in cls.D.warnings" severity="error" icon="pi pi-exclamation-triangle" class="mb-2">{{ w }}</Message>
      <Message v-if="cls.D.pending.length" severity="warn" class="mb-2">
        <b>Tên trong sổ chưa khớp danh sách</b> — bấm vào tên để chọn em đúng:
        <div class="row-gap flex-wrap mt-2">
          <Button v-for="p in cls.D.pending" :key="p.idx" :label="p.query" icon="pi pi-question-circle" severity="danger" @click="resolve(p)" />
        </div>
      </Message>
      <Message v-if="cls.D.not_bt.length" severity="info" class="mb-2">Sổ có ghi tên em <b>không ăn bán trú</b> (theo danh sách hiện nay):
        {{ cls.D.not_bt.join(", ") }}. Giữ nguyên như sổ, không phải tên lạ.</Message>
      <Message v-if="cls.D.extra.length" severity="secondary" class="mb-2">Giữ nguyên chữ đã ghi: {{ cls.D.extra.join(", ") }}
        <Button label="Xóa các tên này" size="small" severity="secondary" outlined class="ms-2" @click="clearExtra" /></Message>
      <div v-if="cls.D.upcoming.length" class="text-muted small mb-2"><i class="pi pi-calendar"></i> Sắp tới: {{ cls.D.upcoming.join("; ") }}</div>

      <div class="row-gap mb-3">
        <IconField class="grow">
          <InputIcon class="pi pi-search" />
          <InputText id="clsSearch" ref="search" v-model="q" size="large" fluid autocomplete="off"
            placeholder="Tìm tên (không cần dấu) — nhiều tên cách nhau dấu phẩy" @paste="paste" @keydown.enter.prevent />
        </IconField>
        <Button :label="friday ? 'Đủ (trừ em nghỉ thứ 6)' : 'Lớp này đủ'" icon="pi pi-check-square" size="large" severity="success" outlined @click="full" />
      </div>

      <div class="names">
        <ToggleButton v-for="x in view.tiles" v-show="x.show" :key="x.n.id" :modelValue="x.n.absent" @update:modelValue="toggle(x.n)"
          :style="{ order: x.order }" class="nm" :title="x.n.full + ' · ' + x.n.dob">
          <i :class="['pi', x.n.absent ? 'pi-times-circle' : 'pi-circle', 'ck']"></i>
          <span class="nm-txt"><span>{{ x.n.name }}</span><span v-if="x.n.tags.length" class="tg">{{ x.n.tags.join(", ") }}</span></span>
        </ToggleButton>
        <div v-for="m in view.miss" :key="m.t" class="nm miss" :class="{ known: m.o }" title="Không tính vào bán trú của lớp">
          <i :class="['pi', m.o ? 'pi-user-minus' : 'pi-question-circle', 'ck']"></i>
          <span class="nm-txt"><span>{{ m.t }}</span><small class="why">{{ m.o ? m.o.why : "Không có trong danh sách" }}</small></span>
        </div>
        <div v-if="!cls.D.names.length" class="text-muted">Lớp này chưa có em nào ăn bán trú trong danh sách.</div>
      </div>
      <div v-if="view.hint" class="text-muted mt-3"><i class="pi pi-lightbulb me-1"></i>Gõ không cần dấu, vd. <i>gia huy</i>; nhiều tên cách nhau dấu phẩy.</div>
    </template>
    <template #footer>
      <div class="row-gap w-100">
        <label for="clsNote" class="text-nowrap">Ghi chú (cột H):</label>
        <InputText id="clsNote" v-model="note" class="grow" @change="saveNote" />
        <Button label="Xong" size="large" class="px-4" @click="cls.open = false" />
      </div>
    </template>
  </Dialog>`,
};
