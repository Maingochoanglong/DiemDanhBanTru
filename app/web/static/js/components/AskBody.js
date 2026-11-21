// Nội dung hộp hỏi chung (mở bằng ask() trong dialogs.js).
const { inject } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const { buttons } = dialogRef.value.data;
    // lưới của hộp xếp các khối (đoạn, danh sách) cách đều; chữ trơn thì bọc thành đoạn, tách đoạn ở <br><br>
    const raw = dialogRef.value.data.html;
    const html = /^\s*<(p|ul|div)\b/.test(raw) ? raw : raw.split(/<br>\s*<br>/).map(x => `<p>${x}</p>`).join("");
    const close = key => dialogRef.value.close(key);
    const btnProps = (b, i) => ({ severity: "severity" in b ? b.severity : (i === 0 ? undefined : "secondary"), outlined: b.outlined ?? i > 0 });
    return { html, buttons, close, btnProps };
  },
  template: /* html */`
    <div class="ask-body"><div class="ask-msg" v-html="html"></div>
    <div class="dlg-foot">
      <Button v-for="(b, i) in buttons" :key="b.key ?? i" :label="b.label" v-bind="btnProps(b, i)" :autofocus="i === 0" @click="close(b.key)" />
    </div></div>`,
};
