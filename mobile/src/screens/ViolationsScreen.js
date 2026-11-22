import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  FlatList,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

export default function ViolationsScreen() {
  const { user } = useAuth();
  const [tab, setTab] = useState("violations"); // 'violations' | 'ai' | 'appeals'
  const [violations, setViolations] = useState([]);
  const [aiEvents, setAiEvents] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const [appealModal, setAppealModal] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState(null);
  const [explanation, setExplanation] = useState("");

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
      if (vpRes.data?.success && Array.isArray(vpRes.data.data)) {
        setViolations(vpRes.data.data);
      }
      if (aiRes.data?.success && Array.isArray(aiRes.data.data)) {
        setAiEvents(aiRes.data.data);
      }
      if (apRes.data?.success && Array.isArray(apRes.data.data)) {
        setAppeals(apRes.data.data);
      }
    } catch (e) {
      console.warn("Load violations/appeals error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [driverId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const openAppealModal = (vp) => {
    setSelectedViolation(vp);
    setExplanation("");
    setAppealModal(true);
  };

  const submitAppeal = async () => {
    if (explanation.trim().length < 5) {
      Alert.alert("Thiếu giải trình", "Vui lòng nhập nội dung giải trình (tối thiểu 5 ký tự).");
      return;
    }
    const res = await apiRequest(`/api/driver/violations/${selectedViolation.id}/appeals`, {
      method: "POST",
      body: JSON.stringify({
        noi_dung_giai_trinh: explanation.trim(),
        minh_chung_urls: [],
      }),
    });
    setAppealModal(false);
    Alert.alert(res.data?.success ? "Đã gửi khiếu nại" : "Thông báo", res.data?.message || "");
    if (res.data?.success) {
      setTab("appeals");
      loadAll();
    }
  };

  const activeData = tab === "violations" ? violations : tab === "ai" ? aiEvents : appeals;

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Vi phạm & Khiếu nại</Text>

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tabBtn, tab === "violations" && styles.tabBtnActive]}
          onPress={() => setTab("violations")}
        >
          <Text style={styles.tabText}>Vi phạm ({violations.length})</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tabBtn, tab === "appeals" && styles.tabBtnActive]}
          onPress={() => setTab("appeals")}
        >
          <Text style={styles.tabText}>Khiếu nại ({appeals.length})</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tabBtn, tab === "ai" && styles.tabBtnActive]}
          onPress={() => setTab("ai")}
        >
          <Text style={styles.tabText}>Cảnh báo AI ({aiEvents.length})</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={activeData}
        keyExtractor={(item, idx) => `${tab}-${item.id || idx}`}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadAll} tintColor="#22d3ee" />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>
            {tab === "violations"
              ? "Không có vi phạm nào đã xác minh."
              : tab === "appeals"
              ? "Bạn chưa gửi khiếu nại nào."
              : "Chưa có cảnh báo AI nào."}
          </Text>
        }
        renderItem={({ item }) => {
          if (tab === "violations") {
            const canAppeal = ["HIEU_LUC", "GIU_NGUYEN"].includes(item.trang_thai);
            return (
              <View style={styles.card}>
                <View style={styles.row}>
                  <Text style={styles.title}>{item.loai_vi_pham} • #{item.id}</Text>
                  <Text style={styles.statusBadge}>{item.trang_thai}</Text>
                </View>
                <Text style={styles.meta}>Lý do xác minh: {item.ly_do_xac_minh}</Text>
                <Text style={styles.time}>Xác minh lúc: {item.xac_minh_at || ""}</Text>
                {canAppeal && (
                  <TouchableOpacity
                    style={styles.appealBtn}
                    onPress={() => openAppealModal(item)}
                  >
                    <Text style={styles.btnText}>Gửi khiếu nại / Giải trình</Text>
                  </TouchableOpacity>
                )}
              </View>
            );
          }

          if (tab === "appeals") {
            return (
              <View style={styles.card}>
                <View style={styles.row}>
                  <Text style={styles.title}>Khiếu nại #{item.id} (VP #{item.vi_pham_id})</Text>
                  <Text style={styles.statusBadge}>{item.trang_thai}</Text>
                </View>
                <Text style={styles.meta}>Giải trình gốc: {item.noi_dung_giai_trinh}</Text>
                {item.ly_do_ket_luan ? (
                  <Text style={styles.decision}>Kết luận QL: {item.ly_do_ket_luan}</Text>
                ) : null}
                <Text style={styles.time}>Gửi lúc: {item.created_at || ""}</Text>
              </View>
            );
          }

          return (
            <View style={styles.card}>
              <View style={styles.row}>
                <Text style={styles.title}>{item.loai_canh_bao || "CANH_BAO"}</Text>
                <Text style={styles.aiNote}>{item.trang_thai || "PENDING_REVIEW"}</Text>
              </View>
              <Text style={styles.meta}>{item.noi_dung || "Cảnh báo an toàn AI (chưa phải vi phạm)"}</Text>
              <Text style={styles.time}>Risk: {item.risk_score ?? 0} • {item.thoi_gian_xay_ra || ""}</Text>
            </View>
          );
        }}
      />

      <Modal visible={appealModal} transparent animationType="slide">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              Gửi khiếu nại Vi phạm #{selectedViolation?.id}
            </Text>
            <Text style={styles.modalHint}>
              Nội dung giải trình gốc được lưu bất biến làm căn cứ để Quản lý xem xét lại.
            </Text>
            <TextInput
              style={styles.input}
              placeholder="Nhập nội dung giải trình của bạn..."
              placeholderTextColor="#64748b"
              multiline
              value={explanation}
              onChangeText={setExplanation}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.mBtn, { backgroundColor: "#334155" }]}
                onPress={() => setAppealModal(false)}
              >
                <Text style={styles.btnText}>Đóng</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.mBtn, { backgroundColor: "#0891b2" }]}
                onPress={submitAppeal}
              >
                <Text style={styles.btnText}>Gửi khiếu nại</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  header: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: 12 },
  tabs: { flexDirection: "row", gap: 6, marginBottom: 14 },
  tabBtn: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 12,
    backgroundColor: "#0f172a",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  tabBtnActive: { backgroundColor: "#0891b2", borderColor: "#22d3ee" },
  tabText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  list: { gap: 12, paddingBottom: 30 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 16,
    padding: 15,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { color: "#fff", fontWeight: "800", fontSize: 14 },
  statusBadge: { color: "#fbbf24", fontSize: 11, fontWeight: "800" },
  aiNote: { color: "#38bdf8", fontSize: 11, fontWeight: "700" },
  meta: { color: "#cbd5e1", fontSize: 13, marginTop: 8, lineHeight: 18 },
  decision: { color: "#6ee7b7", fontSize: 13, marginTop: 6, fontWeight: "600" },
  time: { color: "#64748b", fontSize: 11, marginTop: 6 },
  appealBtn: {
    marginTop: 10,
    backgroundColor: "#b45309",
    paddingVertical: 9,
    borderRadius: 10,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: "#0f172a",
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: "#334155",
  },
  modalTitle: { color: "#fff", fontSize: 17, fontWeight: "800" },
  modalHint: { color: "#94a3b8", fontSize: 12, marginTop: 4, marginBottom: 12 },
  input: {
    backgroundColor: "#020617",
    color: "#fff",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
    padding: 12,
    minHeight: 90,
    textAlignVertical: "top",
  },
  modalActions: { flexDirection: "row", justifyContent: "flex-end", gap: 8, marginTop: 12 },
  mBtn: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10 },
});
