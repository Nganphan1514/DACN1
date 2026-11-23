import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";
import { COLORS, RADIUS } from "../theme/tokens";

export default function SkeletonCard({ height = 110, style }) {
  const pulse = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 0.85, duration: 750, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0.4, duration: 750, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  return (
    <Animated.View style={[styles.card, { height, opacity: pulse }, style]}>
      <View style={styles.lineLg} />
      <View style={styles.lineMd} />
      <View style={styles.lineSm} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surfaceCard,
    borderRadius: RADIUS.card,
    borderWidth: 1,
    borderColor: COLORS.borderSubtle,
    padding: 18,
    justifyContent: "space-between",
  },
  lineLg: { height: 14, width: "62%", borderRadius: 7, backgroundColor: COLORS.surfaceElevated },
  lineMd: { height: 11, width: "86%", borderRadius: 6, backgroundColor: COLORS.surfaceElevated },
  lineSm: { height: 10, width: "40%", borderRadius: 6, backgroundColor: COLORS.surfaceElevated },
});
