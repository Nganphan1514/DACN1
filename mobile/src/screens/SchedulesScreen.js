import React, { useCallback, useEffect, useState } from "react";
import {
  FlatList,
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

const QUICK_REASONS = [
  "Kẹt lịch cá nhân đột xuất",
  "Sức khỏe chưa đảm bảo an toàn",
  "Phương tiện có dấu hiệu bất thường",
];

export default function SchedulesScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [activeTrip, setActiveTrip] = useState(null);
  const [filter, setFilter] = useState("ALL"); // ALL | ACTION | RUNNING | DONE
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  // Sheet Tu choi / Doi lich
  const [reasonSheet, setReasonSheet] = useState(false);
  const [sheetMode, setSheetMode] = useState("reject");
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [reasonText, setReasonText] = useState("");
  const [changeType, setChangeType] = useState("DOI_THOI_GIAN");

  // Sheet Checklist 6 hang muc (FIX-03)
  const [checklistSheet, setChecklistSheet] = useState(false);
  const [checklistItems, setChecklistItems] = useState([]);
  const [checklistNote, setChecklistNote] = useState("");
  const [checklistMap, setChecklistMap] = useState({}); // lich_id -> 'DAT' | 'KHONG_DAT'

  const isDriver = user?.vai_tro === "tai_xe";
  const driverId = user?.tai_xe_id || user?.id;

  const loadSchedules = useCallback(async () => {
    setRefreshing(true);
    try {
      const endpoint = isDriver ? `/api/driver/schedules/${driverId}` : "/api/admin/schedules";
      const res = await apiRequest(endpoint);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setItems(res.data.data);
      }
      if (isDriver) {
        const tripRes = await apiRequest("/api/driver/trips");
        if (tripRes.data?.success && Array.isArray(tripRes.data.data)) {
          setActiveTrip(tripRes.data.data.find((t) => t.trang_thai === "DANG_CHAY") || null);
        }
      }
    } catch (e) {
      console.warn("Load schedules error:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [isDriver, driverId]);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  async function handleConfirm(lichId) {
    const res = await apiRequest(`/api/driver/schedules/${lichId}/confirm`, { method: "POST" });
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || "Đã xử lý xác nhận lịch.",
    });
    if (res.data?.success) loadSchedules();
  }

  async function handleStartTrip(lichId) {
    const res = await apiRequest("/api/driver/trips/start", {
      method: "POST",
      body: JSON.stringify({ lich_chay_id: lichId }),
    });
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || (res.data?.success ? "Đã bắt đầu chuyến đi." : "Không thể bắt đầu."),
    });
    if (res.data?.success) loadSchedules();
  }

  async function handleCompleteTrip(chuyenId) {
    const res = await apiRequest(`/api/driver/trips/${chuyenId}/complete`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || "Đã kết thúc chuyến đi.",
    });
    if (res.data?.success) loadSchedules();
  }

  async function openChecklist(schedule) {
    setSelectedSchedule(schedule);
    setChecklistNote("");
    const tplRes = await apiRequest("/api/driver/checklist/template");
    const list = (tplRes.data?.data || []).map((x) => ({
      ma_hang_muc: x.ma_hang_muc,
      ten_hang_muc: x.ten_hang_muc,
      ket_qua: "DAT",
    }));
    setChecklistItems(list);
    setChecklistSheet(true);
  }

  function setItemResult(ma, ketQua) {
    setChecklistItems((prev) =>
      prev.map((it) => (it.ma_hang_muc === ma ? { ...it, ket_qua: ketQua } : it))
    );
  }

  async function submitChecklist() {
    if (!selectedSchedule) return;
    const hasFailed = checklistItems.some((it) => it.ket_qua === "KHONG_DAT");
    if (hasFailed && !checklistNote.trim()) {
      setToast({ type: "warning", message: "Có mục KHÔNG ĐẠT — vui lòng nhập mô tả lỗi để báo Quản lý." });
      return;
    }
    const res = await apiRequest(`/api/driver/schedules/${selectedSchedule.id}/checklist`, {
      method: "POST",
      body: JSON.stringify({
        items: checklistItems.map((it) => ({ ma_hang_muc: it.ma_hang_muc, ket_qua: it.ket_qua })),
        ghi_chu: checklistNote.trim(),
      }),
    });
    setChecklistSheet(false);
    if (res.data?.success) {
      const kq = res.data?.data?.ket_qua_tong || (hasFailed ? "KHONG_DAT" : "DAT");
      setChecklistMap((prev) => ({ ...prev, [selectedSchedule.id]: kq }));
      setToast({
        type: kq === "DAT" ? "success" : "warning",
        message: res.data?.message || "Đã lưu Checklist.",
      });
      loadSchedules();
    } else {
      setToast({ type: "error", message: res.data?.message || "Lưu Checklist thất bại." });
    }
  }

  function openReasonSheet(mode, schedule) {
    setSheetMode(mode);
    setSelectedSchedule(schedule);
    setReasonText("");
    setChangeType("DOI_THOI_GIAN");
    setReasonSheet(true);
  }

  async function submitReasonSheet() {
    if (!reasonText.trim()) {
      setToast({ type: "warning", message: "Vui lòng chọn hoặc nhập lý do chi tiết." });
      return;
    }
    if (!selectedSchedule) return;
    const res =
      sheetMode === "reject"
        ? await apiRequest(`/api/driver/schedules/${selectedSchedule.id}/reject`, {
            method: "POST",
            body: JSON.stringify({ ly_do: reasonText.trim() }),
          })
        : await apiRequest(`/api/driver/schedules/${selectedSchedule.id}/change-requests`, {
            method: "POST",
            body: JSON.stringify({
              loai_yeu_cau: changeType,
              du_lieu_de_xuat: {},
              ly_do: reasonText.trim(),
            }),
          });
    setReasonSheet(false);
    setToast({
      type: res.data?.success ? "success" : "error",
      message: res.data?.message || "Đã gửi yêu cầu.",
    });
    if (res.data?.success) loadSchedules();
  }

  const filtered = items.filter((it) => {
    const st = String(it.trang_thai || "").toUpperCase();
    if (filter === "ACTION") return ["CHO_XAC_NHAN", "DA_XAC_NHAN", "SAP_CHAY"].includes(st);
    if (filter === "RUNNING") return ["DANG_THUC_HIEN", "DANG_CHAY"].includes(st);
    if (filter === "DONE") return ["HOAN_THANH", "DA_HUY", "BI_TU_CHOI", "KET_THUC_NGOAI_LE"].includes(st);
    return true;
  });

  return (
    <View style={styles.container}>
      <ToastBanner toast={toast} onHide={() => setToast(null)} />

      <Text style={styles.header}>Lịch trình & Chuyến đi</Text>

      {/* FILTER PILLS */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow} contentContainerStyle={{ gap: 8 }}>
        {[
          { k: "ALL", l: `Tất cả (${items.length})` },
          { k: "ACTION", l: "Cần xử lý" },
          { k: "RUNNING", l: "Đang chạy" },
          { k: "DONE", l: "Lịch sử" },
        ].map((f) => (
          <TouchableOpacity
            key={f.k}
            style={[styles.pill, filter === f.k && styles.pillActive]}
            onPress={() => setFilter(f.k)}
          >
            <Text style={[styles.pillText, filter === f.k && { color: "#fff" }]}>{f.l}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* ACTIVE TRIP BANNER WITH SLIDE TO COMPLETE */}
      {isDriver && activeTrip && (
        <View style={styles.activeBanner}>
          <Text style={styles.activeTag}>CHUYẾN ĐANG CHẠY • #{activeTrip.id} • {activeTrip.bien_so || ""}</Text>
          <Text style={styles.activeRoute}>{activeTrip.tuyen_duong || ""}</Text>
          <View style={{ marginTop: 10 }}>
            <SlideToConfirm
              label="Trượt để Kết thúc chuyến an toàn"
              color={COLORS.danger}
              icon="flag"
              onConfirm={() => handleCompleteTrip(activeTrip.id)}
            />
          </View>
        </View>
      )}

      {loading ? (
        <View style={{ gap: 12 }}>
          <SkeletonCard height={140} />
          <SkeletonCard height={140} />
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item, idx) => String(item.id || idx)}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={loadSchedules} tintColor={COLORS.primary} />
          }
          contentContainerStyle={{ gap: 14, paddingBottom: 32 }}
          ListEmptyComponent={
            <View style={styles.emptyWrap}>
              <Ionicons name="calendar-outline" size={44} color={COLORS.textMuted} />
              <Text style={styles.emptyText}>Không có lịch chạy nào trong mục này.</Text>
            </View>
          }
          renderItem={({ item }) => {
            const st = String(item.trang_thai || "CHO_XAC_NHAN").toUpperCase();
            const canConfirm = isDriver && (st === "CHO_XAC_NHAN" || st === "SAP_CHAY");
            const isConfirmed = st === "DA_XAC_NHAN";
            const canStart = isDriver && !activeTrip && isConfirmed;
            const canChange = isDriver && ["CHO_XAC_NHAN", "DA_XAC_NHAN"].includes(st);
            const chkState = checklistMap[item.id]; // undefined | 'DAT' | 'KHONG_DAT'

            const stepDone1 = isConfirmed || st === "DANG_THUC_HIEN" || st === "HOAN_THANH";
            const stepDone2 = chkState === "DAT" || st === "DANG_THUC_HIEN" || st === "HOAN_THANH";
            const stepDone3 = st === "DANG_THUC_HIEN" || st === "HOAN_THANH";

            return (
              <View style={styles.card}>
                <View style={styles.rowBetween}>
                  <Text style={styles.route}>{item.tuyen_duong || "Chưa rõ tuyến"}</Text>
                  <View style={styles.statusChip}>
                    <Text style={styles.statusChipText}>{st}</Text>
                  </View>
                </View>

                <Text style={[styles.meta, TABULAR_NUMS]}>
                  Xe: {item.bien_so || "N/A"} • Bắt đầu: {item.gio_bat_dau || "N/A"}
                </Text>

                {/* MINI 3-STEP STEPPER */}
                {isDriver && !["DA_HUY", "BI_TU_CHOI"].includes(st) && (
                  <View style={styles.stepper}>
                    <StepItem num="1" label="Xác nhận" done={stepDone1} />
                    <View style={styles.stepLine} />
                    <StepItem num="2" label="Checklist" done={stepDone2} failed={chkState === "KHONG_DAT"} />
                    <View style={styles.stepLine} />
                    <StepItem num="3" label="Khởi hành" done={stepDone3} />
                  </View>
                )}

                {canConfirm && (
                  <View style={styles.btnRow}>
                    <TouchableOpacity
                      style={[styles.actionBtn, { backgroundColor: COLORS.safe, flex: 1 }]}
                      onPress={() => handleConfirm(item.id)}
                    >
                      <Text style={styles.btnText}>Xác nhận lịch</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.actionBtn, { backgroundColor: COLORS.dangerDark }]}
                      onPress={() => openReasonSheet("reject", item)}
                    >
                      <Text style={styles.btnText}>Từ chối</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {canStart && (
                  <View style={{ gap: 10, marginTop: 12 }}>
                    <TouchableOpacity
                      style={[
                        styles.actionBtn,
                        { backgroundColor: chkState === "DAT" ? COLORS.safeDark : COLORS.cautionDark },
                      ]}
                      onPress={() => openChecklist(item)}
                    >
                      <Ionicons name="clipboard-outline" size={16} color="#fff" />
                      <Text style={styles.btnText}>
                        {chkState === "DAT"
                          ? "Checklist xe: ĐẠT ✓ (Kiểm tra lại)"
                          : chkState === "KHONG_DAT"
                          ? "Checklist KHÔNG ĐẠT — Thực hiện lại"
                          : "Thực hiện Checklist xe (6 mục)"}
                      </Text>
                    </TouchableOpacity>

                    <SlideToConfirm
                      label={
                        chkState === "KHONG_DAT"
                          ? "Đã khóa khởi hành (Checklist không đạt)"
                          : "Trượt sang phải để Bắt đầu chuyến"
                      }
                      color={COLORS.primary}
                      disabled={chkState === "KHONG_DAT"}
                      onConfirm={() => handleStartTrip(item.id)}
                    />
                  </View>
                )}

                {canChange && (
                  <TouchableOpacity
                    style={styles.changeLink}
                    onPress={() => openReasonSheet("change", item)}
                  >
                    <Ionicons name="swap-horizontal" size={15} color={COLORS.textSecondary} />
                    <Text style={styles.changeLinkText}>Gửi yêu cầu đổi lịch / đổi xe</Text>
                  </TouchableOpacity>
                )}
              </View>
            );
          }}
        />
      )}

      {/* BOTTOM SHEET TU CHOI / DOI LICH */}
      <BottomSheet
        visible={reasonSheet}
        title={sheetMode === "reject" ? "Từ chối lịch chạy" : "Yêu cầu đổi lịch / đổi xe"}
        subtitle="Chọn nhanh lý do bên dưới hoặc nhập chi tiết để Điều phối viên xử lý."
        onClose={() => setReasonSheet(false)}
      >
        {sheetMode === "change" && (
          <View style={styles.chipWrap}>
            {["DOI_THOI_GIAN", "DOI_XE", "HUY_LICH"].map((t) => (
              <TouchableOpacity
                key={t}
                style={[styles.quickChip, changeType === t && { backgroundColor: COLORS.primary }]}
                onPress={() => setChangeType(t)}
              >
                <Text style={styles.quickChipText}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={styles.chipWrap}>
          {QUICK_REASONS.map((qr) => (
            <TouchableOpacity key={qr} style={styles.quickChip} onPress={() => setReasonText(qr)}>
              <Text style={styles.quickChipText}>{qr}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <TextInput
          style={styles.input}
          placeholder="Nhập lý do chi tiết (bắt buộc)..."
          placeholderTextColor={COLORS.textMuted}
          multiline
          value={reasonText}
          onChangeText={setReasonText}
        />

        <TouchableOpacity style={styles.sheetPrimaryBtn} onPress={submitReasonSheet}>
          <Text style={styles.btnText}>GỬI XÁC NHẬN</Text>
        </TouchableOpacity>
      </BottomSheet>

      {/* BOTTOM SHEET CHECKLIST 6 HANG MUC (FIX-03) */}
      <BottomSheet
        visible={checklistSheet}
        title="Checklist kiểm tra xe trước chuyến"
        subtitle="Kiểm tra 6 hạng mục an toàn. Nếu có mục Lỗi, hệ thống sẽ tự tạo phiếu sự cố gửi Quản lý."
        onClose={() => setChecklistSheet(false)}
      >
        <View style={{ gap: 8, marginBottom: 12 }}>
          {checklistItems.map((it) => {
            const ok = it.ket_qua === "DAT";
            return (
              <View key={it.ma_hang_muc} style={styles.chkRow}>
                <Text style={styles.chkName}>{it.ten_hang_muc}</Text>
                <View style={{ flexDirection: "row", gap: 6 }}>
                  <TouchableOpacity
                    style={[styles.chkBtn, ok && { backgroundColor: COLORS.safe }]}
                    onPress={() => setItemResult(it.ma_hang_muc, "DAT")}
                  >
                    <Text style={styles.chkBtnText}>✓ Đạt</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.chkBtn, !ok && { backgroundColor: COLORS.danger }]}
                    onPress={() => setItemResult(it.ma_hang_muc, "KHONG_DAT")}
                  >
                    <Text style={styles.chkBtnText}>✕ Lỗi</Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </View>

        <TextInput
          style={styles.input}
          placeholder="Ghi chú (bắt buộc nếu có mục Lỗi)..."
          placeholderTextColor={COLORS.textMuted}
          multiline
          value={checklistNote}
          onChangeText={setChecklistNote}
        />

        <TouchableOpacity
          style={[styles.sheetPrimaryBtn, { backgroundColor: COLORS.safe }]}
          onPress={submitChecklist}
        >
          <Text style={styles.btnText}>XÁC NHẬN CHECKLIST</Text>
        </TouchableOpacity>
      </BottomSheet>
    </View>
  );
}

function StepItem({ num, label, done, failed }) {
  const bg = failed ? COLORS.danger : done ? COLORS.safe : COLORS.surfaceElevated;
  return (
    <View style={{ alignItems: "center", gap: 4 }}>
      <View style={[styles.stepCircle, { backgroundColor: bg }]}>
        <Text style={{ color: "#fff", fontSize: 10, fontWeight: "800" }}>
          {failed ? "!" : done ? "✓" : num}
        </Text>
      </View>
      <Text style={{ color: done ? COLORS.textPrimary : COLORS.textMuted, fontSize: 10, fontWeight: "600" }}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bgCanvas, paddingHorizontal: 18, paddingTop: 52 },
  header: { color: COLORS.textPrimary, fontSize: 24, fontWeight: "800", marginBottom: 12 },
  filterRow: { flexGrow: 0, marginBottom: 14 },
  pill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: RADIUS.pill,
    backgroundColor: COLORS.surfaceCard,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
  },
  pillActive: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  pillText: { color: COLORS.textSecondary, fontSize: 12, fontWeight: "700" },
  activeBanner: {
    backgroundColor: COLORS.surfaceElevated,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: "rgba(16,185,129,0.45)",
    padding: 15,
    marginBottom: 14,
  },
  activeTag: { color: COLORS.safe, fontSize: 11.5, fontWeight: "800" },
  activeRoute: { color: COLORS.textPrimary, fontSize: 16, fontWeight: "700", marginTop: 4 },
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 16,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  route: { color: COLORS.textPrimary, fontSize: 16, fontWeight: "700", flex: 1 },
  statusChip: {
    backgroundColor: COLORS.primaryTint,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
  },
  statusChipText: { color: COLORS.primary, fontSize: 10.5, fontWeight: "800" },
  meta: { color: COLORS.textSecondary, fontSize: 12.5, marginTop: 6 },
  stepper: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 14,
    paddingHorizontal: 8,
  },
  stepCircle: { width: 22, height: 22, borderRadius: 11, justifyContent: "center", alignItems: "center" },
  stepLine: { flex: 1, height: 1, backgroundColor: COLORS.borderElevated, marginHorizontal: 6, marginBottom: 14 },
  btnRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  actionBtn: {
    height: 48,
    paddingHorizontal: 16,
    borderRadius: RADIUS.button,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  btnText: { color: "#fff", fontSize: 13, fontWeight: "700" },
  changeLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 12,
    paddingVertical: 6,
  },
  changeLinkText: { color: COLORS.textSecondary, fontSize: 12.5, fontWeight: "600" },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 10 },
  emptyText: { color: COLORS.textMuted, fontSize: 13.5 },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 10 },
  quickChip: {
    backgroundColor: COLORS.surfaceCard,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: RADIUS.pill,
  },
  quickChipText: { color: COLORS.textPrimary, fontSize: 11.5, fontWeight: "600" },
  input: {
    backgroundColor: COLORS.bgCanvas,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.input,
    borderWidth: 1,
    borderColor: COLORS.borderElevated,
    padding: 14,
    minHeight: 82,
    textAlignVertical: "top",
  },
  sheetPrimaryBtn: {
    marginTop: 14,
    height: 52,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  chkRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: COLORS.surfaceCard,
    borderRadius: 12,
    padding: 11,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    gap: 8,
  },
  chkName: { color: COLORS.textPrimary, fontSize: 12.5, fontWeight: "600", flex: 1 },
  chkBtn: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 9,
    backgroundColor: COLORS.bgCanvas,
  },
  chkBtnText: { color: "#fff", fontSize: 11, fontWeight: "700" },
});
