// Khởi động giao diện: Vue 3 + PrimeVue (theme Aura, màu chính xanh dương), chữ tiếng Việt cho các thành phần.
import App from "./components/App.js";

const PV = PrimeVue;
const Theme = PV.definePreset(PrimeUIX.Themes.Aura, {
  semantic: { primary: Object.fromEntries([50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map(n => [n, `{blue.${n}}`])) },
});

const VI = {
  dayNames: ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"],
  dayNamesShort: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
  dayNamesMin: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
  monthNames: Array.from({ length: 12 }, (_, i) => `Tháng ${i + 1}`),
  monthNamesShort: Array.from({ length: 12 }, (_, i) => `Th${i + 1}`),
  firstDayOfWeek: 1, today: "Hôm nay", clear: "Xóa", dateFormat: "dd/mm/yy", weekHeader: "Tuần",
  emptyMessage: "Không có dữ liệu", emptyFilterMessage: "Không tìm thấy", emptySelectionMessage: "Chưa chọn",
  selectionMessage: "Đã chọn {0}", choose: "Chọn", cancel: "Hủy", accept: "Đồng ý", reject: "Không",
  aria: { close: "Đóng", maximizeWindow: "Phóng to", minimizeWindow: "Thu nhỏ" },
};

const app = Vue.createApp(App);
app.use(PV.Config, { theme: { preset: Theme, options: { darkModeSelector: false } }, locale: VI });
app.use(PV.ToastService);
app.use(PV.DialogService);
for (const name of ["Button", "Card", "Checkbox", "Column", "DataTable", "DatePicker", "Dialog", "DynamicDialog", "IconField", "InputGroup",
  "InputIcon", "InputText", "Listbox", "Menu", "Message", "Popover", "RadioButton", "Select", "SelectButton", "Tag", "Toast", "ToggleButton"]) {
  app.component(name, PV[name]);
}
app.mount("#app");
