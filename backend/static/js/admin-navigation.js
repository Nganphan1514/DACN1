(function () {
    "use strict";
    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("navToggle");
    const close = document.getElementById("navClose");
    const scrim = document.getElementById("scrim");
    const narrow = window.matchMedia("(max-width: 960px)");
    const body = document.body;
    const preference = "sleep-alert:sidebar-collapsed";

    function focusCurrentLink() {
        (sidebar.querySelector('[aria-current="page"]') || sidebar.querySelector("a")).focus();
    }

    function setMobileOpen(open) {
        body.classList.toggle("ds-nav-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        if (open) focusCurrentLink();
        else if (sidebar.contains(document.activeElement)) toggle.focus();
    }

    function setDesktopCollapsed(collapsed, moveFocus = true) {
        body.classList.toggle("ds-nav-collapsed", collapsed);
        toggle.setAttribute("aria-expanded", String(!collapsed));
        if (moveFocus) {
            if (collapsed) toggle.focus();
            else focusCurrentLink();
            try { localStorage.setItem(preference, String(collapsed)); } catch { /* Session-only layout. */ }
        }
    }

    function syncViewport() {
        if (narrow.matches) {
            setMobileOpen(false);
        } else {
            body.classList.remove("ds-nav-open");
            let collapsed = body.classList.contains("ds-nav-collapsed");
            try { collapsed = localStorage.getItem(preference) === "true"; } catch { /* Keep the current layout. */ }
            setDesktopCollapsed(collapsed, false);
        }
    }

    toggle.addEventListener("click", () => {
        if (narrow.matches) setMobileOpen(toggle.getAttribute("aria-expanded") !== "true");
        else setDesktopCollapsed(false);
    });
    close.addEventListener("click", () => {
        if (narrow.matches) setMobileOpen(false);
        else setDesktopCollapsed(true);
    });
    scrim.addEventListener("click", () => setMobileOpen(false));
    sidebar.addEventListener("click", (event) => {
        if (narrow.matches && event.target.closest("a")) setMobileOpen(false);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && narrow.matches && body.classList.contains("ds-nav-open") &&
            !document.querySelector(".sa-dialog[open]")) setMobileOpen(false);
    });
    narrow.addEventListener("change", syncViewport);
    syncViewport();
})();
