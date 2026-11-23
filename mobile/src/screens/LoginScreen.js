import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import { COLORS, RADIUS } from "../theme/tokens";
import BottomSheet from "../components/BottomSheet";
import ToastBanner from "../components/ToastBanner";

export default function LoginScreen() {
  const { apiUrl, login, updateApiUrl } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [serverUrl, setServerUrl] = useState(apiUrl);
  const [serverSheet, setServerSheet] = useState(false);
  const [pingResult, setPingResult] = useState(null);
  const [pinging, setPinging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    setServerUrl(apiUrl);
  }, [apiUrl]);

  async function handlePing() {
    const cleaned = (serverUrl || "").trim().replace(/\/+$/, "");
    if (!cleaned) return;
    setPinging(true);
    setPingResult(null);
    const t0 = Date.now();
    try {
      const resp = await fetch(`${cleaned}/login`, { method: "GET" });
      const ms = Date.now() - t0;
      setPingResult({ ok: resp.ok || resp.status < 500, text: `Kết nối thành công (${ms} ms)` });
    } catch (e) {
      setPingResult({ ok: false, text: "Không kết nối được tới máy chủ. Kiểm tra IP LAN & run_web.bat." });
    } finally {
      setPinging(false);
    }
  }

  async function handleSaveServer() {
    await updateApiUrl(serverUrl);
    setServerSheet(false);
    setToast({ type: "success", message: `Đã lưu địa chỉ máy chủ: ${serverUrl.trim()}` });
  }

  async function handleLogin() {
    if (!username.trim() || !password.trim()) {
      setToast({ type: "warning", message: "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu." });
      return;
    }
    setSubmitting(true);
    try {
      const res = await login(username.trim(), password, serverUrl);
      if (!res.success) {
        setToast({ type: "error", message: res.message || "Sai tài khoản hoặc mật khẩu." });
      }
    } catch (e) {
      setToast({
        type: "error",
        message: "Không thể kết nối tới máy chủ. Bấm biểu tượng bánh răng góc trên phải để kiểm tra Server URL.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ToastBanner toast={toast} onHide={() => setToast(null)} />

      {/* Top right server config gear */}
      <TouchableOpacity style={styles.gearBtn} onPress={() => setServerSheet(true)}>
        <Ionicons name="settings-outline" size={22} color={COLORS.textSecondary} />
      </TouchableOpacity>

      <View style={styles.brandWrap}>
        <View style={styles.shield}>
          <Ionicons name="shield-checkmark" size={34} color={COLORS.primary} />
        </View>
        <Text style={styles.title}>DACN1 Safety AI</Text>
        <Text style={styles.subtitle}>Hệ thống quản lý đội xe & giám sát an toàn V4.0</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Tên đăng nhập</Text>
        <View style={styles.inputRow}>
          <Ionicons name="person-outline" size={18} color={COLORS.textMuted} />
          <TextInput
            style={styles.input}
            placeholder="Nhập tên đăng nhập"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            value={username}
            onChangeText={setUsername}
          />
        </View>

        <Text style={[styles.label, { marginTop: 14 }]}>Mật khẩu</Text>
        <View style={styles.inputRow}>
          <Ionicons name="lock-closed-outline" size={18} color={COLORS.textMuted} />
          <TextInput
            style={styles.input}
            placeholder="Nhập mật khẩu"
            placeholderTextColor={COLORS.textMuted}
            secureTextEntry={!showPass}
            value={password}
            onChangeText={setPassword}
          />
          <TouchableOpacity onPress={() => setShowPass(!showPass)} style={{ padding: 4 }}>
            <Ionicons
              name={showPass ? "eye-off-outline" : "eye-outline"}
              size={20}
              color={COLORS.textMuted}
            />
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.loginBtn, submitting && { opacity: 0.7 }]}
          onPress={handleLogin}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.loginBtnText}>ĐĂNG NHẬP</Text>
          )}
        </TouchableOpacity>
      </View>

      <Text style={styles.footerHint}>Máy chủ hiện tại: {apiUrl}</Text>

      {/* Bottom Sheet Cau hinh Server URL + Ping */}
      <BottomSheet
        visible={serverSheet}
        title="Cấu hình Máy chủ (Backend API)"
        subtitle="Nhập địa chỉ IP LAN của máy tính đang chạy run_web.bat (cùng mạng Wi-Fi)."
        onClose={() => setServerSheet(false)}
      >
        <Text style={styles.label}>Địa chỉ Server URL</Text>
        <View style={styles.inputRow}>
          <Ionicons name="server-outline" size={18} color={COLORS.textMuted} />
          <TextInput
            style={styles.input}
            placeholder="http://192.168.1.13:5000"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            value={serverUrl}
            onChangeText={setServerUrl}
          />
        </View>

        {pingResult && (
          <View
            style={[
              styles.pingBox,
              {
                backgroundColor: pingResult.ok ? COLORS.safeTint : COLORS.dangerTint,
                borderColor: pingResult.ok ? COLORS.safe : COLORS.danger,
              },
            ]}
          >
            <Ionicons
              name={pingResult.ok ? "checkmark-circle" : "close-circle"}
              size={18}
              color={pingResult.ok ? COLORS.safe : COLORS.danger}
            />
            <Text style={[styles.pingText, { color: pingResult.ok ? COLORS.safe : COLORS.danger }]}>
              {pingResult.text}
            </Text>
          </View>
        )}

        <View style={styles.sheetActions}>
          <TouchableOpacity style={styles.pingBtn} onPress={handlePing} disabled={pinging}>
            <Text style={styles.pingBtnText}>{pinging ? "Đang kiểm tra..." : "Kiểm tra (Ping)"}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.saveBtn} onPress={handleSaveServer}>
            <Text style={styles.saveBtnText}>Lưu cấu hình</Text>
          </TouchableOpacity>
        </View>
      </BottomSheet>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bgCanvas,
    justifyContent: "center",
    paddingHorizontal: 22,
  },
  gearBtn: {
    position: "absolute",
    top: 48,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.surfaceCard,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    justifyContent: "center",
    alignItems: "center",
  },
  brandWrap: { alignItems: "center", marginBottom: 28 },
  shield: {
    width: 68,
    height: 68,
    borderRadius: 22,
    backgroundColor: COLORS.primaryTint,
    borderWidth: 1,
    borderColor: "rgba(14,165,233,0.35)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 14,
  },
  title: { color: COLORS.textPrimary, fontSize: 26, fontWeight: "800", letterSpacing: -0.4 },
  subtitle: { color: COLORS.textSecondary, fontSize: 13, marginTop: 4, textAlign: "center" },
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 20,
  },
  label: { color: COLORS.textSecondary, fontSize: 12, fontWeight: "700", marginBottom: 8 },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: COLORS.bgCanvas,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    paddingHorizontal: 14,
    height: 50,
  },
  input: { flex: 1, color: COLORS.textPrimary, fontSize: 14 },
  loginBtn: {
    marginTop: 22,
    height: 54,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  loginBtnText: { color: "#fff", fontSize: 15, fontWeight: "800", letterSpacing: 0.6 },
  footerHint: { color: COLORS.textMuted, fontSize: 11.5, textAlign: "center", marginTop: 18 },
  pingBox: {
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  pingText: { fontSize: 12.5, fontWeight: "600", flex: 1 },
  sheetActions: { flexDirection: "row", gap: 10, marginTop: 16 },
  pingBtn: {
    flex: 1,
    height: 48,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.surfaceCard,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    justifyContent: "center",
    alignItems: "center",
  },
  pingBtnText: { color: COLORS.textPrimary, fontSize: 13, fontWeight: "700" },
  saveBtn: {
    flex: 1,
    height: 48,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  saveBtnText: { color: "#fff", fontSize: 13, fontWeight: "700" },
});
