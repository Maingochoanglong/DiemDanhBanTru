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
const wordsOf = s => String(s || "").replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
// chữ có dấu, không phụ thuộc vị trí dấu thanh: "Thuý" và "Thúy" là một, "Nguyên" khác "Nguyễn"
const TONE = /[\u0300\u0301\u0303\u0309\u0323]/g;
const toneKey = w => { const d = w.normalize("NFD").toLowerCase(); return d.replace(TONE, "").normalize("NFC") + (d.match(TONE) || []).join(""); };
// mức khớp của tên gõ với một em: 3 = đủ chữ, đúng dấu · 2 = đủ chữ (bỏ dấu) · 1 = chỉ khớp đầu chữ · 0 = không khớp
function matchLevel(q, text) {
  const qw = wordsOf(q), tw = wordsOf(text), qf = qw.map(fold), tf = tw.map(fold);
  if (!qf.length || !qf.every(t => tf.some(w => w.startsWith(t)))) return 0;
  if (!qf.every(t => tf.includes(t))) return 1;
  if (!/[^\x00-\x7f]/.test(q)) return 2;  // gõ không dấu
  const tk = tw.map(toneKey);
  return qw.map(toneKey).every(t => tk.includes(t)) ? 3 : 2;
}
// tên gõ trùng phần cuối tên em (GV hay gọi tên cuối): "Thư" -> Minh Thư đứng trước Thư Kỳ
function tailMatch(q, b) {
  const qf = wordsOf(q).map(fold);
  return [b.dataset.full, b.dataset.name].some(s => {
    const w = wordsOf(s).map(fold);
    return w.length >= qf.length && qf.every((t, i) => w[w.length - qf.length + i] === t);
  });
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
let ddFilter = "all";  // lọc bảng điểm danh: all | unrep (chưa báo) | absent (có vắng)
function renderDiemDanh() {
  const st = S;
  const sum = $("#summary");
  let h = "";
  if (st.hint) h += `<div class="alert alert-warning py-2 mb-0 todo" data-go="cd"><i class="bi bi-gear me-2"></i>${esc(st.hint)}</div>`;
  for (const t of st.todo) h += `<div class="alert alert-danger py-2 mb-0 todo" data-open="${esc(t.code || "")}"><i class="bi bi-exclamation-triangle-fill me-2"></i>${esc(t.text)}</div>`;
  if (st.info.length) h += `<div class="text-muted small px-1"><i class="bi bi-info-circle me-1"></i>${st.info.map(esc).join(" · ")}</div>`;

  sum.innerHTML = h;
  sum.style.display = h ? "" : "none";
  const un = st.unreported || [];  // lớp chưa báo: bấm mã lớp để mở lớp đó
  const show = un.slice(0, 12);
  $("#unrep").innerHTML = !un.length ? `<span class="text-success small"><i class="bi bi-check-circle me-1"></i>Các lớp đều đã báo</span>`
    : `<span class="text-muted me-1"><i class="bi bi-hourglass-split me-1"></i>Chưa báo (${un.length}):</span>` +
      show.map(c => `<button class="btn btn-sm btn-outline-secondary py-0" data-open="${esc(c)}">${esc(c)}</button>`).join("") +
      (un.length > show.length ? `<span class="text-muted small ms-1">và ${un.length - show.length} lớp khác</span>` : "");

  const t = st.totals;
  $("#totals").textContent = t ? `Sĩ số ${t.si} · Vắng ${t.vang} · Hiện diện ${t.hd}` : "";  // ngày ở thanh trên, lớp chưa báo ở dòng "Chưa báo"
  const m = st.meal;
  $("#mealBadge").innerHTML = m ? `<span class="badge fs-6 ${m.ok ? "text-bg-success" : "text-bg-danger"}" role="button" data-go="sa">
    <i class="bi ${m.ok ? "bi-check-circle" : "bi-exclamation-triangle"}"></i> ${m.ok ? `Tổng suất ${m.total} = hiện diện ${m.present}`
      : `Suất ăn ${mealDiff(m)}${m.ask ? ` · ${m.ask} em ghép chưa rõ nhóm` : ""}`}</span>` : "";

  // lọc bảng: tất cả / chưa báo / có vắng
  const cls = st.rows.filter(r => r.kind === "class");
  const counts = { all: cls.length, unrep: cls.filter(r => !r.reported).length, absent: cls.filter(r => r.vang > 0).length };
  $("#ddFilter").innerHTML = [["all", "Tất cả"], ["unrep", "Chưa báo"], ["absent", "Có vắng"]].map(([k, label]) =>
    `<button type="button" class="btn ${ddFilter === k ? "btn-secondary" : "btn-outline-secondary"}" data-filter="${k}">${label} (${counts[k]})</button>`).join("");
  const keep = r => ddFilter === "all" || (ddFilter === "unrep" ? !r.reported : r.vang > 0);
  const rows = st.rows.filter(r => r.kind === "class" ? keep(r) : ddFilter === "all").map(r => {
    if (r.kind === "khoi") return `<tr class="khoi"><td>${esc(r.code)}</td><td></td><td class="num">${r.si}</td><td class="num">${r.vang}</td><td class="num">${r.hd}</td><td></td><td></td></tr>`;
    const note = [r.sched ? "[Lịch]" : "", r.warn, r.not_bt ? `Không ăn BT: ${r.not_bt}` : "", r.note].filter(Boolean).join(" · ");
    const tip = (r.sched ? "[Lịch] = sĩ số đổi theo lịch thêm/cắt. " : "") + [r.warn, r.note].filter(Boolean).join(" · ");
    const ten = r.reported ? esc(r.ten) : `<span class="text-muted fst-italic">(chưa báo)</span>` +
      (r.auto ? ` <span class="text-muted small">· nghỉ T6: ${esc(r.auto)}</span>` : "");
    return `<tr class="cls st-${r.status}" data-code="${esc(r.code)}">
      <td><span class="dot ${r.status}"></span>${esc(r.code)}${r.ma ? ` <span class="text-muted fw-normal small">(${esc(r.ma)})</span>` : ""}</td>
      <td class="gv"><div class="cut" title="${esc(r.gvcn)}">${esc(r.gvcn)}</div></td><td class="num">${r.si}</td><td class="num fw-bold">${r.vang || 0}</td><td class="num">${r.hd}</td>
      <td class="ten">${ten}</td><td class="note"><div class="cut" title="${esc(tip)}">${esc(note)}</div></td></tr>`;
  });
  if (t) rows.push(`<tr class="tong"><td>TỔNG CỘNG</td><td></td><td class="num">${t.si}</td><td class="num">${t.vang}</td><td class="num">${t.hd}</td><td></td><td></td></tr>`);
  $("#soBody").innerHTML = rows.join("") || `<tr><td colspan="7" class="text-center text-muted py-5">Chưa có danh sách học sinh. Vào Cài đặt để nhập.</td></tr>`;
  if (ddFilter !== "all" && !cls.some(keep)) $("#soBody").insertAdjacentHTML("afterbegin",
    `<tr><td colspan="7" class="text-center text-muted py-4">${ddFilter === "unrep" ? "Các lớp đều đã báo." : "Không lớp nào có em vắng."}</td></tr>`);

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
  if (d.not_bt.length) a += `<div class="alert alert-info py-2 mb-2"><i class="bi bi-info-circle-fill me-2"></i>Sổ có ghi tên em <b>không ăn bán trú</b> (theo danh sách hiện nay): ${esc(d.not_bt.join(", "))}. Giữ nguyên như sổ, không phải tên lạ.</div>`;
  if (d.extra.length) a += `<div class="alert alert-secondary py-2 mb-2">Giữ nguyên chữ đã ghi: ${esc(d.extra.join(", "))} <button class="btn btn-sm btn-outline-secondary ms-2" id="clsClearExtra">Xóa các tên này</button></div>`;
  if (d.upcoming.length) a += `<div class="text-muted small mb-2"><i class="bi bi-calendar-event"></i> Sắp tới: ${esc(d.upcoming.join("; "))}</div>`;
  $("#clsAlerts").innerHTML = a;
  $("#clsNote").value = d.note;
  const fri = d.names.some(n => n.absent && n.tags.includes("cắt thứ 6"));
  $("#clsFull").innerHTML = `<i class="bi bi-check2-all"></i> ${fri ? "Đủ (trừ em nghỉ thứ 6)" : "Lớp này đủ"}`;
  $("#clsNames").innerHTML = d.names.map(n => `
    <button class="nm ${n.absent ? "on" : ""}" data-sid="${esc(n.id)}" title="${esc(n.full)} · ${esc(n.dob)}"
      data-s="${esc(n.full + " " + n.name + " " + (n.alias || ""))}" data-full="${esc(n.full)}" data-name="${esc(n.name)}">
      <i class="bi ${n.absent ? "bi-x-circle-fill" : "bi-circle"} ck"></i><span>${esc(n.name)}</span>
      ${n.tags.length ? `<span class="tg">${esc(n.tags.join(", "))}</span>` : ""}</button>`).join("")
    || `<div class="text-muted">Lớp này chưa có em nào ăn bán trú trong danh sách.</div>`;
  filterNames();
}

// tách ô tìm thành các tên: dấu phẩy, chấm phẩy, xuống dòng hoặc chữ "và"; bỏ dấu câu thừa
const searchTerms = q => q.split(/[,;\n]|\s+v[aà]\s+/i)
  .map(t => t.replace(/[^\p{L}\p{N}\s]/gu, " ").trim()).filter(Boolean);

// tên gõ / dán không có trong bảng: ô viền đứt nằm luôn trong lưới tên, ghi lý do
function missTile(t) {
  const o = (D.others || []).find(x => matches(t, x.s));
  return `<div class="nm miss ${o ? "known" : ""}" style="order:2" title="Không tính vào bán trú của lớp">
    <i class="bi ${o ? "bi-person-slash" : "bi-question-circle"} ck"></i>
    <span><span class="d-block">${esc(t)}</span><small class="why">${esc(o ? o.why : "Không có trong danh sách")}</small></span></div>`;
}

function filterNames() {  // chỉ lọc, không chọn: hiện các em khớp một trong các tên đã gõ / dán
  const terms = searchTerms($("#clsSearch").value), found = new Set();
  $$("#clsNames .nm.miss").forEach(x => x.remove());
  const tiles = $$("#clsNames .nm"), rank = new Map();
  for (const t of terms) {  // mỗi tên chỉ hiện các em khớp tốt nhất (đủ chữ, đúng dấu trước; khớp đầu chữ khi đang gõ dở)
    const lv = tiles.map(b => matchLevel(t, b.dataset.s));
    const best = Math.max(0, ...lv);
    if (!best) continue;
    found.add(t);
    tiles.forEach((b, i) => { if (lv[i] === best) rank.set(b, Math.min(rank.get(b) ?? 1, tailMatch(t, b) ? 0 : 1)); });
  }
  let n = 0;
  tiles.forEach(b => {
    const ok = !terms.length || rank.has(b);
    b.style.display = ok ? "" : "none";
    b.style.order = terms.length && ok ? rank.get(b) : "";
    n += ok;
  });
  const miss = terms.filter(t => !found.has(t));
  $("#clsNames").insertAdjacentHTML("beforeend", miss.map(missTile).join(""));
  const none = $("#clsNoMatch");  // không khớp em nào và có tên lạ: nhắc cách gõ
  const lost = miss.filter(t => !(D.others || []).some(x => matches(t, x.s)));
  none.style.display = !n && lost.length ? "" : "none";
  none.innerHTML = `<i class="bi bi-lightbulb me-1"></i>Gõ không cần dấu, vd. <i>gia huy</i>; nhiều tên cách nhau dấu phẩy.`;
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

function showBlocked(b) {  // còn tên chưa rõ: chưa lưu được, đưa tới lớp cần xử lý
  return ask("Chưa lưu được", `<p class="text-danger fw-bold">Còn ${b.n} tên chưa rõ — chưa lưu được.</p>
    <ul>${b.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`, [{ key: "fix", label: "Xử lý ngay", cls: "btn-danger" }], { icon: "bi-exclamation-triangle-fill", danger: true })
    .then(() => { showPage("dd"); if (b.code) openClass(b.code); return false; });
}

async function doSave() {
  // hỏi một lần mọi điều cần biết trước khi lưu
  const ck = await api("save_check");
  if (ck.blocked) return showBlocked(ck.blocked);
  const items = [];
  if (ck.unreported && ck.unreported.length) items.push(`<li class="mb-2"><b>${ck.unreported.length} lớp chưa báo</b>: ${esc(ck.unreported.join(", "))}.
    Lưu bây giờ thì các lớp này coi như <b>không em nào vắng</b>` +
    `${ck.unreported_auto && ck.unreported_auto.length ? ` (trừ các em nghỉ thứ 6 ở lớp ${esc(ck.unreported_auto.join(", "))})` : ""}.</li>`);
  if (ck.meal) items.push(`<li class="mb-2"><b class="text-danger">Suất ăn ${mealDiff(ck.meal)}</b> (tổng suất ${ck.meal.total}, hiện diện ${ck.meal.present})` +
    `${ck.meal.ask ? `: ${ck.meal.ask} em ăn ghép vắng chưa chọn nhóm` : ""}. Lưu bây giờ thì bảng suất ăn trong sổ cũng lệch.</li>`);
  if (ck.conflicts && ck.conflicts.length) items.push(`<li class="mb-2"><b>Sĩ số khác nhau</b> giữa danh sách bán trú và sổ (có thể do thêm/cắt em chưa cập nhật):
    <ul>${ck.conflicts.map(l => `<li>${esc(l)}</li>`).join("")}</ul></li>`);
  let choice = null;
  if (items.length) {
    const btns = ck.conflicts && ck.conflicts.length
      ? [{ key: "keep", label: "Lưu, giữ sĩ số như sổ" }, { key: "list", label: "Lưu, dùng sĩ số theo danh sách", cls: "btn-outline-primary" }]
      : [{ key: "go", label: "Vẫn lưu" }];
    if (ck.meal) btns.push({ key: "see", label: "Xem trang Suất ăn", cls: "btn-outline-secondary" });
    btns.push({ key: "stay", label: "Hủy", cls: "btn-outline-secondary" });
    const k = await ask("Kiểm tra trước khi lưu", `<ul class="ps-3 mb-0">${items.join("")}</ul>`, btns, { icon: "bi-clipboard-check" });
    if (k === "see") { showPage("sa"); return false; }
    if (!["go", "keep", "list"].includes(k)) return false;
    if (k !== "go") choice = k;
  }
  let r = await api("save", choice);
  if (r.blocked) return showBlocked(r.blocked);
  if (r.conflicts) {  // hiếm: sĩ số đổi giữa lúc hỏi và lúc lưu
    choice = await ask("Sĩ số khác nhau", `<p>Ghi sĩ số nào vào sổ?</p><ul>${r.conflicts.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`,
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
// tổng suất so với hiện diện: "thừa 1 suất" / "thiếu 2 suất"
function mealDiff(m) { const d = m.total - m.present; return d > 0 ? `thừa ${d} suất` : `thiếu ${-d} suất`; }

async function renderMeals() {
  const m = await api("meals");
  if (m.empty) {
    $("#mealTotal").textContent = "Sổ chưa có bảng suất ăn";
    $("#mealSub").textContent = "";
    $("#mealAlerts").innerHTML = "";
    $("#mealBody").innerHTML = "";
    $("#mealInfo").textContent = "Sheet mẫu của sổ không có bảng suất ăn bên dưới bảng điểm danh.";
    return;
  }
  const d = mealDiff(m);
  $("#mealTotal").innerHTML = m.ok
    ? `<span class="text-success"><i class="bi bi-check-circle-fill"></i> Tổng suất ${m.total} = hiện diện ${m.present}</span>`
    : `<span class="text-danger"><i class="bi bi-exclamation-triangle-fill"></i> ${d[0].toUpperCase() + d.slice(1)}: tổng suất ${m.total}, hiện diện ${m.present}</span>`;
  $("#mealSub").textContent = m.self ? `Các nhóm ${m.groups_total} + tự ăn tại lớp ${m.self.meals} = ${m.total} suất` : `Các nhóm: ${m.groups_total} suất`;
  let a = "";
  if (m.ask.length) {  // em ghép vắng mà danh sách chưa ghi nhóm: hỏi em đó ăn nhóm nào
    a += `<div class="alert alert-warning py-2 mb-2"><div class="mb-1"><span class="fw-semibold"><i class="bi bi-question-circle-fill me-2"></i>Em ăn ghép vắng — chọn nhóm em đó ăn:</span>
      <span class="small text-muted ms-2">chỉ cho ngày này; muốn app tự biết thì ghi cột <b>Ăn ghép</b> trong file Excel danh sách</span></div>` +
      m.ask.map(x => `<div class="d-flex align-items-center gap-2 flex-wrap"><span class="ask-name"><b>${esc(x.name)}</b> <span class="text-muted">lớp ${esc(x.cls)}</span></span>` +
        x.groups.map(g => `<button class="btn btn-sm btn-outline-dark py-0" data-pick="${esc(x.sid)}" data-g="${esc(g)}">Nhóm ${esc(g)}</button>`).join("") + `</div>`).join("") + `</div>`;
  }
  for (const w of m.warnings) a += `<div class="alert alert-danger py-2 mb-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>${esc(w)}</div>`;
  if (m.note) a += `<div class="alert alert-info py-2 mb-2"><i class="bi bi-info-circle-fill me-2"></i>${esc(m.note)}</div>`;
  $("#mealAlerts").innerHTML = a;
  const rows = [];
  let prev = null;
  for (const l of m.lines) {  // như bảng trong sổ: cột suất, cột tên ghép; dòng trống giữ chỗ cách dòng
    for (let r = prev === null ? l.row : prev + 1; r < l.row; r++) rows.push(`<tr class="gap"><td colspan="3"></td></tr>`);
    prev = l.row;
    const vang = l.absent.length ? ` <span class="text-danger">− vắng ${l.absent.length}: ${l.absent.map(x => x.picked
      ? `<a href="#" class="link-danger" data-unpick="${esc(x.sid)}" title="Bấm để chọn lại nhóm">${esc(x.name)}</a>` : esc(x.name)).join(", ")}</span>` : "";
    rows.push(`<tr class="${l.m ? "table-warning" : ""}"><td class="text-center fw-bold text-danger fs-6">${l.meals}</td>
      <td class="fw-semibold">${esc(l.label)}</td><td>${esc(l.gom)}${vang}</td></tr>`);
  }
  if (m.self) rows.push(`<tr class="text-muted"><td class="text-center fw-bold">${m.self.meals}</td><td>${esc(m.self.label)}</td><td>${esc(m.self.gom)}</td></tr>`);
  $("#mealBody").innerHTML = rows.join("");
  const gh = (m.ghep || []).map(g => `<span class="me-3 text-nowrap"><i class="bi bi-diagram-3 me-1"></i>Lớp ghép <b>${esc(g.code)}</b>:
    đã ghi nhóm <b class="${g.done < g.n ? "text-warning-emphasis" : "text-success"}">${g.done}/${g.n} em</b> ·
    <a href="#" data-hs="${esc(g.code)}">Xem các em</a></span>`).join("");
  const todo = (m.ghep || []).some(g => g.done < g.n);
  $("#mealInfo").innerHTML = gh + (todo ? `<span class="text-muted">(ghi nhóm ở cột <b>Ăn ghép</b> trong Excel)</span>` : "");
  $("#mealInfo").style.display = gh ? "" : "none";
  $$("#mealInfo [data-hs]").forEach(a => a.onclick = e => { e.preventDefault(); hsPreset = a.dataset.hs; showPage("hs"); });
  const pick = async (sid, g) => { const r = await api("pick_ghep", sid, g); applyState(r.state); renderMeals(); };
  $$("#mealAlerts [data-pick]").forEach(b => b.onclick = () => pick(b.dataset.pick, b.dataset.g));
  $$("#mealBody [data-unpick]").forEach(b => b.onclick = e => { e.preventDefault(); pick(b.dataset.unpick, ""); });
}

// ------------------------------------------------------------------ Sửa cách ghép (bảng suất ăn)
let MG = null;  // {groups: [{label, classes, code, gap}], classes: [{code, ma}], exists}

async function editMeals() {
  MG = await api("meal_groups");
  MG.groups = MG.groups.map(g => ({ ...g, classes: [...g.classes], gap: !g.label && !g.classes.length && !g.code }));
  $("#mealEditor").hidden = false;
  $("#mealView").hidden = true;
  $("#mealEditBtn").hidden = true;
  renderMealEditor();
}

function closeMealEditor() {
  MG = null;
  $("#mealEditor").hidden = true;
  $("#mealView").hidden = false;
  $("#mealEditBtn").hidden = false;
}

function renderMealEditor() {
  const used = {};
  MG.groups.forEach((g, i) => g.classes.forEach(c => { used[c] = i; }));
  const ma = Object.fromEntries(MG.classes.map(c => [c.code, c.ma]));
  const free = MG.classes.map(c => c.code).filter(c => !(c in used));
  const n = MG.groups.length;
  const rows = MG.groups.map((g, i) => {
    const btns = `<div class="btn-group btn-group-sm">
      <button class="btn btn-outline-secondary" data-mv="${i}" data-d="-1" title="Lên" ${i === 0 ? "disabled" : ""}><i class="bi bi-arrow-up"></i></button>
      <button class="btn btn-outline-secondary" data-mv="${i}" data-d="1" title="Xuống" ${i === n - 1 ? "disabled" : ""}><i class="bi bi-arrow-down"></i></button>
      <button class="btn btn-outline-danger" data-del="${i}" title="Xóa dòng"><i class="bi bi-x-lg"></i></button></div>`;
    if (g.gap) return `<tr class="gap"><td colspan="3" class="text-muted small fst-italic">— dòng trống (cách dòng trong sổ) —</td><td class="text-end">${btns}</td></tr>`;
    const chips = g.classes.map(c => `<span class="badge text-bg-light border fs-6 fw-semibold me-1">${esc(c)}${ma[c] ? ` <span class="text-muted fw-normal">(${esc(ma[c])})</span>` : ""}</span>`).join("");
    return `<tr><td><input class="form-control fw-semibold" data-lb="${i}" value="${esc(g.label)}" placeholder="vd. 1.2 ghép"></td>
      <td>${chips || `<span class="text-muted small me-1">chưa có lớp</span>`}<button class="btn btn-sm btn-outline-primary py-0" data-cls="${i}"><i class="bi bi-pencil-square"></i> Chọn lớp</button></td>
      <td><input class="form-control text-center" data-code="${i}" value="${esc(g.code)}" placeholder="—" title="Chỉ ghi khi dòng này nhận em ghép lẻ (vd. 1.2)"></td>
      <td class="text-end text-nowrap">${btns}</td></tr>`;
  });
  $("#mealEditor").innerHTML = `<div class="alert alert-light border small my-2">Mỗi dòng ở đây = 1 dòng bảng suất ăn trong sổ (cột suất + cột tên ghép), đúng thứ tự từ trên xuống.
      Lớp không thuộc dòng nào thì <b>ăn tại lớp</b>. <b>Mã ghép lẻ</b>: chỉ ghi ở dòng nhận em ghép lẻ từ lớp chia nhóm (vd. 1.2); em nào ăn dòng đó thì cột <b>Ăn ghép</b> trong file danh sách ghi đúng mã này.</div>
    <div id="mgErr"></div>
    <table class="table table-sm align-middle meal-edit mb-2"><thead><tr><th style="width:230px">Tên ghép (in ở sổ)</th><th>Các lớp ăn chung</th><th style="width:105px">Mã ghép lẻ</th><th style="width:120px"></th></tr></thead>
      <tbody>${rows.join("")}</tbody></table>
    <div class="d-flex gap-2 flex-wrap mb-2">
      <button class="btn btn-outline-primary" id="mgAdd"><i class="bi bi-plus-lg"></i> Thêm dòng</button>
      <button class="btn btn-outline-secondary" id="mgGap"><i class="bi bi-dash-lg"></i> Thêm dòng trống</button></div>
    <div class="mb-2"><b>Ăn tại lớp:</b> ${free.map(esc).join(", ") || "—"}</div>
    <div class="d-flex align-items-center gap-3 border-top pt-2 pb-2 flex-wrap">
      ${MG.exists ? `<div class="form-check"><input class="form-check-input" type="checkbox" id="mgToday"><label class="form-check-label" for="mgToday">Dựng lại bảng suất ăn cả tờ ngày đang mở (tờ này đã có trong sổ)</label></div>`
        : `<span class="text-muted">Áp dụng từ tờ ngày đang mở (chưa có trong sổ) và các ngày sau.</span>`}
      <div class="ms-auto d-flex gap-2"><button class="btn btn-primary" id="mgSave"><i class="bi bi-check-lg"></i> Lưu cách ghép</button>
        <button class="btn btn-outline-secondary" id="mgCancel">Hủy</button></div></div>`;
  const E = $("#mealEditor");
  $$("[data-lb]", E).forEach(x => x.oninput = () => { MG.groups[+x.dataset.lb].label = x.value; });
  $$("[data-code]", E).forEach(x => x.oninput = () => { MG.groups[+x.dataset.code].code = x.value.trim(); });
  $$("[data-mv]", E).forEach(b => b.onclick = () => {
    const i = +b.dataset.mv, j = i + +b.dataset.d;
    [MG.groups[i], MG.groups[j]] = [MG.groups[j], MG.groups[i]];
    renderMealEditor();
  });
  $$("[data-del]", E).forEach(b => b.onclick = () => { MG.groups.splice(+b.dataset.del, 1); renderMealEditor(); });
  $$("[data-cls]", E).forEach(b => b.onclick = () => pickMealClasses(+b.dataset.cls));
  $("#mgAdd").onclick = () => { MG.groups.push({ label: "", classes: [], code: "", gap: false }); renderMealEditor(); };
  $("#mgGap").onclick = () => { MG.groups.push({ label: "", classes: [], code: "", gap: true }); renderMealEditor(); };
  $("#mgCancel").onclick = closeMealEditor;
  $("#mgSave").onclick = saveMealGroups;
}

async function pickMealClasses(i) {
  const g = MG.groups[i];
  const used = {};
  MG.groups.forEach((x, j) => x.classes.forEach(c => { used[c] = j; }));
  await form(`Chọn lớp ăn chung dòng "${g.label || "mới"}"`, b => {
    b.innerHTML = `<p class="text-muted mb-2">Bấm chọn các lớp ăn cả lớp ở dòng này. Lớp đang ở dòng khác hiện mờ; chọn thì lớp đó chuyển sang dòng này.</p><div class="cls-grid">` +
      MG.classes.map(c => {
        const o = used[c.code], other = o !== undefined && o !== i;
        return `<label class="cls-pick ${other ? "other" : ""}"><input type="checkbox" class="form-check-input me-1" value="${esc(c.code)}" ${g.classes.includes(c.code) ? "checked" : ""}>${esc(c.code)}` +
          (c.ma ? ` <span class="text-muted fw-normal small">(${esc(c.ma)})</span>` : "") +
          (other ? `<div class="small text-muted fw-normal">đang ở: ${esc(MG.groups[o].label || "dòng " + (o + 1))}</div>` : "") + `</label>`;
      }).join("") + `</div>`;
  }, "Xong", async b => {
    const pick = $$("input:checked", b).map(x => x.value);
    MG.groups.forEach((x, j) => { if (j !== i) x.classes = x.classes.filter(c => !pick.includes(c)); });
    g.classes = MG.classes.map(c => c.code).filter(c => pick.includes(c));
    return true;
  }, { size: "modal-xl" });
  renderMealEditor();
}

async function saveMealGroups() {
  const bad = MG.groups.findIndex(g => !g.gap && !g.label.trim() && !g.code);
  const showErr = list => { $("#mgErr").innerHTML = `<div class="alert alert-danger py-2"><b>Chưa lưu được:</b><ul class="mb-0">${list.map(e => `<li>${esc(e)}</li>`).join("")}</ul></div>`; };
  if (bad >= 0) return showErr([`Dòng ${bad + 1} chưa có tên ghép.`]);
  const groups = MG.groups.map(g => g.gap ? { label: "", classes: [], code: "" } : { label: g.label, classes: g.classes, code: g.code });
  const r = await api("save_meal_groups", groups, !!($("#mgToday") && $("#mgToday").checked));
  if (r.errors) return showErr(r.errors);
  closeMealEditor();
  applyState(r.state);
  toast(r.flash);
  renderMeals();
}

// ------------------------------------------------------------------ Học sinh
let HS = null;
let hsPreset = null;  // mở trang Học sinh lọc sẵn 1 lớp (bấm "Xem các em" ở trang Suất ăn)
async function renderStudents() {
  const sel = $("#hsClass");
  if (hsPreset !== null) {
    if (![...sel.options].some(o => o.value === hsPreset)) sel.insertAdjacentHTML("beforeend", `<option>${esc(hsPreset)}</option>`);
    sel.value = hsPreset;
    $("#hsQ").value = "";
    hsPreset = null;
  }
  const cur = sel.value;
  HS = await api("students", $("#hsQ").value, cur, $("#hsBt").checked);
  if (sel.options.length !== HS.classes.length + 1) {
    sel.innerHTML = `<option value="">Tất cả lớp</option>` + HS.classes.map(c => `<option>${esc(c)}</option>`).join("");
    sel.value = cur;
  }
  $("#hsCount").textContent = `${HS.rows.length} em`;
  $("#hsBody").innerHTML = HS.rows.map(s => `<tr class="${s.now ? "" : "text-muted"}">
    <td>${esc(s.lop)}</td><td class="fw-semibold">${esc(s.ten)}</td><td>${esc(s.ns)}</td><td class="text-center">${s.bt ? `<i class="bi bi-check-lg text-success"></i>` : ""}</td>
    <td>${esc(s.goi)}</td><td>${esc(s.ghep)}</td><td>${esc(s.db)}</td><td>${esc(s.gc)}</td></tr>`).join("");
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

// ------------------------------------------------------------------ Cài đặt
async function renderSettings() {
  const s = await api("settings");
  $("#ver").textContent = "Phiên bản " + s.version;
  // mỗi file 1 hàng: tên file (rê chuột xem đường dẫn đủ) + các nút của file đó
  const row = (k, icon, label, btns, help = "") => {
    const p = s[k] || "", name = p.split(/[\\/]/).pop();
    return `<div class="d-flex align-items-center gap-3 py-2 border-top">
      <i class="bi ${icon} fs-4 text-secondary"></i>
      <div class="flex-grow-1" style="min-width:0"><div class="text-muted small">${label}</div>
        <div class="fw-semibold text-truncate" title="${esc(p)}">${p ? esc(name) : `<span class="text-muted fw-normal">chưa có</span>`}</div>
        ${help ? `<div class="text-muted small">${help}</div>` : ""}</div>
      <div class="d-flex gap-2 flex-shrink-0">${btns}</div></div>`;
  };
  const folder = k => `<button class="btn btn-outline-secondary text-nowrap" data-open="${k}"><i class="bi bi-folder2-open"></i> Thư mục</button>`;
  $("#cdFiles").innerHTML =
    row("so_file", "bi-journal-text", "Sổ điểm danh tháng",
      `<button class="btn btn-primary text-nowrap" data-cd="book"><i class="bi bi-journal-arrow-up"></i> Chọn sổ khác…</button>
       <button class="btn btn-outline-primary text-nowrap" data-cd="notes"><i class="bi bi-journal-text"></i> Đọc ghi chú sổ…</button>` + folder("so_folder")) +
    row("cdhs_file", "bi-file-earmark-spreadsheet", "Danh sách học sinh (Excel)",
      `<button class="btn btn-primary text-nowrap" data-cd="import"><i class="bi bi-file-earmark-arrow-down"></i> Nhập danh sách…</button>
       <button class="btn btn-outline-secondary text-nowrap" data-open="cdhs_file"><i class="bi bi-box-arrow-up-right"></i> Mở file</button>`,
      "Cột: Lớp · Họ tên · Ngày sinh · Bán trú (Có/Không) · Tên gọi khác · Ăn ghép (file toàn trường tô đỏ cũng nhập được)."
      + (s.nhom_an ? ` Bảng suất ăn: dựng theo sheet <b>Nhóm ăn</b> (${s.nhom_an} dòng).` : ` Muốn app dựng bảng suất ăn: thêm sheet <b>Nhóm ăn</b>.`)) +
    row("data", "bi-database", "Dữ liệu của app", folder("data_folder"));
}

async function importList(path) {
  const p = await api("import_list", path || null);
  if (p.cancel) return;
  if (p.error) return info("Không đọc được file", p.error);
  let sel = p.changes.filter(c => c.apply).map(c => c.i);
  const ok = await form("Nhập danh sách học sinh", b => {
    b.innerHTML = `<p class="fs-6">Đọc được <b>${p.n}</b> học sinh trong <b>${esc(p.file)}</b>, <b>${p.n_bt}</b> em ăn bán trú.</p>`
      + (p.mismatch.length ? `<div class="alert alert-warning py-2">Lưu ý: màu chữ khác cột "Phân loại HS" ở: ${esc(p.mismatch.join("; "))}.</div>` : "")
      + (p.meal_errors.length ? `<div class="alert alert-danger py-2"><b>Sheet Nhóm ăn có lỗi nên app chưa dùng</b> (giữ bảng Nhóm ăn cũ). Sửa trong Excel rồi nhập lại:<ul class="mb-0">${p.meal_errors.map(e => `<li>${esc(e)}</li>`).join("")}</ul></div>` : "")
      + (p.meal_warnings.length ? `<div class="alert alert-warning py-2">${p.meal_warnings.map(e => `<div>${esc(e)}</div>`).join("")}</div>` : "")
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
  if (p === "sa") { if (MG) closeMealEditor(); renderMeals(); }
  if (p === "hs") renderStudents();
  if (p === "lich") renderLich();
  if (p === "cd") renderSettings();
}

// ------------------------------------------------------------------ gắn sự kiện
function wire() {
  $("#nav").onclick = e => { const a = e.target.closest("[data-page]"); if (a) { e.preventDefault(); showPage(a.dataset.page); } };
  document.body.addEventListener("click", e => {
    const go = e.target.closest("[data-go]");
    if (go) { showPage(go.dataset.go); return; }
    const op = e.target.closest("[data-open]");
    if (op && op.closest("#summary, #unrep")) { openClass(op.dataset.open); return; }
    if (op && op.dataset.open) { api("open_path", op.dataset.open).then(r => r.error && info("Chưa mở được", r.error)); }
  });
  $("#soBody").onclick = e => { const tr = e.target.closest("tr.cls"); if (tr) openClass(tr.dataset.code); };
  $("#ddFilter").onclick = e => { const b = e.target.closest("[data-filter]"); if (b) { ddFilter = b.dataset.filter; renderDiemDanh(); } };
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
  $("#btnReset").onclick = async () => {
    const k = await ask("Đặt lại điểm danh ngày này?", `<p>Mọi lớp về <b>chưa báo</b>, bỏ hết tên vắng đã chọn. Ghi chú và sĩ số giữ nguyên.</p>
      <p class="text-muted mb-0">Dùng khi sheet trong sổ đã tạo sẵn nên app hiểu nhầm là các lớp đã điểm danh. Sổ chỉ thay đổi khi bấm <b>Lưu vào sổ</b>; bấm <b>Hoàn tác</b> nếu nhầm.</p>`,
      [{ key: "ok", label: "Đặt lại", cls: "btn-danger" }, { key: "no", label: "Thôi" }], { icon: "bi-arrow-repeat" });
    if (k === "ok") handle(await api("reset_day"));
  };
  $("#mealEditBtn").onclick = editMeals;
  const appEl = $(".app");
  const setSide = min => {
    appEl.classList.toggle("side-min", min);
    $("#sideToggle").innerHTML = `<i class="bi ${min ? "bi-chevron-double-right" : "bi-chevron-double-left"}"></i>`;
    $("#sideToggle").title = min ? "Mở rộng thanh bên" : "Thu gọn thanh bên";
    try { localStorage.setItem("sideMin", min ? "1" : "0"); } catch { /* bỏ qua */ }
  };
  let sideMin = false;
  try { sideMin = localStorage.getItem("sideMin") === "1"; } catch { /* bỏ qua */ }
  setSide(sideMin);
  $("#sideToggle").onclick = () => setSide(!appEl.classList.contains("side-min"));
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
  $("#clsSearch").oninput = filterNames;  // ô tìm chỉ để lọc tên; chọn vắng = bấm vào ô tên
  // dán tên nhiều dòng: ô một dòng sẽ dính các dòng lại, nên đổi xuống dòng thành dấu phẩy
  $("#clsSearch").addEventListener("paste", e => {
    const t = (e.clipboardData || window.clipboardData).getData("text");
    if (!/[\r\n]/.test(t)) return;
    e.preventDefault();
    const el = e.target;
    el.setRangeText(t.trim().replace(/\s*[\r\n]+\s*/g, ", "), el.selectionStart, el.selectionEnd, "end");
    filterNames();
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

  // Cài đặt
  $("#cdFiles").onclick = async e => {
    const b = e.target.closest("[data-cd]");
    if (!b) return;
    if (b.dataset.cd === "book") { const r = await api("choose_book"); if (!r.cancel) { handle(r); renderSettings(); } }
    else if (b.dataset.cd === "import") importList();
    else if (b.dataset.cd === "notes") noteSuggestions();
  };
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

// ------------------------------------------------------------------ Thiết lập lần đầu (bản mới tải về)
let SETUP = null;

function renderSetup(s) {
  SETUP = s;
  const step = (n, key, title, desc, value, btns, off) => `<div class="setup-step ${s[key + "_done"] ? "done" : ""} ${off ? "off" : ""}">
      <div class="num">${s[key + "_done"] ? '<i class="bi bi-check-lg"></i>' : n}</div>
      <div class="txt"><div class="fw-semibold">${title}</div><div class="small text-muted">${desc}</div>
        ${value ? `<div class="path"><i class="bi bi-check-circle-fill text-success me-1"></i>${esc(value)}</div>` : ""}</div>
      <div class="d-flex gap-2 flex-shrink-0">${btns}</div></div>`;
  const noFolder = !s.folder_done;
  $("#setupSteps").innerHTML =
    step(1, "folder", "Nơi đặt file dữ liệu của app", s.folder_done ? "" : `Gợi ý: ${esc(s.folder)}`, s.folder_done ? s.folder : "",
      `<button class="btn btn-primary" data-setup="default">Dùng thư mục gợi ý</button>
       <button class="btn btn-outline-primary" data-setup="folder">Chọn thư mục…</button>`, false) +
    step(2, "book", "Sổ điểm danh tháng (Excel)", "Chọn file sổ của tháng đang điểm danh.", s.book,
      `<button class="btn ${s.book_done ? "btn-outline-primary" : "btn-primary"}" data-setup="book" ${noFolder ? "disabled" : ""}>Chọn sổ…</button>`, noFolder) +
    step(3, "list", "Danh sách học sinh (Excel)", "Chọn file danh sách để nhập.", s.list ? `${s.list} (${s.n} học sinh)` : "",
      `<button class="btn ${s.list_done ? "btn-outline-primary" : "btn-primary"}" data-setup="list" ${noFolder ? "disabled" : ""}>Nhập danh sách…</button>`, noFolder);
  $("#setupDone").disabled = s.missing.length > 0;
  $("#setupErr").textContent = s.missing.length ? "Còn thiếu: " + s.missing.join(", ") + "." : "";
  $("#setup").hidden = false;
}

async function setupStep(kind) {
  if (kind === "default" || kind === "folder") {
    const r = await api("setup_folder", null, kind === "default");
    if (r.error) info("Chưa dùng được thư mục", r.error);
    return renderSetup(r.setup);
  }
  if (kind === "book") { const r = await api("choose_book"); if (!r.cancel) handle(r); }
  if (kind === "list") await importList();
  renderSetup(await api("setup_info"));
}

document.addEventListener("DOMContentLoaded", async () => {
  wire();
  await apiReady();
  const r = handle(await api("boot"));
  $("#setupSteps").onclick = e => { const b = e.target.closest("[data-setup]"); if (b && !b.disabled) setupStep(b.dataset.setup); };
  $("#setupDone").onclick = async () => {
    const res = await api("finish_setup");
    if (res.error) { $("#setupErr").textContent = res.error; return renderSetup(res.setup); }
    $("#setup").hidden = true;
    SETUP = null;
    handle(res);
    renderSettings();
  };
  if (r && r.setup) return renderSetup(r.setup);
  renderSettings();
  if (r && r.restore) await askRestore(r.restore);
  if (r && r.list_changed) {  // file Excel danh sách đã được sửa sau lần nhập trước
    const k = await ask("File danh sách đã sửa", `File <b>${esc(r.list_changed.file)}</b> đã được sửa sau lần nhập trước.<br>Nhập lại để cập nhật danh sách trong app?`,
      [{ key: "go", label: "Nhập lại" }, { key: "later", label: "Để sau", cls: "btn-outline-secondary" }], { icon: "bi-file-earmark-excel" });
    if (k === "go") importList(r.list_changed.path);
  }
});
