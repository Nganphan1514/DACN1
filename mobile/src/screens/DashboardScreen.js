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
  const [cameraStatus, setCameraStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const isDriver = user?.vai_tro === "tai_xe";
  const isAdmin = !isDriver;
  const driverId = user?.tai_xe_id || user?.id;

  const loadData = useCallback(async () => {
    setRefreshing(true);
    try {
      if (isAdmin) {
        const res = await apiRequest("/api/admin/dashboard");
        if (res.data?.success) setData(res.data.data);
      } else if (driverId) {
        const [dashRes, faceRes, camRes] = await Promise.all([
          apiRequest(`/api/driver/dashboard/${driverId}`),
          apiRequest(`/api/driver/face-status/${driverId}`),
          apiRequest("/api/driver/camera-status"),
        ]);
        if (dashRes.data?.success) setData(dashRes.data.data);
        if (faceRes.data?.success) setFaceStatus(faceRes.data.data);
        if (camRes.data?.success) setCameraStatus(camRes.data.data);
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

  const camHealth = cameraStatus?.health_status || cameraStatus?.status || "UNKNOWN";
  const isCamOffline = camHealth === "OFFLINE";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={loadData} tintColor="#22d3ee" />
      }
    >
      <Text style={styles.title}>
        {isAdmin ? "Tổng quan Quản trị" : "Cabin Tài xế"}
      </Text>
      <Text style={styles.sub}>
        Xin chào, {data?.ho_ten || user?.ten_dang_nhap} ({user?.vai_tro_label || user?.vai_tro})
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
          {/* BANNER TRANG THAI CAMERA (CAM-01, CAM-02) */}
          <View
            style={[
              styles.card,
              isCamOffline ? styles.camOfflineCard : styles.camOnlineCard,
            ]}
          >
            <Text style={styles.cardLabel}>TRẠNG THÁI CAMERA CABIN</Text>
            <Text style={[styles.cardBig, { color: isCamOffline ? "#fca5a5" : "#6ee7b7" }]}>
              {camHealth === "ONLINE_HEALTHY"
                ? "Đang hoạt động tốt"
                : camHealth === "ONLINE_DEGRADED"
                ? "Tín hiệu suy giảm"
                : isCamOffline
                ? "CAMERA MẤT KẾT NỐI"
                : "Chưa có tín hiệu"}
            </Text>
            <Text style={styles.cardSub}>
              {isCamOffline
                ? "Chuyến đi vẫn tiếp tục ghi nhận (không tự kết thúc). Quản lý đã được thông báo; vui lòng kiểm tra thiết bị khi dừng xe an toàn."
                : cameraStatus?.device_id
                ? `Thiết bị: ${cameraStatus.device_id} • FPS: ${Number(cameraStatus.fps || 0).toFixed(1)}`
                : "Chưa ghi nhận thiết bị camera trên xe phụ trách."}
            </Text>
          </View>

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
  statLabel: { color: "#94a3b8", fontSize: 13 },
  statValue: { fontSize: 30, fontWeight: "900", marginTop: 8 },
  stack: { gap: 14 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  camOfflineCard: {
    backgroundColor: "#450a0a",
    borderColor: "#dc2626",
  },
  camOnlineCard: {
    borderColor: "#0f766e",
  },
  cardLabel: { color: "#94a3b8", fontSize: 11, fontWeight: "700", letterSpacing: 1 },
  cardBig: { color: "#fff", fontSize: 22, fontWeight: "800", marginTop: 6 },
  cardSub: { color: "#cbd5e1", fontSize: 13, marginTop: 6, lineHeight: 19 },
  badge: { color: "#22d3ee", fontSize: 13, fontWeight: "700", marginTop: 10 },
});
