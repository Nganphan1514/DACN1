(function () {
    "use strict";
    const $ = (id) => document.getElementById(id);
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const num = (v) => Number(v || 0);
    const canMonitor = document.body.dataset.monitor === "true";
    const canUpdateAlerts = document.body.dataset.updateAlerts === "true";
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const metricFrames = new Map();

    function setMetric(id, value) {
        const element = $(id);
        const target = num(value);
        const from = Number(element.textContent) || 0;
        if (metricFrames.has(id)) {
            window.cancelAnimationFrame(metricFrames.get(id));
            metricFrames.delete(id);
        }
        if (reducedMotion.matches || from === target) {
            element.textContent = target;
            return;
        }

        let start;
        function tick(time) {
            start ??= time;
            const progress = Math.min(1, (time - start) / 400);
            element.textContent = Math.round(from + (target - from) * progress);
            if (progress === 1) metricFrames.delete(id);
            else metricFrames.set(id, window.requestAnimationFrame(tick));
        }
        metricFrames.set(id, window.requestAnimationFrame(tick));
    }
    function imageUrl(value) {
        if (!value) return "";
        try {
            const url = new URL(value, window.location.origin);
            return url.protocol === "http:" || url.protocol === "https:" ? esc(url.href) : "";
        } catch {
            return "";
        }
    }

    // ---- Nhãn trạng thái: [mức, biểu tượng, chữ]. Mức luôn có biểu tượng + chữ, không chỉ màu.
    const STATUS = {
        "BUON NGU": ["danger", "▲", "Buồn ngủ"], "MET MOI": ["caution", "◆", "Mệt mỏi"], "TINH TAO": ["safe", "●", "Tỉnh táo"],
        BUON_NGU: ["danger", "▲", "Buồn ngủ"], NGUOI_LA: ["danger", "▲", "Người lạ"], SAI_XE: ["danger", "▲", "Sai xe"],
        MOI: ["danger", "▲", "Mới"], DA_TIEP_NHAN: ["caution", "◆", "Đã tiếp nhận"], DANG_XU_LY: ["info", "◐", "Đang xử lý"],
        DA_DONG: ["safe", "✓", "Đã đóng"], CANH_BAO_SAI: ["neutral", "✕", "Cảnh báo sai"],
        CHO_XU_LY: ["caution", "◆", "Chờ xử lý"], DA_XU_LY: ["safe", "✓", "Đã xử lý"],
    };
    const meta = (code) => STATUS[code] || ["neutral", "○", code || "Chưa có"];
    const badge = (code) => { const m = meta(code); return `<span class="ds-badge ds-badge--${m[0]}"><span aria-hidden="true">${m[1]}</span>${esc(m[2])}</span>`; };

    // ---- Trạng thái tải / trống / lỗi
    const emptyHtml = (icon, msg) => `<div class="ds-state"><span aria-hidden="true">${icon}</span><p>${esc(msg)}</p></div>`;
    const errorHtml = (what, retry) => `<div class="ds-state ds-state--error" role="alert"><span aria-hidden="true">⚠</span><p>Không tải được ${esc(what)}. Kiểm tra kết nối rồi thử lại.</p><button class="ds-btn ds-btn--sm" type="button" data-retry="${retry}">Thử lại</button></div>`;
    const rowWrap = (inner) => `<tr><td colspan="6">${inner}</td></tr>`;

    async function fetchJson(url, opts) {
        const res = await fetch(url, opts);
        if (!res.ok) { const e = new Error("HTTP " + res.status); e.res = res; throw e; }
        return res.json();
    }

    const loaded = {}; // đã có dữ liệu hợp lệ chưa → giữ dữ liệu cũ khi một lần làm mới lỗi
    function setSync(state, text) {
        document.querySelectorAll("[data-sync]").forEach((el) => {
            el.dataset.state = state;
            el.querySelector("[data-sync-text]").textContent = text;
        });
    }
    const hhmmss = () => new Date().toLocaleTimeString("vi-VN");

    const alertFilter = $("alert_status_filter");
    alertFilter.addEventListener("change", () => loadAlertLifecycle());

    // ---- Tải dữ liệu
    let refreshing = false;
    async function loadDashboard() {
        if (refreshing) return;
        refreshing = true;
        const secondary = canMonitor && Promise.all([loadSnapshots(), loadDevices(), loadAlertLifecycle()]);
        try {
            const json = await fetchJson("/api/admin/dashboard");
            const data = json.data || {};
            $("tong_tai_xe").innerText = num(data.tong_tai_xe);
            $("tong_xe").innerText = num(data.tong_xe);
            setMetric("xe_dang_hoat_dong", data.xe_dang_hoat_dong);
            setMetric("canh_bao_hom_nay", data.canh_bao_hom_nay);
            setMetric("bao_cao_chua_xu_ly", data.bao_cao_chua_xu_ly);
            $("canh_bao_hom_nay").closest(".ds-stat").classList.toggle("is-hot", num(data.canh_bao_hom_nay) > 0);
            renderLive(data.xe_live || []);
            renderAlerts(data.canh_bao_moi || []);
            renderReports(data.bao_cao_moi || []);
            loaded.dash = true;
            setSync("ok", "Cập nhật " + hhmmss());
        } catch (error) {
            console.error("Dashboard error:", error);
            setSync("bad", "Mất đồng bộ");
            if (!loaded.dash) {
                $("xe_live").innerHTML = rowWrap(errorHtml("danh sách xe đang chạy", "dash"));
                $("canh_bao_moi").innerHTML = errorHtml("cảnh báo AI", "dash");
                $("bao_cao_moi").innerHTML = errorHtml("báo cáo tài xế", "dash");
            }
        }
        await secondary;
        refreshing = false;
    }

    async function loadDevices() {
        const box = $("device_status_list");
        try {
            const json = await fetchJson("/api/admin/devices");
            const rows = json.data || [];
            const healthOf = (d) => d.health_status || (d.online ? "ONLINE_HEALTHY" : "OFFLINE");
            const online = rows.filter((d) => healthOf(d) !== "OFFLINE").length;
            setMetric("camera_online", online);
            $("camera_total").innerText = rows.length;
            $("camera_hint").innerText = rows.length === 0 ? "Chưa có thiết bị" : (rows.length - online > 0 ? `${rows.length - online} camera mất kết nối` : "Tất cả đang kết nối");
            loaded.dev = true;

            if (rows.length === 0) { box.innerHTML = emptyHtml("◉", "Chưa có camera nào gửi heartbeat."); return; }
            box.innerHTML = rows.map((d) => {
                const h = healthOf(d);
                const fps = Number(d.fps || 0).toFixed(0);
                const b = h === "ONLINE_HEALTHY" ? `<span class="ds-badge ds-badge--safe">● Ổn định · ${fps} FPS</span>`
                    : h === "ONLINE_DEGRADED" ? `<span class="ds-badge ds-badge--caution">◆ Suy giảm · ${fps} FPS</span>`
                    : `<span class="ds-badge ds-badge--danger">▲ Mất kết nối (${esc(d.seconds_since_seen ?? "?")}s)</span>`;
                const cls = h === "ONLINE_HEALTHY" ? "safe" : h === "ONLINE_DEGRADED" ? "caution" : "danger";
                const outbox = num(d.outbox_pending) > 0 ? ` • Outbox chờ: ${num(d.outbox_pending)}` : "";
                const dlq = num(d.dead_letter_count) > 0 ? ` • Lỗi DLQ: ${num(d.dead_letter_count)}` : "";
                return `<div class="ds-item ds-item--${cls}">
                    <div class="ds-item__main">
                        <strong>${esc(d.device_id)}</strong>
                        <p class="ds-item__meta">Xe ${esc(d.bien_so || "ID " + (d.xe_id || "N/A"))} • Nguồn ${esc(d.nguon_camera || "0")} • Tài xế ${esc(d.ho_ten || "chưa khóa")}${outbox}${dlq}</p>
                        <p class="ds-item__meta">Heartbeat cuối: ${esc(d.lan_cuoi_ket_noi || "")}</p>
                    </div>${b}</div>`;
            }).join("");
        } catch (err) {
            console.error("Load devices error:", err);
            if (!loaded.dev) { box.innerHTML = errorHtml("trạng thái camera", "dev"); $("camera_hint").innerText = "Không tải được"; }
        }
    }

    let alertRequest = 0;
    async function loadAlertLifecycle() {
        const box = $("alert_lifecycle_list");
        const request = ++alertRequest;
        try {
            const q = alertFilter.value ? `?trang_thai=${encodeURIComponent(alertFilter.value)}` : "";
            const json = await fetchJson(`/api/admin/alerts${q}`);
            if (request !== alertRequest) return;
            const rows = json.data || [];
            loaded.life = true;
            if (rows.length === 0) { box.innerHTML = emptyHtml("✓", "Không có sự kiện cảnh báo nào ở trạng thái này."); return; }
            box.innerHTML = rows.map((item) => {
                const open = item.trang_thai !== "DA_DONG" && item.trang_thai !== "CANH_BAO_SAI";
                const id = Number(item.id);
                const st = esc(item.trang_thai);
                const photo = imageUrl(item.image_url);
                const action = (status, label, primary = "") =>
                    `<button type="button" class="ds-btn ds-btn--sm ${primary}" data-alert-id="${id}" data-alert-status="${status}" data-expected-status="${st}">${label}</button>`;
                return `<div class="ds-item ds-item--${meta(item.trang_thai)[0]}">
                    <div class="ds-item__main">
                        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">
                            ${badge(item.loai_canh_bao)} ${badge(item.trang_thai)}
                            <span class="ds-item__meta" style="margin:0">${esc(item.bien_so || "Xe " + (item.xe_id || "N/A"))} • ${esc(item.ho_ten || "Chưa xác định")}</span>
                        </div>
                        <p style="margin:8px 0 0;font-size:14px">${esc(item.noi_dung || "")}</p>
                        <p class="ds-item__meta">Điểm rủi ro ${num(item.risk_score)} • Nguồn ${esc(item.nguon || "edge")} • ${esc(item.thoi_gian_xay_ra || "")}${item.nguoi_xu_ly ? " • Xử lý bởi " + esc(item.nguoi_xu_ly) : ""}${item.ghi_chu_xu_ly ? " • Ghi chú: " + esc(item.ghi_chu_xu_ly) : ""}</p>
                    </div>
                    <div class="ds-item__actions">
                        ${photo ? `<a class="ds-btn ds-btn--sm" href="${photo}" target="_blank" rel="noopener">Xem ảnh</a>` : ""}
                        ${canUpdateAlerts && item.trang_thai === "MOI" ? action("DA_TIEP_NHAN", "Tiếp nhận", "ds-btn--primary") : ""}
                        ${canUpdateAlerts && open ? action("DA_DONG", "Đóng") + action("CANH_BAO_SAI", "Báo sai") : ""}
                    </div></div>`;
            }).join("");
        } catch (err) {
            if (request !== alertRequest) return;
            console.error("Load alert lifecycle error:", err);
            if (!loaded.life) box.innerHTML = errorHtml("danh sách xử lý cảnh báo", "life");
        }
    }

    async function updateAlertStatus(alertId, newStatus, expectedStatus) {
        try {
            const res = await fetch(`/api/admin/alerts/${alertId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ trang_thai: newStatus, expected_status: expectedStatus || null }),
            });
            const result = await res.json().catch(() => ({}));
            const success = res.ok && result.success !== false;
            UI.notify(
                result.message || (success ? "Đã cập nhật trạng thái cảnh báo." : "Không thể cập nhật trạng thái cảnh báo."),
                success ? "success" : "error"
            );
        } catch (err) {
            console.error("Update alert status error:", err);
            UI.notify("Không kết nối được máy chủ.", "error");
        }
        loadAlertLifecycle();
    }

    async function loadSnapshots() {
        const box = $("snapshot_gallery");
        try {
            const json = await fetchJson("/api/admin/snapshots");
            const rows = (json.data || []).filter((item) => imageUrl(item.image_url));
            loaded.snap = true;
            if (rows.length === 0) { box.innerHTML = `<div style="grid-column:1/-1">${emptyHtml("▣", "Chưa có ảnh vi phạm nào được lưu.")}</div>`; return; }
            box.innerHTML = rows.slice(0, 8).map((item) => `
                <a class="ds-photo" href="${imageUrl(item.image_url)}" target="_blank" rel="noopener">
                    <img class="ds-thumb" src="${imageUrl(item.image_url)}" alt="Ảnh ${esc(item.type)} của ${esc(item.driver_name)}" loading="lazy" onerror="this.style.display='none'">
                    <div>
                        <div style="display:flex;justify-content:space-between;gap:8px;align-items:center">${badge(item.type)}<span class="ds-item__meta" style="margin:0">${esc(item.vehicle)}</span></div>
                        <p style="margin:8px 0 0;font-weight:600">${esc(item.driver_name)}</p>
                        <p class="ds-item__meta">${esc(item.note || "")}</p>
                        <p class="ds-item__meta">${esc(item.thoi_gian || "")}</p>
                    </div></a>`).join("");
        } catch (err) {
            console.error("Load snapshots error:", err);
            if (!loaded.snap) box.innerHTML = `<div style="grid-column:1/-1">${errorHtml("thư viện ảnh", "snap")}</div>`;
        }
    }

    function renderLive(rows) {
        const body = $("xe_live");
        if (rows.length === 0) { body.innerHTML = rowWrap(emptyHtml("▣", "Chưa có xe nào đang chạy.")); return; }
        body.innerHTML = rows.map((item) => `
            <tr>
                <td data-label="Biển số" class="ds-num">${esc(item.bien_so || "N/A")}</td>
                <td data-label="Tài xế">${esc(item.ho_ten || "Chưa xác định")}</td>
                <td data-label="Phiên">${esc(item.trang_thai_phien || "N/A")}</td>
                <td data-label="Trạng thái AI">${item.ai_status ? badge(item.ai_status) : '<span class="ds-badge ds-badge--neutral">○ Chưa có</span>'}</td>
                <td data-label="Điểm rủi ro" class="ds-num">${num(item.risk_score)}</td>
                <td data-label="Cập nhật AI" class="ds-muted">${esc(item.thoi_gian || "")}</td>
            </tr>`).join("");
    }

    function renderAlerts(rows) {
        const box = $("canh_bao_moi");
        if (rows.length === 0) { box.innerHTML = emptyHtml("✓", "Chưa có cảnh báo AI."); return; }
        box.innerHTML = rows.map((item) => `
            <div class="ds-item ds-item--${meta(item.trang_thai)[0]}">
                <div class="ds-item__main">
                    <strong>${esc(item.ho_ten || "Chưa xác định")}</strong>
                    <p class="ds-item__meta">${esc(item.bien_so || "N/A")}</p>
                    <p style="margin:8px 0 0;font-size:14px">Điểm rủi ro <b>${num(item.risk_score)}</b> • EAR ${num(item.ear)} • MAR ${num(item.mar)}</p>
                    <p class="ds-item__meta">${esc(item.thoi_gian || "")}</p>
                </div>${badge(item.trang_thai)}</div>`).join("");
    }

    function renderReports(rows) {
        const box = $("bao_cao_moi");
        if (rows.length === 0) { box.innerHTML = emptyHtml("✎", "Chưa có báo cáo từ tài xế."); return; }
        box.innerHTML = rows.map((item) => `
            <div class="ds-item ds-item--${meta(item.trang_thai)[0]}">
                <div class="ds-item__main">
                    <strong>${esc(item.tieu_de || "Không có tiêu đề")}</strong>
                    <p class="ds-item__meta">${esc(item.ho_ten || "Tài xế ID " + item.tai_xe_id)}</p>
                    <p style="margin:8px 0 0;font-size:14px">${esc(item.loai_su_co || "KHAC")} • ${esc(item.bien_so || "N/A")}</p>
                    <p class="ds-item__meta">${esc(item.created_at || "")}</p>
                </div>${badge(item.trang_thai)}</div>`).join("");
    }

    // ---- Toast + realtime SSE
    const toastBox = $("realtimeToastContainer");
    function pushToast(innerHtml, level, title, ms) {
        const t = document.createElement("div");
        t.className = `ds-toast ds-toast--${level || "caution"}`;
        t.innerHTML = (title ? `<strong>${esc(title)}</strong><br>` : "") + innerHtml;
        toastBox.prepend(t);
        setTimeout(() => t.remove(), ms || 8000);
    }
    function showRealtimeAlertToast(ev) {
        const critical = ["BUON_NGU", "NGUOI_LA", "SAI_XE"].includes(ev.type);
        const photo = imageUrl(ev.snapshot_url);
        const img = photo ? `<img class="ds-thumb" style="margin-top:8px;height:120px" src="${photo}" alt="Ảnh chụp cảnh báo">` : "";
        pushToast(`<div style="display:flex;justify-content:space-between;gap:8px;align-items:center">${badge(ev.type)}<span class="ds-item__meta" style="margin:0">${esc(ev.timestamp || "")}</span></div>
            <p style="margin:8px 0 0;font-weight:600">${esc(ev.driver_name || "Chưa xác định")} • ${esc(ev.vehicle_name || "N/A")}</p>
            <p class="ds-item__meta">${esc(ev.message || "")}</p>${img}`, critical ? "danger" : "caution", "", 12000);
    }

    document.addEventListener("click", (e) => {
        const b = e.target.closest("[data-retry]");
        if (!b) return;
        ({ dash: loadDashboard, dev: loadDevices, life: loadAlertLifecycle, snap: loadSnapshots }[b.dataset.retry] || loadDashboard)();
    });

    $("alert_lifecycle_list").addEventListener("click", async (event) => {
        const button = event.target.closest("[data-alert-id]");
        if (!button || button.disabled) return;
        button.disabled = true;
        const { alertId, alertStatus, expectedStatus } = button.dataset;
        await updateAlertStatus(alertId, alertStatus, expectedStatus);
        button.disabled = false;
    });

    loadDashboard();
    setInterval(loadDashboard, 5000);

    if (!canMonitor) return;
    try {
        const sse = new EventSource("/api/admin/events");
        sse.addEventListener("alert", (e) => {
            try { showRealtimeAlertToast(JSON.parse(e.data)); loadDashboard(); }
            catch (err) { console.error("Parse SSE alert error:", err); }
        });
        sse.onerror = () => console.warn("SSE mất kết nối, trình duyệt sẽ tự nối lại.");
    } catch (err) {
        console.warn("SSE khong kha dung:", err);
    }
})();
