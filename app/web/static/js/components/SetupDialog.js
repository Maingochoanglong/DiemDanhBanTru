// Thiết lập lần đầu (bản .exe mới tải về): nơi đặt file dữ liệu, sổ tháng, danh sách học sinh.
import { api } from "../api.js";
import { chooseBook, handle, importList, loadSettings, store } from "../store.js";

const { computed, ref } = Vue;

export default {
  setup() {
    const err = ref("");
    const s = computed(() => store.setup);
    const steps = computed(() => {
      const x = s.value, noFolder = !x.folder_done;
      return [
        { key: "folder", title: "Nơi đặt file dữ liệu của app", desc: x.folder_done ? "" : `Gợi ý: ${x.folder}`, value: x.folder_done ? x.folder : "",
          buttons: [{ label: "Dùng thư mục gợi ý", run: () => folder(true) }, { label: "Chọn thư mục…", outlined: true, run: () => folder(false) }] },
        { key: "book", title: "Sổ điểm danh tháng (Excel)", desc: "Chọn file sổ của tháng đang điểm danh.", value: x.book, off: noFolder,
          buttons: [{ label: "Chọn sổ…", outlined: x.book_done, run: () => step(chooseBook) }] },
        { key: "list", title: "Danh sách học sinh (Excel)", desc: "Chọn file danh sách để nhập.", value: x.list ? `${x.list} (${x.n} học sinh)` : "", off: noFolder,
          buttons: [{ label: "Nhập danh sách…", outlined: x.list_done, run: () => step(() => importList()) }] },
      ].map(st => ({ ...st, done: x[st.key + "_done"] }));
    });
    async function folder(useDefault) {
      const r = await api("setup_folder", null, useDefault);
      err.value = r.error || "";
      store.setup = r.setup;
    }
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
      <p class="text-muted">Bản app mới tải về: làm đủ 3 bước dưới đây rồi bấm <b>Bắt đầu điểm danh</b>.</p>
      <div v-for="(st, i) in steps" :key="st.key" :class="['setup-step', { done: st.done, off: st.off }]">
        <div class="num"><i v-if="st.done" class="pi pi-check"></i><template v-else>{{ i + 1 }}</template></div>
        <div class="grow">
          <div class="fw-semibold">{{ st.title }}</div><div class="small text-muted">{{ st.desc }}</div>
          <div v-if="st.value" class="path"><i class="pi pi-check-circle text-success me-1"></i>{{ st.value }}</div>
        </div>
        <div class="row-gap"><Button v-for="b in st.buttons" :key="b.label" :label="b.label" :outlined="b.outlined" :disabled="st.off" @click="b.run" /></div>
      </div>
      <div class="text-danger small mt-2 pre-line">{{ err || missing }}</div>
    </template>
    <template #footer>
      <Button label="Bắt đầu điểm danh" icon="pi pi-check-circle" size="large" :disabled="!s || s.missing.length > 0" @click="finish" />
    </template>
  </Dialog>`,
};
