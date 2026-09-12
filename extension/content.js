(() => {
  "use strict";
  const permitted = () => window.top === window &&
    location.origin === "https://ezpost.post.gov.tw" && location.pathname === "/Account/Login";
  if (!permitted() || globalThis.__ezpostAutofillStarted) return;
  globalThis.__ezpostAutofillStarted = true;
  let model, image, input, status, timer, generation = 0, edits = 0, filling = false;
  let lastKey = "";

  function message(text, state, detail = "") {
    if (!permitted() || !input?.isConnected) return;
    if (!status?.isConnected) {
      status = document.createElement("small");
      status.id = "ezpost-ocr-status";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      status.style.cssText = "display:block;margin-top:6px;font-size:12px;line-height:1.5;";
      input.insertAdjacentElement("afterend", status);
    }
    status.textContent = text;
    status.dataset.state = state;
    status.title = detail;
    status.style.color = state === "review" || state === "error" ? "#885200" : "#16675c";
  }
  function edited() { if (!filling) edits++; }
  function fingerprint(data) {
    let hash = 2166136261;
    for (const value of data) hash = Math.imul(hash ^ value, 16777619);
    return hash >>> 0;
  }
  async function process(ticket) {
    if (!permitted() || !image?.isConnected || !input?.isConnected) return;
    const target = image, field = input, source = target.currentSrc || target.src;
    const editVersion = edits;
    if (!target.getAttribute("src")) return;
    try {
      await target.decode();
      if (!permitted() || ticket !== generation || target !== image || field !== input ||
          !field.isConnected || source !== (target.currentSrc || target.src)) return;
      const url = new URL(target.currentSrc || target.src, location.href);
      if (url.origin !== location.origin) throw new Error("驗證碼來源已改變，請手動輸入");
      if (target.naturalWidth !== 100 || target.naturalHeight !== 40)
        throw new Error("圖片尺寸已改變，請手動輸入");
      const canvas = document.createElement("canvas");
      canvas.width = 100; canvas.height = 40;
      const context = canvas.getContext("2d", {willReadFrequently: true});
      context.drawImage(target, 0, 0);
      const pixels = context.getImageData(0, 0, 100, 40);
      const key = source + ":" + fingerprint(pixels.data);
      if (key === lastKey) return;
      model ||= EZPostOCR.loadModel(EZPostModel);
      const result = EZPostOCR.recognize(pixels, model);
      if (!permitted() || ticket !== generation) return;
      lastKey = key;
      if (editVersion !== edits || field.disabled || field.readOnly) {
        message("已保留目前輸入的驗證碼", "manual");
        return;
      }
      filling = true;
      try {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(field, result.text);
        field.dispatchEvent(new Event("input", {bubbles: true}));
        field.dispatchEvent(new Event("change", {bubbles: true}));
      } finally { filling = false; }
      message(result.review ? "驗證碼已自動填入，建議核對圖片" : "驗證碼已自動填入",
        result.review ? "review" : "filled", result.reasons.join("；"));
    } catch (error) {
      if (ticket === generation && permitted())
        message("無法自動辨識，請手動輸入驗證碼", "error", error.message);
    }
  }
  function schedule() {
    if (!permitted()) return;
    const ticket = ++generation;
    clearTimeout(timer);
    timer = setTimeout(() => process(ticket), 35);
  }
  function failed() {
    ++generation;
    clearTimeout(timer);
    message("驗證碼圖片載入失敗，請重新整理圖片", "error");
  }
  function bind() {
    if (!permitted()) { status?.remove(); return; }
    const form = document.getElementById("form-login");
    const nextImage = form?.querySelector("img#imgCode");
    const nextInput = form?.querySelector("input#inputCaptcha[name='Code']");
    if (nextImage === image && nextInput === input) return;
    ++generation;
    clearTimeout(timer);
    image?.removeEventListener("load", schedule);
    image?.removeEventListener("error", failed);
    input?.removeEventListener("input", edited);
    status?.remove();
    image = nextImage; input = nextInput; lastKey = ""; edits = 0;
    if (!image || !input) return;
    image.addEventListener("load", schedule);
    image.addEventListener("error", failed);
    input.addEventListener("input", edited);
    schedule();
  }
  new MutationObserver(records => {
    bind();
    if (records.some(record => record.type === "attributes" && record.target === image)) schedule();
  }).observe(document.documentElement, {subtree: true, childList: true,
    attributes: true, attributeFilter: ["src", "srcset"]});
  window.addEventListener("pageshow", bind);
  window.addEventListener("popstate", bind);
  bind();
})();
