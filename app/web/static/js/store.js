// Trạng thái chung của giao diện và các thao tác dùng ở nhiều trang. Mọi xử lý sổ nằm ở Python (app/web/api.py).
import { api, conn, IS_APP } from "./api.js";
import { ask, info, SAVE_CHOICES, toast } from "./dialogs.js";
import { esc, mealDiff } from "./util.js";

const { reactive } = Vue;

export const store = reactive({
  S: null,              // trạng thái màn chính (api.state)
  page: "dd",           // dd | sa | hs | cd
  cls: { open: false, code: null, D: null },  // bảng chọn tên của lớp đang mở
  settings: null,       // api.settings (file đang dùng, phiên bản)
  setup: null,          // màn Thiết lập (bản mới tải về)
  hsPreset: null,       // mở trang Học sinh lọc sẵn 1 lớp
});

export function handle(r) {  // kết quả chung từ Python: lỗi, thông báo, trạng thái
  if (!r) return r;
  if (r.state) store.S = r.state;
  if (r.flash) toast(r.flash);
  if (r.error) info("Có lỗi", r.error);
  return r;
}

// kết quả thao tác trên 1 lớp: {state, detail}
export function applyClass(r) {
  if (r.state) store.S = r.state;
  if (r.detail) store.cls.D = r.detail;
}

export async function loadSettings() { store.settings = await api("settings"); }

// ------------------------------------------------------------------ lớp
export async function openClass(code) {
  if (!code) return;
  const d = await api("class_detail", code);
  if (d.error) return info("Có lỗi", d.error);
  Object.assign(store.cls, { code, D: d, open: true });
}

// ------------------------------------------------------------------ ngày, lưu
export async function gotoDay(fn) {
  let r = await fn(false);
  if (r.ask_save) {
    const k = await ask("Chưa lưu", `Ngày ${esc(r.ask_save.day)} có thay đổi chưa lưu vào sổ.`, SAVE_CHOICES("chuyển ngày"));
    if (k === "save") { if (!(await doSave())) return; }
    else if (k !== "discard") { store.S = { ...store.S }; return; }  // trả ô ngày về ngày đang mở
    r = await fn(true);
  }
  handle(r);
  if (r.need_month) {
    const n = r.need_month;
    const k = await ask("Sổ tháng mới", `Chưa có sổ điểm danh tháng ${n.month}/${n.year} trong thư mục<br><code>${esc(n.folder)}</code>.<br><br>
      Tạo sổ mới từ sheet cuối của sổ <b>${esc(n.prev)}</b>? (giữ nguyên mẫu, chữ ký, ghi chú)`,
      [{ key: "new", label: "Tạo sổ tháng mới" }, { key: "pick", label: "Chọn file sổ có sẵn…", severity: undefined, outlined: true },
        { key: "later", label: "Để sau" }]);
    if (k === "new") handle(await api("create_month_book", n.target));
    else if (k === "pick") handle(await api("choose_book"));
  }
}

async function showBlocked(b) {  // còn tên chưa rõ: chưa lưu được, đưa tới lớp cần xử lý
  await ask("Chưa lưu được", `<p class="text-danger fw-bold">Còn ${b.n} tên chưa rõ — chưa lưu được.</p>
    <ul>${b.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`, [{ key: "fix", label: "Xử lý ngay", severity: "danger" }],
  { icon: "pi-exclamation-triangle", danger: true });
  store.page = "dd";
  if (b.code) openClass(b.code);
  return false;
}

export async function doSave() {
  // hỏi một lần mọi điều cần biết trước khi lưu
  const ck = await api("save_check");
  if (ck.blocked) return showBlocked(ck.blocked);
  const items = [];
  if (ck.unreported?.length) items.push(`<li class="mb-2"><b>${ck.unreported.length} lớp chưa báo</b>: ${esc(ck.unreported.join(", "))}.
    Lưu bây giờ thì các lớp này coi như <b>không em nào vắng</b>` +
    `${ck.unreported_auto?.length ? ` (trừ các em nghỉ thứ 6 ở lớp ${esc(ck.unreported_auto.join(", "))})` : ""}.</li>`);
  if (ck.meal) items.push(`<li class="mb-2"><b class="text-danger">Suất ăn ${mealDiff(ck.meal)}</b> (tổng suất ${ck.meal.total}, hiện diện ${ck.meal.present})` +
    `${ck.meal.ask ? `: ${ck.meal.ask} em ăn ghép vắng chưa chọn nhóm` : ""}. Lưu bây giờ thì bảng suất ăn trong sổ cũng lệch.</li>`);
  if (ck.conflicts?.length) items.push(`<li class="mb-2"><b>Sĩ số khác nhau</b> giữa danh sách bán trú và sổ (có thể do thêm/cắt em chưa cập nhật):
    <ul>${ck.conflicts.map(l => `<li>${esc(l)}</li>`).join("")}</ul></li>`);
  let choice = null;
  if (items.length) {
    const btns = ck.conflicts?.length
      ? [{ key: "keep", label: "Lưu, giữ sĩ số như sổ" }, { key: "list", label: "Lưu, dùng sĩ số theo danh sách", severity: undefined }]
      : [{ key: "go", label: "Vẫn lưu" }];
    if (ck.meal) btns.push({ key: "see", label: "Xem trang Suất ăn" });
    btns.push({ key: "stay", label: "Hủy" });
    const k = await ask("Kiểm tra trước khi lưu", `<ul class="ps-3 mb-0">${items.join("")}</ul>`, btns, { icon: "pi-clipboard", width: "42rem" });
    if (k === "see") { store.page = "sa"; return false; }
    if (!["go", "keep", "list"].includes(k)) return false;
    if (k !== "go") choice = k;
  }
  let r = await api("save", choice);
  if (r.blocked) return showBlocked(r.blocked);
  if (r.conflicts) {  // hiếm: sĩ số đổi giữa lúc hỏi và lúc lưu
    choice = await ask("Sĩ số khác nhau", `<p>Ghi sĩ số nào vào sổ?</p><ul>${r.conflicts.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`,
      [{ key: "keep", label: "Giữ sĩ số như trong sổ" }, { key: "list", label: "Dùng sĩ số theo danh sách", severity: undefined }, { key: null, label: "Hủy" }]);
    if (!choice) return false;
    r = await api("save", choice);
  }
  while (r.locked) {
    const k = await ask("File đang mở", `<div class="pre-line">${esc(r.locked)}</div>`, [{ key: "retry", label: "Thử lại" }, { key: "cancel", label: "Hủy" }]);
    if (k !== "retry") return false;
    r = await api("save", choice);
  }
  if (r.error) { info("Lỗi khi lưu", r.error); return false; }
  store.S = r.state;
  toast(r.ok);
  return true;
}

// ------------------------------------------------------------------ chọn file (hộp chọn file của Windows)
export async function chooseBook() {
  const r = await api("choose_book");
  if (!r.cancel) { handle(r); await loadSettings(); }
}

export async function chooseList() {
  const r = await api("choose_list");
  if (!r.cancel) { handle(r); await loadSettings(); }
}

export async function openPath(kind) {
  const r = await api("open_path", kind);
  if (r.error) info("Chưa mở được", r.error);
}

// ------------------------------------------------------------------ mở / thoát app
// lần trước app tắt khi chưa lưu vào sổ (mất điện…): hỏi khôi phục từ sổ tạm
export async function askRestore(t) {
  const k = await ask("Khôi phục dữ liệu chưa lưu?",
    `Lần trước app bị tắt khi ngày <b>${esc(t.day)}</b> còn thay đổi chưa lưu vào sổ.<br>
     App đã tự lưu tạm lúc ${esc(t.at)} trong file <i>${esc(t.file)}</i>.<br><br>Khôi phục để làm tiếp?`,
    [{ key: "yes", label: "Khôi phục" }, { key: "no", label: "Bỏ bản lưu tạm", severity: "danger" }], { icon: "pi-history" });
  if (k === "yes" || k === "no") handle(await api("restore_temp", k === "yes"));
}

export async function askClose() {
  const c = await api("close_check");
  if (c.dirty) {
    const k = await ask("Chưa lưu", `Ngày ${esc(c.day)} có thay đổi chưa lưu vào sổ.`, SAVE_CHOICES("thoát"));
    if (k === "save") { if (!(await doSave())) return; } else if (k === "discard") await api("discard_temp"); else return;
  }
  await api("quit");
  conn.quit = conn.gone = true;
  window.close();  // trình duyệt chỉ cho đóng thẻ do chính trang mở; không đóng được thì hiện thông báo
}

if (IS_APP) {
  // còn thay đổi chưa lưu: trình duyệt hỏi trước khi đóng thẻ / tải lại
  window.addEventListener("beforeunload", e => {
    if (!conn.gone && store.S?.dirty) { e.preventDefault(); e.returnValue = ""; }
  });
}
