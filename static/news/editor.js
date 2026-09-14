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

  const guardedForm = document.querySelector("form[data-unsaved-guard]");
  if (guardedForm) {
    let dirty = false;
    let submitting = false;
    const markDirty = () => {
      dirty = true;
    };

    guardedForm.addEventListener("input", markDirty);
    guardedForm.addEventListener("change", markDirty);
    guardedForm.addEventListener("submit", (event) => {
      if (event.submitter?.value !== "preview") submitting = true;
    });
    window.addEventListener("beforeunload", (event) => {
      if (!dirty || submitting) return;
      event.preventDefault();
      event.returnValue = "";
    });
  }

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

  const insertImageMarker = (marker, selection = null) => {
    const { start, end } = selection || activeSelection();
    const before = body.value.slice(0, start);
    const after = body.value.slice(end);
    const leading = start === 0 || before.endsWith("\n\n") ? "" : before.endsWith("\n") ? "\n" : "\n\n";
    const trailing = end === body.value.length || after.startsWith("\n\n") ? "" : after.startsWith("\n") ? "\n" : "\n\n";
    const replacement = `${leading}${marker}${trailing}`;
    const cursor = start + replacement.length;
    replace(start, end, replacement, cursor, cursor);
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

  const imageDialog = document.querySelector("#image-dialog");
  const imageUploadForm = document.querySelector("#image-upload-form");
  const imageErrors = imageDialog?.querySelector("[data-image-errors]");
  const imagePreview = imageDialog?.querySelector("[data-image-preview]");
  const imageFile = imageUploadForm?.querySelector('input[type="file"]');
  const imageCaption = imageUploadForm?.querySelector(".image-dialog__caption");
  let previewUrl = null;
  let pendingImageSelection = null;

  const fitImageCaption = () => {
    if (!imageCaption) return;
    imageCaption.style.height = "auto";
    imageCaption.style.height = `${Math.ceil(imageCaption.scrollHeight)}px`;
  };

  const openImageDialog = () => {
    if (!imageDialog) return;
    if (document.activeElement === body) rememberSelection();
    pendingImageSelection = { ...savedSelection };
    if (typeof imageDialog.showModal === "function") imageDialog.showModal();
    else imageDialog.setAttribute("open", "");
    requestAnimationFrame(fitImageCaption);
  };

  const closeImageDialog = () => {
    if (!imageDialog) return;
    if (typeof imageDialog.close === "function") imageDialog.close();
    else imageDialog.removeAttribute("open");
    pendingImageSelection = null;
  };

  const clearPreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    if (imagePreview) {
      imagePreview.removeAttribute("src");
      imagePreview.hidden = true;
    }
  };

  toolbar.addEventListener("pointerdown", (event) => {
    const button = event.target.closest("[data-md-command], [data-image-open]");
    if (!button) return;
    rememberSelection();
    event.preventDefault();
  });

  toolbar.addEventListener("click", (event) => {
    const imageButton = event.target.closest("[data-image-open]");
    if (imageButton) {
      event.preventDefault();
      openImageDialog();
      return;
    }

    const button = event.target.closest("[data-md-command]");
    if (!button) return;
    event.preventDefault();
    run(button.dataset.mdCommand);
  });

  document.querySelectorAll("[data-image-marker]").forEach((button) => {
    button.addEventListener("pointerdown", () => {
      if (document.activeElement === body) rememberSelection();
    });
    button.addEventListener("click", () => insertImageMarker(button.dataset.imageMarker));
  });

  imageDialog?.querySelectorAll("[data-image-close]").forEach((button) => {
    button.addEventListener("click", () => closeImageDialog());
  });

  imageDialog?.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeImageDialog();
  });

  imageCaption?.addEventListener("input", fitImageCaption);

  imageFile?.addEventListener("change", () => {
    clearPreview();
    const file = imageFile.files?.[0];
    if (!file || !imagePreview) return;
    previewUrl = URL.createObjectURL(file);
    imagePreview.src = previewUrl;
    imagePreview.hidden = false;
  });

  imageUploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (imageErrors) {
      imageErrors.hidden = true;
      imageErrors.textContent = "";
    }

    const submit = imageUploadForm.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;

    try {
      const response = await fetch(imageUploadForm.dataset.uploadUrl, {
        method: "POST",
        body: new FormData(imageUploadForm),
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const payload = await response.json();

      if (!response.ok) {
        const messages = Object.values(payload.errors || {})
          .flat()
          .map((item) => item.message)
          .filter(Boolean);
        throw new Error(messages.join(" ") || "Редакция не смогла принять изображение.");
      }

      const insertionPoint = pendingImageSelection ? { ...pendingImageSelection } : activeSelection();
      if (typeof imageDialog.close === "function") imageDialog.close();
      else imageDialog.removeAttribute("open");
      insertImageMarker(payload.marker, insertionPoint);
      pendingImageSelection = null;
      imageUploadForm.reset();
      clearPreview();
      requestAnimationFrame(fitImageCaption);
    } catch (error) {
      if (imageErrors) {
        imageErrors.textContent = error.message;
        imageErrors.hidden = false;
      }
    } finally {
      if (submit) submit.disabled = false;
    }
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
