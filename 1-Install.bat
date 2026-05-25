@echo off
echo ========================================
echo   DnD 5e - Installing dependencies
echo ========================================
echo.
call npm.cmd install
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] npm install failed!
    pause
    exit /b 1
)
echo.
echo ========================================
echo   Done! Now run: 2-Start.bat
echo ========================================
pause
