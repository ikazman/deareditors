document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form[data-unsaved-guard]");
  if (!form) return;

  const previewButtons = Array.from(
    form.querySelectorAll('button[name="action"][value="preview"]'),
  );
  if (!previewButtons.length) return;

  const dialog = document.createElement("dialog");
  dialog.className = "draft-preview-dialog";
  dialog.setAttribute("aria-label", "Предпросмотр заметки");

  const bar = document.createElement("div");
  bar.className = "draft-preview-dialog__bar";

  const label = document.createElement("strong");
  label.textContent = "Предпросмотр";

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "draft-preview-dialog__close";
  closeButton.textContent = "Закрыть";

  const frame = document.createElement("iframe");
  frame.className = "draft-preview-dialog__frame";
  frame.title = "Предпросмотр заметки";

  bar.append(label, closeButton);
  dialog.append(bar, frame);
  document.body.append(dialog);

  const closePreview = () => {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  const openPreview = () => {
    if (dialog.open) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  const loadingDocument = (message) => `<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;padding:2rem;font:16px/1.5 Georgia,serif;background:#f3f0e9;color:#14110e}</style></head>
<body>${message}</body></html>`;

  const wireInnerCloseButton = () => {
    try {
      const innerClose = frame.contentDocument?.querySelector(".article-back--button");
      if (!innerClose) return;
      innerClose.removeAttribute("onclick");
      innerClose.addEventListener("click", (event) => {
        event.preventDefault();
        closePreview();
      });
    } catch (_error) {
      // srcdoc is same-origin in supported browsers; outer close remains available otherwise.
    }
  };

  closeButton.addEventListener("click", closePreview);
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closePreview();
  });
  frame.addEventListener("load", wireInnerCloseButton);

  previewButtons.forEach((button) => {
    button.textContent = "Посмотреть черновик";
  });

  form.addEventListener("submit", async (event) => {
    if (event.submitter?.value !== "preview") return;

    event.preventDefault();
    openPreview();
    frame.srcdoc = loadingDocument("Редакция готовит предпросмотр…");

    const data = new FormData(form);
    if (event.submitter?.name) data.set(event.submitter.name, event.submitter.value);

    try {
      const response = await fetch(form.action || window.location.href, {
        method: (form.method || "post").toUpperCase(),
        body: data,
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      frame.srcdoc = await response.text();
    } catch (_error) {
      frame.srcdoc = loadingDocument(
        "Предпросмотр не загрузился. Текст в редакторе сохранен; закройте окно и попробуйте еще раз.",
      );
    }
  });
});
