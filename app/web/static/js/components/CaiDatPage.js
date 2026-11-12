// Trang Cài đặt: các file đang dùng (sổ tháng, danh sách học sinh, dữ liệu của app).
import { api } from "../api.js";
import { info } from "../dialogs.js";
import { chooseBook, importList, loadSettings, noteSuggestions, store } from "../store.js";

const { computed, onActivated } = Vue;

export default {
  setup() {
    onActivated(loadSettings);
    const s = computed(() => store.settings || {});
    const files = computed(() => [
      { key: "so_file", icon: "pi-book", label: "Sổ điểm danh tháng", buttons: [
        { label: "Chọn sổ khác…", icon: "pi-upload", run: chooseBook },
        { label: "Đọc ghi chú sổ…", icon: "pi-file-edit", outlined: true, run: noteSuggestions },
        { label: "Thư mục", icon: "pi-folder-open", open: "so_folder" }] },
      { key: "cdhs_file", icon: "pi-file-excel", label: "Danh sách học sinh (Excel)", buttons: [
        { label: "Nhập danh sách…", icon: "pi-download", run: () => importList() },
        { label: "Mở file", icon: "pi-external-link", open: "cdhs_file" }],
      help: "Cột: Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không) · Tên gọi khác · Ăn ghép (file toàn trường tô đỏ cũng nhập được). " +
        (s.value.nhom_an ? `Bảng suất ăn: dựng theo sheet <b>Nhóm ăn</b> (${s.value.nhom_an} dòng).` : "Muốn app dựng bảng suất ăn: thêm sheet <b>Nhóm ăn</b>.") },
      { key: "data", icon: "pi-database", label: "Dữ liệu của app", buttons: [{ label: "Thư mục", icon: "pi-folder-open", open: "data_folder" }] },
    ]);
    async function open(kind) { const r = await api("open_path", kind); if (r.error) info("Chưa mở được", r.error); }
    const click = b => b.open ? open(b.open) : b.run();
    const btnProps = b => b.open ? { severity: "secondary", outlined: true } : { outlined: !!b.outlined };
    const fileName = p => p.split(/[\\/]/).pop();
    return { s, files, open, click, btnProps, fileName };
  },
  template: /* html */`
  <section class="page">
    <Card>
      <template #title>File đang dùng</template>
      <template #content>
        <div v-for="f in files" :key="f.key" class="file-row">
          <i :class="['pi', f.icon, 'file-icon']"></i>
          <div class="grow min-w-0">
            <div class="text-muted small">{{ f.label }}</div>
            <div class="fw-semibold text-truncate" :title="s[f.key]">{{ s[f.key] ? fileName(s[f.key]) : "" }}<span v-if="!s[f.key]" class="text-muted fw-normal">chưa có</span></div>
            <div v-if="f.help" class="text-muted small" v-html="f.help"></div>
          </div>
          <div class="row-gap">
            <Button v-for="b in f.buttons" :key="b.label" :label="b.label" :icon="'pi ' + b.icon" v-bind="btnProps(b)" class="text-nowrap" @click="click(b)" />
          </div>
        </div>
      </template>
    </Card>
    <div class="text-muted small">
      • Mỗi lần ghi, app tự sao lưu sổ cũ vào thư mục SaoLuu cạnh sổ (giữ 30 bản gần nhất) — <a href="#" @click.prevent="open('backup')">mở thư mục sao lưu</a>.<br>
      • Nếu sổ đang mở trong Excel, hãy đóng Excel rồi bấm Lưu lại.
    </div>
  </section>`,
};
