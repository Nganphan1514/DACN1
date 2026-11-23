import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import { COLORS } from "./src/theme/tokens";
import LoginScreen from "./src/screens/LoginScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import AdminDriversScreen from "./src/screens/AdminDriversScreen";
import AdminOpsScreen from "./src/screens/AdminOpsScreen";
import SchedulesScreen from "./src/screens/SchedulesScreen";
import ViolationsScreen from "./src/screens/ViolationsScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

const Tab = createBottomTabNavigator();

const TAB_ICONS = {
  Cabin: ["speedometer", "speedometer-outline"],
  "Lịch trình": ["calendar", "calendar-outline"],
  "An toàn": ["shield-checkmark", "shield-checkmark-outline"],
  "Điều hành": ["pulse", "pulse-outline"],
  "Đội ngũ": ["people", "people-outline"],
  "Lịch & Sự cố": ["briefcase", "briefcase-outline"],
  "Cá nhân": ["person-circle", "person-circle-outline"],
};

function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color={COLORS.primary} />
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
            return <Ionicons name={focused ? pair[0] : pair[1]} size={size} color={color} />;
          },
          tabBarStyle: {
            backgroundColor: COLORS.surfaceElevated,
            borderTopColor: COLORS.borderElevated,
            borderTopWidth: 1,
            height: 68,
            paddingBottom: 10,
            paddingTop: 8,
          },
          tabBarLabelStyle: {
            fontSize: 11,
            fontWeight: "700",
          },
          tabBarActiveTintColor: COLORS.primary,
          tabBarInactiveTintColor: COLORS.textMuted,
        })}
      >
        {isDriver ? (
          <>
            <Tab.Screen name="Cabin" component={DashboardScreen} />
            <Tab.Screen name="Lịch trình" component={SchedulesScreen} />
            <Tab.Screen name="An toàn" component={ViolationsScreen} />
            <Tab.Screen name="Cá nhân" component={ProfileScreen} />
          </>
        ) : (
          <>
            <Tab.Screen name="Điều hành" component={DashboardScreen} />
            <Tab.Screen name="Đội ngũ" component={AdminDriversScreen} />
            <Tab.Screen name="Lịch & Sự cố" component={AdminOpsScreen} />
            <Tab.Screen name="Cá nhân" component={ProfileScreen} />
          </>
        )}
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
    backgroundColor: COLORS.bgCanvas,
    justifyContent: "center",
    alignItems: "center",
  },
});
