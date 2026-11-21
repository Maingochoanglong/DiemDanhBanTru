// Nội dung hộp hỏi chung (mở bằng ask() trong dialogs.js).
const { inject } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    // mảng con trong buttons = nhóm nút cùng loại (rộng bằng nhau); i đánh số liên tục để nút đầu là nút chính
    let n = 0;
    const groups = dialogRef.value.data.buttons.map(g => (Array.isArray(g) ? g : [g]).map(b => ({ b, i: n++ })));
    // lưới của hộp xếp các khối (đoạn, danh sách) cách đều; chữ trơn thì bọc thành đoạn, tách đoạn ở <br><br>
    const raw = dialogRef.value.data.html;
    const html = /^\s*<(p|ul|div)\b/.test(raw) ? raw : raw.split(/<br>\s*<br>/).map(x => `<p>${x}</p>`).join("");
    const close = key => dialogRef.value.close(key);
    const btnProps = (b, i) => ({ severity: "severity" in b ? b.severity : (i === 0 ? undefined : "secondary"), outlined: b.outlined ?? i > 0 });
    return { html, groups, close, btnProps };
  },
  template: /* html */`
    <div class="ask-body"><div class="ask-msg" v-html="html"></div>
    <div class="dlg-foot">
      <div v-for="(g, gi) in groups" :key="gi" class="same-w">
        <Button v-for="{ b, i } in g" :key="b.key ?? i" :label="b.label" v-bind="btnProps(b, i)" :autofocus="i === 0" @click="close(b.key)" />
      </div>
    </div></div>`,
};
