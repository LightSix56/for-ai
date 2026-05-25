@echo off
echo ========================================
echo   DnD 5e Character Sheet Generator
echo ========================================
echo.
echo   On this PC:
echo     http://localhost:3000
echo.
echo   From phone (same WiFi, find your IP with ipconfig):
echo     http://YOUR_IP:3000
echo.
echo ========================================
echo   Press Ctrl+C to stop
echo ========================================
echo.
call npm.cmd run dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start!
    echo Make sure you ran 1-Install.bat first.
    pause
)
