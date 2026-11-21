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
import { useAuth } from "../context/AuthContext";

export default function FaceRegisterScreen() {
  const { user } = useAuth();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef(null);
  const [capturing, setCapturing] = useState(false);
  const [statusText, setStatusText] = useState("Giữ khuôn mặt ngay giữa khung hình và đủ sáng.");

  const driverId = user?.tai_xe_id || user?.id;

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerBox}>
        <Text style={styles.title}>Cần quyền truy cập Camera</Text>
        <Text style={styles.sub}>
          Ứng dụng sử dụng camera trước để chụp 3 mẫu khuôn mặt 128D đăng ký lên Supabase.
        </Text>
        <TouchableOpacity style={styles.btn} onPress={requestPermission}>
          <Text style={styles.btnText}>CẤP QUYỀN CAMERA</Text>
        </TouchableOpacity>
      </View>
    );
  }

  async function handleCaptureAndRegister() {
    if (!cameraRef.current || capturing) return;

    setCapturing(true);
    try {
      const images = [];
      for (let i = 1; i <= 3; i++) {
        setStatusText(`Đang chụp mẫu ${i}/3... Giữ nguyên khuôn mặt`);
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

      const res = await apiRequest("/api/driver/register-face", {
        method: "POST",
        body: JSON.stringify({
          tai_xe_id: driverId,
          images,
        }),
      });

      if (res.data?.success) {
        setStatusText(res.data.message || "Đăng ký khuôn mặt thành công!");
        Alert.alert("Thành công", res.data.message || "Đã lưu dữ liệu khuôn mặt 128D.");
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
      <Text style={styles.header}>Đăng ký khuôn mặt 128D</Text>

      <View style={styles.cameraWrap}>
        <CameraView ref={cameraRef} style={styles.camera} facing="front" />
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
          <Text style={styles.btnText}>QUÉT & ĐĂNG KÝ KHUÔN MẶT</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 18 },
  centerBox: {
    flex: 1,
    backgroundColor: "#020617",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  header: { color: "#fff", fontSize: 22, fontWeight: "800", marginBottom: 14 },
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
