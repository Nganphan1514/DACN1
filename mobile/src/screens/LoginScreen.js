import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useAuth } from "../context/AuthContext";

export default function LoginScreen() {
  const { apiUrl, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [serverUrl, setServerUrl] = useState(apiUrl);
  const [showServerConfig, setShowServerConfig] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin() {
    if (!username.trim() || !password.trim()) {
      setError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.");
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      const result = await login(username.trim(), password.trim(), serverUrl.trim());
      if (!result.success) {
        setError(result.message);
      }
    } catch (e) {
      setError("Không kết nối được máy chủ. Kiểm tra lại Server URL và Wi-Fi chung mạng.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.brand}>DACN1</Text>
        <Text style={styles.subtitle}>Hệ thống giám sát tài xế bằng AI</Text>

        <Text style={styles.label}>TÊN ĐĂNG NHẬP</Text>
        <TextInput
          style={styles.input}
          placeholder="admin hoặc taixe01"
          placeholderTextColor="#64748b"
          autoCapitalize="none"
          value={username}
          onChangeText={setUsername}
        />

        <Text style={styles.label}>MẬT KHẨU</Text>
        <TextInput
          style={styles.input}
          placeholder="Nhập mật khẩu"
          placeholderTextColor="#64748b"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity
          onPress={() => setShowServerConfig((v) => !v)}
          style={styles.toggleServer}
        >
          <Text style={styles.toggleServerText}>
            {showServerConfig ? "Ẩn cấu hình máy chủ" : "Cấu hình địa chỉ máy chủ (IP LAN)"}
          </Text>
        </TouchableOpacity>

        {showServerConfig && (
          <View style={styles.serverBox}>
            <Text style={styles.label}>SERVER URL (BACKEND DOCKER)</Text>
            <TextInput
              style={styles.input}
              placeholder="http://192.168.1.15:5000"
              placeholderTextColor="#64748b"
              autoCapitalize="none"
              value={serverUrl}
              onChangeText={setServerUrl}
            />
          </View>
        )}

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity
          style={[styles.button, submitting && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>ĐĂNG NHẬP</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#020617",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: "#0f172a",
    borderRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  brand: {
    color: "#ffffff",
    fontSize: 34,
    fontWeight: "900",
    textAlign: "center",
  },
  subtitle: {
    color: "#94a3b8",
    textAlign: "center",
    marginTop: 6,
    marginBottom: 24,
  },
  label: {
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: "#1e293b",
    color: "#f8fafc",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#334155",
  },
  toggleServer: {
    marginTop: 14,
    alignItems: "flex-end",
  },
  toggleServerText: {
    color: "#22d3ee",
    fontSize: 12,
    fontWeight: "600",
  },
  serverBox: {
    marginTop: 4,
  },
  error: {
    color: "#f87171",
    fontSize: 13,
    textAlign: "center",
    marginTop: 14,
  },
  button: {
    backgroundColor: "#2563eb",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
    marginTop: 20,
  },
  buttonDisabled: {
    opacity: 0.65,
  },
  buttonText: {
    color: "#ffffff",
    fontWeight: "800",
    letterSpacing: 0.6,
  },
});
