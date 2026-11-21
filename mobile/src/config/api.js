import AsyncStorage from "@react-native-async-storage/async-storage";

// Doi sang IP Wi-Fi may tinh chay Docker/Backend (vd: http://192.168.1.15:5000)
// Hoac doi truc tiep ngay tren man hinh Dang nhap cua App
export const DEFAULT_API_URL = "http://192.168.1.10:5000";

export const STORAGE_KEYS = {
  TOKEN: "dacn1_token",
  USER: "dacn1_user",
  API_URL: "dacn1_api_url",
};

export async function getApiBaseUrl() {
  const saved = await AsyncStorage.getItem(STORAGE_KEYS.API_URL);
  return (saved || DEFAULT_API_URL).replace(/\/+$/, "");
}

export async function apiRequest(path, options = {}) {
  const baseUrl = await getApiBaseUrl();
  const token = await AsyncStorage.getItem(STORAGE_KEYS.TOKEN);

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({
    success: false,
    message: `Lỗi máy chủ (HTTP ${response.status})`,
  }));

  if (!response.ok && data.success === undefined) {
    data.success = false;
  }

  return { ok: response.ok, status: response.status, data };
}
