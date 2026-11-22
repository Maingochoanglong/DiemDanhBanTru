// Tên trong sổ chưa khớp danh sách: chọn em đúng / giữ nguyên chữ đã ghi / bỏ qua.
// Đóng hộp với {key: "pick" | "raw" | "skip", sid} (null = đóng hộp).
const { inject, ref } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const { D, p } = dialogRef.value.data;
    const sid = ref(p.cands.length ? p.cands[0].id : null);
    const err = ref("");
    const names = D.names.map(n => ({ id: n.id, label: n.full + (n.name !== n.full ? ` (${n.name})` : "") }));
    function done(key) {
      if (key === "pick" && !sid.value) { err.value = "Hãy chọn em đúng trong danh sách, hoặc bấm Giữ nguyên chữ đã ghi."; return; }
      dialogRef.value.close({ key, sid: sid.value });
    }
    return { D, p, sid, err, names, done };
  },
  template: /* html */`
    <div class="stack-3">
      <p>Lớp {{ D.code }}: tên <b>"{{ p.query }}"</b> trong sổ chưa khớp danh sách bán trú.</p>
      <p v-if="p.other.length" class="text-muted">Có em cùng tên ở lớp khác: {{ p.other.join("; ") }}.</p>
      <div v-if="p.cands.length" class="pick-list">
        <label v-for="c in p.cands" :key="c.id" class="pick-item">
          <RadioButton v-model="sid" :value="c.id" /><span><b>{{ c.name }}</b> ({{ c.full }}, sinh {{ c.dob }})</span>
        </label>
      </div>
      <template v-else-if="names.length">
        <!-- không có em nào tên gần giống: cho chọn trong cả lớp -->
        <p>Nếu đây là tên gọi khác của một em trong lớp, chọn em đó
          <span class="text-muted">(muốn app tự nhận ra lần sau: ghi tên này vào cột <b>Tên gọi khác</b> trong file Excel danh sách)</span>:</p>
        <Select v-model="sid" :options="names" optionLabel="label" optionValue="id" placeholder="Chọn em" filter fluid />
      </template>
      <div v-if="err" class="text-danger">{{ err }}</div>
      <div class="dlg-foot">
        <div class="same-w">
          <Button label="Chọn em này" @click="done('pick')" />
          <Button label="Giữ nguyên chữ đã ghi" outlined @click="done('raw')" />
        </div>
        <Button label="Bỏ qua tên này" severity="secondary" outlined @click="done('skip')" />
      </div>
    </div>`,
};
