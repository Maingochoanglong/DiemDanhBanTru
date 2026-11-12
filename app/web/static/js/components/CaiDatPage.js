// Trang Cài đặt: 3 file app làm việc — sổ điểm danh tháng, danh sách học sinh (Excel), CaiDat.txt.
import { chooseBook, chooseList, loadSettings, openPath, store } from "../store.js";

const { computed, onActivated } = Vue;

export default {
  setup() {
    onActivated(loadSettings);
    const s = computed(() => store.settings || {});
    const files = computed(() => [
      { key: "so_file", icon: "pi-book", label: "Sổ điểm danh tháng", help: "Lưu vào sổ: app ghi sheet của ngày rồi xóa sổ tạm (… tamthoi.xlsx cạnh sổ, ghi sau mỗi thao tác).",
        buttons: [{ label: "Chọn sổ khác…", icon: "pi-upload", run: chooseBook }, { label: "Thư mục", icon: "pi-folder-open", open: "so_folder" }] },
      { key: "cdhs_file", icon: "pi-file-excel", label: `Danh sách học sinh (Excel)${s.value.n ? ` — ${s.value.n} học sinh` : ""}`,
        help: "Cột: Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không) · Tên gọi khác · Ăn ghép · Ghi chú (vd. <i>cắt thứ 6</i>, <i>cắt từ 30/10</i>, <i>ăn từ 3/11</i>). " +
          (s.value.nhom_an ? `Bảng suất ăn: dựng theo sheet <b>Nhóm ăn</b> (${s.value.nhom_an} dòng).` : "Muốn app dựng bảng suất ăn: thêm sheet <b>Nhóm ăn</b>.") +
          " Sửa file này bằng Excel: app tự đọc lại khi mở ngày.",
        errors: [s.value.list_error, ...(s.value.nhom_an_errors || [])].filter(Boolean),
        buttons: [{ label: "Chọn file khác…", icon: "pi-upload", run: chooseList }, { label: "Mở file", icon: "pi-external-link", open: "cdhs_file" }] },
      { key: "settings_file", icon: "pi-cog", label: "Cài đặt của app (cạnh file .exe)",
        buttons: [{ label: "Mở file", icon: "pi-external-link", open: "settings" }] },
    ]);
    const click = b => b.open ? openPath(b.open) : b.run();
    const fileName = p => p.split(/[\\/]/).pop();
    return { s, files, click, fileName };
  },
  template: /* html */`
  <section class="page">
    <Card>
      <template #title>3 file app làm việc</template>
      <template #content>
        <div v-for="f in files" :key="f.key" class="file-row">
          <i :class="['pi', f.icon, 'file-icon']"></i>
          <div class="grow min-w-0">
            <div class="text-muted small">{{ f.label }}</div>
            <div class="fw-semibold text-truncate" :title="s[f.key]">{{ s[f.key] ? fileName(s[f.key]) : "" }}<span v-if="!s[f.key]" class="text-muted fw-normal">chưa có</span></div>
            <div v-if="f.help" class="text-muted small" v-html="f.help"></div>
            <Message v-for="e in f.errors" severity="warn" size="small" class="mt-1">{{ e }}</Message>
          </div>
          <div class="row-gap">
            <Button v-for="b in f.buttons" :key="b.label" :label="b.label" :icon="'pi ' + b.icon" :severity="b.open ? 'secondary' : undefined"
              :outlined="!!b.open" class="text-nowrap" @click="click(b)" />
          </div>
        </div>
      </template>
    </Card>
    <div class="text-muted small">• Nếu sổ đang mở trong Excel, hãy đóng Excel rồi bấm Lưu lại.</div>
  </section>`,
};
