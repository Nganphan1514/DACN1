import React, { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

function getBadgeStyle(status) {
  if (status === "BUON NGU") {
    return { bg: "#991b1b", text: "#fecaca" };
  }
  if (status === "MET MOI") {
    return { bg: "#9a3412", text: "#fed7aa" };
  }
  if (status === "MAT TAP TRUNG") {
    return { bg: "#854d0e", text: "#fef08a" };
  }
  return { bg: "#14532d", text: "#bbf7d0" };
}

export default function ViolationsScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const driverId = user?.tai_xe_id || user?.id;

  const loadViolations = useCallback(async () => {
    if (!driverId) return;
    setRefreshing(true);
    try {
      const res = await apiRequest(`/api/driver/violations/${driverId}`);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setItems(res.data.data);
      }
    } catch (e) {
      console.warn("Load violations error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [driverId]);

  useEffect(() => {
    loadViolations();
  }, [loadViolations]);

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Lịch sử vi phạm AI</Text>
      <FlatList
        data={items}
        keyExtractor={(item, idx) => String(item.id || idx)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadViolations} tintColor="#22d3ee" />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>Chưa ghi nhận cảnh báo vi phạm nào.</Text>}
        renderItem={({ item }) => {
          const badge = getBadgeStyle(item.trang_thai);
          return (
            <View style={styles.card}>
              <View style={styles.row}>
                <View style={[styles.badge, { backgroundColor: badge.bg }]}>
                  <Text style={[styles.badgeText, { color: badge.text }]}>
                    {item.trang_thai || "CANH BAO"}
                  </Text>
                </View>
                <Text style={styles.risk}>Risk: {item.risk_score ?? 0}/10</Text>
              </View>
              <Text style={styles.metrics}>
                EAR: {Number(item.ear || 0).toFixed(2)} • MAR: {Number(item.mar || 0).toFixed(2)}
              </Text>
              <Text style={styles.time}>{item.thoi_gian || ""}</Text>
            </View>
          );
        }}
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
    borderRadius: 16,
    padding: 15,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  badgeText: { fontSize: 11, fontWeight: "800" },
  risk: { color: "#f8fafc", fontWeight: "700", fontSize: 13 },
  metrics: { color: "#cbd5e1", fontSize: 13, marginTop: 8 },
  time: { color: "#64748b", fontSize: 12, marginTop: 4 },
});
