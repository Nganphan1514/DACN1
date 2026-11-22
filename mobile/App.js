import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import SchedulesScreen from "./src/screens/SchedulesScreen";
import ViolationsScreen from "./src/screens/ViolationsScreen";
import NotificationsScreen from "./src/screens/NotificationsScreen";
import ReportsScreen from "./src/screens/ReportsScreen";
import FaceRegisterScreen from "./src/screens/FaceRegisterScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

const Tab = createBottomTabNavigator();

function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#22d3ee" />
      </View>
    );
  }

  if (!user) {
    return <LoginScreen />;
  }

  const isDriver = user.vai_tro === "tai_xe";

  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            backgroundColor: "#0f172a",
            borderTopColor: "#1e293b",
            height: 62,
            paddingBottom: 8,
            paddingTop: 6,
          },
          tabBarLabelStyle: {
            fontSize: 10,
            fontWeight: "700",
          },
          tabBarActiveTintColor: "#22d3ee",
          tabBarInactiveTintColor: "#64748b",
        }}
      >
        <Tab.Screen name="Tổng quan" component={DashboardScreen} />
        <Tab.Screen name="Lịch chạy" component={SchedulesScreen} />
        {isDriver && (
          <Tab.Screen name="Vi phạm" component={ViolationsScreen} />
        )}
        {isDriver && (
          <Tab.Screen name="Thông báo" component={NotificationsScreen} />
        )}
        <Tab.Screen name="Sự cố" component={ReportsScreen} />
        {isDriver && (
          <Tab.Screen name="Khuôn mặt" component={FaceRegisterScreen} />
        )}
        <Tab.Screen name="Tài khoản" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <AppNavigator />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    backgroundColor: "#020617",
    justifyContent: "center",
    alignItems: "center",
  },
});
