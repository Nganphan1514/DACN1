@echo off
chcp 65001 >nul
title DACN1 V3 - Backend API ^& Web Server
cd /d "%~dp0"

echo ========================================================
echo   DACN1 V3.0 - KHOI CHAY BACKEND API ^& WEB SERVER
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong ao venv\Scripts\python.exe
    echo Hay tao venv hoac kiem tra lai duong dan du an.
    pause
    exit /b 1
)

echo [INFO] Web Quan tri / Tai xe (Local): http://127.0.0.1:5000
echo [INFO] Trung tam Van hanh V3:           http://127.0.0.1:5000/admin/operations
echo [INFO] Dien thoai cung Wi-Fi ket noi:   http://IP_LAN_MAY_TINH:5000
echo [INFO] Nhan Ctrl + C de dung server.
echo.

set PYTHONPATH=%~dp0
set FLASK_HOST=0.0.0.0
set FLASK_PORT=5000
"venv\Scripts\python.exe" backend\app.py

echo.
echo [INFO] Server da dung.
pause
