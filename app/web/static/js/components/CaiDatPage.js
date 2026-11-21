// Trang Cài đặt: 3 file app làm việc (sổ điểm danh tháng, danh sách học sinh (Excel), CaiDat.txt).
import { chooseBook, chooseList, loadSettings, openPath, store } from "../store.js";

const { computed, onActivated } = Vue;

export default {
  setup() {
    onActivated(loadSettings);
    const s = computed(() => store.settings || {});
    const files = computed(() => [
      { key: "app_dir", icon: "pi-folder", label: "Thư mục app (file .exe, file cài đặt, sổ tạm). Gỡ app: xóa thư mục này.", full: true,
        buttons: [{ label: "Mở thư mục", icon: "pi-folder-open", open: "settings_folder" }] },
      { key: "so_file", icon: "pi-book", label: "Sổ điểm danh tháng", help: "Lưu vào sổ: app ghi sheet của ngày rồi xóa sổ tạm (sổ tạm nằm trong thư mục app, ghi sau mỗi thao tác).",
        buttons: [{ label: "Chọn sổ khác", icon: "pi-upload", run: chooseBook }] },
      { key: "cdhs_file", icon: "pi-file-excel", label: `Danh sách học sinh (Excel)${s.value.n ? `: ${s.value.n} học sinh` : ""}`,
        help: "Cột: Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không) · Tên gọi khác · Ăn ghép · Ăn từ · Cắt từ · Cắt thứ 6 (đặt ở trang <b>Học sinh</b>) · Ghi chú. " +
          (s.value.nhom_an ? `Bảng suất ăn: dựng theo sheet <b>Nhóm ăn</b> (${s.value.nhom_an} dòng).` : "Muốn app dựng bảng suất ăn: thêm sheet <b>Nhóm ăn</b>.") +
          " Sửa file này bằng Excel, lưu là app đọc lại ngay.",
        errors: [s.value.list_error, ...(s.value.nhom_an_errors || [])].filter(Boolean),
        buttons: [{ label: "Chọn file khác", icon: "pi-upload", run: chooseList }] },
      { key: "settings_file", icon: "pi-cog", label: "Cài đặt của app (cạnh file .exe)",
        buttons: [{ label: "Mở file", icon: "pi-external-link", open: "settings_file" }] },
    ]);
    const outside = key => (s.value.outside || []).includes(key);
    const click = b => b.open ? openPath(b.open) : b.run();
    const fileName = p => p.split(/[\\/]/).pop();
    return { s, files, click, fileName, outside };
  },
  template: /* html */`
  <section class="page">
    <Card>
      <template #title>3 file app làm việc</template>
      <template #content>
        <div class="files">
          <div v-for="f in files" :key="f.key" class="file-row">
            <i :class="['pi', f.icon, 'file-icon']"></i>
            <div class="stack">
              <div class="text-muted small">{{ f.label }}</div>
              <div :class="['fw-semibold', f.full ? 'text-break' : 'text-truncate']" :title="s[f.key]">{{ s[f.key] ? (f.full ? s[f.key] : fileName(s[f.key])) : "" }}<span v-if="!s[f.key]" class="text-muted fw-normal">chưa có</span></div>
              <div v-if="f.help" class="text-muted small" v-html="f.help"></div>
              <Message v-for="e in f.errors" severity="warn" size="small">{{ e }}</Message>
              <Message v-if="outside(f.key)" severity="info" size="small">File này nằm ngoài thư mục app. Nên chép vào thư mục app rồi chọn lại, để mọi file nằm chung một chỗ.</Message>
            </div>
            <div :class="['btn-col', f.buttons[0].open ? 'open' : 'pick']">
              <Button v-for="b in f.buttons" :key="b.label" :label="b.label" :icon="'pi ' + b.icon" :severity="b.open ? 'secondary' : undefined"
                :outlined="!!b.open" class="text-nowrap" @click="click(b)" />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </section>`,
};
