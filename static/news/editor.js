document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("textarea.textarea").forEach((textarea) => {
    const initialHeight = textarea.getBoundingClientRect().height;
    let manualFloor = initialHeight;
    let lastAppliedHeight = initialHeight;
    let lastValueLength = textarea.value.length;
    let applyingHeight = false;

    const markAppliedHeight = () => {
      lastAppliedHeight = textarea.getBoundingClientRect().height;
      requestAnimationFrame(() => {
        applyingHeight = false;
      });
    };

    const applyHeight = (height) => {
      const currentHeight = textarea.getBoundingClientRect().height;
      const nextHeight = Math.max(manualFloor, Math.ceil(height));
      if (Math.abs(currentHeight - nextHeight) <= 1) return;

      applyingHeight = true;
      textarea.style.height = `${nextHeight}px`;
      markAppliedHeight();
    };

    const shrinkToContent = () => {
      const currentHeight = textarea.getBoundingClientRect().height;
      applyingHeight = true;
      textarea.style.height = "auto";
      const nextHeight = Math.max(manualFloor, textarea.scrollHeight);
      textarea.style.height = `${Math.ceil(nextHeight)}px`;
      lastAppliedHeight = textarea.getBoundingClientRect().height;

      if (Math.abs(currentHeight - lastAppliedHeight) <= 1) {
        textarea.style.height = `${Math.ceil(currentHeight)}px`;
        lastAppliedHeight = textarea.getBoundingClientRect().height;
      }

      requestAnimationFrame(() => {
        applyingHeight = false;
      });
    };

    const fitToContent = (event) => {
      const currentHeight = textarea.getBoundingClientRect().height;
      if (!applyingHeight && Math.abs(currentHeight - lastAppliedHeight) > 2) {
        manualFloor = currentHeight;
      }

      const currentValueLength = textarea.value.length;
      const valueShrank = currentValueLength < lastValueLength;
      const deletion = event?.inputType?.startsWith?.("delete") ?? false;
      const contentOverflows = textarea.scrollHeight > textarea.clientHeight + 1;

      if (contentOverflows) {
        applyHeight(textarea.scrollHeight);
      } else if (valueShrank || deletion) {
        shrinkToContent();
      }

      lastValueLength = currentValueLength;
    };

    if (window.ResizeObserver) {
      const observer = new ResizeObserver(() => {
        if (applyingHeight) return;
        const currentHeight = textarea.getBoundingClientRect().height;
        if (Math.abs(currentHeight - lastAppliedHeight) > 2) {
          manualFloor = currentHeight;
          lastAppliedHeight = currentHeight;
        }
      });
      observer.observe(textarea);
    }

    if (textarea.scrollHeight > textarea.clientHeight + 1) {
      applyHeight(textarea.scrollHeight);
    }
    textarea.addEventListener("input", fitToContent);
  });

  const body = document.querySelector("textarea.textarea--body");
  const toolbar = document.querySelector(".editor-toolbar");
  if (!body || !toolbar) return;

  let savedSelection = {
    start: body.selectionStart,
    end: body.selectionEnd,
    direction: body.selectionDirection,
  };

  const rememberSelection = () => {
    savedSelection = {
      start: body.selectionStart,
      end: body.selectionEnd,
      direction: body.selectionDirection,
    };
  };

  const focusBodyWithoutJump = () => {
    if (document.activeElement === body) return;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    try {
      body.focus({ preventScroll: true });
    } catch (_error) {
      body.focus();
      window.scrollTo(scrollX, scrollY);
    }
  };

  const notifyInput = () => body.dispatchEvent(new Event("input", { bubbles: true }));

  const replace = (start, end, text, selectionStart, selectionEnd) => {
    body.setRangeText(text, start, end, "end");
    const nextStart = selectionStart ?? body.selectionStart;
    const nextEnd = selectionEnd ?? nextStart;
    body.setSelectionRange(nextStart, nextEnd);
    savedSelection = { start: nextStart, end: nextEnd, direction: "none" };
    notifyInput();
    focusBodyWithoutJump();
  };

  const activeSelection = () => {
    if (document.activeElement === body) rememberSelection();
    return savedSelection;
  };

  const wrapSelection = (prefix, suffix, placeholder) => {
    const { start, end } = activeSelection();
    const selected = body.value.slice(start, end);
    const content = selected || placeholder;
    const replacement = `${prefix}${content}${suffix}`;
    replace(start, end, replacement, start + prefix.length, start + prefix.length + content.length);
  };

  const makeList = (ordered) => {
    const value = body.value;
    const { start, end } = activeSelection();
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
    const { start, end } = activeSelection();
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

  ["select", "keyup", "pointerup", "input"].forEach((eventName) => {
    body.addEventListener(eventName, rememberSelection);
  });
  document.addEventListener("selectionchange", () => {
    if (document.activeElement === body) rememberSelection();
  });

  toolbar.addEventListener("pointerdown", (event) => {
    const button = event.target.closest("[data-md-command]");
    if (!button) return;
    rememberSelection();
    event.preventDefault();
  });

  toolbar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-md-command]");
    if (!button) return;
    event.preventDefault();
    run(button.dataset.mdCommand);
  });

  body.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    const shortcuts = { b: "bold", i: "italic", k: "link" };
    if (!shortcuts[key]) return;
    event.preventDefault();
    rememberSelection();
    run(shortcuts[key]);
  });
});
