// Hộp hỏi / thông báo dùng dịch vụ của PrimeVue (DialogService, ToastService).
import AskBody from "./components/AskBody.js";
import { esc } from "./util.js";

const { h, markRaw } = Vue;
export const ui = { dialog: null, toast: null };  // App.js gán useDialog() / useToast() khi khởi động

// Mở một thành phần trong hộp thoại; thành phần gọi dialogRef.value.close(kết quả) để đóng
export function openDialog(comp, { header = "", width = "40rem", data = {}, icon = "", danger = false } = {}) {
  return new Promise(resolve => {
    ui.dialog.open(markRaw(comp), {
      props: { header, modal: true, draggable: false, style: { width }, breakpoints: { "960px": "92vw" } },
      templates: icon || danger ? { header: markRaw({ render: () => h("span", { class: ["p-dialog-title", { "text-danger": danger }] },
        [icon ? h("i", { class: `pi ${icon} me-2` }) : null, header]) }) } : undefined,
      data,
      onClose: opt => resolve(opt && opt.data !== undefined ? opt.data : null),
    });
  });
}

// buttons = [{key, label, severity, outlined}] → trả về key (null nếu đóng hộp)
export const ask = (title, html, buttons, opts = {}) =>
  openDialog(AskBody, { header: title, width: opts.width || "34rem", icon: opts.icon, danger: opts.danger, data: { html, buttons } });

export const info = (title, msg) => ask(title, `<div class="pre-line">${esc(msg)}</div>`, [{ key: "ok", label: "Đóng" }]);

export function toast(msg, severity = "success") {
  if (msg) ui.toast.add({ severity, summary: msg, life: severity === "error" ? 12000 : 6000 });
}

// 3 lựa chọn hay dùng khi còn thay đổi chưa lưu
export const SAVE_CHOICES = go => [{ key: "save", label: `Lưu rồi ${go}` },
  { key: "discard", label: "Không lưu", severity: "danger", outlined: true }, { key: "stay", label: "Ở lại", severity: "secondary", outlined: true }];
