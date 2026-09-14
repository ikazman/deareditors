document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector("[data-wordly-input]");
  const activeCells = [...document.querySelectorAll("[data-active-cell]")];
  const keys = [...document.querySelectorAll("[data-wordly-key]")];

  if (!input || !activeCells.length) return;

  const normalize = (value) => value
    .toUpperCase()
    .replaceAll("Ё", "Е")
    .replace(/[^А-Я]/g, "")
    .slice(0, 5);

  const sync = () => {
    input.value = normalize(input.value);
    activeCells.forEach((cell, index) => {
      cell.textContent = input.value[index] || "";
    });
  };

  input.addEventListener("input", sync);
  keys.forEach((key) => {
    key.addEventListener("click", () => {
      if (input.value.length >= 5) return;
      input.value += key.dataset.wordlyKey || "";
      sync();
      input.focus();
    });
  });

  sync();
});
