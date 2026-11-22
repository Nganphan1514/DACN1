import React, { useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useAuth } from "../context/AuthContext";
import FaceRegisterScreen from "./FaceRegisterScreen";

export default function ProfileScreen() {
  const { user, apiUrl, logout } = useAuth();
  const [showFaceRegister, setShowFaceRegister] = useState(false);

  if (showFaceRegister) {
    return (
      <View style={{ flex: 1, backgroundColor: "#020617" }}>
        <TouchableOpacity
          style={styles.backBar}
          onPress={() => setShowFaceRegister(false)}
        >
          <Text style={styles.backText}>← Quay lại Tài khoản</Text>
        </TouchableOpacity>
        <FaceRegisterScreen />
      </View>
    );
  }

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
        <TouchableOpacity
          style={styles.faceBtn}
          onPress={() => setShowFaceRegister(true)}
        >
          <Text style={styles.logoutText}>ĐĂNG KÝ / CẬP NHẬT KHUÔN MẶT 128D</Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutText}>ĐĂNG XUẤT</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  backBar: { paddingTop: 14, paddingHorizontal: 18, paddingBottom: 4 },
  backText: { color: "#22d3ee", fontWeight: "700", fontSize: 14 },
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
  faceBtn: {
    marginTop: 18,
    backgroundColor: "#0891b2",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  logoutBtn: {
    marginTop: 12,
    backgroundColor: "#dc2626",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  logoutText: { color: "#fff", fontWeight: "800", letterSpacing: 0.6 },
});
