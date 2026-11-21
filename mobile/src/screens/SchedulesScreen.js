import React, { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

export default function SchedulesScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const isAdmin = user?.vai_tro === "quan_ly";
  const driverId = user?.tai_xe_id || user?.id;

  const loadSchedules = useCallback(async () => {
    setRefreshing(true);
    try {
      const endpoint = isAdmin
        ? "/api/admin/schedules"
        : `/api/driver/schedules/${driverId}`;
      const res = await apiRequest(endpoint);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setItems(res.data.data);
      }
    } catch (e) {
      console.warn("Load schedules error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [isAdmin, driverId]);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Lịch chạy</Text>
      <FlatList
        data={items}
        keyExtractor={(item, index) => String(item.id || index)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadSchedules} tintColor="#22d3ee" />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>Chưa có lịch chạy nào.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.route}>{item.tuyen_duong || "Chưa rõ tuyến"}</Text>
            <Text style={styles.meta}>
              Xe: {item.bien_so || "N/A"} {item.ho_ten ? `• Tài xế: ${item.ho_ten}` : ""}
            </Text>
            <Text style={styles.meta}>Bắt đầu: {item.gio_bat_dau || "N/A"}</Text>
            <Text style={styles.status}>Trạng thái: {item.trang_thai || "sap_chay"}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  header: { color: "#fff", fontSize: 24, fontWeight: "800", marginBottom: 14 },
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
});
