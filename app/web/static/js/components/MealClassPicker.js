// Chọn các lớp ăn chung một dòng bảng suất ăn. Đóng hộp với danh sách mã lớp đã tích (null = hủy).
const { inject, ref } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const { groups, classes, g } = dialogRef.value.data;
    const pick = ref([...g.classes]);
    const other = code => groups.find(x => x !== g && x.classes.includes(code));  // lớp đang ở dòng khác
    const where = code => { const o = other(code); return o.label || "dòng " + (groups.indexOf(o) + 1); };
    return { classes, pick, other, where, close: v => dialogRef.value.close(v) };
  },
  template: /* html */`
    <p class="text-muted mb-2">Bấm chọn các lớp ăn cả lớp ở dòng này. Lớp đang ở dòng khác hiện mờ; chọn thì lớp đó chuyển sang dòng này.</p>
    <div class="cls-grid">
      <label v-for="c in classes" :key="c.code" :class="['cls-pick', { other: other(c.code) }]">
        <Checkbox v-model="pick" :value="c.code" /> {{ c.code }}<span v-if="c.ma" class="text-muted small fw-normal"> ({{ c.ma }})</span>
        <div v-if="other(c.code)" class="small text-muted fw-normal">đang ở: {{ where(c.code) }}</div>
      </label>
    </div>
    <div class="dlg-foot">
      <Button label="Xong" icon="pi pi-check" @click="close(pick)" />
      <Button label="Hủy" severity="secondary" outlined @click="close(null)" />
    </div>`,
};
