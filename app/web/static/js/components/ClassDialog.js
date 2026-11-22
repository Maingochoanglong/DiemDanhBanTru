// Bảng chọn tên của 1 lớp: bấm tên em để đánh vắng; ô tìm (gõ không dấu, dán nhiều tên) chỉ để lọc.
import { api, CONFIG } from "../api.js";
import { openDialog } from "../dialogs.js";
import { applyClass, store } from "../store.js";
import { matches, matchLevel, namesIn, searchTerms, tailMatch } from "../util.js";
import ResolveDialog from "./ResolveDialog.js";

const { computed, ref, watch } = Vue;

export default {
  setup() {
    const cls = store.cls;
    const q = ref(""), note = ref("");
    watch(() => cls.D, D => { note.value = D ? D.note : ""; });
    watch(() => [cls.open, cls.code], () => { q.value = ""; });  // mở bảng / sang lớp khác: xóa ô tìm

    // lọc theo các tên đã gõ / dán (dán nguyên tin Zalo của GVCN cũng được): mỗi tên chỉ hiện các em khớp tốt nhất
    // (đủ chữ, đúng dấu trước; khớp đầu chữ khi đang gõ dở); tên không khớp em nào hiện ô viền đứt
    const view = computed(() => {
      const D = cls.D;
      if (!D) return { tiles: [], miss: [], hint: false };
      const names = D.names.map(n => ({ n, s: `${n.full} ${n.name} ${n.alias || ""}` }));
      const texts = [...names.map(x => x.s), ...(D.others || []).map(x => x.s)];
      const terms = searchTerms(q.value).flatMap(t => namesIn(t, texts, CONFIG.name_words_max)), found = new Set(), rank = new Map();
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
    const friday = computed(() => cls.D?.names.some(n => n.absent && n.auto));  // có em cắt thứ 6 tự tính vắng

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
    return { cls, q, note, view, friday, toggle, full, clearExtra, saveNote, resolve, paste };
  },
  template: /* html */`
  <Dialog v-model:visible="cls.open" modal :draggable="false" class="cls-dialog">
    <template #header>
      <div v-if="cls.D" class="cls-head">
        <div><div class="p-dialog-title">Lớp {{ cls.D.code }}{{ cls.D.ma ? " (" + cls.D.ma + ")" : "" }}</div>
          <div class="text-muted">{{ cls.D.gvcn ? "GVCN " + cls.D.gvcn : "" }}</div></div>
        <div class="inline">
          <Tag severity="secondary" :value="'Sĩ số ' + cls.D.si" /><Tag :severity="cls.D.vang ? 'warn' : 'secondary'" :value="'Vắng ' + cls.D.vang" />
          <Tag severity="secondary" :value="'Hiện diện ' + cls.D.hd" />
        </div>
      </div>
    </template>
    <div v-if="cls.D" class="cls-body">
      <Message v-for="w in cls.D.warnings" severity="error" icon="pi pi-exclamation-triangle">{{ w }}</Message>
      <Message v-if="cls.D.pending.length" severity="error">
        <div class="stack"><span><b>Tên trong sổ chưa khớp danh sách.</b> Bấm vào tên để chọn em đúng:</span>
          <div class="inline">
            <Button v-for="p in cls.D.pending" :key="p.idx" :label="p.query" icon="pi pi-question-circle" severity="danger" @click="resolve(p)" />
          </div></div>
      </Message>
      <Message v-if="cls.D.not_bt.length" severity="info">Sổ có ghi tên em <b>không ăn bán trú</b> (theo danh sách hiện nay):
        {{ cls.D.not_bt.join(", ") }}. Giữ nguyên như sổ, không phải tên lạ.</Message>
      <Message v-if="cls.D.extra.length" severity="error" icon="pi pi-exclamation-triangle">
        <div class="inline"><span>Tên trong sổ chưa xác định: <b>{{ cls.D.extra.join(", ") }}</b>. Bấm chọn đúng em bên dưới (nếu có), rồi bấm</span>
          <Button label="Xóa các tên này" size="small" severity="danger" outlined @click="clearExtra" /></div></Message>
      <div v-if="cls.D.upcoming.length" class="text-muted small"><i class="pi pi-calendar"></i> Sắp tới: {{ cls.D.upcoming.join("; ") }}</div>

      <div class="search-row">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText id="clsSearch" v-model="q" size="large" fluid autocomplete="off" autofocus
            placeholder="Gõ tên hoặc dán tin Zalo (không cần dấu, nhiều tên cách nhau dấu phẩy)" @paste="paste" @keydown.enter.prevent />
        </IconField>
        <Button :label="friday ? 'Đủ (trừ em cắt thứ 6)' : 'Lớp này đủ'" icon="pi pi-check-square" size="large" severity="success" outlined @click="full" />
      </div>

      <div class="names">
        <ToggleButton v-for="x in view.tiles" v-show="x.show" :key="x.n.id" :modelValue="x.n.absent" @update:modelValue="toggle(x.n)"
          :style="{ order: x.order }" class="nm" :title="x.n.full + ' · ' + x.n.dob">
          <i :class="['pi', x.n.absent ? 'pi-times-circle' : 'pi-circle', 'ck']"></i>
          <span class="nm-txt"><span>{{ x.n.name }}</span><span v-if="x.n.tags.length" class="tg">{{ x.n.tags.join(", ") }}</span></span>
        </ToggleButton>
        <div v-for="m in view.miss" :key="m.t" class="nm miss" :class="{ known: m.o }" title="Không tính vào bán trú của lớp">
          <i :class="['pi', m.o ? 'pi-user-minus' : 'pi-question-circle', 'ck']"></i>
          <span class="nm-txt"><span>{{ m.t }}</span><small class="why">{{ m.o ? m.o.why : "Không có trong lớp này" }}</small></span>
        </div>
        <div v-if="!cls.D.names.length" class="text-muted">Lớp này chưa có em nào ăn bán trú trong danh sách.</div>
      </div>
      <div v-if="view.hint" class="text-muted"><i class="pi pi-lightbulb"></i> Gõ không cần dấu, vd. <i>gia huy</i>; nhiều tên cách nhau dấu phẩy.</div>
    </div>
    <template #footer>
      <div class="note-row">
        <label for="clsNote" class="text-nowrap">Ghi chú (cột H):</label>
        <InputText id="clsNote" v-model="note" @change="saveNote" />
        <Button label="Xong" size="large" @click="cls.open = false" />
      </div>
    </template>
  </Dialog>`,
};
