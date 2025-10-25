@echo off
chcp 65001 >nul
color 0B
title PDF Question Generator - Quick Run
echo ========================================
echo   PDF Question Generator v2.0
echo   Quick Install ^& Run
echo ========================================
echo.

cd /d "%~dp0"

REM ==================================
REM   BƯỚC 1: KIỂM TRA PYTHON
REM ==================================
echo [1/6] Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python không được cài đặt!
    echo.
    echo Vui lòng cài đặt Python 3.8+ từ:
    echo https://www.python.org/downloads/
    echo.
    echo Lưu ý: Tick vào "Add Python to PATH" khi cài
    pause
    exit /b 1
)
python --version
echo [OK] Python đã sẵn sàng
echo.

REM ==================================
REM   BƯỚC 2: KIỂM TRA DEPENDENCIES
REM ==================================
echo [2/6] Kiểm tra dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [INFO] Đang cài đặt dependencies vào máy...
    echo Có thể mất 2-3 phút, vui lòng chờ...
    echo.
    python -m pip install --upgrade pip
    pip install -r backend\requirements.txt
    if errorlevel 1 (
        color 0C
        echo [ERROR] Không thể cài đặt dependencies
        echo.
        echo Thử cài thủ công:
        echo   pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies đã được cài đặt
) else (
    echo [OK] Dependencies đã có sẵn, bỏ qua cài đặt
)
echo.

REM ==================================
REM   BƯỚC 3: KIỂM TRA .ENV
REM ==================================
echo [3/6] Kiểm tra cấu hình...
if not exist "backend\.env" (
    color 0E
    echo [WARNING] File .env không tồn tại!
    echo.
    echo Đang tạo file .env mẫu...
    (
        echo OPENAI_API_KEY=your-openai-api-key-here
        echo OPENAI_MODEL=gpt-3.5-turbo
    ) > backend\.env
    echo.
    echo [ACTION REQUIRED] Vui lòng:
    echo 1. Mở file: backend\.env
    echo 2. Thay your-openai-api-key-here bằng API key thật
    echo 3. Lưu file và chạy lại script này
    echo.
    color 0C
    pause
    exit /b 1
)
echo [OK] File .env đã tồn tại
echo.

REM ==================================
REM   BƯỚC 4: KHỞI ĐỘNG BACKEND
REM ==================================
echo [4/6] Khởi động Backend Server...
echo Backend đang chạy tại: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo.
start "Backend Server" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul
echo [OK] Backend đã khởi động
echo.

REM ==================================
REM   BƯỚC 5: KHỞI ĐỘNG FRONTEND
REM ==================================
echo [5/5] Khởi động Frontend Server...
echo Frontend đang chạy tại: http://127.0.0.1:8080
echo.
start "Frontend Server" cmd /k "cd /d %~dp0 && python -m http.server 8080"
timeout /t 3 >nul
echo [OK] Frontend đã khởi động
echo.

REM ==================================
REM   BƯỚC 6: MỞ TRÌNH DUYỆT
REM ==================================
echo [6/6] Mở trình duyệt...
timeout /t 2 >nul
start "" "http://127.0.0.1:8080/frontend/index.html"
echo [OK] Trình duyệt đã mở
echo.

REM ==================================
REM   HOÀN TẤT
REM ==================================
color 0A
echo ========================================
echo   ✓ HOÀN TẤT!
echo ========================================
echo.
echo Backend API:  http://127.0.0.1:8000
echo API Docs:     http://127.0.0.1:8000/docs
echo Frontend:     http://127.0.0.1:8080/frontend/index.html
echo.
echo Lưu ý:
echo - Backend đang chạy ở cửa sổ "Backend Server"
echo - Frontend đang chạy ở cửa sổ "Frontend Server"
echo - Đóng 2 cửa sổ đó để dừng server
echo.
echo Nhấn phím bất kỳ để đóng cửa sổ này...
pause >nul
