@echo off
setlocal enabledelayedexpansion

title ACASH Dashboard - Portable Machine Setup

echo ============================================================
echo   ACASH Research Dashboard - Machine Setup
echo ============================================================
echo.

:: 1. Determine ACASH root directory from script location
set "REPO_ROOT=%~dp0"
set "DASHBOARD_DIR=%REPO_ROOT%dashboard"

echo [*] Root Directory: "%REPO_ROOT%"
echo [*] Dashboard Dir:  "%DASHBOARD_DIR%"
echo.

:: 2. Check Node.js and npm availability
echo [*] Checking runtime prerequisites...

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not found in system PATH.
    echo.
    echo Please install Node.js [v18 or higher recommended] from:
    echo   https://nodejs.org/
    echo.
    echo After installing Node.js, re-run this SETUP.bat script.
    echo.
    pause
    exit /b 1
)

where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm is not installed or not found in system PATH.
    echo.
    echo Please ensure npm is included with your Node.js installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node -v 2^>nul') do set "NODE_VER=%%v"
for /f "tokens=*" %%v in ('npm -v 2^>nul') do set "NPM_VER=%%v"

echo [OK] Node.js detected: %NODE_VER%
echo [OK] npm detected:     v%NPM_VER%
echo.

:: 3. Verify dashboard directory and package.json
if not exist "%DASHBOARD_DIR%\package.json" (
    echo [ERROR] Dashboard directory or package.json not found at:
    echo   "%DASHBOARD_DIR%\package.json"
    echo.
    echo Please ensure this repository was cloned completely.
    echo.
    pause
    exit /b 1
)

:: 4. Install dependencies using lockfile (Strict reproducibility: no silent npm install fallback)
echo [*] Navigating to dashboard directory...
cd /d "%DASHBOARD_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to switch directory to: "%DASHBOARD_DIR%"
    pause
    exit /b 1
)

echo [*] Installing dependencies...
if exist "%DASHBOARD_DIR%\package-lock.json" (
    echo [*] Found package-lock.json. Running 'npm ci'...
    call npm ci
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] 'npm ci' failed.
        echo [ERROR] Dependency installation was aborted to preserve lockfile reproducibility.
        echo [ERROR] Please inspect the npm error above and resolve the environment or lockfile issue.
        cd /d "%REPO_ROOT%"
        pause
        exit /b 1
    )
) else (
    echo [*] No package-lock.json found. Running 'npm install'...
    call npm install
    if %ERRORLEVEL% NEQ 0 goto error_install
)

echo.
echo [OK] Dependencies installed successfully.
echo.

:: 5. Validate setup with project validation scripts
echo [*] Running automated contract validation tests...
call npm test
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Contract test suite [npm test] failed.
    goto error_validation
)

echo.
echo [*] Running strict TypeScript typecheck...
call npm run typecheck
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] TypeScript typecheck [npm run typecheck] failed.
    goto error_validation
)

echo.
echo [*] Testing production build compilation...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Production build [npm run build] failed.
    goto error_validation
)

echo.
echo ============================================================
echo   ACASH Dashboard setup completed successfully!
echo.
echo   Dashboard directory: "%DASHBOARD_DIR%"
echo   Start the dashboard daily using: START-DASHBOARD.bat
echo ============================================================
echo.
cd /d "%REPO_ROOT%"
pause
exit /b 0

:error_install
echo.
echo [ERROR] Failed to install dashboard dependencies via npm.
echo Please check your internet connection and npm permissions.
cd /d "%REPO_ROOT%"
pause
exit /b 1

:error_validation
echo.
echo [ERROR] Dashboard validation step failed.
echo Review the error log above. Do not launch unverified dashboard.
cd /d "%REPO_ROOT%"
pause
exit /b 1
