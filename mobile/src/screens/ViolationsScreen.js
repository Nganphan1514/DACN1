import React, { useCallback, useEffect, useState } from "react";
import {
  FlatList,
  Image,
  Modal,
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
import { COLORS, RADIUS, TABULAR_NUMS } from "../theme/tokens";
import BottomSheet from "../components/BottomSheet";
import SkeletonCard from "../components/SkeletonCard";
import ToastBanner from "../components/ToastBanner";

export default function ViolationsScreen() {
  const { user } = useAuth();
  const [tab, setTab] = useState("violations"); // 'violations' | 'appeals' | 'ai'
  const [violations, setViolations] = useState([]);
  const [aiEvents, setAiEvents] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  const [appealSheet, setAppealSheet] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState(null);
  const [explanation, setExplanation] = useState("");
  const [zoomImageUrl, setZoomImageUrl] = useState(null);

  const driverId = user?.tai_xe_id || user?.id;

  const loadAll = useCallback(async () => {
    if (!driverId) return;
    setRefreshing(true);
    try {
      const [vpRes, aiRes, apRes] = await Promise.all([
        apiRequest("/api/driver/violations"),
        apiRequest("/api/driver/ai-events"),
        apiRequest("/api/driver/appeals"),
      ]);
      if (vpRes.data?.success && Array.isArray(vpRes.data.data)) setViolations(vpRes.data.data);
      if (aiRes.data?.success && Array.isArray(aiRes.data.data)) setAiEvents(aiRes.data.data);
      if (apRes.data?.success && Array.isArray(apRes.data.data)) setAppeals(apRes.data.data);
    } catch (e) {
      console.warn("Load violations/appeals error:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [driverId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  function openAppealSheet(vp) {
    setSelectedViolation(vp);
    setExplanation("");
    setAppealSheet(true);
  }

  async function submitAppeal() {
    if (explanation.trim().length < 5) {
      setToast({ type: "warning", message: "Vui lòng nhập nội dung giải trình (tối thiểu 5 ký tự)." });
      return;
    }
    const res = await apiRequest(`/api/driver/violations/${selectedViolation.id}/appeals`, {
      method: "POST",
      body: JSON.stringify({
        noi_dung_giai_trinh: explanation.trim(),
        minh_chung_urls: [],
      }),
    });
    setAppealSheet(false);
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || (res.data?.success ? "Đã gửi khiếu nại." : "Thất bại."),
    });
    if (res.data?.success) {
      setTab("appeals");
      loadAll();
    }
  }

  const activeData = tab === "violations" ? violations : tab === "appeals" ? appeals : aiEvents;

  return (
    <View style={styles.container}>
      <ToastBanner toast={toast} onHide={() => setToast(null)} />

      <Text style={styles.header}>An toàn & Khiếu nại</Text>

      {/* SEGMENTED CONTROL */}
      <View style={styles.segmented}>
        {[
          { k: "violations", l: `Vi phạm (${violations.length})` },
          { k: "appeals", l: `Khiếu nại (${appeals.length})` },
          { k: "ai", l: `AI (${aiEvents.length})` },
        ].map((t) => (
          <TouchableOpacity
            key={t.k}
            style={[styles.segBtn, tab === t.k && styles.segBtnActive]}
            onPress={() => setTab(t.k)}
          >
            <Text style={[styles.segText, tab === t.k && { color: "#fff" }]}>{t.l}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === "ai" && (
        <View style={styles.infoBanner}>
          <Ionicons name="information-circle" size={18} color={COLORS.primary} />
          <Text style={styles.infoBannerText}>
            Các ghi nhận tự động từ AI chỉ hỗ trợ an toàn — chưa được tính là vi phạm chính thức.
          </Text>
        </View>
      )}

      {loading ? (
        <View style={{ gap: 12 }}>
          <SkeletonCard height={120} />
          <SkeletonCard height={120} />
        </View>
      ) : (
        <FlatList
          data={activeData}
          keyExtractor={(item, idx) => `${tab}-${item.id || idx}`}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={loadAll} tintColor={COLORS.primary} />
          }
          contentContainerStyle={{ gap: 12, paddingBottom: 32 }}
          ListEmptyComponent={
            <View style={styles.emptyWrap}>
              <Ionicons name="shield-checkmark-outline" size={46} color={COLORS.safe} />
              <Text style={styles.emptyTitle}>
                {tab === "violations"
                  ? "Tuyệt vời! Chưa có vi phạm nào."
                  : tab === "appeals"
                  ? "Chưa có phiếu khiếu nại nào."
                  : "Chưa có cảnh báo AI nào."}
              </Text>
            </View>
          }
          renderItem={({ item }) => {
            if (tab === "violations") {
              const canAppeal =
                item.can_appeal !== undefined
                  ? Boolean(item.can_appeal)
                  : ["HIEU_LUC", "GIU_NGUYEN"].includes(item.trang_thai);
              return (
                <View style={styles.card}>
                  <View style={styles.rowBetween}>
                    <Text style={styles.cardTitle}>{item.loai_vi_pham} • #{item.id}</Text>
                    <View style={styles.badge}>
                      <Text style={styles.badgeText}>{item.trang_thai}</Text>
                    </View>
                  </View>

                  <View style={styles.quoteBox}>
                    <Text style={styles.quoteLabel}>Nhận xét của Quản lý:</Text>
                    <Text style={styles.quoteText}>{item.ly_do_xac_minh}</Text>
                  </View>

                  {item.image_url ? (
                    <TouchableOpacity onPress={() => setZoomImageUrl(item.image_url)}>
                      <Image source={{ uri: item.image_url }} style={styles.thumb} />
                      <Text style={styles.zoomHint}>Chạm vào ảnh để phóng to bằng chứng</Text>
                    </TouchableOpacity>
                  ) : null}

                  <Text style={styles.time}>Xác minh lúc: {item.xac_minh_at || ""}</Text>

                  {canAppeal ? (
                    <TouchableOpacity style={styles.appealBtn} onPress={() => openAppealSheet(item)}>
                      <Ionicons name="chatbox-ellipses-outline" size={16} color="#fff" />
                      <Text style={styles.btnText}>Gửi giải trình / Khiếu nại</Text>
                    </TouchableOpacity>
                  ) : item.appeal_block_reason ? (
                    <Text style={styles.blockHint}>{item.appeal_block_reason}</Text>
                  ) : null}
                </View>
              );
            }

            if (tab === "appeals") {
              const st = item.trang_thai || "SUBMITTED";
              const step2 = ["UNDER_REVIEW", "NEED_MORE_INFO", "ACCEPTED", "REJECTED", "CLOSED"].includes(st);
              const step3 = ["ACCEPTED", "REJECTED", "CLOSED"].includes(st);
              return (
                <View style={styles.card}>
                  <View style={styles.rowBetween}>
                    <Text style={styles.cardTitle}>Khiếu nại #{item.id} (VP #{item.vi_pham_id})</Text>
                    <View style={styles.badge}>
                      <Text style={styles.badgeText}>{st}</Text>
                    </View>
                  </View>

                  {/* TIMELINE 3 MOC */}
                  <View style={styles.timeline}>
                    <TimelineDot label="Đã gửi" active />
                    <View style={styles.tLine} />
                    <TimelineDot label="Xem xét" active={step2} />
                    <View style={styles.tLine} />
                    <TimelineDot label="Kết luận" active={step3} color={st === "ACCEPTED" ? COLORS.safe : COLORS.primary} />
                  </View>

                  <View style={styles.quoteBox}>
                    <Text style={styles.quoteLabel}>🔒 Nội dung giải trình gốc (bất biến):</Text>
                    <Text style={styles.quoteText}>{item.noi_dung_giai_trinh}</Text>
                  </View>

                  {item.ly_do_ket_luan ? (
                    <Text style={[styles.decision, { color: st === "ACCEPTED" ? COLORS.safe : COLORS.caution }]}>
                      Kết luận QL: {item.ly_do_ket_luan}
                    </Text>
                  ) : null}
                </View>
              );
            }

            const risk = Math.min(10, Math.max(0, Number(item.risk_score || 0)));
            return (
              <View style={styles.card}>
                <View style={styles.rowBetween}>
                  <Text style={styles.cardTitle}>{item.loai_canh_bao || "CANH_BAO"}</Text>
                  <Text style={[styles.riskTag, TABULAR_NUMS]}>Risk {risk}/10</Text>
                </View>
                <View style={styles.progressTrack}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${risk * 10}%`,
                        backgroundColor: risk >= 7 ? COLORS.danger : risk >= 4 ? COLORS.caution : COLORS.primary,
                      },
                    ]}
                  />
                </View>
                <Text style={styles.meta}>{item.noi_dung || ""}</Text>
                <Text style={styles.time}>
                  Trạng thái: {item.trang_thai || "PENDING_REVIEW"} • {item.thoi_gian_xay_ra || ""}
                </Text>
              </View>
            );
          }}
        />
      )}

      {/* BOTTOM SHEET GUI KHIEU NAI */}
      <BottomSheet
        visible={appealSheet}
        title={`Gửi khiếu nại Vi phạm #${selectedViolation?.id || ""}`}
        subtitle="🔒 Nội dung giải trình gốc được lưu bất biến trong hệ thống làm căn cứ để Quản lý xem xét."
        onClose={() => setAppealSheet(false)}
      >
        <TextInput
          style={styles.input}
          placeholder="Trình bày rõ bối cảnh và lý do giải trình..."
          placeholderTextColor={COLORS.textMuted}
          multiline
          value={explanation}
          onChangeText={setExplanation}
        />
        <TouchableOpacity style={styles.submitBtn} onPress={submitAppeal}>
          <Text style={styles.btnText}>GỬI KHIẾU NẠI CHÍNH THỨC</Text>
        </TouchableOpacity>
      </BottomSheet>

      {/* LIGHTBOX ZOOM ANH BANG CHUNG */}
      <Modal visible={Boolean(zoomImageUrl)} transparent animationType="fade" onRequestClose={() => setZoomImageUrl(null)}>
        <TouchableOpacity style={styles.lightbox} activeOpacity={1} onPress={() => setZoomImageUrl(null)}>
          {zoomImageUrl && <Image source={{ uri: zoomImageUrl }} style={styles.zoomImg} resizeMode="contain" />}
          <Text style={styles.zoomClose}>Chạm bất kỳ đâu để đóng</Text>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

function TimelineDot({ label, active, color = COLORS.primary }) {
  return (
    <View style={{ alignItems: "center", gap: 4 }}>
      <View style={[styles.tDot, { backgroundColor: active ? color : COLORS.surfaceElevated }]} />
      <Text style={{ color: active ? COLORS.textPrimary : COLORS.textMuted, fontSize: 10, fontWeight: "700" }}>
        {label}
      </Text>
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
    marginBottom: 14,
  },
  segBtn: { flex: 1, paddingVertical: 10, borderRadius: 11, alignItems: "center" },
  segBtnActive: { backgroundColor: COLORS.primary },
  segText: { color: COLORS.textSecondary, fontSize: 11.5, fontWeight: "700" },
  infoBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: COLORS.primaryTint,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
  },
  infoBannerText: { color: COLORS.textPrimary, fontSize: 12, flex: 1, lineHeight: 17 },
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 16,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  cardTitle: { color: COLORS.textPrimary, fontSize: 15, fontWeight: "700", flex: 1 },
  badge: { backgroundColor: COLORS.cautionTint, paddingHorizontal: 10, paddingVertical: 4, borderRadius: RADIUS.pill },
  badgeText: { color: COLORS.caution, fontSize: 10.5, fontWeight: "800" },
  quoteBox: {
    marginTop: 10,
    backgroundColor: COLORS.bgCanvas,
    borderLeftWidth: 3,
    borderLeftColor: COLORS.primary,
    borderRadius: 10,
    padding: 11,
  },
  quoteLabel: { color: COLORS.textMuted, fontSize: 11, fontWeight: "700", marginBottom: 4 },
  quoteText: { color: COLORS.textPrimary, fontSize: 13, lineHeight: 19 },
  thumb: { width: "100%", height: 150, borderRadius: 12, marginTop: 10 },
  zoomHint: { color: COLORS.primary, fontSize: 11, textAlign: "center", marginTop: 4 },
  time: { color: COLORS.textMuted, fontSize: 11.5, marginTop: 8 },
  meta: { color: COLORS.textSecondary, fontSize: 13, marginTop: 8, lineHeight: 18 },
  appealBtn: {
    marginTop: 12,
    height: 46,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.cautionDark,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  blockHint: { color: COLORS.textMuted, fontSize: 12, marginTop: 8, fontStyle: "italic" },
  btnText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  timeline: { flexDirection: "row", alignItems: "center", marginTop: 12, paddingHorizontal: 10 },
  tDot: { width: 14, height: 14, borderRadius: 7 },
  tLine: { flex: 1, height: 2, backgroundColor: COLORS.borderElevated, marginHorizontal: 6, marginBottom: 14 },
  decision: { fontSize: 13, fontWeight: "700", marginTop: 10 },
  riskTag: { color: COLORS.caution, fontSize: 12, fontWeight: "800" },
  progressTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: COLORS.bgCanvas,
    marginTop: 10,
    overflow: "hidden",
  },
  progressFill: { height: 6, borderRadius: 3 },
  emptyWrap: { alignItems: "center", marginTop: 64, gap: 10 },
  emptyTitle: { color: COLORS.textSecondary, fontSize: 14, fontWeight: "600" },
  input: {
    backgroundColor: COLORS.bgCanvas,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    padding: 14,
    minHeight: 96,
    textAlignVertical: "top",
  },
  submitBtn: {
    marginTop: 14,
    height: 52,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  lightbox: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.92)",
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
  },
  zoomImg: { width: "100%", height: "78%" },
  zoomClose: { color: COLORS.textSecondary, fontSize: 12, marginTop: 14 },
});
