@echo off
echo ========================================
echo   DnD 5e - Production build
echo ========================================
echo.
call npm.cmd run build
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo.
echo ========================================
echo   Done! To run production server:
echo   call npm.cmd run start
echo ========================================
pause
