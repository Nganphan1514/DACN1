import React, { useCallback, useEffect, useState } from "react";
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";
import { COLORS, RADIUS } from "../theme/tokens";
import BottomSheet from "../components/BottomSheet";
import ToastBanner from "../components/ToastBanner";
import SkeletonCard from "../components/SkeletonCard";

export default function AdminOpsScreen() {
  const { hasPermission } = useAuth();
  const canResolve = hasPermission("reports:resolve");

  const [tab, setTab] = useState("schedules"); // 'schedules' | 'reports'
  const [schedules, setSchedules] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  const [resolveSheet, setResolveSheet] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [replyText, setReplyText] = useState("");

  const loadAll = useCallback(async () => {
    setRefreshing(true);
    try {
      const [sRes, rRes] = await Promise.all([
        apiRequest("/api/admin/schedules"),
        apiRequest("/api/admin/reports"),
      ]);
      if (sRes.data?.success && Array.isArray(sRes.data.data)) setSchedules(sRes.data.data);
      if (rRes.data?.success && Array.isArray(rRes.data.data)) setReports(rRes.data.data);
    } catch (e) {
      console.warn("Load admin ops error:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  function openResolve(rep) {
    setSelectedReport(rep);
    setReplyText("Đã xác nhận và xử lý sự cố.");
    setResolveSheet(true);
  }

  async function submitResolve() {
    if (!selectedReport) return;
    const res = await apiRequest(`/api/admin/reports/${selectedReport.id}`, {
      method: "PUT",
      body: JSON.stringify({
        trang_thai: "DA_XU_LY",
        phan_hoi_quan_ly: replyText.trim() || "Đã xử lý.",
      }),
    });
    setResolveSheet(false);
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || (res.data?.success ? "Đã xử lý sự cố." : "Thất bại."),
    });
    if (res.data?.success) loadAll();
  }

  const activeList = tab === "schedules" ? schedules : reports;

  return (
    <View style={styles.container}>
      <ToastBanner toast={toast} onHide={() => setToast(null)} />

      <Text style={styles.header}>Lịch chạy & Sự cố</Text>
      <View style={styles.segmented}>
        <TouchableOpacity
          style={[styles.segBtn, tab === "schedules" && styles.segBtnActive]}
          onPress={() => setTab("schedules")}
        >
          <Text style={[styles.segText, tab === "schedules" && styles.segTextActive]}>
            Lịch đội xe ({schedules.length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.segBtn, tab === "reports" && styles.segBtnActive]}
          onPress={() => setTab("reports")}
        >
          <Text style={[styles.segText, tab === "reports" && styles.segTextActive]}>
            Sự cố ({reports.length})
          </Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={{ gap: 12 }}>
          <SkeletonCard height={115} />
          <SkeletonCard height={115} />
        </View>
      ) : (
        <FlatList
          data={activeList}
          keyExtractor={(item, idx) => `${tab}-${item.id || idx}`}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={loadAll} tintColor={COLORS.primary} />
          }
          contentContainerStyle={{ gap: 12, paddingBottom: 30 }}
          ListEmptyComponent={
            <View style={styles.emptyWrap}>
              <Ionicons name="folder-open-outline" size={44} color={COLORS.textMuted} />
              <Text style={styles.emptyText}>
                {tab === "schedules" ? "Chưa có lịch chạy nào." : "Không có báo cáo sự cố nào."}
              </Text>
            </View>
          }
          renderItem={({ item }) =>
            tab === "schedules" ? (
              <View style={styles.card}>
                <View style={styles.rowBetween}>
                  <Text style={styles.cardTitle}>{item.tuyen_duong || "Chưa rõ tuyến"}</Text>
                  <Text style={styles.badge}>{item.trang_thai}</Text>
                </View>
                <Text style={styles.meta}>
                  Xe: {item.bien_so || "N/A"} • Tài xế: {item.ho_ten || "N/A"}
                </Text>
                <Text style={styles.meta}>Bắt đầu: {item.gio_bat_dau || "N/A"}</Text>
              </View>
            ) : (
              <View style={styles.card}>
                <View style={styles.rowBetween}>
                  <Text style={styles.cardTitle}>{item.tieu_de || "Sự cố"}</Text>
                  <Text style={styles.badge}>{item.trang_thai || "CHO_XU_LY"}</Text>
                </View>
                <Text style={styles.meta}>{item.noi_dung || ""}</Text>
                {item.phan_hoi_quan_ly ? (
                  <Text style={styles.reply}>Phản hồi: {item.phan_hoi_quan_ly}</Text>
                ) : null}
                {canResolve && item.trang_thai !== "DA_XU_LY" && (
                  <TouchableOpacity style={styles.resolveBtn} onPress={() => openResolve(item)}>
                    <Text style={styles.resolveBtnText}>Xử lý & Phản hồi</Text>
                  </TouchableOpacity>
                )}
              </View>
            )
          }
        />
      )}

      <BottomSheet
        visible={resolveSheet}
        title={`Xử lý sự cố #${selectedReport?.id || ""}`}
        subtitle="Nhập phản hồi gửi tới tài xế trước khi đóng phiếu sự cố."
        onClose={() => setResolveSheet(false)}
      >
        <TextInput
          style={styles.input}
          multiline
          placeholder="Nhập phản hồi xử lý..."
          placeholderTextColor={COLORS.textMuted}
          value={replyText}
          onChangeText={setReplyText}
        />
        <TouchableOpacity style={styles.submitBtn} onPress={submitResolve}>
          <Text style={styles.resolveBtnText}>Xác nhận Đã xử lý</Text>
        </TouchableOpacity>
      </BottomSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bgCanvas, paddingHorizontal: 18, paddingTop: 52 },
  header: { color: COLORS.textPrimary, fontSize: 24, fontWeight: "800", marginBottom: 14 },
  segmented: {
    flexDirection: "row",
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.button,
    padding: 4,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    marginBottom: 16,
  },
  segBtn: { flex: 1, paddingVertical: 10, borderRadius: 11, alignItems: "center" },
  segBtnActive: { backgroundColor: COLORS.primary },
  segText: { color: COLORS.textSecondary, fontSize: 12.5, fontWeight: "700" },
  segTextActive: { color: "#fff" },
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 16,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  cardTitle: { color: COLORS.textPrimary, fontSize: 15, fontWeight: "700", flex: 1 },
  badge: { color: COLORS.primary, fontSize: 11, fontWeight: "800" },
  meta: { color: COLORS.textSecondary, fontSize: 13, marginTop: 6, lineHeight: 19 },
  reply: { color: COLORS.safe, fontSize: 12.5, marginTop: 6, fontWeight: "600" },
  resolveBtn: {
    marginTop: 12,
    height: 44,
    borderRadius: 12,
    backgroundColor: COLORS.safeDark,
    justifyContent: "center",
    alignItems: "center",
  },
  resolveBtnText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 10 },
  emptyText: { color: COLORS.textMuted, fontSize: 13.5 },
  input: {
    backgroundColor: COLORS.bgCanvas,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    padding: 14,
    minHeight: 88,
    textAlignVertical: "top",
  },
  submitBtn: {
    marginTop: 14,
    height: 50,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.safe,
    justifyContent: "center",
    alignItems: "center",
  },
});
