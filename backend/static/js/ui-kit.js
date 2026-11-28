/**
 * DACN1 V4.0 — Shared Web UI Kit (Zero alert/confirm/prompt)
 * Primitives: UI.notify, UI.confirmDialog, UI.openDrawer, UI.closeDrawer, UI.confirmAction,
 *             UI.openLightbox, UI.skeletonRows, UI.hasPerm
 */
(function (global) {
  function _ensureContainers() {
    if (!document.getElementById("v4-drawer-root")) {
      const dr = document.createElement("div");
      dr.id = "v4-drawer-root";
      dr.className = "hidden fixed inset-0 z-[9990]";
      document.body.appendChild(dr);
    }
    if (!document.getElementById("v4-lightbox-root")) {
      const lb = document.createElement("div");
      lb.id = "v4-lightbox-root";
      lb.className = "hidden fixed inset-0 z-[9995] bg-black/90 flex flex-col items-center justify-center p-4";
      lb.onclick = () => lb.classList.add("hidden");
      document.body.appendChild(lb);
    }
  }

  function escHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  let dialogQueue = Promise.resolve();

  function showDialog(message, { title, type = "info", confirmLabel } = {}) {
    const open = () => new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.className = "sa-dialog";
      dialog.dataset.type = type;
      dialog.setAttribute("aria-labelledby", "sa-dialog-title");
      dialog.setAttribute("aria-describedby", "sa-dialog-message");
      dialog.innerHTML = `
        <form method="dialog">
          <h2 id="sa-dialog-title"></h2>
          <p id="sa-dialog-message"></p>
          <div class="sa-dialog-actions">
            <button class="sa-dialog-cancel" value="cancel" autofocus>Quay lại</button>
            <button class="sa-dialog-confirm" value="confirm">Đóng</button>
          </div>
        </form>
      `;
      dialog.querySelector("h2").textContent = title || ({
        success: "Thành công", error: "Thao tác thất bại", warning: "Cần kiểm tra"
      }[type] || "Thông báo");
      dialog.querySelector("p").textContent = message || "Không có thông tin chi tiết.";
      const cancel = dialog.querySelector(".sa-dialog-cancel");
      const confirm = dialog.querySelector(".sa-dialog-confirm");
      if (confirmLabel) confirm.textContent = confirmLabel;
      else {
        cancel.hidden = true;
        cancel.removeAttribute("autofocus");
        confirm.autofocus = true;
      }
      dialog.addEventListener("close", () => {
        const accepted = dialog.returnValue === "confirm";
        dialog.remove();
        resolve(accepted);
      }, { once: true });
      document.body.appendChild(dialog);
      dialog.showModal();
    });
    const result = dialogQueue.then(open);
    dialogQueue = result.catch(() => {});
    return result;
  }

  const UI = {
    escHtml,

    hasPerm(user, perm) {
      if (!user) return false;
      if (Array.isArray(user.permissions)) return user.permissions.includes(perm);
      return user.vai_tro === "quan_ly" || user.vai_tro === "quan_tri_cong_ty";
    },

    notify(message, type = "info") {
      return showDialog(message, { type });
    },

    confirmDialog(message, { title, confirmLabel = "Xác nhận" } = {}) {
      return showDialog(message, { title, type: "warning", confirmLabel });
    },

    openDrawer({ title = "", subtitle = "", html = "" }) {
      _ensureContainers();
      const root = document.getElementById("v4-drawer-root");
      root.innerHTML = `
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" onclick="UI.closeDrawer()"></div>
        <aside class="v4-drawer-panel absolute top-0 right-0 h-full w-full max-w-xl bg-[#161f30] border-l border-white/10 shadow-2xl flex flex-col">
          <div class="p-5 border-b border-white/10 flex items-start justify-between gap-3">
            <div>
              <h3 class="text-lg font-bold text-white">${escHtml(title)}</h3>
              ${subtitle ? `<p class="text-xs text-slate-400 mt-1">${escHtml(subtitle)}</p>` : ""}
            </div>
            <button onclick="UI.closeDrawer()" aria-label="Đóng" class="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center">✕</button>
          </div>
          <div class="p-5 overflow-y-auto flex-1">${html}</div>
        </aside>
      `;
      root.classList.remove("hidden");
    },

    closeDrawer() {
      const root = document.getElementById("v4-drawer-root");
      if (root) {
        root.classList.add("hidden");
        root.innerHTML = "";
      }
    },

    confirmAction({
      title,
      subtitle = "",
      warning = "",
      chips = [],
      requireReason = false,
      reasonPlaceholder = "Nhập lý do chi tiết...",
      confirmLabel = "Xác nhận",
      danger = false,
      onConfirm,
    }) {
      const chipsHtml = chips.length
        ? `<div class="flex flex-wrap gap-2 mb-3">${chips
            .map(
              (c) =>
                `<button type="button" class="px-3 py-1.5 rounded-full bg-white/5 hover:bg-sky-500/20 border border-white/10 text-xs text-slate-200" onclick="document.getElementById('v4-confirm-reason').value = this.dataset.val" data-val="${escHtml(c)}">${escHtml(c)}</button>`
            )
            .join("")}</div>`
        : "";

      const html = `
        <div class="space-y-4">
          ${warning ? `<div class="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs leading-relaxed">${escHtml(warning)}</div>` : ""}
          ${chipsHtml}
          ${
            requireReason
              ? `<div>
                   <label class="block text-xs font-semibold text-slate-300 mb-1.5">Lý do / Ghi chú (bắt buộc)</label>
                   <textarea id="v4-confirm-reason" rows="4" placeholder="${escHtml(reasonPlaceholder)}" class="w-full p-3.5 rounded-2xl bg-[#090d16] border border-white/15 text-sm text-white outline-none focus:border-sky-500"></textarea>
                 </div>`
              : ""
          }
          <div class="flex gap-2.5 pt-2">
            <button type="button" onclick="UI.closeDrawer()" class="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-semibold text-slate-200">Hủy</button>
            <button type="button" id="v4-confirm-submit" class="flex-1 py-3 rounded-xl ${
              danger ? "bg-rose-600 hover:bg-rose-500" : "bg-sky-500 hover:bg-sky-400 text-slate-950"
            } text-sm font-bold">${escHtml(confirmLabel)}</button>
          </div>
        </div>
      `;
      UI.openDrawer({ title, subtitle, html });
      const btn = document.getElementById("v4-confirm-submit");
      btn.onclick = async () => {
        const reasonEl = document.getElementById("v4-confirm-reason");
        const reason = reasonEl ? reasonEl.value.trim() : "";
        if (requireReason && reason.length < 3) {
          UI.notify("Vui lòng nhập lý do chi tiết trước khi xác nhận.", "warning");
          return;
        }
        btn.disabled = true;
        btn.textContent = "Đang xử lý...";
        try {
          await onConfirm(reason);
          UI.closeDrawer();
        } catch (err) {
          UI.notify(err?.message || "Thao tác thất bại.", "error");
          btn.disabled = false;
          btn.textContent = confirmLabel;
        }
      };
    },

    openLightbox(imgUrl, caption = "") {
      _ensureContainers();
      const lb = document.getElementById("v4-lightbox-root");
      lb.innerHTML = `
        <img src="${escHtml(imgUrl)}" class="max-h-[82vh] max-w-[94vw] rounded-2xl border border-white/15 shadow-2xl object-contain" />
        ${caption ? `<p class="text-xs text-slate-300 mt-3">${escHtml(caption)}</p>` : ""}
        <p class="text-[11px] text-slate-500 mt-1">Nhấn ra ngoài hoặc phím ESC để đóng</p>
      `;
      lb.classList.remove("hidden");
    },

    skeletonRows(count = 3) {
      return Array.from({ length: count })
        .map(() => `<div class="v4-skeleton h-20 w-full mb-3"></div>`)
        .join("");
    },
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.querySelector(".sa-dialog[open]")) {
      UI.closeDrawer();
      const lb = document.getElementById("v4-lightbox-root");
      if (lb) lb.classList.add("hidden");
    }
  });

  global.UI = UI;
})(window);
