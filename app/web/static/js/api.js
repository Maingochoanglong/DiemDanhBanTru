// Gọi Python: POST /api/<tên hàm> (máy chủ FastAPI, app/web/server.py).
const { reactive } = Vue;

export const CONFIG = window.APP_CONFIG;  // giá trị cố định do máy chủ gửi (app/config.py qua /config.js), không viết cứng ở đây
export const IS_APP = CONFIG.mode === "app";  // app thật (có nút Thoát); "dev" = máy chủ chạy thử
export const CLIENT = Math.random().toString(36).slice(2) + Date.now().toString(36);  // mã của thẻ trình duyệt này
export const conn = reactive({ gone: false, quit: false });  // máy chủ đã tắt / đã bấm Thoát

// gọi lần lượt từng việc (bấm nhanh liên tiếp cũng không chạy chồng lên nhau)
let chain = Promise.resolve();
export function api(name, ...args) {
  const run = async () => {
    let r;
    try {
      r = await fetch("/api/" + name, { method: "POST", body: JSON.stringify(args),
        headers: { "Content-Type": "application/json", [CONFIG.apiHeader]: "1", [CONFIG.clientHeader]: CLIENT } });
    } catch (e) {
      conn.gone = true;
      throw e;
    }
    if (!r.ok) return { error: `Lỗi máy chủ (${r.status}).` };
    return await r.json();
  };
  const p = chain.then(run, run);
  chain = p.catch(() => {});
  return p;
}

if (IS_APP) {
  // đóng thẻ: báo máy chủ (thẻ cuối cùng đóng thì app tự thoát)
  window.addEventListener("pagehide", () => { if (!conn.gone) navigator.sendBeacon("/bye", CLIENT); });
  window.addEventListener("pageshow", e => { if (e.persisted && !conn.gone) api("close_check").catch(() => {}); });
}
