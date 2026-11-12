// Thanh ngày: lùi/tới ngày học, gõ ngày hoặc chọn trên lịch, hôm nay, sổ đang dùng.
import { api } from "../api.js";
import { info } from "../dialogs.js";
import { gotoDay, store } from "../store.js";
import { dateOf, isoOf } from "../util.js";

const { computed, ref, watch } = Vue;

export default {
  setup() {
    const S = computed(() => store.S);
    const text = ref(""), cal = ref(null);
    watch(S, s => { if (s) text.value = s.date_text; }, { immediate: true });  // đổi ngày không được: ô ngày trả về ngày đang mở
    const step = d => gotoDay(f => api("step_day", d, f));
    const open = iso => gotoDay(f => api("open_day", iso, f));
    const typed = () => { const v = text.value.trim(); if (v && v !== S.value.date_text) open(v); };  // Python hiểu nhiều cách gõ ngày
    function picked(d) { cal.value.hide(); if (d && isoOf(d) !== S.value.date) open(isoOf(d)); }
    const book = computed(() => S.value.book ? `${S.value.book_stem} · sheet ${S.value.sheet}${S.value.exists ? "" : " (mới)"}` : "Chưa chọn sổ tháng này");
    async function openBook() { const r = await api("open_book"); if (r.error) info("Chưa có sổ", r.error); }
    return { S, text, cal, step, typed, picked, book, openBook, dateOf, today: () => open(isoOf(new Date())) };
  },
  template: /* html */`
  <div class="topbar">
    <Button icon="pi pi-chevron-left" severity="secondary" outlined title="Ngày học trước" @click="step(-1)" />
    <InputGroup class="w-auto">
      <InputText id="dayInput" v-model="text" size="large" placeholder="dd/mm/yyyy" title="Gõ ngày rồi bấm Enter" @change="typed" /><!-- change: cả khi bấm Enter lẫn khi rời ô -->
      <Button icon="pi pi-calendar" severity="secondary" outlined title="Chọn ngày trên lịch" @click="cal.toggle($event)" />
    </InputGroup>
    <Popover ref="cal"><DatePicker :modelValue="dateOf(S.date)" inline @update:modelValue="picked" /></Popover>
    <Button icon="pi pi-chevron-right" severity="secondary" outlined title="Ngày học sau" @click="step(1)" />
    <Button label="Hôm nay" icon="pi pi-calendar-clock" outlined @click="today" />
    <span class="weekday">{{ S.weekday }}</span>
    <span class="book ms-auto" :title="S.book">{{ book }}</span>
    <Button label="Mở sổ Excel" icon="pi pi-file-excel" severity="success" outlined @click="openBook" />
  </div>`,
};
