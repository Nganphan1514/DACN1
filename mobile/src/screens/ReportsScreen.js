import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

export default function ReportsScreen() {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isAdmin = user?.vai_tro === "quan_ly";
  const driverId = user?.tai_xe_id || user?.id;

  const loadReports = useCallback(async () => {
    setRefreshing(true);
    try {
      const endpoint = isAdmin
        ? "/api/admin/reports"
        : `/api/driver/reports/${driverId}`;
      const res = await apiRequest(endpoint);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setReports(res.data.data);
      }
    } catch (e) {
      console.warn("Load reports error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [isAdmin, driverId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  async function handleSubmit() {
    if (!title.trim() || !content.trim()) {
      Alert.alert("Thiếu thông tin", "Vui lòng nhập tiêu đề và nội dung sự cố.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiRequest("/api/driver/reports", {
        method: "POST",
        body: JSON.stringify({
          tai_xe_id: driverId,
          tieu_de: title.trim(),
          loai_su_co: "SU_CO_XE",
          noi_dung: content.trim(),
        }),
      });
      if (res.data?.success) {
        setTitle("");
        setContent("");
        Alert.alert("Thành công", "Đã gửi báo cáo sự cố tới quản lý.");
        loadReports();
      } else {
        Alert.alert("Lỗi", res.data?.message || "Gửi báo cáo thất bại.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleMarkDone(reportId) {
    const res = await apiRequest(`/api/admin/reports/${reportId}`, {
      method: "PUT",
      body: JSON.stringify({
        trang_thai: "DA_XU_LY",
        phan_hoi_quan_ly: "Đã xác nhận và xử lý từ ứng dụng di động.",
      }),
    });
    if (res.data?.success) {
      loadReports();
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Báo cáo sự cố</Text>

      {!isAdmin && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Tiêu đề sự cố (vd: Hỏng lốp, kẹt xe...)"
            placeholderTextColor="#64748b"
            value={title}
            onChangeText={setTitle}
          />
          <TextInput
            style={[styles.input, { minHeight: 68 }]}
            placeholder="Mô tả chi tiết tình huống..."
            placeholderTextColor="#64748b"
            multiline
            value={content}
            onChangeText={setContent}
          />
          <TouchableOpacity
            style={styles.btn}
            onPress={handleSubmit}
            disabled={submitting}
          >
            <Text style={styles.btnText}>
              {submitting ? "ĐANG GỬI..." : "GỬI BÁO CÁO SỰ CỐ"}
            </Text>
          </TouchableOpacity>
        </View>
      )}

      <FlatList
        data={reports}
        keyExtractor={(item, idx) => String(item.id || idx)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadReports} tintColor="#22d3ee" />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>Chưa có báo cáo sự cố nào.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.tieu_de || "Không tiêu đề"}</Text>
            <Text style={styles.cardBody}>{item.noi_dung || ""}</Text>
            <Text style={styles.status}>Trạng thái: {item.trang_thai || "CHO_XU_LY"}</Text>
            {item.phan_hoi_quan_ly ? (
              <Text style={styles.reply}>Phản hồi: {item.phan_hoi_quan_ly}</Text>
            ) : null}
            {isAdmin && item.trang_thai !== "DA_XU_LY" && (
              <TouchableOpacity
                style={styles.doneBtn}
                onPress={() => handleMarkDone(item.id)}
              >
                <Text style={styles.doneBtnText}>Đánh dấu Đã xử lý</Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  header: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: 14 },
  form: {
    backgroundColor: "#0f172a",
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1e293b",
    marginBottom: 16,
    gap: 10,
  },
  input: {
    backgroundColor: "#1e293b",
    color: "#f8fafc",
    borderRadius: 12,
    padding: 12,
  },
  btn: {
    backgroundColor: "#0891b2",
    borderRadius: 12,
    padding: 13,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 13 },
  list: { gap: 12, paddingBottom: 30 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 30 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 16,
    padding: 15,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  cardTitle: { color: "#fff", fontWeight: "700", fontSize: 15 },
  cardBody: { color: "#cbd5e1", marginTop: 6 },
  status: { color: "#fbbf24", fontSize: 12, fontWeight: "700", marginTop: 8 },
  reply: { color: "#34d399", fontSize: 12, marginTop: 4 },
  doneBtn: {
    marginTop: 10,
    backgroundColor: "#16a34a",
    borderRadius: 10,
    padding: 10,
    alignItems: "center",
  },
  doneBtnText: { color: "#fff", fontWeight: "700", fontSize: 12 },
});
