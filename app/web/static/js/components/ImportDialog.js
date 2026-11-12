// Duyệt thay đổi trước khi áp dụng: nhập danh sách học sinh (kind "import") / gợi ý từ ghi chú sổ (kind "notes").
// Đóng hộp với danh sách số thứ tự các dòng được tích (null = hủy).
const { inject, ref } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const { kind, p } = dialogRef.value.data;
    const items = kind === "import" ? p.changes : p.items;
    const sel = ref(items.filter(c => c.apply).map(c => c.i));
    const close = v => dialogRef.value.close(v);
    return { kind, p, items, sel, close };
  },
  template: /* html */`
    <template v-if="kind === 'import'">
      <p>Đọc được <b>{{ p.n }}</b> học sinh trong <b>{{ p.file }}</b>, <b>{{ p.n_bt }}</b> em ăn bán trú.</p>
      <Message v-if="p.mismatch.length" severity="warn" class="mb-2">Lưu ý: màu chữ khác cột "Phân loại HS" ở: {{ p.mismatch.join("; ") }}.</Message>
      <Message v-if="p.meal_errors.length" severity="error" class="mb-2">
        <b>Sheet Nhóm ăn có lỗi nên app chưa dùng</b> (giữ bảng Nhóm ăn cũ). Sửa trong Excel rồi nhập lại:
        <ul class="mb-0"><li v-for="e in p.meal_errors">{{ e }}</li></ul>
      </Message>
      <Message v-if="p.meal_warnings.length" severity="warn" class="mb-2"><div v-for="e in p.meal_warnings">{{ e }}</div></Message>
      <Message v-if="!items.length" severity="success">Không có thay đổi nào so với danh sách hiện tại.</Message>
    </template>
    <p v-else class="text-muted">App đọc ghi chú cột H của sổ tháng rồi gợi ý cập nhật danh sách để sĩ số tự khớp và thứ 6 tự tính vắng. Bỏ tích dòng nào không đúng.</p>
    <template v-if="items.length">
      <p v-if="kind === 'import'" class="text-muted mb-1">Bỏ tích dòng nào không muốn áp dụng:</p>
      <Listbox v-model="sel" :options="items" optionValue="i" multiple listStyle="max-height: 50vh">
        <template #option="{ option, selected }"><Checkbox :modelValue="selected" binary readonly class="me-2" />
          <span :class="{ 'text-danger': option.removed }">{{ option.text }}</span></template>
      </Listbox>
    </template>
    <div class="dlg-foot">
      <Button label="Áp dụng" icon="pi pi-check" @click="close(sel)" />
      <Button label="Hủy" severity="secondary" outlined @click="close(null)" />
    </div>`,
};
