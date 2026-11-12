// Khung app: thanh bên (trang), thanh ngày, trang đang mở, các hộp thoại.
import { api, conn, IS_APP } from "../api.js";
import { ui } from "../dialogs.js";
import { askClose, askRestore, doSave, handle, loadSettings, store } from "../store.js";
import CaiDatPage from "./CaiDatPage.js";
import ClassDialog from "./ClassDialog.js";
import DiemDanhPage from "./DiemDanhPage.js";
import HocSinhPage from "./HocSinhPage.js";
import SetupDialog from "./SetupDialog.js";
import SuatAnPage from "./SuatAnPage.js";
import TopBar from "./TopBar.js";

const { computed, onMounted, ref, watch } = Vue;
const PAGES = { dd: DiemDanhPage, sa: SuatAnPage, hs: HocSinhPage, cd: CaiDatPage };

function readSide() { try { return localStorage.getItem("sideMin") === "1"; } catch { return false; } }

export default {
  components: { ClassDialog, SetupDialog, TopBar },
  setup() {
    ui.dialog = PrimeVue.useDialog();
    ui.toast = PrimeVue.useToast();
    const nav = [["dd", "Điểm danh", "pi-check-square"], ["sa", "Suất ăn", "pi-shopping-bag"], ["hs", "Học sinh", "pi-users"],
      ["cd", "Cài đặt", "pi-cog"]]
      .map(([page, label, icon]) => ({ page, label, icon: "pi " + icon, command: () => { store.page = page; } }));
    const page = computed(() => PAGES[store.page]);
    const sideMin = ref(readSide());
    watch(sideMin, v => { try { localStorage.setItem("sideMin", v ? "1" : "0"); } catch { /* bỏ qua */ } });

    document.addEventListener("keydown", e => {
      if (e.ctrlKey && e.key.toLowerCase() === "s") { e.preventDefault(); doSave(); }
      if (e.ctrlKey && e.key.toLowerCase() === "z" && !e.target.matches("input,textarea")) { e.preventDefault(); api("undo").then(handle); }
    });

    // Esc khi có hộp chồng lên hộp (vd. lên lịch trên bảng chọn tên của lớp): chỉ đóng hộp trên cùng
    window.addEventListener("keydown", e => {
      if (e.key !== "Escape") return;
      const masks = [...document.querySelectorAll(".p-dialog-mask")];
      if (masks.length < 2) return;
      e.stopPropagation();
      e.preventDefault();
      const top = masks.reduce((a, b) => (+getComputedStyle(b).zIndex > +getComputedStyle(a).zIndex ? b : a));
      top.querySelector(".p-dialog-close-button")?.click();
    }, true);

    onMounted(async () => {
      const r = handle(await api("boot"));
      if (r?.setup) { store.setup = r.setup; return; }
      loadSettings();
      if (r?.restore) await askRestore(r.restore);
    });
    return { store, conn, IS_APP, nav, page, sideMin, askClose };
  },
  template: /* html */`
  <div :class="['app', { 'side-min': sideMin }]">
    <aside class="sidebar">
      <div class="brand-row">
        <div class="brand">Điểm danh<br>bán trú</div>
        <Button :icon="sideMin ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'" text rounded severity="secondary"
          :title="sideMin ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên'" @click="sideMin = !sideMin" />
      </div>
      <Menu :model="nav" class="nav">
        <template #item="{ item, props }">
          <a v-bind="props.action" :class="['nav-link', { active: store.page === item.page }]" :title="item.label">
            <i :class="item.icon"></i><span class="lbl">{{ item.label }}</span></a>
        </template>
      </Menu>
      <a v-if="IS_APP" href="#" class="nav-link quit" title="Thoát app (hỏi lưu trước nếu còn thay đổi)" @click.prevent="askClose">
        <i class="pi pi-sign-out"></i><span class="lbl">Thoát</span></a>
      <div class="ver">{{ store.settings ? "Phiên bản " + store.settings.version : "" }}</div>
    </aside>
    <main v-if="store.S">
      <TopBar />
      <KeepAlive><component :is="page" /></KeepAlive>
    </main>
  </div>
  <ClassDialog />
  <SetupDialog />
  <DynamicDialog />
  <Toast position="bottom-right" />
  <Dialog :visible="conn.gone" modal :closable="false" :closeOnEscape="false" :draggable="false" :header="conn.quit ? 'Đã thoát app' : 'App đã tắt'">
    <div class="text-center"><i class="pi pi-power-off gone-icon"></i>
      <p class="text-muted mb-0">Có thể đóng thẻ trình duyệt này.<br>Muốn dùng tiếp: mở lại <b>DiemDanhBanTru.exe</b>.</p></div>
  </Dialog>`,
};
