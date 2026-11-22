import React, { useEffect, useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  Vibration,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Speech from "expo-speech";
import { apiRequest } from "../config/api";
import { useAuth } from "../context/AuthContext";

const VOICE_COOLDOWN_MS = 6000;

function getStatusColor(status) {
  if (status === "BUON NGU") return "#ef4444";
  if (status === "MET MOI") return "#f97316";
  if (status === "MAT TAP TRUNG") return "#eab308";
  if (status === "TINH TAO") return "#22c55e";
  return "#94a3b8";
}

export default function MonitorScreen() {
  const { user } = useAuth();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef(null);
  const runningRef = useRef(false);
  const lastVoiceRef = useRef(0);

  const [monitoring, setMonitoring] = useState(false);
  const [result, setResult] = useState({
    status: "SAN SANG",
    fatigue_score: 0,
    ear: 0,
    mar: 0,
    pitch: 0,
    yaw: 0,
    reasons: [],
  });
  const [errorMsg, setErrorMsg] = useState("");

  const driverId = user?.tai_xe_id || user?.id;

  useEffect(() => {
    return () => {
      runningRef.current = false;
      Speech.stop();
    };
  }, []);

  function triggerAlertFeedback(status) {
    const now = Date.now();
    if (now - lastVoiceRef.current < VOICE_COOLDOWN_MS) return;

    if (status === "BUON NGU") {
      Vibration.vibrate([0, 400, 200, 400]);
      Speech.speak(
        "Cảnh báo. Tài xế đang buồn ngủ. Hãy dừng xe nghỉ ngơi ngay.",
        { language: "vi-VN", rate: 1.0 }
      );
      lastVoiceRef.current = now;
    } else if (status === "MAT TAP TRUNG") {
      Vibration.vibrate(250);
      Speech.speak(
        "Cảnh báo. Bạn đang mất tập trung. Hãy chú ý quan sát phía trước.",
        { language: "vi-VN", rate: 1.0 }
      );
      lastVoiceRef.current = now;
    } else if (status === "MET MOI") {
      Vibration.vibrate(200);
      Speech.speak("Bạn có dấu hiệu mệt mỏi. Hãy chú ý lái xe an toàn.", {
        language: "vi-VN",
        rate: 1.0,
      });
      lastVoiceRef.current = now;
    }
  }

  async function loopAnalyze() {
    while (runningRef.current) {
      const start = Date.now();
      try {
        if (cameraRef.current) {
          const photo = await cameraRef.current.takePictureAsync({
            base64: true,
            quality: 0.35,
            skipProcessing: true,
          });

          if (!runningRef.current) break;

          if (photo?.base64) {
            const res = await apiRequest("/api/ai/analyze-frame", {
              method: "POST",
              body: JSON.stringify({
                tai_xe_id: driverId,
                image: `data:image/jpeg;base64,${photo.base64}`,
              }),
            });

            if (res.data?.success && res.data.data) {
              setErrorMsg("");
              const d = res.data.data;
              setResult(d);
              triggerAlertFeedback(d.status);
            } else {
              setErrorMsg(res.data?.message || "Lỗi phân tích khung hình.");
            }
          }
        }
      } catch (e) {
        setErrorMsg("Mất kết nối tới máy chủ AI. Đang thử lại...");
      }

      const elapsed = Date.now() - start;
      const waitMs = Math.max(200, 750 - elapsed);
      await new Promise((r) => setTimeout(r, waitMs));
    }
  }

  async function toggleMonitoring() {
    if (monitoring) {
      runningRef.current = false;
      setMonitoring(false);
      Speech.stop();
      apiRequest("/api/ai/reset-monitor", {
        method: "POST",
        body: JSON.stringify({ tai_xe_id: driverId }),
      }).catch(() => {});
      setResult((prev) => ({ ...prev, status: "TAM DUNG", reasons: [] }));
    } else {
      setErrorMsg("");
      runningRef.current = true;
      setMonitoring(true);
      loopAnalyze();
    }
  }

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerBox}>
        <Text style={styles.title}>Cần quyền Camera</Text>
        <Text style={styles.sub}>
          Chế độ giám sát dự phòng cần mở camera trước điện thoại để phát hiện buồn ngủ khi camera trên xe gặp sự cố.
        </Text>
        <TouchableOpacity style={styles.startBtn} onPress={requestPermission}>
          <Text style={styles.btnText}>CẤP QUYỀN CAMERA</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const statusColor = getStatusColor(result.status);
  const fatiguePct = Math.max(0, Math.min(100, Number(result.fatigue_score || 0)));

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Giám sát AI dự phòng</Text>

      <View style={[styles.cameraWrap, { borderColor: statusColor }]}>
        <CameraView ref={cameraRef} style={styles.camera} facing="front" />
        <View style={[styles.statusPill, { backgroundColor: statusColor }]}>
          <Text style={styles.statusPillText}>{result.status}</Text>
        </View>
      </View>

      {/* FATIGUE BAR */}
      <View style={styles.panel}>
        <View style={styles.rowBetween}>
          <Text style={styles.label}>Mức độ mệt mỏi (Fatigue)</Text>
          <Text style={[styles.pctText, { color: statusColor }]}>
            {fatiguePct.toFixed(0)}%
          </Text>
        </View>
        <View style={styles.barTrack}>
          <View
            style={[
              styles.barFill,
              { width: `${fatiguePct}%`, backgroundColor: statusColor },
            ]}
          />
        </View>

        <Text style={styles.metrics}>
          EAR: {Number(result.ear || 0).toFixed(2)} • MAR: {Number(result.mar || 0).toFixed(2)} • Pitch: {Number(result.pitch || 0).toFixed(1)}° • Yaw: {Number(result.yaw || 0).toFixed(1)}°
        </Text>

        {result.reasons && result.reasons.length > 0 ? (
          <Text style={[styles.reasons, { color: statusColor }]}>
            Lý do: {result.reasons.join(", ")}
          </Text>
        ) : null}

        {errorMsg ? <Text style={styles.err}>{errorMsg}</Text> : null}
      </View>

      <TouchableOpacity
        style={[styles.startBtn, monitoring && styles.stopBtn]}
        onPress={toggleMonitoring}
      >
        <Text style={styles.btnText}>
          {monitoring ? "TẠM DỪNG GIÁM SÁT" : "BẮT ĐẦU GIÁM SÁT DỰ PHÒNG"}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 16 },
  centerBox: {
    flex: 1,
    backgroundColor: "#020617",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  header: { color: "#fff", fontSize: 22, fontWeight: "800", marginBottom: 10 },
  title: { color: "#fff", fontSize: 20, fontWeight: "800", marginBottom: 10 },
  sub: { color: "#94a3b8", textAlign: "center", marginBottom: 20, lineHeight: 20 },
  cameraWrap: {
    flex: 1,
    borderRadius: 22,
    overflow: "hidden",
    borderWidth: 2,
    marginBottom: 12,
    position: "relative",
  },
  camera: { flex: 1 },
  statusPill: {
    position: "absolute",
    top: 12,
    alignSelf: "center",
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 999,
  },
  statusPillText: { color: "#fff", fontWeight: "900", fontSize: 13 },
  panel: {
    backgroundColor: "#0f172a",
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: "#1e293b",
    marginBottom: 12,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label: { color: "#cbd5e1", fontSize: 12, fontWeight: "700" },
  pctText: { fontSize: 15, fontWeight: "900" },
  barTrack: {
    height: 10,
    backgroundColor: "#1e293b",
    borderRadius: 999,
    overflow: "hidden",
    marginTop: 8,
  },
  barFill: { height: "100%", borderRadius: 999 },
  metrics: { color: "#94a3b8", fontSize: 11, marginTop: 8 },
  reasons: { fontSize: 12, fontWeight: "700", marginTop: 6 },
  err: { color: "#f87171", fontSize: 12, marginTop: 6 },
  startBtn: {
    backgroundColor: "#16a34a",
    borderRadius: 16,
    padding: 15,
    alignItems: "center",
  },
  stopBtn: {
    backgroundColor: "#dc2626",
  },
  btnText: { color: "#fff", fontWeight: "800", letterSpacing: 0.5 },
});
