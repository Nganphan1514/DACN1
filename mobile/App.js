import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import MonitorScreen from "./src/screens/MonitorScreen";
import AdminDriversScreen from "./src/screens/AdminDriversScreen";
import SchedulesScreen from "./src/screens/SchedulesScreen";
import ViolationsScreen from "./src/screens/ViolationsScreen";
import NotificationsScreen from "./src/screens/NotificationsScreen";
import ReportsScreen from "./src/screens/ReportsScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

const Tab = createBottomTabNavigator();

const TAB_ICONS = {
  Cabin: ["speedometer", "speedometer-outline"],
  "AI Cam": ["eye", "eye-outline"],
  "Tài xế": ["people", "people-outline"],
  "Lịch": ["calendar", "calendar-outline"],
  "Vi phạm": ["warning", "warning-outline"],
  "T.Báo": ["notifications", "notifications-outline"],
  "Sự cố": ["construct", "construct-outline"],
  "Cá nhân": ["person-circle", "person-circle-outline"],
};

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
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ focused, color, size }) => {
            const pair = TAB_ICONS[route.name] || ["ellipse", "ellipse-outline"];
            return <Ionicons name={focused ? pair[0] : pair[1]} size={size - 2} color={color} />;
          },
          tabBarStyle: {
            backgroundColor: "#0f172a",
            borderTopColor: "#1e293b",
            height: 64,
            paddingBottom: 8,
            paddingTop: 6,
          },
          tabBarLabelStyle: {
            fontSize: 9.5,
            fontWeight: "700",
          },
          tabBarActiveTintColor: "#22d3ee",
          tabBarInactiveTintColor: "#64748b",
        })}
      >
        <Tab.Screen name="Cabin" component={DashboardScreen} />
        {!isDriver && (
          <Tab.Screen name="Tài xế" component={AdminDriversScreen} />
        )}
        {isDriver && (
          <Tab.Screen name="AI Cam" component={MonitorScreen} />
        )}
        <Tab.Screen name="Lịch" component={SchedulesScreen} />
        {isDriver && (
          <Tab.Screen name="Vi phạm" component={ViolationsScreen} />
        )}
        {isDriver && (
          <Tab.Screen name="T.Báo" component={NotificationsScreen} />
        )}
        <Tab.Screen name="Sự cố" component={ReportsScreen} />
        <Tab.Screen name="Cá nhân" component={ProfileScreen} />
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
