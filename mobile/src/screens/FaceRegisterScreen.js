import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { apiRequest } from "../config/api";

export default function FaceRegisterScreen({
  targetDriverId,
  targetDriverName,
  onDone,
}) {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef(null);
  const [facing, setFacing] = useState("back");
  const [capturing, setCapturing] = useState(false);
  const [statusText, setStatusText] = useState(
    "Đưa khuôn mặt tài xế vào giữa khung hình, đủ sáng và nhìn thẳng."
  );

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerBox}>
        <Text style={styles.title}>Cần quyền truy cập Camera</Text>
        <Text style={styles.sub}>
          Quản lý cần mở camera để chụp 3 mẫu khuôn mặt 128D cho tài xế lưu lên Supabase.
        </Text>
        <TouchableOpacity style={styles.btn} onPress={requestPermission}>
          <Text style={styles.btnText}>CẤP QUYỀN CAMERA</Text>
        </TouchableOpacity>
      </View>
    );
  }

  async function handleCaptureAndRegister() {
    if (!cameraRef.current || capturing || !targetDriverId) return;

    setCapturing(true);
    try {
      const images = [];
      for (let i = 1; i <= 3; i++) {
        setStatusText(`Đang chụp mẫu ${i}/3 cho ${targetDriverName || "tài xế"}...`);
        const photo = await cameraRef.current.takePictureAsync({
          base64: true,
          quality: 0.75,
        });
        if (photo?.base64) {
          images.push(`data:image/jpeg;base64,${photo.base64}`);
        }
        if (i < 3) {
          await new Promise((r) => setTimeout(r, 350));
        }
      }

      setStatusText("Đang trích xuất vector khuôn mặt 128D trên máy chủ...");

      const res = await apiRequest("/api/admin/drivers/register-face", {
        method: "POST",
        body: JSON.stringify({
          tai_xe_id: targetDriverId,
          images,
        }),
      });

      if (res.data?.success) {
        setStatusText(res.data.message || "Đăng ký khuôn mặt thành công!");
        Alert.alert(
          "Thành công",
          res.data.message || "Đã lưu dữ liệu khuôn mặt 128D.",
          [{ text: "Xong", onPress: () => onDone && onDone() }]
        );
      } else {
        setStatusText(res.data?.message || "Đăng ký thất bại.");
        Alert.alert("Không hợp lệ", res.data?.message || "Vui lòng thử lại ở nơi đủ sáng.");
      }
    } catch (e) {
      setStatusText("Lỗi kết nối máy chủ.");
      Alert.alert("Lỗi", "Không thể gửi ảnh khuôn mặt lên máy chủ.");
    } finally {
      setCapturing(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.header}>Đăng ký khuôn mặt 128D</Text>
          <Text style={styles.driverLabel}>
            Tài xế: {targetDriverName || `#${targetDriverId}`} (ID #{targetDriverId})
          </Text>
        </View>
        <TouchableOpacity
          style={styles.flipBtn}
          onPress={() => setFacing((f) => (f === "back" ? "front" : "back"))}
        >
          <Text style={styles.flipText}>Đổi cam</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.cameraWrap}>
        <CameraView ref={cameraRef} style={styles.camera} facing={facing} />
      </View>

      <Text style={styles.status}>{statusText}</Text>

      <TouchableOpacity
        style={[styles.btn, capturing && { opacity: 0.65 }]}
        onPress={handleCaptureAndRegister}
        disabled={capturing}
      >
        {capturing ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnText}>CHỤP 3 MẪU & LƯU KHUÔN MẶT</Text>
        )}
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
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  header: { color: "#fff", fontSize: 20, fontWeight: "800" },
  driverLabel: { color: "#22d3ee", fontSize: 13, fontWeight: "600", marginTop: 2 },
  flipBtn: {
    backgroundColor: "#1e293b",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#334155",
  },
  flipText: { color: "#f8fafc", fontSize: 12, fontWeight: "700" },
  title: { color: "#fff", fontSize: 20, fontWeight: "800", marginBottom: 10 },
  sub: { color: "#94a3b8", textAlign: "center", marginBottom: 20, lineHeight: 20 },
  cameraWrap: {
    flex: 1,
    borderRadius: 24,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "#06b6d4",
    marginBottom: 14,
  },
  camera: { flex: 1 },
  status: {
    color: "#cbd5e1",
    textAlign: "center",
    marginBottom: 14,
    fontSize: 13,
  },
  btn: {
    backgroundColor: "#0891b2",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "800", letterSpacing: 0.5 },
});
