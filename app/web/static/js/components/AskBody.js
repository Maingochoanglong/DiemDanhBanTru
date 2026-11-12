// Nội dung hộp hỏi chung (mở bằng ask() trong dialogs.js).
const { inject } = Vue;

export default {
  setup() {
    const dialogRef = inject("dialogRef");
    const { html, buttons } = dialogRef.value.data;
    const close = key => dialogRef.value.close(key);
    const btnProps = (b, i) => ({ severity: "severity" in b ? b.severity : (i === 0 ? undefined : "secondary"), outlined: b.outlined ?? i > 0 });
    return { html, buttons, close, btnProps };
  },
  template: /* html */`
    <div v-html="html"></div>
    <div class="dlg-foot">
      <Button v-for="(b, i) in buttons" :key="b.key ?? i" :label="b.label" v-bind="btnProps(b, i)" :autofocus="i === 0" @click="close(b.key)" />
    </div>`,
};
