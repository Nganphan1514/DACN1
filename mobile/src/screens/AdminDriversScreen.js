import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { apiRequest } from "../config/api";
import FaceRegisterScreen from "./FaceRegisterScreen";

/**
 * Phan tich ma QR tren Can cuoc cong dan (CCCD) gan chip Viet Nam:
 * Dinh dang chuan Bo Cong An:
 *   SoCCCD|SoCMND_Cu|HoTen|NgaySinh(DDMMYYYY)|GioiTinh|DiaChiThuongTru|NgayCap
 */
function parseVietnamCCCDQr(rawData) {
  if (!rawData || typeof rawData !== "string") return null;
  const parts = rawData.split("|").map((s) => s.trim());
  if (parts.length < 6) return null;

  const soCccd = parts[0] || "";
  const hoTen = parts[2] || "";
  const ngaySinhRaw = parts[3] || "";
  const gioiTinh = parts[4] || "";
  const diaChi = parts[5] || "";

  let ngaySinh = ngaySinhRaw;
  if (ngaySinhRaw.length === 8) {
    ngaySinh = `${ngaySinhRaw.slice(0, 2)}/${ngaySinhRaw.slice(2, 4)}/${ngaySinhRaw.slice(4)}`;
  }

  const last4 = soCccd.length >= 4 ? soCccd.slice(-4) : String(Date.now()).slice(-4);
  return {
    soCccd,
    hoTen,
    ngaySinh,
    gioiTinh,
    diaChi,
    suggestedUsername: `taixe_${last4}`,
  };
}

export default function AdminDriversScreen() {
  const [drivers, setDrivers] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  // Che do hien thi: "list" | "create" | "scan_cccd" | "register_face"
  const [mode, setMode] = useState("list");
  const [selectedDriver, setSelectedDriver] = useState(null);

  // Form tao tai khoan tai xe
  const [hoTen, setHoTen] = useState("");
  const [soCccd, setSoCccd] = useState("");
  const [diaChi, setDiaChi] = useState("");
  const [soDienThoai, setSoDienThoai] = useState("");
  const [soGplx, setSoGplx] = useState("");
  const [tenDangNhap, setTenDangNhap] = useState("");
  const [matKhau, setMatKhau] = useState("123456");
  const [submitting, setSubmitting] = useState(false);

  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);

  const loadDrivers = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await apiRequest("/api/admin/drivers");
      if (res.data?.success && Array.isArray(res.data.data)) {
        setDrivers(res.data.data);
      }
    } catch (e) {
      console.warn("Load drivers error:", e);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDrivers();
  }, [loadDrivers]);

  function resetForm() {
    setHoTen("");
    setSoCccd("");
    setDiaChi("");
    setSoDienThoai("");
    setSoGplx("");
    setTenDangNhap("");
    setMatKhau("123456");
  }

  async function openCccdScanner() {
    if (!permission?.granted) {
      const res = await requestPermission();
      if (!res.granted) {
        Alert.alert("Thiếu quyền", "Vui lòng cấp quyền Camera để quét QR Căn cước công dân.");
        return;
      }
    }
    setScanned(false);
    setMode("scan_cccd");
  }

  function handleBarcodeScanned({ data }) {
    if (scanned) return;
    setScanned(true);

    const parsed = parseVietnamCCCDQr(data);
    if (!parsed) {
      Alert.alert(
        "Không phải mã QR CCCD",
        "Vui lòng quét mã QR ở góc trên bên phải mặt trước Căn cước công dân gắn chip.",
        [{ text: "Quét lại", onPress: () => setScanned(false) }]
      );
      return;
    }

    setSoCccd(parsed.soCccd);
    setHoTen(parsed.hoTen);
    setDiaChi(parsed.diaChi);
    if (!tenDangNhap) setTenDangNhap(parsed.suggestedUsername);

    Alert.alert(
      "Đã quét thành công CCCD",
      `Họ tên: ${parsed.hoTen}\nCCCD: ${parsed.soCccd}\nNgày sinh: ${parsed.ngaySinh}\nĐịa chỉ: ${parsed.diaChi}`
    );
    setMode("create");
  }

  async function handleCreateDriver() {
    if (!hoTen.trim() || !tenDangNhap.trim() || !matKhau.trim()) {
      Alert.alert("Thiếu thông tin", "Vui lòng nhập Họ tên, Tên đăng nhập và Mật khẩu.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiRequest("/api/admin/drivers", {
        method: "POST",
        body: JSON.stringify({
          ten_dang_nhap: tenDangNhap.trim(),
          mat_khau: matKhau.trim(),
          ho_ten: hoTen.trim(),
          so_dien_thoai: soDienThoai.trim() || null,
          so_gplx: soGplx.trim() || null,
          dia_chi: diaChi.trim() || null,
          trang_thai: "dang_lam",
        }),
      });

      if (res.data?.success) {
        const newId = res.data.id;
        const createdName = hoTen.trim();
        resetForm();
        loadDrivers();

        Alert.alert(
          "Tạo tài khoản thành công",
          `Đã tạo tài xế ${createdName} (ID #${newId}). Bạn có muốn đăng ký khuôn mặt 128D ngay cho tài xế này không?`,
          [
            { text: "Để sau", onPress: () => setMode("list") },
            {
              text: "Đăng ký khuôn mặt ngay",
              onPress: () => {
                setSelectedDriver({ id: newId, ho_ten: createdName });
                setMode("register_face");
              },
            },
          ]
        );
      } else {
        Alert.alert("Tạo thất bại", res.data?.message || "Kiểm tra trùng tên đăng nhập hoặc GPLX.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // 1. MAN HINH DANG KY KHUON MAT CHO TAI XE DUOC CHON
  if (mode === "register_face" && selectedDriver) {
    return (
      <View style={{ flex: 1, backgroundColor: "#020617" }}>
        <TouchableOpacity style={styles.backBar} onPress={() => setMode("list")}>
          <Text style={styles.backText}>← Quay lại danh sách tài xế</Text>
        </TouchableOpacity>
        <FaceRegisterScreen
          targetDriverId={selectedDriver.id}
          targetDriverName={selectedDriver.ho_ten}
          onDone={() => {
            setMode("list");
            loadDrivers();
          }}
        />
      </View>
    );
  }

  // 2. MAN HINH QUET QR CAN CUOC CONG DAN (CCCD)
  if (mode === "scan_cccd") {
    return (
      <View style={styles.container}>
        <TouchableOpacity style={styles.backBarInline} onPress={() => setMode("create")}>
          <Text style={styles.backText}>← Quay lại form đăng ký</Text>
        </TouchableOpacity>
        <Text style={styles.header}>Quét QR Căn cước công dân</Text>
        <Text style={styles.sub}>
          Hướng camera vào mã QR nhỏ ở góc trên bên phải mặt trước thẻ CCCD gắn chip.
        </Text>
        <View style={styles.scannerBox}>
          <CameraView
            style={{ flex: 1 }}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
          />
        </View>
      </View>
    );
  }

  // 3. MAN HINH FORM TAO TAI KHOAN TAI XE (CO QUET QR CCCD)
  if (mode === "create") {
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
        <TouchableOpacity style={styles.backBarInline} onPress={() => setMode("list")}>
          <Text style={styles.backText}>← Quay lại danh sách tài xế</Text>
        </TouchableOpacity>

        <Text style={styles.header}>Tạo tài khoản tài xế</Text>

        <TouchableOpacity style={styles.scanBtn} onPress={openCccdScanner}>
          <Text style={styles.scanBtnText}>📷 QUÉT QR CĂN CƯỚC CÔNG DÂN (CCCD)</Text>
        </TouchableOpacity>

        {soCccd ? (
          <Text style={styles.cccdTag}>Số CCCD đã quét: {soCccd}</Text>
        ) : null}

        <Text style={styles.label}>HỌ VÀ TÊN *</Text>
        <TextInput
          style={styles.input}
          placeholder="Tự điền khi quét CCCD hoặc nhập tay"
          placeholderTextColor="#64748b"
          value={hoTen}
          onChangeText={setHoTen}
        />

        <Text style={styles.label}>ĐỊA CHỈ THƯỜNG TRÚ</Text>
        <TextInput
          style={styles.input}
          placeholder="Tự điền khi quét CCCD"
          placeholderTextColor="#64748b"
          value={diaChi}
          onChangeText={setDiaChi}
        />

        <Text style={styles.label}>SỐ ĐIỆN THOẠI</Text>
        <TextInput
          style={styles.input}
          placeholder="0905xxxxxx"
          placeholderTextColor="#64748b"
          keyboardType="phone-pad"
          value={soDienThoai}
          onChangeText={setSoDienThoai}
        />

        <Text style={styles.label}>SỐ GIẤY PHÉP LÁI XE (GPLX)</Text>
        <TextInput
          style={styles.input}
          placeholder="VD: GPLX006"
          placeholderTextColor="#64748b"
          value={soGplx}
          onChangeText={setSoGplx}
        />

        <Text style={styles.label}>TÊN ĐĂNG NHẬP *</Text>
        <TextInput
          style={styles.input}
          placeholder="VD: taixe06"
          placeholderTextColor="#64748b"
          autoCapitalize="none"
          value={tenDangNhap}
          onChangeText={setTenDangNhap}
        />

        <Text style={styles.label}>MẬT KHẨU ĐĂNG NHẬP *</Text>
        <TextInput
          style={styles.input}
          placeholder="Mật khẩu ban đầu"
          placeholderTextColor="#64748b"
          value={matKhau}
          onChangeText={setMatKhau}
        />

        <TouchableOpacity
          style={[styles.createBtn, submitting && { opacity: 0.65 }]}
          onPress={handleCreateDriver}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.createBtnText}>TẠO TÀI KHOẢN TÀI XẾ</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // 4. DANH SACH TAI XE (QUAN LY)
  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <Text style={styles.header}>Quản lý Tài xế</Text>
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => {
            resetForm();
            setMode("create");
          }}
        >
          <Text style={styles.addBtnText}>+ Thêm / Quét CCCD</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={drivers}
        keyExtractor={(item, idx) => String(item.id || idx)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={loadDrivers} tintColor="#22d3ee" />
        }
        contentContainerStyle={{ gap: 12, paddingBottom: 30 }}
        ListEmptyComponent={<Text style={styles.empty}>Chưa có tài xế nào.</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardTop}>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{item.ho_ten || `Tài xế #${item.id}`}</Text>
                <Text style={styles.meta}>
                  ID #{item.id} • SĐT: {item.so_dien_thoai || "Chưa có"} • GPLX: {item.so_gplx || "Chưa có"}
                </Text>
                <Text style={styles.meta}>Địa chỉ: {item.dia_chi || "Chưa cập nhật"}</Text>
              </View>
            </View>

            <TouchableOpacity
              style={styles.faceBtn}
              onPress={() => {
                setSelectedDriver({ id: item.id, ho_ten: item.ho_ten });
                setMode("register_face");
              }}
            >
              <Text style={styles.faceBtnText}>📷 Đăng ký / Đăng ký lại khuôn mặt 128D</Text>
            </TouchableOpacity>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#020617", padding: 16 },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  backBar: { paddingTop: 14, paddingHorizontal: 16, paddingBottom: 4 },
  backBarInline: { marginBottom: 10 },
  backText: { color: "#22d3ee", fontWeight: "700", fontSize: 14 },
  header: { color: "#fff", fontSize: 22, fontWeight: "800" },
  sub: { color: "#94a3b8", fontSize: 13, marginTop: 6, marginBottom: 14 },
  addBtn: {
    backgroundColor: "#2563eb",
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderRadius: 12,
  },
  addBtnText: { color: "#fff", fontWeight: "800", fontSize: 12 },
  scanBtn: {
    backgroundColor: "#0891b2",
    borderRadius: 14,
    padding: 15,
    alignItems: "center",
    marginTop: 12,
    marginBottom: 10,
  },
  scanBtnText: { color: "#fff", fontWeight: "800", fontSize: 13 },
  cccdTag: { color: "#34d399", fontWeight: "700", fontSize: 13, marginBottom: 6 },
  scannerBox: {
    flex: 1,
    borderRadius: 22,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "#22d3ee",
  },
  label: { color: "#94a3b8", fontSize: 11, fontWeight: "700", marginTop: 10, marginBottom: 4 },
  input: {
    backgroundColor: "#0f172a",
    color: "#f8fafc",
    borderRadius: 12,
    padding: 13,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  createBtn: {
    marginTop: 20,
    backgroundColor: "#16a34a",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
  },
  createBtnText: { color: "#fff", fontWeight: "800", letterSpacing: 0.5 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40 },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 18,
    padding: 15,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  cardTop: { flexDirection: "row", justifyContent: "space-between" },
  name: { color: "#fff", fontSize: 16, fontWeight: "800" },
  meta: { color: "#94a3b8", fontSize: 12, marginTop: 3 },
  faceBtn: {
    marginTop: 12,
    backgroundColor: "#1e293b",
    borderWidth: 1,
    borderColor: "#06b6d4",
    borderRadius: 12,
    padding: 11,
    alignItems: "center",
  },
  faceBtnText: { color: "#22d3ee", fontWeight: "700", fontSize: 12 },
});
