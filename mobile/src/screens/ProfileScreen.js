import React, { useState } from "react";
import {
  ScrollView,
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

export default function ProfileScreen() {
  const { user, apiUrl, logout, updateApiUrl } = useAuth();
  const [serverSheet, setServerSheet] = useState(false);
  const [logoutSheet, setLogoutSheet] = useState(false);
  const [newUrl, setNewUrl] = useState(apiUrl);
  const [toast, setToast] = useState(null);

  const initials = (user?.ten_dang_nhap || "U").slice(0, 2).toUpperCase();

  async function handleSaveServer() {
    await updateApiUrl(newUrl);
    setServerSheet(false);
    setToast({ type: "success", message: "Đã cập nhật địa chỉ máy chủ." });
  }

  return (
    <View style={styles.root}>
      <ToastBanner toast={toast} onHide={() => setToast(null)} />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.header}>Cá nhân & Cài đặt</Text>

        {/* PROFILE HERO */}
        <View style={styles.heroCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.username}>{user?.ten_dang_nhap || "Người dùng"}</Text>
            <Text style={styles.roleText}>
              {user?.vai_tro_label || user?.vai_tro}
            </Text>
            <Text style={styles.scopeText}>
              Công ty #{user?.cong_ty_id || 1}
              {user?.chi_nhanh_id ? ` • Chi nhánh #${user.chi_nhanh_id}` : ""}
              {user?.doi_xe_id ? ` • Đội xe #${user.doi_xe_id}` : ""}
            </Text>
          </View>
        </View>

        {/* LIST CARD MENU */}
        <View style={styles.menuCard}>
          <TouchableOpacity
            style={styles.menuItem}
            onPress={() => {
              setNewUrl(apiUrl);
              setServerSheet(true);
            }}
          >
            <View style={[styles.menuIcon, { backgroundColor: COLORS.primaryTint }]}>
              <Ionicons name="server-outline" size={20} color={COLORS.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.menuTitle}>Máy chủ kết nối (Server URL)</Text>
              <Text style={styles.menuSub} numberOfLines={1}>{apiUrl}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={COLORS.textMuted} />
          </TouchableOpacity>

          <View style={styles.divider} />

          <View style={styles.menuItem}>
            <View style={[styles.menuIcon, { backgroundColor: COLORS.safeTint }]}>
              <Ionicons name="shield-checkmark-outline" size={20} color={COLORS.safe} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.menuTitle}>Quyền hạn phiên hiện tại</Text>
              <Text style={styles.menuSub}>
                {Array.isArray(user?.permissions)
                  ? `${user.permissions.length} quyền được cấp từ máy chủ`
                  : "Đồng bộ theo vai trò"}
              </Text>
            </View>
          </View>

          <View style={styles.divider} />

          <View style={styles.menuItem}>
            <View style={[styles.menuIcon, { backgroundColor: "rgba(167,139,250,0.14)" }]}>
              <Ionicons name="information-circle-outline" size={20} color="#a78bfa" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.menuTitle}>Phiên bản ứng dụng</Text>
              <Text style={styles.menuSub}>DACN1 Safety AI — V4.0 Automotive HMI</Text>
            </View>
          </View>
        </View>

        {/* LOGOUT BUTTON */}
        <TouchableOpacity style={styles.logoutBtn} onPress={() => setLogoutSheet(true)}>
          <Ionicons name="log-out-outline" size={20} color={COLORS.danger} />
          <Text style={styles.logoutText}>Đăng xuất tài khoản</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* SHEET SERVER URL */}
      <BottomSheet
        visible={serverSheet}
        title="Đổi địa chỉ Máy chủ"
        subtitle="Nhập IP LAN của máy tính đang chạy Backend API."
        onClose={() => setServerSheet(false)}
      >
        <TextInput
          style={styles.input}
          value={newUrl}
          onChangeText={setNewUrl}
          autoCapitalize="none"
          placeholder="http://192.168.1.13:5000"
          placeholderTextColor={COLORS.textMuted}
        />
        <TouchableOpacity style={styles.primaryBtn} onPress={handleSaveServer}>
          <Text style={styles.primaryBtnText}>LƯU ĐỊA CHỈ MỚI</Text>
        </TouchableOpacity>
      </BottomSheet>

      {/* SHEET XAC NHAN DANG XUAT */}
      <BottomSheet
        visible={logoutSheet}
        title="Xác nhận đăng xuất?"
        subtitle="Bạn sẽ cần đăng nhập lại để tiếp tục nhận thông báo và thao tác chuyến đi."
        onClose={() => setLogoutSheet(false)}
      >
        <View style={{ flexDirection: "row", gap: 10 }}>
          <TouchableOpacity
            style={[styles.primaryBtn, { flex: 1, backgroundColor: COLORS.surfaceCard }]}
            onPress={() => setLogoutSheet(false)}
          >
            <Text style={styles.primaryBtnText}>Ở lại</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.primaryBtn, { flex: 1, backgroundColor: COLORS.danger }]}
            onPress={() => {
              setLogoutSheet(false);
              logout();
            }}
          >
            <Text style={styles.primaryBtnText}>Đăng xuất</Text>
          </TouchableOpacity>
        </View>
      </BottomSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.bgCanvas },
  content: { paddingHorizontal: 18, paddingTop: 52, paddingBottom: 40 },
  header: { color: COLORS.textPrimary, fontSize: 24, fontWeight: "800", marginBottom: 16 },
  heroCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 18,
    marginBottom: 16,
  },
  avatar: {
    width: 58,
    height: 58,
    borderRadius: 20,
    backgroundColor: COLORS.primaryTint,
    borderWidth: 1,
    borderColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: { color: COLORS.primary, fontSize: 20, fontWeight: "800" },
  username: { color: COLORS.textPrimary, fontSize: 18, fontWeight: "800" },
  roleText: { color: COLORS.primary, fontSize: 13, fontWeight: "700", marginTop: 2 },
  scopeText: { color: COLORS.textMuted, fontSize: 11.5, marginTop: 4 },
  menuCard: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  menuItem: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 14 },
  menuIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: "center", alignItems: "center" },
  menuTitle: { color: COLORS.textPrimary, fontSize: 14, fontWeight: "700" },
  menuSub: { color: COLORS.textSecondary, fontSize: 12, marginTop: 2 },
  divider: { height: 1, backgroundColor: COLORS.borderSubtle },
  logoutBtn: {
    marginTop: 20,
    height: 52,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.dangerTint,
    borderWidth: 1,
    borderColor: "rgba(239,68,68,0.35)",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  logoutText: { color: COLORS.danger, fontSize: 14, fontWeight: "800" },
  input: {
    backgroundColor: COLORS.bgCanvas,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    padding: 14,
  },
  primaryBtn: {
    marginTop: 14,
    height: 50,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  primaryBtnText: { color: "#fff", fontSize: 13.5, fontWeight: "700" },
});
