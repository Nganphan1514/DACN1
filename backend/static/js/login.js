(function () {
    "use strict";
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const messageEl = document.getElementById("message");
    const loginBtn = document.getElementById("loginBtn");
    const toggleBtn = document.getElementById("togglePassword");
    const form = document.getElementById("loginForm");
    const adminRoles = new Set([
        "admin_he_thong", "quan_tri_cong_ty", "quan_ly", "dieu_phoi_vien", "giam_sat"
    ]);

    // Enter trong form sẽ kích hoạt submit; nút bấm cũng đi qua submit.
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        login();
    });

    toggleBtn.addEventListener("click", function () {
        const show = passwordInput.type === "password";
        passwordInput.type = show ? "text" : "password";
        toggleBtn.textContent = show ? "Ẩn" : "Hiện";
        toggleBtn.setAttribute("aria-pressed", String(show));
    });

    function setLoading(isLoading) {
        loginBtn.disabled = isLoading;
        loginBtn.setAttribute("aria-busy", String(isLoading));
        loginBtn.innerText = isLoading ? "Đang đăng nhập..." : "Đăng nhập";
    }

    async function login() {
        if (loginBtn.disabled) return; // chống gửi trùng
        const ten_dang_nhap = usernameInput.value.trim();
        const mat_khau = passwordInput.value.trim();

        messageEl.innerText = "";

        if (!ten_dang_nhap || !mat_khau) {
            messageEl.innerText = "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.";
            (ten_dang_nhap ? passwordInput : usernameInput).focus();
            return;
        }

        try {
            setLoading(true);

            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ten_dang_nhap, mat_khau })
            });

            const data = await res.json();

            if (!data.success) {
                messageEl.innerText = data.message || "Đăng nhập thất bại.";
                passwordInput.select();
                return;
            }

            localStorage.setItem("token", data.token || "");
            localStorage.setItem("user", JSON.stringify(data.user || {}));

            const user = data.user || {};
            if (adminRoles.has(user.vai_tro)) {
                window.location.assign("/admin/dashboard");
            } else {
                const driverId = user.tai_xe_id || user.id;
                window.location.assign(`/driver/dashboard?tai_xe_id=${encodeURIComponent(driverId)}`);
            }
        } catch (error) {
            messageEl.innerText = "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.";
        } finally {
            setLoading(false);
        }
    }

})();
