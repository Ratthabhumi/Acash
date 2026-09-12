@echo off
setlocal enabledelayedexpansion

title ACASH Research Dashboard - Development Server

echo ============================================================
echo   ACASH Research Dashboard Launcher
echo ============================================================
echo.

:: 1. Determine ACASH root directory from script location
set "REPO_ROOT=%~dp0"
set "DASHBOARD_DIR=%REPO_ROOT%dashboard"

:: 2. Pre-flight checks
if not exist "%DASHBOARD_DIR%\package.json" (
    echo [ERROR] Dashboard directory or package.json not found at:
    echo   "%DASHBOARD_DIR%\package.json"
    echo.
    echo Please ensure the ACASH repository is intact.
    echo.
    pause
    exit /b 1
)

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not found in system PATH.
    echo Please install Node.js or run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm is not found in system PATH.
    echo Please ensure Node.js and npm are properly installed.
    echo.
    pause
    exit /b 1
)

if not exist "%DASHBOARD_DIR%\node_modules" (
    echo.
    echo [ERROR] Dashboard dependencies are not installed.
    echo Please run SETUP.bat first to initialize the environment.
    echo.
    pause
    exit /b 1
)

:: 3. Launch dashboard
echo [*] Starting ACASH Research Dashboard...
echo [*] Target URL: http://localhost:3000
echo [*] Press Ctrl+C in this terminal to stop the server.
echo.

cd /d "%DASHBOARD_DIR%"

:: Open default browser
start "" http://localhost:3000

:: Run Vite development server (keeps terminal open)
call npm run dev

cd /d "%REPO_ROOT%"
pause
