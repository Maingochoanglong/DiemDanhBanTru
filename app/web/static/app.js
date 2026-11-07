/* Điểm danh bán trú — điều khiển giao diện. Mọi xử lý sổ nằm ở Python (app/web/api.py). */
"use strict";

// ------------------------------------------------------------------ gọi Python
const IN_APP = !window.DEV_SERVER;  // máy chủ thử (devserver.py) đặt DEV_SERVER; trong app thì gọi qua pywebview
function apiReady() {
  if (!IN_APP) return Promise.resolve();
  if (window.pywebview && window.pywebview.api) return Promise.resolve();
  return new Promise(r => window.addEventListener("pywebviewready", r, { once: true }));
}
// Gọi lần lượt từng việc (bấm nhanh liên tiếp cũng không chạy chồng lên nhau)
let chain = Promise.resolve();
function api(name, ...args) {
  const run = async () => {
    if (IN_APP) return await window.pywebview.api[name](...args);
    const r = await fetch("/api/" + name, { method: "POST", body: JSON.stringify(args) });
    return await r.json();
  };
  const p = chain.then(run, run);
  chain = p.catch(() => {});
  return p;
}

// ------------------------------------------------------------------ tiện ích
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fold = s => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
function matches(q, text) {  // mỗi từ gõ vào là đầu của một chữ trong tên: "h long" khớp "Hải Long"
  const words = fold(text).split(/\s+/);
  return fold(q).split(/\s+/).filter(Boolean).every(t => words.some(w => w.startsWith(t)));
}

function toast(msg, kind = "success") {
  if (!msg) return;
  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${kind} border-0 show mb-2`;
  el.innerHTML = `<div class="d-flex"><div class="toast-body fs-6">${esc(msg)}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div>`;
  $("#toasts").appendChild(el);
  $(".btn-close", el).onclick = () => el.remove();
  setTimeout(() => el.remove(), kind === "danger" ? 12000 : 6000);
}

// Hộp hỏi: buttons = [{key, label, cls}] → trả về key (null nếu đóng)
function ask(title, html, buttons, opts = {}) {
  return new Promise(resolve => {
    $("#askTitle").innerHTML = (opts.icon ? `<i class="bi ${opts.icon} me-2"></i>` : "") + esc(title);
    $("#askTitle").className = "modal-title " + (opts.danger ? "text-danger" : "");
    $("#askBody").innerHTML = html;
    const bar = $("#askBtns");
    bar.innerHTML = "";
    let result = null;
    const md = bootstrap.Modal.getOrCreateInstance($("#mdAsk"));
    buttons.forEach((b, i) => {
      const btn = document.createElement("button");
      btn.className = "btn " + (b.cls || (i === 0 ? "btn-primary" : "btn-outline-secondary"));
      btn.textContent = b.label;
      btn.onclick = () => { result = b.key; md.hide(); };
      bar.appendChild(btn);
    });
    $("#mdAsk").addEventListener("hidden.bs.modal", () => resolve(result), { once: true });
    md.show();
  });
}
const info = (title, msg) => ask(title, `<div style="white-space:pre-line">${esc(msg)}</div>`, [{ key: "ok", label: "Đóng" }]);

// Hộp form chung: build(body) dựng nội dung; onOk() trả về true để đóng, hoặc chuỗi lỗi
function form(title, build, okLabel, onOk, opts = {}) {
  return new Promise(resolve => {
    $("#formTitle").textContent = title;
    $("#formErr").textContent = "";
    const body = $("#formBody");
    body.innerHTML = "";
    build(body);
    const md = bootstrap.Modal.getOrCreateInstance($("#mdForm"));
    const bar = $("#formBtns");
    bar.innerHTML = "";
    let done = false;
    const ok = document.createElement("button");
    ok.className = "btn btn-primary btn-lg px-4";
    ok.textContent = okLabel;
    ok.onclick = async () => {
      ok.disabled = true;
      const r = await onOk(body);
      ok.disabled = false;
      if (r === true) { done = true; md.hide(); } else if (r) $("#formErr").textContent = r;
    };
    const cancel = document.createElement("button");
    cancel.className = "btn btn-outline-secondary btn-lg ms-2";
    cancel.textContent = opts.cancel || "Hủy";
    cancel.onclick = () => md.hide();
    bar.append(ok, cancel);
    $("#mdForm .modal-dialog").className = "modal-dialog modal-dialog-centered modal-dialog-scrollable " + (opts.size || "modal-lg");
    $("#mdForm").addEventListener("hidden.bs.modal", () => resolve(done), { once: true });
    md.show();
  });
}

// ------------------------------------------------------------------ trạng thái chung
let S = null;          // trạng thái màn chính (từ api.state)
let curClass = null;   // lớp đang mở trong bảng chọn tên
let D = null;          // chi tiết lớp đang mở

function applyState(st) {
  if (!st) return;
  S = st;
  $("#dayInput").value = st.date_text;
  $("#dayPick").value = st.date;
  $("#weekday").textContent = st.weekday;
  $("#book").textContent = st.book ? `${st.book_stem} · sheet ${st.sheet}${st.exists ? "" : " (mới)"}` : "Chưa chọn sổ tháng này";
  $("#book").title = st.book;
  renderDiemDanh();
}

function handle(r) {  // kết quả chung từ Python: lỗi, thông báo, trạng thái
  if (!r) return r;
  if (r.state) applyState(r.state);
  if (r.flash) toast(r.flash);
  if (r.error) info("Có lỗi", r.error);
  return r;
}

// ------------------------------------------------------------------ màn Điểm danh
function renderDiemDanh() {
  const st = S;
  const sum = $("#summary");
  let h = "";
  if (st.hint) h += `<div class="alert alert-warning py-2 mb-0 todo" data-go="cd"><i class="bi bi-gear me-2"></i>${esc(st.hint)}</div>`;
  for (const t of st.todo) h += `<div class="alert alert-danger py-2 mb-0 todo" data-open="${esc(t.code || "")}"><i class="bi bi-exclamation-triangle-fill me-2"></i>${esc(t.text)}</div>`;
  if (st.info.length) h += `<div class="text-muted small px-1"><i class="bi bi-info-circle me-1"></i>${st.info.map(esc).join(" · ")}</div>`;
  sum.innerHTML = h;
  sum.style.display = h ? "" : "none";

  const t = st.totals;
  $("#totals").textContent = t ? `${st.weekday} ${st.date_text} · Đã báo ${t.rep}/${t.n} lớp · Sĩ số ${t.si} · Vắng ${t.vang} · Hiện diện ${t.hd}` : "";
  const m = st.meal;
  $("#mealBadge").innerHTML = m ? `<span class="badge fs-6 ${m.ok ? "text-bg-success" : "text-bg-danger"}" role="button" data-go="sa">
    <i class="bi ${m.ok ? "bi-check-circle" : "bi-exclamation-triangle"}"></i> Tổng suất ${m.total} ${m.ok ? "=" : "≠"} hiện diện ${m.present}</span>` : "";

  const rows = st.rows.map(r => {
    if (r.kind === "khoi") return `<tr class="khoi"><td>${esc(r.code)}</td><td></td><td class="num">${r.si}</td><td class="num">${r.vang}</td><td class="num">${r.hd}</td><td></td><td></td></tr>`;
    const note = [r.sched ? "[Lịch]" : "", r.warn, r.note].filter(Boolean).join(" · ");
    const ten = r.reported ? esc(r.ten) : `<span class="text-muted fst-italic">(chưa báo)</span>`;
    return `<tr class="cls st-${r.status}" data-code="${esc(r.code)}">
      <td><span class="dot ${r.status}"></span>${esc(r.code)}${r.ma ? ` <span class="text-muted fw-normal small">(${esc(r.ma)})</span>` : ""}</td>
      <td class="gv">${esc(r.gvcn)}</td><td class="num">${r.si}</td><td class="num fw-bold">${r.vang || 0}</td><td class="num">${r.hd}</td>
      <td class="ten">${ten}</td><td class="note"><div class="cut" title="${esc(note)}">${esc(note)}</div></td></tr>`;
  });
  if (t) rows.push(`<tr class="tong"><td>TỔNG CỘNG</td><td>đã báo ${t.rep}/${t.n} lớp</td><td class="num">${t.si}</td><td class="num">${t.vang}</td><td class="num">${t.hd}</td><td></td><td></td></tr>`);
  $("#soBody").innerHTML = rows.join("") || `<tr><td colspan="7" class="text-center text-muted py-5">Chưa có danh sách học sinh. Vào Cài đặt để nhập.</td></tr>`;

  const ss = $("#saveState");
  if (st.unresolved) { ss.className = "state err"; ss.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> Còn ${st.unresolved} tên chưa rõ — xử lý xong mới lưu được`; }
  else if (st.dirty) {
    ss.className = "state dirty";
    const tmp = st.temp_error ? ` — <span class="text-danger">${esc(st.temp_error)}</span>`
      : (st.temp_at ? ` (đã lưu tạm lúc ${esc(st.temp_at)})` : "");
    ss.innerHTML = `<i class="bi bi-pencil"></i> Có thay đổi chưa lưu vào sổ${tmp}`;
  }
  else { ss.className = "state"; ss.textContent = st.exists ? "Đã có trong sổ" : (st.book ? "Ngày này chưa có trong sổ" : ""); }
}

// ------------------------------------------------------------------ bảng chọn tên của 1 lớp
async function openClass(code) {
  if (!code) return;
  curClass = code;
  const d = await api("class_detail", code);
  if (d.error) return info("Có lỗi", d.error);
  D = d;
  $("#clsSearch").value = "";
  renderClass();
  bootstrap.Modal.getOrCreateInstance($("#mdClass")).show();
}

function renderClass() {
  const d = D;
  $("#clsTitle").textContent = `Lớp ${d.code}${d.ma ? " (" + d.ma + ")" : ""}`;
  $("#clsGv").textContent = d.gvcn ? `GVCN ${d.gvcn}` : "";
  $("#clsCounts").innerHTML = `<span class="badge text-bg-secondary fs-6">Sĩ số ${d.si}</span>
    <span class="badge text-bg-danger fs-6">Vắng ${d.vang}</span><span class="badge text-bg-success fs-6">Hiện diện ${d.hd}</span>`;
  let a = "";
  for (const w of d.warnings) a += `<div class="alert alert-danger py-2 mb-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>${esc(w)}</div>`;
  if (d.pending.length) {
    a += `<div class="alert alert-warning py-2 mb-2"><b>Tên trong sổ chưa khớp danh sách</b> — bấm vào tên để chọn em đúng:<div class="mt-2 d-flex gap-2 flex-wrap">` +
      d.pending.map(p => `<button class="btn btn-danger" data-pend="${p.idx}"><i class="bi bi-question-circle"></i> ${esc(p.query)}</button>`).join("") + `</div></div>`;
  }
  if (d.extra.length) a += `<div class="alert alert-secondary py-2 mb-2">Giữ nguyên chữ đã ghi: ${esc(d.extra.join(", "))} <button class="btn btn-sm btn-outline-secondary ms-2" id="clsClearExtra">Xóa các tên này</button></div>`;
  if (d.upcoming.length) a += `<div class="text-muted small mb-2"><i class="bi bi-calendar-event"></i> Sắp tới: ${esc(d.upcoming.join("; "))}</div>`;
  $("#clsAlerts").innerHTML = a;
  $("#clsNote").value = d.note;
  $("#clsNames").innerHTML = d.names.map(n => `
    <button class="nm ${n.absent ? "on" : ""}" data-sid="${esc(n.id)}" title="${esc(n.full)} · ${esc(n.dob)}" data-s="${esc(n.full + " " + n.name + " " + (n.alias || ""))}">
      <i class="bi ${n.absent ? "bi-x-circle-fill" : "bi-circle"} ck"></i><span>${esc(n.name)}</span>
      ${n.tags.length ? `<span class="tg">${esc(n.tags.join(", "))}</span>` : ""}</button>`).join("")
    || `<div class="text-muted">Lớp này chưa có em nào ăn bán trú trong danh sách.</div>`;
  filterNames();
}

function filterNames() {
  const q = $("#clsSearch").value;
  let n = 0;
  $$("#clsNames .nm").forEach(b => { const ok = matches(q, b.dataset.s); b.style.display = ok ? "" : "none"; n += ok; });
  const none = $("#clsNoMatch");
  none.style.display = q.trim() && !n ? "" : "none";
  none.innerHTML = `<i class="bi bi-search me-2"></i>Không có em nào trong lớp khớp “${esc(q.trim())}”.<br>
    <span class="fs-6">Gõ không cần dấu (vd. <i>gia huy</i>). Muốn chọn nhiều em: dán cả tin GV báo, tên cách nhau dấu phẩy.</span>`;
}

async function pasteNames(text) {
  const r = await api("paste_class", curClass, text);
  if (r.error) return info("Chưa đọc được", r.error);
  applyState(r.state);
  D = r.detail;
  $("#clsSearch").value = "";
  renderClass();
  const p = r.report, parts = [];
  if (p.full) parts.push(`Lớp ${curClass}: <b>đủ</b>.`);
  if (p.ok.length) parts.push(`Đã chọn vắng <b>${p.ok.length} em</b>: ${esc(p.ok.join(", "))}.`);
  if (p.unclear.length) parts.push(`Chưa rõ ${p.unclear.length} tên: <b>${esc(p.unclear.join(", "))}</b> — bấm nút đỏ để chọn em đúng.`);
  if (p.not_bt.length) parts.push(`Không ăn bán trú (không tính): ${esc(p.not_bt.join(", "))}.`);
  clsNote(parts.join(" ") || "Không có tên mới.", p.unclear.length ? "warning" : "success", "bi-clipboard-check");
}

function clsNote(html, kind = "success", icon = "bi-check-circle") {
  $$("#clsAlerts .cls-note").forEach(x => x.remove());
  const box = document.createElement("div");
  box.className = `alert alert-${kind} py-2 mb-2 fs-6 cls-note`;
  box.innerHTML = `<i class="bi ${icon} me-2"></i>${html}`;
  $("#clsAlerts").prepend(box);
}


async function toggleName(btn) {
  const sid = btn.dataset.sid;
  const on = !btn.classList.contains("on");
  const r = await api("set_absent", curClass, sid, on);
  applyState(r.state);
  D = r.detail;
  const q = $("#clsSearch").value;
  renderClass();
  $("#clsSearch").value = q;
  filterNames();
}

async function resolvePending(idx) {
  const p = D.pending.find(x => x.idx === idx);
  if (!p) return;
  let html = `<p>Lớp ${esc(D.code)}: tên <b>"${esc(p.query)}"</b> trong sổ chưa khớp danh sách bán trú.</p>`;
  if (p.other.length) html += `<p class="text-muted">Có em cùng tên ở lớp khác: ${esc(p.other.join("; "))}.</p>`;
  if (p.cands.length) {
    html += `<div class="list-group">` + p.cands.map((c, i) => `<label class="list-group-item list-group-item-action fs-6">
      <input class="form-check-input me-2" type="radio" name="cand" value="${esc(c.id)}" ${i === 0 ? "checked" : ""}>
      <b>${esc(c.name)}</b> — ${esc(c.full)} — sinh ${esc(c.dob)}</label>`).join("") + `</div>`;
  } else if (D.names.length) {
    // không có em nào tên gần giống: cho chọn trong cả lớp (tên gọi khác thì thêm vào cột "Tên gọi khác" của file danh sách)
    html += `<label class="form-label">Nếu đây là tên gọi khác của một em trong lớp, chọn em đó
      <span class="text-muted">(muốn app tự nhận ra lần sau: ghi tên này vào cột <b>Tên gọi khác</b> trong file Excel danh sách rồi nhập lại)</span>:</label>
      <select class="form-select form-select-lg" id="candSel"><option value="">— chọn em —</option>` +
      D.names.map(n => `<option value="${esc(n.id)}">${esc(n.full)}${n.name !== n.full ? " (" + esc(n.name) + ")" : ""}</option>`).join("") +
      `</select>`;
  }
  const btns = [{ key: "pick", label: "Chọn em này", cls: "btn-primary" },
    { key: "raw", label: "Giữ nguyên chữ đã ghi", cls: "btn-outline-primary" }, { key: "skip", label: "Bỏ qua tên này", cls: "btn-outline-secondary" }];
  let sid = null;
  const md = $("#mdAsk");
  const grab = () => {
    const c = $("input[name=cand]:checked", md), sel = $("#candSel", md);
    sid = c ? c.value : (sel && sel.value ? sel.value : null);
  };
  md.addEventListener("click", grab);
  md.addEventListener("change", grab);
  const key = await ask("Chọn học sinh", html, btns);
  md.removeEventListener("click", grab);
  md.removeEventListener("change", grab);
  if (!key) return;
  if (key === "pick" && !sid) { await info("Chưa chọn em", "Hãy chọn em đúng trong danh sách, hoặc bấm Giữ nguyên chữ đã ghi."); return resolvePending(idx); }
  const r = await api("resolve", D.code, idx, key, sid);
  applyState(r.state);
  D = r.detail;
  renderClass();
}

// ------------------------------------------------------------------ ngày, lưu, in
async function gotoDay(fn) {
  let r = await fn(false);
  if (r.ask_save) {
    const k = await ask("Chưa lưu", `Ngày ${esc(r.ask_save.day)} có thay đổi chưa lưu vào sổ.`,
      [{ key: "save", label: "Lưu rồi chuyển ngày" }, { key: "discard", label: "Không lưu", cls: "btn-outline-danger" }, { key: "stay", label: "Ở lại", cls: "btn-outline-secondary" }]);
    if (k === "save") { if (!(await doSave())) return; }
    else if (k !== "discard") { applyState(S); return; }
    r = await fn(true);
  }
  handle(r);
  if (r.need_month) {
    const n = r.need_month;
    const k = await ask("Sổ tháng mới", `Chưa có sổ điểm danh tháng ${n.month}/${n.year} trong thư mục<br><code>${esc(n.folder)}</code>.<br><br>
      Tạo sổ mới từ sheet cuối của sổ <b>${esc(n.prev)}</b>? (giữ nguyên mẫu, chữ ký, ghi chú)`,
      [{ key: "new", label: "Tạo sổ tháng mới" }, { key: "pick", label: "Chọn file sổ có sẵn…", cls: "btn-outline-primary" }, { key: "later", label: "Để sau", cls: "btn-outline-secondary" }]);
    if (k === "new") handle(await api("create_month_book", n.target));
    else if (k === "pick") handle(await api("choose_book"));
  }
}

async function doSave() {
  if (S && S.unreported && S.unreported.length) {  // lời nhắc trước đây nằm ở nút In
    const k = await ask("Còn lớp chưa báo", `<p>Còn <b>${S.unreported.length} lớp chưa báo</b>: ${esc(S.unreported.join(", "))}.</p>
      <p>Lưu bây giờ thì các lớp này được tính <b>đủ</b> (không em nào vắng).</p>`,
      [{ key: "go", label: "Vẫn lưu" }, { key: "stay", label: "Ở lại", cls: "btn-outline-secondary" }], { icon: "bi-exclamation-circle" });
    if (k !== "go") return false;
  }
  let r = await api("save");
  let choice = null;
  if (r.blocked) {
    await ask("Chưa lưu được", `<p class="text-danger fw-bold">Còn ${r.blocked.n} tên chưa rõ — chưa lưu được.</p>
      <ul>${r.blocked.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`, [{ key: "fix", label: "Xử lý ngay", cls: "btn-danger" }], { icon: "bi-exclamation-triangle-fill", danger: true });
    showPage("dd");
    if (r.blocked.code) openClass(r.blocked.code);
    return false;
  }
  if (r.conflicts) {
    choice = await ask("Sĩ số khác nhau", `<p>Các lớp sau có sĩ số theo danh sách bán trú khác sĩ số đang ghi trong sổ (có thể do thêm/cắt em chưa cập nhật). Ghi sĩ số nào vào sổ?</p>
      <ul>${r.conflicts.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`,
      [{ key: "keep", label: "Giữ sĩ số như trong sổ" }, { key: "list", label: "Dùng sĩ số theo danh sách", cls: "btn-outline-primary" }, { key: null, label: "Hủy", cls: "btn-outline-secondary" }]);
    if (!choice) return false;
    r = await api("save", choice);
  }
  while (r.locked) {
    const k = await ask("File đang mở", `<div style="white-space:pre-line">${esc(r.locked)}</div>`, [{ key: "retry", label: "Thử lại" }, { key: "cancel", label: "Hủy", cls: "btn-outline-secondary" }]);
    if (k !== "retry") return false;
    r = await api("save", choice);
  }
  if (r.error) { info("Lỗi khi lưu", r.error); return false; }
  applyState(r.state);
  toast(r.ok);
  return true;
}

// ------------------------------------------------------------------ Suất ăn
async function renderMeals() {
  const m = await api("meals");
  if (m.empty) {
    $("#mealTotal").textContent = "Sổ chưa có bảng suất ăn";
    $("#mealBody").innerHTML = "";
    $("#mealInfo").textContent = "Sheet mẫu của sổ không có bảng suất ăn bên dưới bảng điểm danh.";
    return;
  }
  $("#mealTotal").innerHTML = `<span class="${m.ok ? "text-success" : "text-danger"}"><i class="bi ${m.ok ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill"}"></i>
    Tổng suất ${m.total} ${m.ok ? "=" : "≠"} hiện diện ${m.present}</span>`;
  const rows = m.lines.map((l, i) => `<tr class="${l.m ? "table-warning" : ""}" data-meal="${i}" role="button">
    <td class="fw-semibold">${l.manual ? `<i class="bi bi-pencil-square text-primary"></i> ` : ""}${esc(l.label)}</td>
    <td>${esc(l.gom)}${l.absent.length ? ` <span class="text-danger small">(vắng: ${esc(l.absent.join(", "))})</span>` : ""}</td>
    <td class="text-center fs-5 fw-bold">${l.meals}</td></tr>`);
  if (m.self) rows.push(`<tr class="text-muted"><td>${esc(m.self.label)}</td><td>${esc(m.self.gom)}</td><td class="text-center fs-5">${m.self.meals}</td></tr>`);
  $("#mealBody").innerHTML = rows.join("");
  $("#mealInfo").innerHTML = m.warnings.length ? `<span class="text-danger">${m.warnings.map(esc).join("<br>")}</span>`
    : `<span class="text-muted">Nhóm có hình bút chì: bấm vào để nhập số em ghép vắng (lớp ghép chưa gán đủ danh sách).</span>`;
  $$("#mealBody tr[data-meal]").forEach(tr => tr.onclick = async () => {
    const l = m.lines[+tr.dataset.meal];
    if (!l.manual) return;
    let val = l.manual_m;
    const ok = await form(`Vắng ghép nhóm ${l.code}`, b => {
      b.innerHTML = `<label class="form-label">Số em ghép vắng ở nhóm ${esc(l.code)}:</label>
        <input type="number" min="0" max="99" class="form-control form-control-lg" id="mval" value="${val}">`;
      setTimeout(() => $("#mval").select(), 300);
    }, "Lưu", async () => { val = parseInt($("#mval").value || "0", 10); return isNaN(val) || val < 0 ? "Nhập số từ 0 trở lên." : true; }, { size: "" });
    if (!ok) return;
    const r = await api("set_manual_m", l.code, val);
    applyState(r.state);
    renderMeals();
  });
}

// ------------------------------------------------------------------ Học sinh
let HS = null;
async function renderStudents() {
  const sel = $("#hsClass");
  const cur = sel.value;
  HS = await api("students", $("#hsQ").value, cur, $("#hsBt").checked);
  if (sel.options.length !== HS.classes.length + 1) {
    sel.innerHTML = `<option value="">Tất cả lớp</option>` + HS.classes.map(c => `<option>${esc(c)}</option>`).join("");
    sel.value = cur;
  }
  $("#hsCount").textContent = `${HS.rows.length} em`;
  $("#hsBody").innerHTML = HS.rows.map(s => `<tr class="${s.now ? "" : "text-muted"}">
    <td>${esc(s.lop)}</td><td class="fw-semibold">${esc(s.ten)}</td><td>${esc(s.ns)}</td><td class="text-center">${s.bt ? `<i class="bi bi-check-lg text-success"></i>` : ""}</td>
    <td>${esc(s.ghiso)}</td><td>${esc(s.ghep)}</td><td>${esc(s.db)}</td><td>${esc(s.gc)}</td></tr>`).join("");
}

// ------------------------------------------------------------------ Lịch thêm / cắt
async function renderLich() {
  const g = await api("schedules");
  const groups = [["soon", "Sắp áp dụng", "table-warning"], ["weekly", "Hàng tuần – cắt thứ 6", ""], ["done", "Đã áp dụng (30 ngày qua)", "text-muted"]];
  $("#lichBody").innerHTML = groups.map(([k, title, cls]) => `<tr class="table-light"><td colspan="5" class="fw-bold">${title} (${g[k].length})</td></tr>` +
    g[k].map(it => `<tr class="${cls}"><td><input class="form-check-input" type="checkbox" value="${esc(it.key)}"></td>
      <td>${esc(it.ngay)}</td><td>${esc(it.lop)}</td><td>${esc(it.hs)}</td><td>${esc(it.viec)}</td></tr>`).join("")).join("");
}

const KIND = { cat: "Cắt bán trú", them: "Thêm bán trú", thu6: "Cắt thứ 6 hàng tuần" };
async function scheduleDialog(kind, code, ids = []) {
  code = code || curClass || (S && S.rows.find(r => r.kind === "class") || {}).code || "";
  const preset = new Set(ids);
  let opt = await api("schedule_options", kind, code, "");
  const ok = await form("Lên lịch thêm / cắt bán trú", b => {
    b.innerHTML = `
      <div class="btn-group mb-3" role="group">${Object.entries(KIND).map(([k, l]) => `
        <input type="radio" class="btn-check" name="skind" id="sk_${k}" value="${k}" ${k === kind ? "checked" : ""}><label class="btn btn-outline-primary" for="sk_${k}">${l}</label>`).join("")}</div>
      <div class="d-flex gap-2 mb-2"><select class="form-select" id="scode" style="width:120px">${opt.classes.map(c => `<option ${c === code ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
        <input class="form-control" id="sq" placeholder="Tìm tên…"></div>
      <div class="text-muted small mb-1" id="shint"></div>
      <div class="list-group list-pick" id="slist"></div>
      <div class="row g-2 mt-1" id="snew" style="display:none"><div class="col-8"><input class="form-control" id="sname" placeholder="Họ tên em mới"></div>
        <div class="col-4"><input class="form-control" id="sdob" placeholder="Ngày sinh"></div></div>
      <div class="mt-3" id="sdate"><label class="form-label mb-1">Áp dụng từ ngày:</label>
        <div class="d-flex gap-2 flex-wrap"><input class="form-control" id="sstart" style="width:150px" value="${esc(opt.next)}">
        <button class="btn btn-outline-secondary btn-sm" data-d="${esc(opt.next)}">Ngày học kế tiếp (${esc(opt.next.slice(0, 5))})</button>
        <button class="btn btn-outline-secondary btn-sm" data-d="${esc(opt.month)}">Đầu tháng sau (${esc(opt.month.slice(0, 5))})</button>
        <button class="btn btn-outline-secondary btn-sm" data-d="${esc(opt.today)}">Hôm nay (${esc(opt.today.slice(0, 5))})</button></div></div>
      <div class="form-check mt-3"><input class="form-check-input" type="checkbox" id="snote" checked><label class="form-check-label" for="snote">Ghi chú vào cột H của lớp (như "Tháng 11 cắt bán trú …")</label></div>`;
    const hints = { cat: "Tích các em thôi ăn bán trú.", them: "Tích em trong lớp chưa ăn bán trú, hoặc dòng cuối để thêm em mới.", thu6: "Tích các em nghỉ ăn thứ 6 hàng tuần." };
    const fill = async () => {
      const k = $("input[name=skind]:checked", b).value;
      opt = await api("schedule_options", k, $("#scode", b).value, $("#sq", b).value);
      $("#shint", b).textContent = hints[k];
      $("#sdate", b).style.display = k === "thu6" ? "none" : "";
      $("#slist", b).innerHTML = opt.students.map(s => `<label class="list-group-item"><input class="form-check-input me-2" type="checkbox" value="${esc(s.id)}" ${preset.has(s.id) ? "checked" : ""}>
        ${esc(s.ten)} <span class="text-muted">— sinh ${esc(s.ns)}${k === "them" && !s.bt ? " (chưa ăn BT)" : ""}</span></label>`).join("")
        + (k === "them" ? `<label class="list-group-item"><input class="form-check-input me-2" type="checkbox" value="__new" id="snewchk"> <b>+ Học sinh mới (chưa có trong danh sách)…</b></label>` : "")
        || `<div class="list-group-item text-muted">Không có em nào phù hợp.</div>`;
      const nc = $("#snewchk", b);
      $("#snew", b).style.display = nc && nc.checked ? "" : "none";
      if (nc) nc.onchange = () => { $("#snew", b).style.display = nc.checked ? "" : "none"; };
    };
    $$("input[name=skind]", b).forEach(r => r.onchange = fill);
    $("#scode", b).onchange = fill;
    $("#sq", b).oninput = fill;
    $$("[data-d]", b).forEach(x => x.onclick = () => { $("#sstart", b).value = x.dataset.d; });
    fill();
  }, "Lưu lịch", async b => {
    const k = $("input[name=skind]:checked", b).value;
    const chosen = $$("#slist input:checked", b).map(x => x.value);
    const isNew = chosen.includes("__new");
    const r = await api("add_schedule", k, $("#scode", b).value, chosen.filter(x => x !== "__new"), $("#sstart", b).value,
      isNew ? $("#sname", b).value : "", isNew ? $("#sdob", b).value : "", $("#snote", b).checked);
    if (r.error) return r.error;
    applyState(r.state);
    toast(r.ok);
    return true;
  });
  if (ok) {
    if ($("#page-lich").classList.contains("show")) renderLich();
    if (curClass && $("#mdClass").classList.contains("show")) { D = await api("class_detail", curClass); renderClass(); }
  }
}

// ------------------------------------------------------------------ Ghép lớp
async function renderGhep() {
  const g = await api("ghep");
  if (!g.classes.length) {
    $("#ghepBody").innerHTML = `<div class="card"><div class="card-body text-muted">Sổ đang mở không có lớp ghép (bảng suất ăn không có hàng "… ghép" nhận học sinh lẻ).</div></div>`;
    return;
  }
  $("#ghepBody").innerHTML = g.classes.map(c => `
    <div class="card shadow-sm mb-3" data-ghep="${esc(c.code)}"><div class="card-header bg-white d-flex align-items-center gap-2">
      <b class="fs-6">Lớp ${esc(c.code)}${c.ma ? " (" + esc(c.ma) + ")" : ""} — ${c.n} em ăn bán trú</b>
      <span class="badge ${c.total === c.n ? "text-bg-success" : "text-bg-danger"}">Tổng ghép ${c.total}/${c.n}</span>
      <div class="ms-auto d-flex gap-2 flex-wrap">${c.groups.map(gr => `<button class="btn btn-sm btn-outline-primary" data-g="${esc(gr.g)}">→ Ăn ở ${esc(gr.g)} (${gr.n} em${gr.book != null ? ", sổ ghi " + gr.book : ""})</button>`).join("")}
        <button class="btn btn-sm btn-outline-secondary" data-g="">Bỏ gán</button>
        <button class="btn btn-sm btn-outline-dark" data-paste="1">Dán danh sách ghép…</button></div></div>
      <div class="card-body p-0"><table class="table table-sm table-hover mb-0"><thead><tr><th style="width:40px"></th><th>Tên ghi sổ</th><th>Họ tên</th><th>Ngày sinh</th><th>Ăn ghép tại</th></tr></thead><tbody>
      ${c.students.map(s => `<tr class="${s.ok ? "" : "table-danger"}"><td><input class="form-check-input" type="checkbox" value="${esc(s.id)}"></td>
        <td>${esc(s.name)}</td><td>${esc(s.full)}</td><td>${esc(s.dob)}</td><td>${esc(s.g || "chưa gán")}</td></tr>`).join("")}
      </tbody></table></div></div>`).join("");
  $("#ghepSave").classList.toggle("btn-warning", !!g.data_dirty);
}

// ------------------------------------------------------------------ Cài đặt
async function renderSettings() {
  const s = await api("settings");
  $("#ver").textContent = "Phiên bản " + s.version;
  const row = (k, label) => `<div class="d-flex align-items-center gap-2 mb-2"><span style="width:260px" class="text-muted">${label}</span>
    <input class="form-control" readonly value="${esc(s[k])}"><button class="btn btn-outline-secondary" data-open="${k}">Mở</button></div>`;
  $("#cdFiles").innerHTML = row("so_file", "Sổ điểm danh tháng đang dùng") + row("cdhs_file", "File danh sách học sinh đã nhập") + row("data", "File dữ liệu của app");
}

async function importList(path) {
  const p = await api("import_list", path || null);
  if (p.cancel) return;
  if (p.error) return info("Không đọc được file", p.error);
  let sel = p.changes.filter(c => c.apply).map(c => c.i);
  const ok = await form("Nhập danh sách học sinh", b => {
    b.innerHTML = `<p class="fs-6">Đọc được <b>${p.n}</b> học sinh trong <b>${esc(p.file)}</b>, <b>${p.n_bt}</b> em ăn bán trú.</p>`
      + (p.mismatch.length ? `<div class="alert alert-warning py-2">Lưu ý: màu chữ khác cột "Phân loại HS" ở: ${esc(p.mismatch.join("; "))}.</div>` : "")
      + (p.changes.length ? `<p class="text-muted mb-1">Bỏ tích dòng nào không muốn áp dụng:</p><div class="list-group list-pick">`
        + p.changes.map(c => `<label class="list-group-item ${c.removed ? "list-group-item-danger" : ""}"><input class="form-check-input me-2" type="checkbox" value="${c.i}" ${c.apply ? "checked" : ""}>${esc(c.text)}</label>`).join("") + `</div>`
        : `<div class="alert alert-success">Không có thay đổi nào so với danh sách hiện tại.</div>`);
  }, "Áp dụng", async b => { sel = $$(".list-pick input:checked", b).map(x => +x.value); return true; });
  if (ok) handle(await api("apply_import", sel));
}

async function noteSuggestions() {
  const p = await api("note_suggestions");
  if (p.error) return info("Không đọc được sổ", p.error);
  if (!p.items.length) return info("Ghi chú trong sổ", "Không có gợi ý mới nào từ ghi chú trong sổ.");
  let sel = [];
  const ok = await form("Gợi ý từ ghi chú trong sổ", b => {
    b.innerHTML = `<p class="text-muted">App đọc ghi chú cột H của sổ tháng rồi gợi ý cập nhật danh sách để sĩ số tự khớp và thứ 6 tự tính vắng. Bỏ tích dòng nào không đúng.</p>
      <div class="list-group list-pick">${p.items.map(g => `<label class="list-group-item"><input class="form-check-input me-2" type="checkbox" value="${g.i}" ${g.apply ? "checked" : ""}>${esc(g.text)}</label>`).join("")}</div>`;
  }, "Áp dụng", async b => { sel = $$(".list-pick input:checked", b).map(x => +x.value); return true; }, { size: "modal-xl" });
  if (ok) handle(await api("apply_notes", sel));
}

// ------------------------------------------------------------------ chuyển trang
function showPage(p) {
  $$("#nav .nav-link").forEach(a => a.classList.toggle("active", a.dataset.page === p));
  $$(".page").forEach(s => s.classList.toggle("show", s.id === "page-" + p));
  if (p === "sa") renderMeals();
  if (p === "hs") renderStudents();
  if (p === "lich") renderLich();
  if (p === "ghep") renderGhep();
  if (p === "cd") renderSettings();
}

// ------------------------------------------------------------------ gắn sự kiện
function wire() {
  $("#nav").onclick = e => { const a = e.target.closest("[data-page]"); if (a) { e.preventDefault(); showPage(a.dataset.page); } };
  document.body.addEventListener("click", e => {
    const go = e.target.closest("[data-go]");
    if (go) { showPage(go.dataset.go); return; }
    const op = e.target.closest("[data-open]");
    if (op && op.closest("#summary")) { openClass(op.dataset.open); return; }
    if (op && op.dataset.open) { api("open_path", op.dataset.open).then(r => r.error && info("Chưa mở được", r.error)); }
  });
  $("#soBody").onclick = e => { const tr = e.target.closest("tr.cls"); if (tr) openClass(tr.dataset.code); };
  $("#dayPrev").onclick = () => gotoDay(f => api("step_day", -1, f));
  $("#dayNext").onclick = () => gotoDay(f => api("step_day", 1, f));
  $("#dayToday").onclick = () => { const d = new Date(); const iso = new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10); gotoDay(f => api("open_day", iso, f)); };
  const typed = () => { const v = $("#dayInput").value.trim(); if (v && S && v !== S.date_text) gotoDay(f => api("open_day", v, f)); };
  $("#dayInput").onkeydown = e => { if (e.key === "Enter") typed(); };
  $("#dayInput").onchange = typed;
  $("#dayPickBtn").onclick = () => { const p = $("#dayPick"); try { p.showPicker(); } catch { p.focus(); p.click(); } };
  $("#dayPick").onchange = e => { if (e.target.value && S && e.target.value !== S.date) gotoDay(f => api("open_day", e.target.value, f)); };
  $("#openBook").onclick = async () => { const r = await api("open_book"); if (r.error) info("Chưa có sổ", r.error); };
  $("#btnSave").onclick = doSave;
  $("#btnUndo").onclick = async () => { handle(await api("undo")); };
  $("#saveState").onclick = async () => { if (S && S.unresolved) { const t = S.todo.find(x => x.code); if (t) openClass(t.code); } };
  document.addEventListener("keydown", e => {
    if (e.ctrlKey && e.key.toLowerCase() === "s") { e.preventDefault(); doSave(); }
    if (e.ctrlKey && e.key.toLowerCase() === "z" && !e.target.matches("input,textarea")) { e.preventDefault(); $("#btnUndo").click(); }
  });
  // Esc khi có hộp nhỏ mở trên cửa sổ lớp: chỉ đóng hộp nhỏ, giữ cửa sổ lớp
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    const open = [...document.querySelectorAll(".modal.show")];
    if (open.length < 2) return;
    e.preventDefault(); e.stopPropagation();
    bootstrap.Modal.getInstance(open[open.length - 1])?.hide();
  }, true);

  // bảng chọn tên
  $("#clsNames").onclick = e => { const b = e.target.closest(".nm"); if (b) toggleName(b); };
  $("#clsNames").oncontextmenu = async e => {  // chuột phải vào tên: cắt bán trú / thứ 6
    const b = e.target.closest(".nm");
    if (!b) return;
    e.preventDefault();
    const n = D.names.find(x => x.id === b.dataset.sid);
    const k = await ask(n.full, `Lớp ${esc(D.code)} · sinh ${esc(n.dob)}`, [{ key: "cat", label: "Cắt bán trú từ ngày…", cls: "btn-outline-danger" },
      n.friday ? { key: "unfri", label: "Bỏ cắt thứ 6", cls: "btn-outline-secondary" } : { key: "thu6", label: "Cắt thứ 6 hàng tuần…", cls: "btn-outline-secondary" },
      { key: null, label: "Đóng", cls: "btn-light" }]);
    if (k === "unfri") { handle(await api("undo_friday", n.id)); D = await api("class_detail", D.code); renderClass(); }
    else if (k) scheduleDialog(k, D.code, [n.id]);
  };
  $("#clsSearch").oninput = filterNames;  // ô tìm chỉ để lọc tên; chọn vắng = bấm vào ô tên
  // dán tin GV báo / nhiều tên cách nhau dấu phẩy: chọn vắng luôn các em đó
  $("#clsSearch").addEventListener("paste", e => {
    const text = (e.clipboardData || window.clipboardData).getData("text");
    if (isList(text)) { e.preventDefault(); pasteNames(text); }
  });
  $("#clsSearch").onkeydown = e => { if (e.key === "Enter") e.preventDefault(); };  // Enter không chọn ai
  $("#clsFull").onclick = async () => { const r = await api("mark_full", curClass); applyState(r.state); D = r.detail; renderClass(); };
  $("#clsNote").onchange = async e => { const r = await api("set_note", curClass, e.target.value); applyState(r.state); };
  $("#clsAlerts").onclick = async e => {
    const p = e.target.closest("[data-pend]");
    if (p) return resolvePending(+p.dataset.pend);
    if (e.target.closest("#clsClearExtra")) { const r = await api("clear_extra", curClass); applyState(r.state); D = r.detail; renderClass(); }
  };
  $$("[data-clsched]").forEach(a => a.onclick = e => { e.preventDefault(); scheduleDialog(a.dataset.clsched, curClass); });
  $("#mdClass").addEventListener("shown.bs.modal", () => $("#clsSearch").focus());

  // Học sinh
  $("#hsClass").onchange = renderStudents;
  $("#hsQ").oninput = renderStudents;
  $("#hsBt").onchange = renderStudents;

  // Lịch
  $$("[data-sched]").forEach(b => b.onclick = () => scheduleDialog(b.dataset.sched));
  $("#lichCancel").onclick = async () => {
    const keys = $$("#lichBody input:checked").map(x => x.value);
    if (!keys.length) return info("Hủy lịch", "Hãy tích các dòng lịch cần hủy.");
    const k = await ask("Hủy lịch", `Hủy ${keys.length} lịch đã tích?`, [{ key: "keep", label: "Giữ lại" }, { key: "cancel", label: "Hủy các lịch này", cls: "btn-danger" }]);
    if (k === "cancel") { const r = handle(await api("cancel_schedules", keys)); if (r.ok) toast(r.ok); renderLich(); }
  };

  // Ghép lớp
  $("#ghepBody").onclick = async e => {
    const card = e.target.closest("[data-ghep]");
    if (!card) return;
    const code = card.dataset.ghep;
    const gb = e.target.closest("[data-g]");
    if (gb) {
      const ids = $$("tbody input:checked", card).map(x => x.value);
      if (!ids.length) return info("Ghép lớp", "Hãy tích một hoặc nhiều em trong danh sách trước.");
      const r = await api("assign_ghep", ids, gb.dataset.g);
      applyState(r.state);
      renderGhep();
    }
    if (e.target.closest("[data-paste]")) {
      let text = "";
      const ok = await form(`Dán danh sách ghép lớp ${code}`, b => {
        b.innerHTML = `<p class="text-muted">Mỗi dòng ghi mã nhóm rồi tên các em, ví dụ:<br><code>1.1: Bảo Ngọc, Gia Hân, Minh Khôi</code><br><code>1.2: Đức Anh, Thảo Vy</code></p>
          <textarea class="form-control" rows="10" id="gtext"></textarea>`;
      }, "Đồng ý", async b => { text = $("#gtext", b).value; return true; });
      if (!ok || !text.trim()) return;
      const r = await api("assign_ghep_text", code, text);
      applyState(r.state);
      renderGhep();
      info("Ghép lớp", `Đã gán ${r.n} em.` + (r.problems.length ? "\n\nCần xem lại:\n" + r.problems.join("\n") : ""));
    }
  };
  $("#ghepSave").onclick = async () => { const r = handle(await api("save_data")); if (r.ok) { toast("Đã lưu danh sách ghép."); renderGhep(); } };

  // Cài đặt
  $("#cdBook").onclick = async () => { const r = await api("choose_book"); if (!r.cancel) { handle(r); renderSettings(); } };
  $("#cdImport").onclick = () => importList();
  $("#cdNotes").onclick = noteSuggestions;
}

// Gọi từ Python khi bấm nút đóng cửa sổ mà còn thay đổi chưa lưu
// lần trước app tắt khi chưa lưu vào sổ (mất điện…): hỏi khôi phục từ sổ tạm
async function askRestore(t) {
  const k = await ask("Khôi phục dữ liệu chưa lưu?",
    `Lần trước app bị tắt khi ngày <b>${esc(t.day)}</b> còn thay đổi chưa lưu vào sổ.<br>
     App đã tự lưu tạm lúc ${esc(t.at)} trong file <i>${esc(t.file)}</i>.<br><br>Khôi phục để làm tiếp?`,
    [{ key: "yes", label: "Khôi phục" }, { key: "no", label: "Bỏ bản lưu tạm", cls: "btn-outline-danger" }],
    { icon: "bi-life-preserver" });
  if (k === "yes" || k === "no") handle(await api("restore_temp", k === "yes"));
}

async function askClose() {
  const c = await api("close_check");
  if (c.dirty) {
    const k = await ask("Chưa lưu", `Ngày ${esc(c.day)} có thay đổi chưa lưu vào sổ.`,
      [{ key: "save", label: "Lưu rồi thoát" }, { key: "discard", label: "Không lưu", cls: "btn-outline-danger" }, { key: "stay", label: "Ở lại", cls: "btn-outline-secondary" }]);
    if (k === "save") { if (!(await doSave())) return; } else if (k === "discard") await api("discard_temp"); else return;
  }
  if (c.data_dirty) {
    const k = await ask("Chưa lưu", "Danh sách học sinh / ghép lớp có thay đổi chưa lưu.",
      [{ key: "save", label: "Lưu rồi thoát" }, { key: "discard", label: "Không lưu", cls: "btn-outline-danger" }, { key: "stay", label: "Ở lại", cls: "btn-outline-secondary" }]);
    if (k === "save") { const r = await api("save_data"); if (r.error) return info("Lỗi khi lưu", r.error); } else if (k !== "discard") return;
  }
  api("quit");
}

document.addEventListener("DOMContentLoaded", async () => {
  wire();
  await apiReady();
  const r = handle(await api("boot"));
  renderSettings();
  if (r && r.restore) await askRestore(r.restore);
  if (r && r.list_changed) {  // file Excel danh sách đã được sửa sau lần nhập trước
    const k = await ask("File danh sách đã sửa", `File <b>${esc(r.list_changed.file)}</b> đã được sửa sau lần nhập trước.<br>Nhập lại để cập nhật danh sách trong app?`,
      [{ key: "go", label: "Nhập lại" }, { key: "later", label: "Để sau", cls: "btn-outline-secondary" }], { icon: "bi-file-earmark-excel" });
    if (k === "go") importList(r.list_changed.path);
  }
});
