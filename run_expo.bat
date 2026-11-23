@echo off
chcp 65001 >nul
title DACN1 V3 - Expo Mobile App (SDK 58)
cd /d "%~dp0mobile"

echo ========================================================
echo   DACN1 V3.0 - KHOI CHAY EXPO MOBILE APP (SDK 58)
echo ========================================================
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong tim thay Node.js trong PATH. Vui long cai dat Node.js truoc.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [INFO] Chua co node_modules. Dang chay npm install...
    call npm install
    if errorlevel 1 (
        echo [LOI] npm install that bai.
        pause
        exit /b 1
    )
)

echo [INFO] Hay mo Expo Go (SDK 58) tren dien thoai cung mang Wi-Fi de quet ma QR.
echo [INFO] Nho chay run_web.bat truoc va nhap dung IP LAN may tinh trong Server URL tren App.
echo.

call npx expo start

echo.
echo [INFO] Expo Dev Server da dung.
pause
