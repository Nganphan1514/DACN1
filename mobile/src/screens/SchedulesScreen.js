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

export default function SchedulesScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [activeTrip, setActiveTrip] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Modal nhap ly do (Tu choi lich hoac Gui yeu cau doi lich/xe)
  const [modalVisible, setModalVisible] = useState(false);
  const [modalMode, setModalMode] = useState("reject"); // 'reject' | 'change'
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [reasonText, setReasonText] = useState("");
  const [changeType, setChangeType] = useState("DOI_THOI_GIAN");

  const isDriver = user?.vai_tro === "tai_xe";
  const driverId = user?.tai_xe_id || user?.id;

  const loadSchedules = useCallback(async () => {
    setRefreshing(true);
    try {
      const endpoint = isDriver
        ? `/api/driver/schedules/${driverId}`
        : "/api/admin/schedules";
      const res = await apiRequest(endpoint);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setItems(res.data.data);
      }
      if (isDriver) {
        const tripRes = await apiRequest("/api/driver/trips");
        if (tripRes.data?.success && Array.isArray(tripRes.data.data)) {
          const running = tripRes.data.data.find((t) => t.trang_thai === "DANG_CHAY");
          setActiveTrip(running || null);
        }
      }
    } catch (e) {
      console.warn("Load schedules error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [isDriver, driverId]);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  const handleConfirm = async (lichId) => {
    const res = await apiRequest(`/api/driver/schedules/${lichId}/confirm`, {
      method: "POST",
    });
    Alert.alert(res.data?.success ? "Thành công" : "Thông báo", res.data?.message || "Đã xử lý");
    if (res.data?.success) loadSchedules();
  };

  const handleStartTrip = async (lichId) => {
    const res = await apiRequest("/api/driver/trips/start", {
      method: "POST",
      body: JSON.stringify({ lich_chay_id: lichId }),
    });
    Alert.alert(res.data?.success ? "Đã bắt đầu chuyến" : "Không thể bắt đầu", res.data?.message || "");
    if (res.data?.success) loadSchedules();
  };

  const handleCompleteTrip = async (chuyenId) => {
    Alert.alert(
      "Xác nhận kết thúc chuyến",
      "Vui lòng đảm bảo xe đã dừng hẳn ở vị trí an toàn trước khi kết thúc chuyến.",
      [
        { text: "Hủy", style: "cancel" },
        {
          text: "Kết thúc chuyến",
          onPress: async () => {
            const res = await apiRequest(`/api/driver/trips/${chuyenId}/complete`, {
              method: "POST",
              body: JSON.stringify({}),
            });
            Alert.alert(res.data?.success ? "Hoàn thành" : "Thông báo", res.data?.message || "");
            if (res.data?.success) loadSchedules();
          },
        },
      ]
    );
  };

  const openModal = (mode, schedule) => {
    setModalMode(mode);
    setSelectedSchedule(schedule);
    setReasonText("");
    setChangeType("DOI_THOI_GIAN");
    setModalVisible(true);
  };

  const submitModal = async () => {
    if (!reasonText.trim()) {
      Alert.alert("Thiếu lý do", "Vui lòng nhập lý do chi tiết.");
      return;
    }
    if (!selectedSchedule) return;

    let res;
    if (modalMode === "reject") {
      res = await apiRequest(`/api/driver/schedules/${selectedSchedule.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ ly_do: reasonText.trim() }),
      });
    } else {
      res = await apiRequest(`/api/driver/schedules/${selectedSchedule.id}/change-requests`, {
        method: "POST",
        body: JSON.stringify({
          loai_yeu_cau: changeType,
          du_lieu_de_xuat: {},
          ly_do: reasonText.trim(),
        }),
      });
    }
    setModalVisible(false);
    Alert.alert(res.data?.success ? "Thành công" : "Thông báo", res.data?.message || "");
    if (res.data?.success) loadSchedules();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Lịch chạy & Chuyến đi</Text>

      {isDriver && activeTrip && (
        <View style={styles.activeTripBanner}>
          <Text style={styles.activeTripTitle}>
            CHUYẾN ĐANG CHẠY (#{activeTrip.id}) • {activeTrip.bien_so || ""}
          </Text>
          <Text style={styles.activeTripSub}>{activeTrip.tuyen_duong || ""}</Text>
          <TouchableOpacity
            style={styles.completeBtn}
            onPress={() => handleCompleteTrip(activeTrip.id)}
          >
            <Text style={styles.btnText}>Kết thúc chuyến đi</Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={items}
        keyExtractor={(item, index) => String(item.id || index)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadSchedules} tintColor="#22d3ee" />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>Chưa có lịch chạy nào.</Text>}
        renderItem={({ item }) => {
          const st = item.trang_thai || "CHO_XAC_NHAN";
          const canConfirm = isDriver && (st === "CHO_XAC_NHAN" || st === "sap_chay");
          const canStart = isDriver && !activeTrip && (st === "DA_XAC_NHAN" || st === "SAP_CHAY");
          const canRequestChange =
            isDriver && ["CHO_XAC_NHAN", "DA_XAC_NHAN", "SAP_CHAY", "sap_chay"].includes(st);

          return (
            <View style={styles.card}>
              <Text style={styles.route}>{item.tuyen_duong || "Chưa rõ tuyến"}</Text>
              <Text style={styles.meta}>
                Xe: {item.bien_so || "N/A"} {item.ho_ten ? `• Tài xế: ${item.ho_ten}` : ""}
              </Text>
              <Text style={styles.meta}>Bắt đầu: {item.gio_bat_dau || "N/A"}</Text>
              {item.gio_ket_thuc ? (
                <Text style={styles.meta}>Kết thúc dự kiến: {item.gio_ket_thuc}</Text>
              ) : null}
              <Text style={styles.status}>Trạng thái: {st}</Text>

              {isDriver && (canConfirm || canStart || canRequestChange) && (
                <View style={styles.actions}>
                  {canConfirm && (
                    <>
                      <TouchableOpacity
                        style={[styles.btn, styles.btnGreen]}
                        onPress={() => handleConfirm(item.id)}
                      >
                        <Text style={styles.btnText}>Xác nhận lịch</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.btn, styles.btnRed]}
                        onPress={() => openModal("reject", item)}
                      >
                        <Text style={styles.btnText}>Từ chối</Text>
                      </TouchableOpacity>
                    </>
                  )}
                  {canStart && (
                    <TouchableOpacity
                      style={[styles.btn, styles.btnCyan]}
                      onPress={() => handleStartTrip(item.id)}
                    >
                      <Text style={styles.btnText}>Bắt đầu chuyến</Text>
                    </TouchableOpacity>
                  )}
                  {canRequestChange && (
                    <TouchableOpacity
                      style={[styles.btn, styles.btnSlate]}
                      onPress={() => openModal("change", item)}
                    >
                      <Text style={styles.btnText}>Đổi lịch/xe</Text>
                    </TouchableOpacity>
                  )}
                </View>
              )}
            </View>
          );
        }}
      />

      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {modalMode === "reject" ? "Từ chối lịch chạy" : "Gửi yêu cầu đổi lịch / đổi xe"}
            </Text>
            {modalMode === "change" && (
              <View style={styles.typeRow}>
                {["DOI_THOI_GIAN", "DOI_XE", "HUY_LICH"].map((t) => (
                  <TouchableOpacity
                    key={t}
                    style={[styles.typeChip, changeType === t && styles.typeChipActive]}
                    onPress={() => setChangeType(t)}
                  >
                    <Text style={styles.typeChipText}>{t}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
            <TextInput
              style={styles.input}
              placeholder="Nhập lý do chi tiết (bắt buộc)..."
              placeholderTextColor="#64748b"
              multiline
              value={reasonText}
              onChangeText={setReasonText}
            />
            <View style={styles.actions}>
              <TouchableOpacity
                style={[styles.btn, styles.btnSlate]}
                onPress={() => setModalVisible(false)}
              >
                <Text style={styles.btnText}>Đóng</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnCyan]} onPress={submitModal}>
                <Text style={styles.btnText}>Gửi đi</Text>
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
  header: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: 14 },
  activeTripBanner: {
    backgroundColor: "#064e3b",
    borderColor: "#10b981",
    borderWidth: 1,
    borderRadius: 18,
    padding: 14,
    marginBottom: 14,
  },
  activeTripTitle: { color: "#6ee7b7", fontSize: 13, fontWeight: "800" },
  activeTripSub: { color: "#ecfdf5", fontSize: 14, marginTop: 4, marginBottom: 10 },
  completeBtn: {
    backgroundColor: "#dc2626",
    paddingVertical: 10,
    borderRadius: 12,
    alignItems: "center",
  },
  list: { gap: 12, paddingBottom: 30 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  route: { color: "#fff", fontSize: 16, fontWeight: "700" },
  meta: { color: "#94a3b8", fontSize: 13, marginTop: 4 },
  status: { color: "#22d3ee", fontSize: 12, fontWeight: "700", marginTop: 8 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  btn: { paddingHorizontal: 12, paddingVertical: 9, borderRadius: 10 },
  btnGreen: { backgroundColor: "#059669" },
  btnRed: { backgroundColor: "#dc2626" },
  btnCyan: { backgroundColor: "#0891b2" },
  btnSlate: { backgroundColor: "#334155" },
  btnText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
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
  modalTitle: { color: "#fff", fontSize: 17, fontWeight: "800", marginBottom: 12 },
  typeRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  typeChip: { backgroundColor: "#1e293b", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 },
  typeChipActive: { backgroundColor: "#0891b2" },
  typeChipText: { color: "#e2e8f0", fontSize: 11, fontWeight: "700" },
  input: {
    backgroundColor: "#020617",
    color: "#fff",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#334155",
    padding: 12,
    minHeight: 80,
    textAlignVertical: "top",
  },
});
