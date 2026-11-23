import React, { useCallback, useEffect, useState } from "react";
import {
  Modal,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";
import { COLORS, RADIUS, TABULAR_NUMS } from "../theme/tokens";
import BottomSheet from "../components/BottomSheet";
import SlideToConfirm from "../components/SlideToConfirm";
import SkeletonCard from "../components/SkeletonCard";
import ToastBanner from "../components/ToastBanner";
import MonitorScreen from "./MonitorScreen";

export default function DashboardScreen() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [faceStatus, setFaceStatus] = useState(null);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [activeTrip, setActiveTrip] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [priorityAlerts, setPriorityAlerts] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  // Overlays / Sheets cho Tai xe
  const [aiCamModal, setAiCamModal] = useState(false);
  const [notiSheet, setNotiSheet] = useState(false);
  const [sosSheet, setSosSheet] = useState(false);
  const [sosTitle, setSosTitle] = useState("");
  const [sosContent, setSosContent] = useState("");

  const isDriver = user?.vai_tro === "tai_xe";
  const isAdmin = !isDriver;
  const driverId = user?.tai_xe_id || user?.id;

  const loadData = useCallback(async () => {
    setRefreshing(true);
    try {
      if (isAdmin) {
        const [dashRes, prioRes] = await Promise.all([
          apiRequest("/api/admin/dashboard"),
          apiRequest("/api/admin/priority-alerts"),
        ]);
        if (dashRes.data?.success) setData(dashRes.data.data);
        if (prioRes.data?.success) setPriorityAlerts(prioRes.data.data);
      } else if (driverId) {
        const [dashRes, faceRes, camRes, tripRes, notiRes] = await Promise.all([
          apiRequest(`/api/driver/dashboard/${driverId}`),
          apiRequest(`/api/driver/face-status/${driverId}`),
          apiRequest("/api/driver/camera-status"),
          apiRequest("/api/driver/trips"),
          apiRequest(`/api/driver/notifications/${driverId}`),
        ]);
        if (dashRes.data?.success) setData(dashRes.data.data);
        if (faceRes.data?.success) setFaceStatus(faceRes.data.data);
        if (camRes.data?.success) setCameraStatus(camRes.data.data);
        if (tripRes.data?.success && Array.isArray(tripRes.data.data)) {
          setActiveTrip(tripRes.data.data.find((t) => t.trang_thai === "DANG_CHAY") || null);
        }
        if (notiRes.data?.success && Array.isArray(notiRes.data.data)) {
          setNotifications(notiRes.data.data);
        }
      }
    } catch (e) {
      console.warn("Load dashboard error:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [isAdmin, driverId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleCompleteTrip() {
    if (!activeTrip) return;
    const res = await apiRequest(`/api/driver/trips/${activeTrip.id}/complete`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || (res.data?.success ? "Đã kết thúc chuyến an toàn." : "Thất bại."),
    });
    if (res.data?.success) loadData();
  }

  async function handleSubmitSos() {
    if (!sosTitle.trim() || !sosContent.trim()) {
      setToast({ type: "warning", message: "Vui lòng nhập tiêu đề và mô tả sự cố." });
      return;
    }
    const res = await apiRequest("/api/driver/reports", {
      method: "POST",
      body: JSON.stringify({
        tai_xe_id: driverId,
        tieu_de: sosTitle.trim(),
        loai_su_co: "SU_CO_XE",
        noi_dung: sosContent.trim(),
      }),
    });
    setSosSheet(false);
    setSosTitle("");
    setSosContent("");
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || "Đã gửi báo cáo sự cố.",
    });
  }

  const unreadCount = notifications.filter((n) => !n.da_doc).length;
  const camHealth = cameraStatus?.health_status || cameraStatus?.status || "UNKNOWN";
  const isCamOffline = camHealth === "OFFLINE";
  const isCamDegraded = camHealth === "ONLINE_DEGRADED";

  return (
    <View style={styles.root}>
      <ToastBanner toast={toast} onHide={() => setToast(null)} />

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadData} tintColor={COLORS.primary} />
        }
      >
        {/* TOP HEADER */}
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.greeting}>Xin chào, {data?.ho_ten || user?.ten_dang_nhap}</Text>
            <View style={styles.rolePill}>
              <View style={styles.roleDot} />
              <Text style={styles.rolePillText}>
                {user?.vai_tro_label || (isAdmin ? "Quản trị" : "Tài xế")}
              </Text>
            </View>
          </View>

          {isDriver && (
            <View style={styles.headerActions}>
              <TouchableOpacity style={styles.iconCircle} onPress={() => setNotiSheet(true)}>
                <Ionicons name="notifications-outline" size={20} color={COLORS.textPrimary} />
                {unreadCount > 0 && (
                  <View style={styles.badgeDot}>
                    <Text style={styles.badgeDotText}>{unreadCount > 9 ? "9+" : unreadCount}</Text>
                  </View>
                )}
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.iconCircle, { borderColor: "rgba(245,158,11,0.4)", backgroundColor: COLORS.cautionTint }]}
                onPress={() => setSosSheet(true)}
              >
                <Ionicons name="warning-outline" size={20} color={COLORS.caution} />
              </TouchableOpacity>
            </View>
          )}
        </View>

        {loading ? (
          <View style={{ gap: 14 }}>
            <SkeletonCard height={130} />
            <SkeletonCard height={110} />
            <SkeletonCard height={100} />
          </View>
        ) : isAdmin ? (
          /* ================= QUAN TRI V4 ================= */
          <View style={{ gap: 16 }}>
            <View style={styles.bentoGrid}>
              <KpiCard label="Xe đang chạy" value={data?.xe_dang_hoat_dong ?? 0} color={COLORS.safe} icon="car-sport" />
              <KpiCard label="Camera Offline" value={priorityAlerts?.camera_offline ?? 0} color={COLORS.danger} icon="videocam-off" />
              <KpiCard label="AI chờ xác minh" value={priorityAlerts?.su_kien_ai_cho_xac_minh ?? 0} color={COLORS.caution} icon="eye" />
              <KpiCard label="Khiếu nại chờ" value={priorityAlerts?.khieu_nai_cho_xu_ly ?? 0} color="#a78bfa" icon="gavel" />
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionLabel}>TỔNG QUAN ĐỘI XE & ƯU TIÊN</Text>
              <View style={styles.priorityRow}>
                <Text style={styles.priorityName}>Tổng tài xế / Tổng xe</Text>
                <Text style={[styles.priorityVal, TABULAR_NUMS]}>
                  {data?.tong_tai_xe ?? 0} TX • {data?.tong_xe ?? 0} Xe
                </Text>
              </View>
              <View style={styles.priorityRow}>
                <Text style={styles.priorityName}>Lịch chưa xác nhận (24h tới)</Text>
                <Text style={[styles.priorityVal, { color: COLORS.caution }]}>
                  {priorityAlerts?.lich_chua_xac_nhan_sap_chay ?? 0}
                </Text>
              </View>
              <View style={styles.priorityRow}>
                <Text style={styles.priorityName}>Yêu cầu đổi lịch chờ duyệt</Text>
                <Text style={[styles.priorityVal, { color: COLORS.primary }]}>
                  {priorityAlerts?.yeu_cau_doi_lich_cho_duyet ?? 0}
                </Text>
              </View>
              <View style={[styles.priorityRow, { borderBottomWidth: 0 }]}>
                <Text style={styles.priorityName}>Sự cố chờ xử lý</Text>
                <Text style={[styles.priorityVal, { color: COLORS.danger }]}>
                  {data?.bao_cao_chua_xu_ly ?? 0}
                </Text>
              </View>
            </View>
          </View>
        ) : (
          /* ================= CABIN TAI XE V4 ================= */
          <View style={{ gap: 14 }}>
            {/* HERO CARD: CHUYEN DANG CHAY + SLIDE TO COMPLETE */}
            {activeTrip && (
              <View style={styles.heroTripCard}>
                <View style={styles.rowBetween}>
                  <View style={styles.liveTag}>
                    <View style={styles.liveDot} />
                    <Text style={styles.liveTagText}>CHUYẾN ĐANG CHẠY • #{activeTrip.id}</Text>
                  </View>
                  <Text style={[styles.plateMini, TABULAR_NUMS]}>{activeTrip.bien_so || ""}</Text>
                </View>
                <Text style={styles.heroRoute}>{activeTrip.tuyen_duong || "Đang thực hiện"}</Text>
                <Text style={styles.heroMeta}>Bắt đầu: {activeTrip.started_at || ""}</Text>
                <View style={{ marginTop: 14 }}>
                  <SlideToConfirm
                    label="Trượt để Kết thúc chuyến an toàn"
                    color={COLORS.danger}
                    icon="flag"
                    onConfirm={handleCompleteTrip}
                  />
                </View>
              </View>
            )}

            {/* CAMERA CABIN CARD + NUT AI CAM DU PHONG */}
            <View
              style={[
                styles.card,
                isCamOffline
                  ? { backgroundColor: COLORS.dangerTint, borderColor: COLORS.danger }
                  : isCamDegraded
                  ? { backgroundColor: COLORS.cautionTint, borderColor: COLORS.caution }
                  : { borderColor: "rgba(16,185,129,0.35)" },
              ]}
            >
              <View style={styles.rowBetween}>
                <Text style={styles.sectionLabel}>CAMERA CABIN AI</Text>
                <View
                  style={[
                    styles.statusPill,
                    {
                      backgroundColor: isCamOffline
                        ? COLORS.danger
                        : isCamDegraded
                        ? COLORS.caution
                        : COLORS.safe,
                    },
                  ]}
                >
                  <Text style={styles.statusPillText}>
                    {isCamOffline ? "OFFLINE" : isCamDegraded ? "CHẬP CHỜN" : camHealth === "ONLINE_HEALTHY" ? "ONLINE" : "CHƯA KẾT NỐI"}
                  </Text>
                </View>
              </View>

              <Text style={styles.camBody}>
                {isCamOffline
                  ? "Chuyến đi vẫn tiếp tục ghi nhận (không tự kết thúc). Quản lý đã được thông báo; hãy kiểm tra thiết bị khi dừng xe an toàn."
                  : cameraStatus?.device_id
                  ? `Thiết bị ${cameraStatus.device_id} • ${Number(cameraStatus.fps || 0).toFixed(1)} FPS`
                  : "Chưa ghi nhận thiết bị camera trên xe phụ trách."}
              </Text>

              <TouchableOpacity
                style={[styles.aiCamBtn, isCamOffline && { backgroundColor: COLORS.danger }]}
                onPress={() => setAiCamModal(true)}
              >
                <Ionicons name="eye-outline" size={18} color="#fff" />
                <Text style={styles.aiCamBtnText}>Mở AI Cam Dự phòng trên điện thoại</Text>
              </TouchableOpacity>
            </View>

            {/* BENTO 2 COT: XE PHU TRACH & FACE 128D */}
            <View style={styles.bentoGrid}>
              <View style={styles.bentoCard}>
                <Ionicons name="bus-outline" size={22} color={COLORS.primary} />
                <Text style={styles.bentoLabel}>XE PHỤ TRÁCH</Text>
                <Text style={[styles.bentoBig, TABULAR_NUMS]}>{data?.bien_so || "Chưa gán"}</Text>
                <Text style={styles.bentoSub} numberOfLines={2}>
                  {data?.tuyen_duong || "Chưa có tuyến"}
                </Text>
              </View>

              <View style={styles.bentoCard}>
                <Ionicons
                  name="scan-circle-outline"
                  size={22}
                  color={faceStatus?.da_dang_ky ? COLORS.safe : COLORS.caution}
                />
                <Text style={styles.bentoLabel}>FACE ID 128D</Text>
                <Text style={styles.bentoBig}>
                  {faceStatus?.da_dang_ky ? "Đã xác thực" : "Chưa có"}
                </Text>
                <Text style={styles.bentoSub}>
                  {faceStatus?.da_dang_ky
                    ? `${faceStatus.so_mau} mẫu trên Supabase`
                    : "Liên hệ Quản lý đăng ký"}
                </Text>
              </View>
            </View>
          </View>
        )}
      </ScrollView>

      {/* FULL-SCREEN AI CAM DU PHONG */}
      <Modal visible={aiCamModal} animationType="slide" onRequestClose={() => setAiCamModal(false)}>
        <View style={{ flex: 1, backgroundColor: COLORS.bgCanvas }}>
          <TouchableOpacity style={styles.closeCamBtn} onPress={() => setAiCamModal(false)}>
            <Ionicons name="arrow-back" size={20} color="#fff" />
            <Text style={{ color: "#fff", fontWeight: "700", fontSize: 13 }}>Quay lại Cabin</Text>
          </TouchableOpacity>
          <MonitorScreen />
        </View>
      </Modal>

      {/* BOTTOM SHEET THONG BAO */}
      <BottomSheet
        visible={notiSheet}
        title={`Thông báo (${notifications.length})`}
        subtitle="Thông báo phân công lịch, camera, vi phạm & kết quả khiếu nại."
        onClose={() => setNotiSheet(false)}
      >
        {notifications.length === 0 ? (
          <Text style={styles.emptySheet}>Chưa có thông báo nào.</Text>
        ) : (
          <View style={{ gap: 10 }}>
            {notifications.map((n, idx) => (
              <View key={String(n.id || idx)} style={styles.notiItem}>
                <Text style={styles.notiText}>{n.noi_dung}</Text>
                <Text style={styles.notiTime}>{n.thoi_gian || n.created_at || ""}</Text>
              </View>
            ))}
          </View>
        )}
      </BottomSheet>

      {/* BOTTOM SHEET BAO SU CO NHANH */}
      <BottomSheet
        visible={sosSheet}
        title="Báo cáo sự cố nhanh"
        subtitle="Chỉ thao tác khi xe đã dừng hẳn ở vị trí an toàn."
        onClose={() => setSosSheet(false)}
      >
        <TextInput
          style={styles.input}
          placeholder="Tiêu đề sự cố (vd: Hỏng lốp, lỗi camera...)"
          placeholderTextColor={COLORS.textMuted}
          value={sosTitle}
          onChangeText={setSosTitle}
        />
        <TextInput
          style={[styles.input, { minHeight: 86, marginTop: 10 }]}
          placeholder="Mô tả chi tiết tình huống..."
          placeholderTextColor={COLORS.textMuted}
          multiline
          value={sosContent}
          onChangeText={setSosContent}
        />
        <TouchableOpacity style={styles.sosSubmitBtn} onPress={handleSubmitSos}>
          <Text style={styles.aiCamBtnText}>GỬI BÁO CÁO SỰ CỐ</Text>
        </TouchableOpacity>
      </BottomSheet>
    </View>
  );
}

function KpiCard({ label, value, color, icon }) {
  return (
    <View style={styles.bentoCard}>
      <Ionicons name={icon} size={22} color={color} />
      <Text style={[styles.kpiValue, TABULAR_NUMS, { color }]}>{value}</Text>
      <Text style={styles.bentoSub}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: COLORS.bgCanvas },
  container: { flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 52, paddingBottom: 36 },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 18 },
  greeting: { color: COLORS.textPrimary, fontSize: 21, fontWeight: "800", letterSpacing: -0.3 },
  rolePill: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 6,
    marginTop: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
    backgroundColor: COLORS.primaryTint,
  },
  roleDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: COLORS.primary },
  rolePillText: { color: COLORS.primary, fontSize: 11.5, fontWeight: "700" },
  headerActions: { flexDirection: "row", gap: 10 },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.surfaceCard,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    justifyContent: "center",
    alignItems: "center",
  },
  badgeDot: {
    position: "absolute",
    top: 4,
    right: 4,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: COLORS.danger,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 3,
  },
  badgeDotText: { color: "#fff", fontSize: 9, fontWeight: "800" },
  heroTripCard: {
    backgroundColor: COLORS.surfaceElevated,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: "rgba(16,185,129,0.45)",
    padding: 18,
  },
  liveTag: { flexDirection: "row", alignItems: "center", gap: 6 },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.safe },
  liveTagText: { color: COLORS.safe, fontSize: 11.5, fontWeight: "800" },
  plateMini: { color: COLORS.textPrimary, fontSize: 12.5, fontWeight: "800" },
  heroRoute: { color: COLORS.textPrimary, fontSize: 19, fontWeight: "800", marginTop: 8 },
  heroMeta: { color: COLORS.textSecondary, fontSize: 12.5, marginTop: 4 },
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 18,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  sectionLabel: { color: COLORS.textSecondary, fontSize: 11, fontWeight: "800", letterSpacing: 0.8 },
  statusPill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill },
  statusPillText: { color: "#fff", fontSize: 10.5, fontWeight: "800" },
  camBody: { color: COLORS.textPrimary, fontSize: 13.5, marginTop: 10, lineHeight: 20 },
  aiCamBtn: {
    marginTop: 14,
    height: 48,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primaryDark,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  aiCamBtnText: { color: "#fff", fontSize: 13.5, fontWeight: "700" },
  bentoGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  bentoCard: {
    width: "48%",
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 16,
  },
  bentoLabel: { color: COLORS.textMuted, fontSize: 10.5, fontWeight: "800", marginTop: 10, letterSpacing: 0.6 },
  bentoBig: { color: COLORS.textPrimary, fontSize: 18, fontWeight: "800", marginTop: 4 },
  bentoSub: { color: COLORS.textSecondary, fontSize: 12, marginTop: 4, lineHeight: 17 },
  kpiValue: { fontSize: 30, fontWeight: "900", marginTop: 8 },
  priorityRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 11,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderSubtle,
  },
  priorityName: { color: COLORS.textSecondary, fontSize: 13.5 },
  priorityVal: { color: COLORS.textPrimary, fontSize: 14, fontWeight: "800" },
  closeCamBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingTop: 46,
    paddingBottom: 12,
    paddingHorizontal: 18,
    backgroundColor: COLORS.surfaceElevated,
  },
  emptySheet: { color: COLORS.textMuted, textAlign: "center", paddingVertical: 20 },
  notiItem: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: 14,
    padding: 13,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
  },
  notiText: { color: COLORS.textPrimary, fontSize: 13, lineHeight: 19 },
  notiTime: { color: COLORS.textMuted, fontSize: 11, marginTop: 5 },
  input: {
    backgroundColor: COLORS.bgCanvas,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    padding: 14,
    textAlignVertical: "top",
  },
  sosSubmitBtn: {
    marginTop: 14,
    height: 52,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.cautionDark,
    justifyContent: "center",
    alignItems: "center",
  },
});
