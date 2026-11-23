import React, { useRef, useState } from "react";
import { Animated, PanResponder, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { COLORS, RADIUS } from "../theme/tokens";

const THUMB_SIZE = 48;
const PADDING = 4;

export default function SlideToConfirm({
  label = "Trượt để xác nhận",
  onConfirm,
  color = COLORS.primary,
  disabled = false,
  icon = "chevron-forward",
}) {
  const [trackWidth, setTrackWidth] = useState(0);
  const translateX = useRef(new Animated.Value(0)).current;
  const maxSlide = Math.max(0, trackWidth - THUMB_SIZE - PADDING * 2);

  const panResponder = useRef(null);
  panResponder.current = PanResponder.create({
    onStartShouldSetPanResponder: () => !disabled && maxSlide > 0,
    onMoveShouldSetPanResponder: () => !disabled && maxSlide > 0,
    onPanResponderMove: (_, gesture) => {
      const clamped = Math.max(0, Math.min(gesture.dx, maxSlide));
      translateX.setValue(clamped);
    },
    onPanResponderRelease: (_, gesture) => {
      if (gesture.dx >= maxSlide * 0.78 && maxSlide > 0) {
        Animated.timing(translateX, {
          toValue: maxSlide,
          duration: 120,
          useNativeDriver: true,
        }).start(() => {
          onConfirm && onConfirm();
          setTimeout(() => {
            Animated.spring(translateX, {
              toValue: 0,
              useNativeDriver: true,
            }).start();
          }, 400);
        });
      } else {
        Animated.spring(translateX, {
          toValue: 0,
          useNativeDriver: true,
        }).start();
      }
    },
  });

  return (
    <View
      style={[
        styles.track,
        {
          borderColor: disabled ? COLORS.borderSubtle : color,
          opacity: disabled ? 0.45 : 1,
        },
      ]}
      onLayout={(e) => setTrackWidth(e.nativeEvent.layout.width)}
    >
      <Text style={styles.label} numberOfLines={1}>
        {label}
      </Text>
      <Animated.View
        {...panResponder.current.panHandlers}
        style={[
          styles.thumb,
          { backgroundColor: disabled ? COLORS.textMuted : color, transform: [{ translateX }] },
        ]}
      >
        <Ionicons name={icon} size={22} color="#fff" />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: 56,
    borderRadius: RADIUS.button,
    backgroundColor: COLORS.bgCanvas,
    borderWidth: 1,
    justifyContent: "center",
    padding: PADDING,
    overflow: "hidden",
  },
  label: {
    position: "absolute",
    left: 56,
    right: 16,
    textAlign: "center",
    color: COLORS.textSecondary,
    fontSize: 13,
    fontWeight: "700",
  },
  thumb: {
    width: THUMB_SIZE,
    height: THUMB_SIZE,
    borderRadius: 11,
    justifyContent: "center",
    alignItems: "center",
  },
});
