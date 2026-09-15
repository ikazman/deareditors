document.addEventListener("DOMContentLoaded", () => {
  const state = document.querySelector("[data-wordly-state]");
  if (!state) return;

  const normalize = (value) => value
    .toUpperCase()
    .replaceAll("Ё", "Е")
    .replace(/[^А-Я]/g, "")
    .slice(0, 5);

  const currentInput = () => state.querySelector("[data-wordly-input]");

  const sync = () => {
    const input = currentInput();
    if (!input) return;

    input.value = normalize(input.value);
    const activeCells = [...state.querySelectorAll("[data-active-cell]")];
    activeCells.forEach((cell, index) => {
      cell.textContent = input.value[index] || "";
    });
  };

  const focusInput = () => {
    const input = currentInput();
    if (input) input.focus();
  };

  const showNetworkError = () => {
    const form = state.querySelector("[data-wordly-form]");
    if (!form) return;

    let errors = form.querySelector(".wordly-errors");
    if (!errors) {
      errors = document.createElement("div");
      errors.className = "wordly-errors";
      form.appendChild(errors);
    }
    errors.textContent = "Не удалось проверить слово. Попробуйте ещё раз.";
  };

  state.addEventListener("input", (event) => {
    if (!event.target.matches("[data-wordly-input]")) return;
    sync();
  });

  state.addEventListener("click", (event) => {
    const input = currentInput();
    if (!input) return;

    const key = event.target.closest("[data-wordly-key]");
    if (key) {
      if (input.value.length < 5) {
        input.value += key.dataset.wordlyKey || "";
        sync();
      }
      focusInput();
      return;
    }

    if (event.target.closest("[data-wordly-backspace]")) {
      input.value = input.value.slice(0, -1);
      sync();
      focusInput();
      return;
    }

    if (event.target.closest("[data-wordly-enter]")) {
      sync();
      const form = state.querySelector("[data-wordly-form]");
      if (input.value.length === 5 && form) form.requestSubmit();
      else focusInput();
    }
  });

  state.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-wordly-form]");
    if (!form) return;

    event.preventDefault();
    sync();

    const input = currentInput();
    if (!input || input.value.length !== 5) {
      focusInput();
      return;
    }

    const submit = form.querySelector("[data-wordly-submit]");
    if (submit) submit.disabled = true;

    try {
      const response = await fetch(form.action || window.location.href, {
        method: "POST",
        body: new FormData(form),
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json",
        },
        credentials: "same-origin",
      });

      const payload = await response.json();
      if (!payload.html) throw new Error("Wordly response does not contain game state");

      state.innerHTML = payload.html;
      sync();
      focusInput();
    } catch (error) {
      if (submit) submit.disabled = false;
      showNetworkError();
      focusInput();
    }
  });

  sync();
});
