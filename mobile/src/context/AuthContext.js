import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiRequest, DEFAULT_API_URL, STORAGE_KEYS } from "../config/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      try {
        const [savedToken, savedUser, savedUrl] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.TOKEN),
          AsyncStorage.getItem(STORAGE_KEYS.USER),
          AsyncStorage.getItem(STORAGE_KEYS.API_URL),
        ]);
        if (savedUrl) setApiUrl(savedUrl);
        if (savedToken && savedUser) {
          setToken(savedToken);
          setUser(JSON.parse(savedUser));
        }
      } catch (e) {
        console.warn("Restore session error:", e);
      } finally {
        setLoading(false);
      }
    }
    restoreSession();
  }, []);

  async function updateApiUrl(newUrl) {
    const cleaned = (newUrl || DEFAULT_API_URL).trim().replace(/\/+$/, "");
    await AsyncStorage.setItem(STORAGE_KEYS.API_URL, cleaned);
    setApiUrl(cleaned);
  }

  async function login(ten_dang_nhap, mat_khau, customUrl) {
    if (customUrl) {
      await updateApiUrl(customUrl);
    }

    const res = await apiRequest("/api/login", {
      method: "POST",
      body: JSON.stringify({ ten_dang_nhap, mat_khau }),
    });

    if (!res.data?.success) {
      return {
        success: false,
        message: res.data?.message || "Đăng nhập thất bại.",
      };
    }

    await AsyncStorage.setItem(STORAGE_KEYS.TOKEN, res.data.token || "");
    await AsyncStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(res.data.user || {}));
    setToken(res.data.token);
    setUser(res.data.user);

    return { success: true };
  }

  async function logout() {
    await AsyncStorage.multiRemove([STORAGE_KEYS.TOKEN, STORAGE_KEYS.USER]);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, token, apiUrl, loading, login, logout, updateApiUrl }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
