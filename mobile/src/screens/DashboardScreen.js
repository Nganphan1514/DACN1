import React, { useCallback, useEffect, useState } from "react";
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

export default function DashboardScreen() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [faceStatus, setFaceStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const isAdmin = user?.vai_tro === "quan_ly";
  const driverId = user?.tai_xe_id || user?.id;

  const loadData = useCallback(async () => {
    setRefreshing(true);
    try {
      if (isAdmin) {
        const res = await apiRequest("/api/admin/dashboard");
        if (res.data?.success) setData(res.data.data);
      } else if (driverId) {
        const [dashRes, faceRes] = await Promise.all([
          apiRequest(`/api/driver/dashboard/${driverId}`),
          apiRequest(`/api/driver/face-status/${driverId}`),
        ]);
        if (dashRes.data?.success) setData(dashRes.data.data);
        if (faceRes.data?.success) setFaceStatus(faceRes.data.data);
      }
    } catch (e) {
      console.warn("Load dashboard error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [isAdmin, driverId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={loadData} tintColor="#22d3ee" />
      }
    >
      <Text style={styles.title}>
        {isAdmin ? "Tổng quan Quản lý" : "Cabin Tài xế"}
      </Text>
      <Text style={styles.sub}>
        Xin chào, {data?.ho_ten || user?.ten_dang_nhap} ({isAdmin ? "Quản lý" : "Tài xế"})
      </Text>

      {isAdmin ? (
        <View style={styles.grid}>
          <StatCard label="Tổng tài xế" value={data?.tong_tai_xe ?? 0} color="#38bdf8" />
          <StatCard label="Tổng số xe" value={data?.tong_xe ?? 0} color="#34d399" />
          <StatCard label="Xe đang chạy" value={data?.xe_dang_hoat_dong ?? 0} color="#a78bfa" />
          <StatCard label="Cảnh báo hôm nay" value={data?.canh_bao_hom_nay ?? 0} color="#fb7185" />
          <StatCard label="Sự cố chờ xử lý" value={data?.bao_cao_chua_xu_ly ?? 0} color="#fbbf24" />
        </View>
      ) : (
        <View style={styles.stack}>
          <View style={styles.card}>
            <Text style={styles.cardLabel}>XE PHỤ TRÁCH</Text>
            <Text style={styles.cardBig}>{data?.bien_so || "Chưa phân công"}</Text>
            <Text style={styles.cardSub}>
              Tuyến hiện tại: {data?.tuyen_duong || "Chưa có lịch chạy"}
            </Text>
            <Text style={styles.badge}>
              Trạng thái: {data?.trang_thai || "Chưa cập nhật"}
            </Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardLabel}>XÁC THỰC KHUÔN MẶT 128D</Text>
            <Text style={styles.cardBig}>
              {faceStatus?.da_dang_ky ? "Đã đăng ký" : "Chưa đăng ký"}
            </Text>
            <Text style={styles.cardSub}>
              {faceStatus?.da_dang_ky
                ? `Số mẫu lưu trên Supabase: ${faceStatus.so_mau}`
                : "Chưa có dữ liệu khuôn mặt. Vui lòng liên hệ Quản lý để đăng ký khuôn mặt 128D."}
            </Text>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function StatCard({ label, value, color }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617" },
  content: { padding: 18, paddingBottom: 40 },
  title: { color: "#fff", fontSize: 26, fontWeight: "800" },
  sub: { color: "#94a3b8", marginTop: 4, marginBottom: 18 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  statCard: {
    width: "47%",
    backgroundColor: "#0f172a",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  statLabel: { color: "#94a3b8", fontSize: 12, fontWeight: "600" },
  statValue: { fontSize: 28, fontWeight: "900", marginTop: 8 },
  stack: { gap: 14 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  cardLabel: { color: "#22d3ee", fontSize: 11, fontWeight: "700", letterSpacing: 1 },
  cardBig: { color: "#fff", fontSize: 22, fontWeight: "800", marginTop: 6 },
  cardSub: { color: "#cbd5e1", marginTop: 6, lineHeight: 20 },
  badge: { color: "#34d399", fontWeight: "700", marginTop: 10 },
});
