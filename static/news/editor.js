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
});
