(() => {
    const form = document.querySelector("[data-menu-form]");
    if (!form || form.dataset.editable !== "1") return;

    const rows = Array.from(form.querySelectorAll("[data-menu-item]"));
    const submit = form.querySelector("[data-menu-submit]");
    const total = form.querySelector("[data-menu-total]");
    const footnote = document.querySelector("[data-menu-footnote]");
    let hasSaved = form.dataset.hasSelected === "1";

    const formatRubles = (value) => {
        const number = Number(value);
        if (!Number.isFinite(number)) return "0";
        return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(".", ",");
    };

    const syncRowState = (row) => {
        const input = row.querySelector("input[type='checkbox']");
        row.classList.toggle("menu-item--selected", input.checked);
    };

    const syncTotal = () => {
        const sum = rows.reduce((result, row) => {
            const input = row.querySelector("input[type='checkbox']");
            return input.checked ? result + Number(row.dataset.price) : result;
        }, 0);
        total.querySelector("strong").textContent = `${formatRubles(sum)} ₽`;
        total.hidden = !(hasSaved || sum > 0);
    };

    rows.forEach((row) => {
        row.querySelector("input[type='checkbox']").addEventListener("change", () => {
            syncRowState(row);
            syncTotal();
            submit.textContent = "Сохранить выбор";
        });
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        submit.disabled = true;
        submit.textContent = "Сохраняем…";

        try {
            const response = await fetch(form.action || window.location.href, {
                method: "POST",
                body: new FormData(form),
                headers: {"X-Requested-With": "XMLHttpRequest"},
                credentials: "same-origin",
            });
            const payload = await response.json();
            if (!response.ok || !payload.ok) {
                throw new Error(payload.error || "Не удалось сохранить выбор.");
            }

            hasSaved = true;
            form.dataset.hasSelected = "1";
            const resultById = new Map(payload.items.map((item) => [String(item.id), item]));

            rows.forEach((row) => {
                const result = resultById.get(row.dataset.itemId);
                if (!result) return;
                const count = row.querySelector("[data-menu-count]");
                if (result.choice_count > 0) {
                    row.classList.add("menu-item--has-result");
                    row.style.setProperty("--share", `${result.choice_percent}%`);
                    count.hidden = false;
                    count.textContent = result.choice_count;
                    count.setAttribute("aria-label", `${result.choice_count} человек выбрали эту позицию`);
                } else {
                    row.classList.remove("menu-item--has-result");
                    row.style.removeProperty("--share");
                    count.hidden = true;
                    count.textContent = "";
                }
            });

            total.hidden = false;
            total.querySelector("strong").textContent = `${formatRubles(payload.selected_total)} ₽`;
            footnote.textContent = "Выбор сохранен. Можно передумать до конца дня.";
            submit.textContent = "Сохранено";
        } catch (error) {
            footnote.textContent = error.message || "Не удалось сохранить выбор.";
            submit.textContent = "Сохранить выбор";
        } finally {
            submit.disabled = false;
        }
    });

    syncTotal();
})();
