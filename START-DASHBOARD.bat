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
    echo Please run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

:: 3. Launch dashboard
echo [*] Starting ACASH Research Dashboard development server...
echo [*] Target URL: http://localhost:3000
echo [*] Waiting for server readiness before opening browser...
echo [*] Press Ctrl+C in this terminal to stop the server.
echo.

cd /d "%DASHBOARD_DIR%"

:: Background readiness watcher: polls http://localhost:3000 until responsive, then opens browser exactly once
where curl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start /b "" cmd /c "for /l %%i in (1,1,60) do (curl.exe -s -f -o nul http://localhost:3000 && (start """" http://localhost:3000 & exit) || timeout /t 1 /nobreak >nul)"
) else (
    start /b "" powershell -NoProfile -Command "$u='http://localhost:3000'; for($i=0;$i -lt 60;$i++){ try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -eq 200){ Start-Process $u; exit 0 } } catch {} Start-Sleep -Seconds 1 }"
)

:: Run Vite development server in foreground (keeps terminal open)
call npm run dev

cd /d "%REPO_ROOT%"
pause
