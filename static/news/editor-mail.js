document.addEventListener("DOMContentLoaded", () => {
  const mailLink = document.querySelector("[data-editor-mail-link]");
  if (!mailLink) return;

  const statusUrl = mailLink.dataset.statusUrl;
  const inboxUrl = mailLink.href;
  const countNode = document.querySelector("[data-editor-mail-count]");
  const toggle = document.querySelector("[data-mail-notification-toggle]");
  const storageKey = "deareditors.editorMailLastNotifiedId";
  const baseTitle = document.title.replace(/^\(\d+\)\s+/, "");
  let latestKnownId = 0;

  const readStoredId = () => {
    try {
      const value = window.localStorage.getItem(storageKey);
      return value === null ? null : Number(value) || 0;
    } catch (_error) {
      return null;
    }
  };

  const writeStoredId = (value) => {
    try {
      window.localStorage.setItem(storageKey, String(value));
    } catch (_error) {
      // Notifications still work in the current tab if storage is unavailable.
    }
  };

  const renderCount = (count) => {
    if (!countNode) return;
    if (count > 0) {
      countNode.hidden = false;
      countNode.textContent = count > 99 ? "99+" : String(count);
      countNode.setAttribute("aria-label", `Новых писем: ${count}`);
      document.title = `(${count}) ${baseTitle}`;
    } else {
      countNode.hidden = true;
      countNode.textContent = "";
      countNode.removeAttribute("aria-label");
      document.title = baseTitle;
    }
  };

  const syncToggle = () => {
    if (!toggle || !("Notification" in window)) return;
    toggle.hidden = Notification.permission !== "default";
  };

  const showNotification = () => {
    if (!("Notification" in window) || Notification.permission !== "granted") return;

    const notification = new Notification("Dear Editors — новая почта", {
      body: "До дорогой редакции дошло новое письмо.",
      tag: "deareditors-editor-mail",
      renotify: true,
    });

    notification.onclick = () => {
      window.focus();
      window.location.href = inboxUrl;
      notification.close();
    };
  };

  const refreshMailStatus = async ({ allowNotification = true } = {}) => {
    if (!statusUrl) return;

    try {
      const response = await fetch(statusUrl, {
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      const contentType = response.headers.get("content-type") || "";
      if (!response.ok || !contentType.includes("application/json")) return;

      const data = await response.json();
      const count = Number(data.new_count) || 0;
      const latestId = Number(data.latest_id) || 0;
      latestKnownId = latestId;
      renderCount(count);

      const storedId = readStoredId();
      if (storedId === null) {
        writeStoredId(latestId);
        return;
      }

      if (latestId > storedId) {
        // Write first so two open editor tabs are much less likely to duplicate the same alert.
        writeStoredId(latestId);
        if (allowNotification) showNotification();
      }
    } catch (_error) {
      // The editor shell should remain usable when the status check is temporarily unavailable.
    }
  };

  if (toggle && "Notification" in window) {
    toggle.addEventListener("click", async () => {
      const permission = await Notification.requestPermission();
      syncToggle();
      if (permission === "granted") {
        writeStoredId(latestKnownId);
        await refreshMailStatus({ allowNotification: false });
      }
    });
  }

  syncToggle();
  refreshMailStatus();
  window.setInterval(refreshMailStatus, 20000);
  window.addEventListener("focus", refreshMailStatus);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshMailStatus();
  });
});
