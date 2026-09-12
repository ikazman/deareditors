document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("textarea.textarea").forEach((textarea) => {
    const growIfNeeded = () => {
      if (textarea.scrollHeight > textarea.clientHeight + 1) {
        textarea.style.height = `${textarea.scrollHeight}px`;
      }
    };

    growIfNeeded();
    textarea.addEventListener("input", growIfNeeded);
  });

  const body = document.querySelector("textarea.textarea--body");
  const toolbar = document.querySelector(".editor-toolbar");
  if (!body || !toolbar) return;

  const notifyInput = () => body.dispatchEvent(new Event("input", { bubbles: true }));

  const replace = (start, end, text, selectionStart, selectionEnd) => {
    body.setRangeText(text, start, end, "end");
    body.focus();
    if (selectionStart !== undefined) {
      body.setSelectionRange(selectionStart, selectionEnd ?? selectionStart);
    }
    notifyInput();
  };

  const wrapSelection = (prefix, suffix, placeholder) => {
    const start = body.selectionStart;
    const end = body.selectionEnd;
    const selected = body.value.slice(start, end);
    const content = selected || placeholder;
    const replacement = `${prefix}${content}${suffix}`;
    replace(start, end, replacement, start + prefix.length, start + prefix.length + content.length);
  };

  const makeList = (ordered) => {
    const value = body.value;
    const start = body.selectionStart;
    const end = body.selectionEnd;
    const lineStart = value.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
    const nextBreak = value.indexOf("\n", end);
    const lineEnd = nextBreak === -1 ? value.length : nextBreak;
    const block = value.slice(lineStart, lineEnd);
    const lines = block.split("\n");
    const replacement = lines
      .map((line, index) => `${ordered ? `${index + 1}.` : "-"} ${line}`)
      .join("\n");
    replace(lineStart, lineEnd, replacement, lineStart, lineStart + replacement.length);
  };

  const makeLink = () => {
    const start = body.selectionStart;
    const end = body.selectionEnd;
    const selected = body.value.slice(start, end);
    const url = window.prompt("Адрес ссылки", "https://");
    if (!url) return;
    const label = selected || url;
    const replacement = `[${label}](${url})`;
    replace(start, end, replacement, start + 1, start + 1 + label.length);
  };

  const run = (command) => {
    if (command === "bold") wrapSelection("**", "**", "жирный текст");
    if (command === "italic") wrapSelection("*", "*", "курсив");
    if (command === "bullet") makeList(false);
    if (command === "numbered") makeList(true);
    if (command === "link") makeLink();
  };

  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-md-command]");
    if (!button) return;
    run(button.dataset.mdCommand);
  });

  body.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    const shortcuts = { b: "bold", i: "italic", k: "link" };
    if (!shortcuts[key]) return;
    event.preventDefault();
    run(shortcuts[key]);
  });
});
