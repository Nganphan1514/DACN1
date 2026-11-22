import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";

export default function ProfileScreen() {
  const { user, apiUrl, logout } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Tài khoản</Text>

      <View style={styles.card}>
        <Text style={styles.label}>TÊN ĐĂNG NHẬP</Text>
        <Text style={styles.value}>{user?.ten_dang_nhap || "N/A"}</Text>

        <Text style={styles.label}>VAI TRÒ</Text>
        <Text style={styles.value}>
          {user?.vai_tro === "quan_ly" ? "Quản lý đội xe" : "Tài xế"}
        </Text>

        {user?.tai_xe_id ? (
          <>
            <Text style={styles.label}>MÃ TÀI XẾ</Text>
            <Text style={styles.value}>#{user.tai_xe_id}</Text>
          </>
        ) : null}

        <Text style={styles.label}>MÁY CHỦ BACKEND</Text>
        <Text style={styles.value}>{apiUrl}</Text>
      </View>

      {user?.vai_tro === "tai_xe" && (
        <View style={styles.noteBox}>
          <Text style={styles.noteText}>
            Lưu ý: Việc đăng ký hoặc cập nhật lại khuôn mặt 128D chỉ do Quản lý thực hiện để đảm bảo an toàn xác thực.
          </Text>
        </View>
      )}

      <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutText}>ĐĂNG XUẤT</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  header: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: 16 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  label: { color: "#64748b", fontSize: 11, fontWeight: "700", marginTop: 12 },
  value: { color: "#f8fafc", fontSize: 16, fontWeight: "700", marginTop: 4 },
  noteBox: {
    marginTop: 16,
    backgroundColor: "#0f172a",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  noteText: { color: "#94a3b8", fontSize: 12, lineHeight: 18 },
  logoutBtn: {
    marginTop: 18,
    backgroundColor: "#dc2626",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  logoutText: { color: "#fff", fontWeight: "800", letterSpacing: 0.6 },
});
