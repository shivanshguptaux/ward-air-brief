"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("analyse-form");
  const rawTableInput = document.getElementById("raw_table");
  const charCounter = document.getElementById("char-counter");
  const csvFileInput = document.getElementById("csv_file");
  const fileName = document.getElementById("file-name");
  const loadingState = document.getElementById("loading-state");
  const retryBtn = document.getElementById("retry-btn");
  const resultDoc = document.getElementById("result-document");
  const errorState = document.getElementById("error-state");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /** Keep the character counter in step with the table box. */
  const updateCharCount = () => {
    if (!rawTableInput || !charCounter) return;
    const max = rawTableInput.getAttribute("maxlength") || "2000";
    charCounter.textContent = `${rawTableInput.value.length} / ${max}`;
  };

  if (rawTableInput) {
    rawTableInput.addEventListener("input", updateCharCount);
    updateCharCount();
  }

  /** Set a radio group in the form by name, if the value exists. */
  const setRadio = (name, value) => {
    if (!form || !value) return;
    const option = form.querySelector(`input[name="${name}"][value="${CSS.escape(value)}"]`);
    if (option) option.checked = true;
  };

  // Example chips load a sheet and its matching settings
  document.querySelectorAll("[data-sample-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const sampleId = btn.getAttribute("data-sample-id");
      if (!sampleId || !rawTableInput) return;
      try {
        const resp = await fetch(`/samples/${encodeURIComponent(sampleId)}`);
        if (!resp.ok) return;
        const payload = await resp.json();
        if (!payload.ok || !payload.sample) return;
        rawTableInput.value = payload.sample.raw_table || "";
        setRadio("role", payload.sample.role);
        setRadio("language", payload.sample.language);
        setRadio("reading_level", payload.sample.reading_level);
        updateCharCount();
        rawTableInput.focus();
        rawTableInput.setSelectionRange(0, 0);
        rawTableInput.scrollTop = 0;
      } catch (_err) {
        // The user can still paste a table by hand
      }
    });
  });

  // An uploaded file is read into the table box so the user can check it
  if (csvFileInput && rawTableInput) {
    csvFileInput.addEventListener("change", () => {
      const file = csvFileInput.files && csvFileInput.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result !== "string") return;
        rawTableInput.value = reader.result.slice(0, Number(rawTableInput.maxLength) || 2000);
        updateCharCount();
        if (fileName) fileName.textContent = `Loaded ${file.name}`;
      };
      reader.readAsText(file);
    });
  }

  // Loading state on submit
  if (form && loadingState) {
    form.addEventListener("submit", () => {
      loadingState.hidden = false;
      const analyseBtn = document.getElementById("analyse-btn");
      if (analyseBtn) {
        analyseBtn.disabled = true;
        analyseBtn.textContent = "Analysing…";
      }
    });
  }

  if (retryBtn && form) {
    retryBtn.addEventListener("click", () => form.requestSubmit());
  }

  // After a submission, move focus to what the user needs next: the brief, the error,
  // or the first field to fix. Scroll again once the web font loads, since it can
  // change the height of the content above.
  const focusTarget = resultDoc || errorState || document.querySelector("[aria-invalid='true']");
  if (focusTarget) {
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    const block = focusTarget.matches("[aria-invalid='true']") ? "center" : "start";
    const reveal = () => focusTarget.scrollIntoView({ block });
    focusTarget.focus({ preventScroll: true });
    reveal();
    if (document.fonts) document.fonts.ready.then(reveal);
  }

  // ---------- Tabs (WAI-ARIA tabs pattern, manual activation) ----------
  const tablist = document.querySelector("[role='tablist']");
  const tabs = tablist ? Array.from(tablist.querySelectorAll("[role='tab']")) : [];

  /** Show one tab panel and hide the rest. */
  const activateTab = (tab, { focusTab = false, reveal = true } = {}) => {
    tabs.forEach((t) => {
      const selected = t === tab;
      t.setAttribute("aria-selected", String(selected));
      t.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !selected;
    });
    if (reveal) tab.scrollIntoView({ inline: "nearest", block: "nearest" });
    if (focusTab) tab.focus();
  };

  /** Fade the tab bar's edge while more tabs are hidden off-screen (phones). */
  const updateTabOverflow = () => {
    if (!tablist) return;
    const remaining = tablist.scrollWidth - tablist.clientWidth - tablist.scrollLeft;
    tablist.classList.toggle("has-more", remaining > 1);
  };

  const tabByName = (name) => document.getElementById(`tab-${name}`);

  /** Bring the tab bar into view so the newly opened panel starts at the top. */
  const scrollToTabs = () => {
    if (!tablist) return;
    const rect = tablist.getBoundingClientRect();
    const topbar = document.querySelector(".topbar");
    const offset = topbar ? topbar.offsetHeight : 0;
    if (rect.top < offset || rect.top > window.innerHeight) {
      const y = window.scrollY + tablist.parentElement.getBoundingClientRect().top - offset;
      window.scrollTo({ top: Math.max(0, y), behavior: prefersReducedMotion ? "auto" : "smooth" });
    }
  };

  if (tablist && tabs.length) {
    tablist.hidden = false; // without JS every panel stays visible, one after another
    activateTab(tabs[0], { reveal: false });
    updateTabOverflow();
    tablist.addEventListener("scroll", updateTabOverflow, { passive: true });
    window.addEventListener("resize", updateTabOverflow);

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activateTab(tab));
      tab.addEventListener("keydown", (event) => {
        const keys = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
        if (!(event.key in keys)) return;
        event.preventDefault();
        const next = tabs[(keys[event.key] + tabs.length) % tabs.length];
        activateTab(next, { focusTab: true });
      });
    });

    // "Review data trust" and "Next: ..." links switch tabs
    document.querySelectorAll("[data-tab-link]").forEach((link) => {
      link.addEventListener("click", (event) => {
        const tab = tabByName(link.getAttribute("data-tab-link"));
        if (!tab) return;
        event.preventDefault();
        activateTab(tab, { focusTab: true });
        scrollToTabs();
      });
    });
  }

  // Source chips open Data trust and highlight the cited row
  document.querySelectorAll("[data-row-target]").forEach((chip) => {
    chip.addEventListener("click", (event) => {
      const row = document.getElementById(`data-row-${chip.getAttribute("data-row-target")}`);
      if (!row) return;
      event.preventDefault();
      const trustTab = tabByName("trust");
      if (trustTab) activateTab(trustTab);
      document.querySelectorAll(".is-highlighted").forEach((el) => el.classList.remove("is-highlighted"));
      row.classList.add("is-highlighted");
      row.scrollIntoView({ block: "center", behavior: prefersReducedMotion ? "auto" : "smooth" });
      row.focus({ preventScroll: true });
    });
  });

  // ---------- Staff sign-in for the internal note ----------
  const unlockBtn = document.getElementById("staff-unlock-btn");
  const logoutBtn = document.getElementById("staff-logout-btn");
  const staffGate = document.getElementById("staff-login-gate");
  const noteContent = document.getElementById("internal-note-content");
  const staffControls = document.getElementById("staff-controls-bar");
  const loginError = document.getElementById("staff-login-error");
  const userField = document.getElementById("staff-username");
  const passField = document.getElementById("staff-password");

  /** Switch the note between signed-in and signed-out views. */
  const setStaffView = (isStaff) => {
    if (staffGate) staffGate.hidden = isStaff;
    if (noteContent) noteContent.hidden = !isStaff;
    if (staffControls) staffControls.hidden = !isStaff;
  };

  const showLoginError = (message) => {
    if (!loginError) return;
    loginError.textContent = message;
    loginError.hidden = false;
  };

  if (unlockBtn && userField && passField) {
    unlockBtn.addEventListener("click", async () => {
      const body = new URLSearchParams({ username: userField.value, password: passField.value });
      try {
        const resp = await fetch("/staff-login", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
          },
          body: body.toString(),
        });
        const data = await resp.json();
        if (resp.ok && data.ok) {
          setStaffView(true);
          if (loginError) loginError.hidden = true;
          if (noteContent) {
            noteContent.tabIndex = -1;
            noteContent.focus();
          }
        } else {
          showLoginError(data.error || "That username or password didn't match.");
        }
      } catch (_err) {
        showLoginError("Couldn't check your sign-in right now. Try again.");
      }
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetch("/staff-logout", { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } });
        setStaffView(false);
        if (unlockBtn) unlockBtn.focus();
      } catch (_err) {
        // Stay signed in if the request fails
      }
    });
  }

  // "Print note" prints only the internal note
  const printBtn = document.getElementById("print-note-btn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      document.body.dataset.print = "note";
      window.print();
    });
    window.addEventListener("afterprint", () => {
      delete document.body.dataset.print;
    });
  }
});
