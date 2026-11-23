import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { COLORS, RADIUS } from "../theme/tokens";

export default function ToastBanner({ toast, onHide }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!toast?.message) return;
    Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    const timer = setTimeout(() => {
      Animated.timing(opacity, { toValue: 0, duration: 220, useNativeDriver: true }).start(() => {
        onHide && onHide();
      });
    }, 3400);
    return () => clearTimeout(timer);
  }, [toast, onHide, opacity]);

  if (!toast?.message) return null;

  const isError = toast.type === "error";
  const isWarn = toast.type === "warning";
  const accent = isError ? COLORS.danger : isWarn ? COLORS.caution : COLORS.safe;
  const icon = isError ? "alert-circle" : isWarn ? "warning" : "checkmark-circle";

  return (
    <Animated.View style={[styles.wrap, { opacity, borderColor: accent }]}>
      <Ionicons name={icon} size={20} color={accent} />
      <Text style={styles.text} numberOfLines={3}>
        {toast.message}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    top: 46,
    left: 16,
    right: 16,
    zIndex: 999,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: COLORS.surfaceElevated,
    borderRadius: RADIUS.button,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
    shadowColor: "#000",
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8,
  },
  text: { color: COLORS.textPrimary, fontSize: 13, fontWeight: "600", flex: 1, lineHeight: 18 },
});
