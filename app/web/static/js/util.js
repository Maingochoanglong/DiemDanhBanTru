// Tiện ích chữ: so khớp tên tiếng Việt (gõ không dấu, gõ dở), ngày, suất ăn.

export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const fold = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();

// mỗi từ gõ vào là đầu của một chữ trong tên: "h long" khớp "Hải Long"
export function matches(q, text) {
  const words = fold(text).split(/\s+/);
  return fold(q).split(/\s+/).filter(Boolean).every(t => words.some(w => w.startsWith(t)));
}

const wordsOf = s => String(s || "").replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
// chữ có dấu, không phụ thuộc vị trí dấu thanh: "Thuý" và "Thúy" là một, "Nguyên" khác "Nguyễn"
const TONE = /[̣̀́̃̉]/g;
const toneKey = w => { const d = w.normalize("NFD").toLowerCase(); return d.replace(TONE, "").normalize("NFC") + (d.match(TONE) || []).join(""); };

// mức khớp của tên gõ với một em: 3 = đủ chữ, đúng dấu · 2 = đủ chữ (bỏ dấu) · 1 = chỉ khớp đầu chữ · 0 = không khớp
export function matchLevel(q, text) {
  const qw = wordsOf(q), tw = wordsOf(text), qf = qw.map(fold), tf = tw.map(fold);
  if (!qf.length || !qf.every(t => tf.some(w => w.startsWith(t)))) return 0;
  if (!qf.every(t => tf.includes(t))) return 1;
  if (!/[^\x00-\x7f]/.test(q)) return 2;  // gõ không dấu
  const tk = tw.map(toneKey);
  return qw.map(toneKey).every(t => tk.includes(t)) ? 3 : 2;
}

// tên gõ trùng phần cuối tên em (GV hay gọi tên cuối): "Thư" -> Minh Thư đứng trước Thư Kỳ
export function tailMatch(q, ...names) {
  const qf = wordsOf(q).map(fold);
  return names.some(s => {
    const w = wordsOf(s).map(fold);
    return w.length >= qf.length && qf.every((t, i) => w[w.length - qf.length + i] === t);
  });
}

// tách ô tìm thành các tên: dấu phẩy, chấm phẩy, xuống dòng hoặc chữ "và"; bỏ dấu câu thừa
export const searchTerms = q => q.split(/[,;\n]|\s+v[aà]\s+/i).map(t => t.replace(/[^\p{L}\p{N}\s]/gu, " ").trim()).filter(Boolean);

// tổng suất so với hiện diện: "thừa 1 suất" / "thiếu 2 suất"
export function mealDiff(m) { const d = m.total - m.present; return d > 0 ? `thừa ${d} suất` : `thiếu ${-d} suất`; }

export const pad = n => String(n).padStart(2, "0");
export const isoOf = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const dmyOf = d => `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
export function dateOf(text) {  // "2026-10-29" hoặc "29/10/2026" -> Date
  let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text || "");
  if (m) return new Date(+m[1], m[2] - 1, +m[3]);
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text || "");
  return m ? new Date(+m[3], m[2] - 1, +m[1]) : null;
}
