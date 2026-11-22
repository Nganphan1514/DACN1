import React, { useCallback, useEffect, useState } from "react";
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

export default function NotificationsScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const driverId = user?.tai_xe_id || user?.id;

  const loadNotifications = useCallback(async () => {
    if (!driverId) return;
    setRefreshing(true);
    try {
      const res = await apiRequest(`/api/driver/notifications/${driverId}`);
      if (res.data?.success && Array.isArray(res.data.data)) {
        setItems(res.data.data);
      }
    } catch (e) {
      console.warn("Load notifications error:", e);
    } finally {
      setRefreshing(false);
    }
  }, [driverId]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  async function markAsRead(noteId) {
    try {
      const res = await apiRequest(`/driver/read-note/${noteId}`, {
        method: "POST",
      });
      if (res.data?.success) {
        setItems((prev) =>
          prev.map((item) => (item.id === noteId ? { ...item, da_doc: true } : item))
        );
      }
    } catch (e) {
      console.warn("Mark read error:", e);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Thông báo từ quản lý</Text>
      <FlatList
        data={items}
        keyExtractor={(item, idx) => String(item.id || idx)}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={loadNotifications}
            tintColor="#22d3ee"
          />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.empty}>Chưa có thông báo nào.</Text>}
        renderItem={({ item }) => {
          const isRead = Boolean(item.da_doc);
          return (
            <View style={[styles.card, !isRead && styles.unreadCard]}>
              <Text style={styles.content}>{item.noi_dung || ""}</Text>
              <View style={styles.footer}>
                <Text style={styles.time}>{item.thoi_gian || ""}</Text>
                {isRead ? (
                  <Text style={styles.readTag}>Đã đọc</Text>
                ) : (
                  <TouchableOpacity
                    style={styles.readBtn}
                    onPress={() => markAsRead(item.id)}
                  >
                    <Text style={styles.readBtnText}>Đánh dấu đã đọc</Text>
                  </TouchableOpacity>
                )}
              </View>
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
  unreadCard: {
    borderColor: "#06b6d4",
  },
  content: { color: "#f8fafc", fontSize: 14, lineHeight: 20 },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },
  time: { color: "#64748b", fontSize: 11 },
  readTag: { color: "#34d399", fontSize: 11, fontWeight: "700" },
  readBtn: {
    backgroundColor: "#0891b2",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  readBtnText: { color: "#fff", fontSize: 11, fontWeight: "700" },
});
