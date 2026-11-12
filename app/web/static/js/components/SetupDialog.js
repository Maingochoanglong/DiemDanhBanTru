// Thiết lập lần đầu (bản .exe mới tải về): chọn sổ điểm danh tháng và file danh sách học sinh.
import { api } from "../api.js";
import { chooseBook, chooseList, handle, loadSettings, store } from "../store.js";

const { computed, ref } = Vue;

export default {
  setup() {
    const err = ref("");
    const s = computed(() => store.setup);
    const steps = computed(() => {
      const x = s.value;
      return [
        { key: "book", title: "Sổ điểm danh tháng (Excel)", desc: "Chọn file sổ của tháng đang điểm danh.", value: x.book,
          buttons: [{ label: "Chọn sổ…", outlined: x.book_done, run: () => step(chooseBook) }] },
        { key: "list", title: "Danh sách học sinh (Excel)", desc: "Chọn file danh sách học sinh.", value: x.list ? `${x.list} (${x.n} học sinh)` : "",
          buttons: [{ label: "Chọn file…", outlined: x.list_done, run: () => step(chooseList) }] },
      ].map(st => ({ ...st, done: x[st.key + "_done"] }));
    });
    async function step(fn) { await fn(); store.setup = await api("setup_info"); }
    async function finish() {
      const r = await api("finish_setup");
      if (r.error) { err.value = r.error; store.setup = r.setup; return; }
      store.setup = null;
      handle(r);
      loadSettings();
    }
    const missing = computed(() => s.value.missing.length ? "Còn thiếu: " + s.value.missing.join(", ") + "." : "");
    return { s, steps, err, missing, finish };
  },
  template: /* html */`
  <Dialog :visible="!!s" modal :closable="false" :closeOnEscape="false" :draggable="false" header="Thiết lập trước khi điểm danh" class="setup-dialog">
    <template v-if="s">
      <p class="text-muted">Bản app mới tải về: làm đủ 2 bước dưới đây rồi bấm <b>Bắt đầu điểm danh</b>.</p>
      <div v-for="(st, i) in steps" :key="st.key" :class="['setup-step', { done: st.done }]">
        <div class="num"><i v-if="st.done" class="pi pi-check"></i><template v-else>{{ i + 1 }}</template></div>
        <div class="grow">
          <div class="fw-semibold">{{ st.title }}</div><div class="small text-muted">{{ st.desc }}</div>
          <div v-if="st.value" class="path"><i class="pi pi-check-circle text-success me-1"></i>{{ st.value }}</div>
        </div>
        <div class="row-gap"><Button v-for="b in st.buttons" :key="b.label" :label="b.label" :outlined="b.outlined" @click="b.run" /></div>
      </div>
      <div class="text-danger small mt-2 pre-line">{{ err || missing }}</div>
    </template>
    <template #footer>
      <Button label="Bắt đầu điểm danh" icon="pi pi-check-circle" size="large" :disabled="!s || s.missing.length > 0" @click="finish" />
    </template>
  </Dialog>`,
};
