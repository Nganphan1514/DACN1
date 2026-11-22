import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { apiRequest } from "../config/api";

// Hien thong bao day + phat chuong ngay ca khi dang mo App
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function registerForPushNotificationsAsync() {
  try {
    if (!Device.isDevice) {
      // Simulator/Emulator khong tao duoc Expo Push Token that
      return null;
    }

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("alerts", {
        name: "Cảnh báo khẩn cấp DACN1",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 300, 200, 300],
        lightColor: "#ef4444",
      });
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      return null;
    }

    const tokenResp = await Notifications.getExpoPushTokenAsync();
    const expoPushToken = tokenResp?.data;

    if (expoPushToken) {
      await apiRequest("/api/push/register-token", {
        method: "POST",
        body: JSON.stringify({
          expo_push_token: expoPushToken,
          platform: Platform.OS,
        }),
      });
    }

    return expoPushToken;
  } catch (e) {
    console.warn("Register push token error:", e);
    return null;
  }
}

export async function unregisterPushTokenAsync(expoPushToken) {
  if (!expoPushToken) return;
  try {
    await apiRequest("/api/push/unregister-token", {
      method: "POST",
      body: JSON.stringify({ expo_push_token: expoPushToken }),
    });
  } catch (e) {
    console.warn("Unregister push token error:", e);
  }
}
