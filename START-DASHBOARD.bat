@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem ACASH dashboard launcher. Read-only: no git pull/reset/merge, no broker access, no orders.
rem Usage: START-DASHBOARD.bat [private^|synthetic^|check] [--no-browser]
rem   (no argument)  Owner-private dashboard when ODR-001 is RATIFIED, opened already signed in
rem                  (one-time sign-in link, HttpOnly session cookie, no token to copy);
rem                  otherwise the synthetic demo, labelled as such
rem   private        Owner-private only; refuses to start unless ODR-001 is RATIFIED
rem   synthetic      React dashboard with the committed synthetic demo on 127.0.0.1:3002
rem   check          Runs every prerequisite and governance check, starts nothing
rem Set ACASH_LAUNCHER_NO_PAUSE=1 to skip the final pause (scripted runs).

set "REPO_ROOT=%~dp0"
set "DASHBOARD_DIR=%REPO_ROOT%dashboard"
set "DASHBOARD_URL=http://127.0.0.1:3002/"
set "MODE=auto"
set "OPEN_BROWSER=1"

:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="synthetic" (set "MODE=synthetic" & shift & goto parse_args)
if /i "%~1"=="private" (set "MODE=private" & shift & goto parse_args)
if /i "%~1"=="check" (set "MODE=check" & shift & goto parse_args)
if /i "%~1"=="--no-browser" (set "OPEN_BROWSER=" & shift & goto parse_args)
if /i "%~1"=="--help" goto usage
if /i "%~1"=="/?" goto usage
echo [ERROR] Unknown argument.
goto usage_fail

:args_done
title ACASH Dashboard - %MODE%
echo ============================================================
echo   ACASH Dashboard Launcher - mode: %MODE%
echo ============================================================

set "GIT_SHA=unknown"
set "GIT_BRANCH=unknown"
where git >nul 2>&1
if errorlevel 1 goto git_done
for /f "delims=" %%c in ('git -C "%REPO_ROOT%." rev-parse --short HEAD 2^>nul') do set "GIT_SHA=%%c"
for /f "delims=" %%b in ('git -C "%REPO_ROOT%." rev-parse --abbrev-ref HEAD 2^>nul') do set "GIT_BRANCH=%%b"
:git_done
echo   Commit : %GIT_SHA% on %GIT_BRANCH%  (the launcher never pulls, resets or merges)
echo   URL    : %DASHBOARD_URL%
echo.

echo [1/4] Required files
call :require_file "%DASHBOARD_DIR%\package.json" "dashboard\package.json" || goto fail_repo
call :require_file "%DASHBOARD_DIR%\vite.config.ts" "dashboard\vite.config.ts" || goto fail_repo
call :require_file "%DASHBOARD_DIR%\src\fixtures\upi_synthetic_view.json" "dashboard\src\fixtures\upi_synthetic_view.json" || goto fail_repo
call :require_file "%REPO_ROOT%src\acash\dashboard_api\private_view_server.py" "src\acash\dashboard_api\private_view_server.py" || goto fail_repo
echo       OK

echo [2/4] Node.js, npm and dashboard dependencies
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH.
    echo         Install Node.js 24 LTS from https://nodejs.org/ or run SETUP.bat, then open a new terminal.
    goto fail
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH. Reinstall Node.js with npm included.
    goto fail
)
for /f "delims=" %%v in ('node --version') do echo       node %%v
if not exist "%DASHBOARD_DIR%\node_modules\.bin\vite.cmd" (
    echo [ERROR] Dashboard dependencies are not installed.
    echo         Run:  cd /d "%DASHBOARD_DIR%" ^&^& npm ci
    goto fail
)
echo       OK

echo [3/4] Governance and owner-private authorization (statuses only, no values)
set "HAVE_UV=1"
where uv >nul 2>&1
if errorlevel 1 set "HAVE_UV="
if not defined HAVE_UV (
    echo       uv was not found on PATH; governance status unavailable. Run SETUP.bat to install it.
    if /i "%MODE%"=="private" (
        echo [ERROR] Private mode needs uv to verify ODR-001 and run the loopback service.
        goto fail
    )
    if /i "%MODE%"=="auto" set "MODE=synthetic"
    goto status_done
)
pushd "%REPO_ROOT%"
if /i "%MODE%"=="private" (
    uv run --quiet python -m acash.dashboard_api.readiness --require-private
) else (
    uv run --quiet python -m acash.dashboard_api.readiness
)
set "READY_EXIT=%ERRORLEVEL%"
popd
if /i not "%MODE%"=="private" goto status_done
if "%READY_EXIT%"=="0" goto status_done
echo.
echo [BLOCKED] Private mode stays closed (fail-closed). Nothing was started.
echo           It needs ODR-001 ratified by the Owner in
echo           docs\governance\ODR_UPI_PRIVATE_OBSERVATION_001.json.
echo           With ODR-001 ratified and no report yet, private mode opens the Setup Wizard.
echo           Details: docs\research\UPI_PRIVATE_PILOT_RUNBOOK.md
echo           The synthetic demo is still available:  START-DASHBOARD.bat synthetic
goto fail
:status_done
if /i "%MODE%"=="synthetic" echo       Data shown: SYNTHETIC DEMO (no owner data, no orders, no broker access)

echo [4/4] Ports
set "DASH_RUNNING="
netstat -ano -p tcp | findstr /c:"127.0.0.1:3002 " /c:"0.0.0.0:3002 " | findstr /c:"LISTENING" >nul && set "DASH_RUNNING=1"
set "PRIVATE_RUNNING="
netstat -ano -p tcp | findstr /c:"127.0.0.1:8765 " | findstr /c:"LISTENING" >nul && set "PRIVATE_RUNNING=1"
if defined DASH_RUNNING (echo       port 3002: already in use) else (echo       port 3002: free)
if defined PRIVATE_RUNNING (echo       port 8765: already in use) else (echo       port 8765: free)

if /i "%MODE%"=="check" (
    echo.
    echo Check complete. Nothing was started.
    goto done
)

if /i "%MODE%"=="synthetic" goto start_dashboard
echo.
echo [*] Starting ACASH owner-private (loopback only; the browser opens signed in, no token to copy)
set "LAUNCH_FLAGS="
if not defined OPEN_BROWSER set "LAUNCH_FLAGS=--no-browser"
pushd "%REPO_ROOT%"
uv run --quiet python -m acash.dashboard_api.launcher %LAUNCH_FLAGS%
set "LAUNCH_EXIT=%ERRORLEVEL%"
popd
if "%LAUNCH_EXIT%"=="0" goto done
if /i "%MODE%"=="auto" if "%LAUNCH_EXIT%"=="3" (
    echo.
    echo [*] Owner-private mode is not authorized; starting the SYNTHETIC DEMO instead ^(labelled as such^).
    set "MODE=synthetic"
    goto start_dashboard
)
echo.
echo [STOPPED] ACASH did not start ^(code %LAUNCH_EXIT%^). Read the message above.
echo           Details: docs\research\UPI_PRIVATE_PILOT_RUNBOOK.md
goto fail

:start_dashboard
if defined DASH_RUNNING (
    echo.
    echo [*] Port 3002 is already in use - a dashboard is probably running already.
    echo     Not starting a duplicate. If it is not the ACASH dashboard, close that program and retry.
    if defined OPEN_BROWSER start "" "%DASHBOARD_URL%"
    goto done
)
echo.
echo [*] Starting the synthetic demo dashboard at %DASHBOARD_URL%
echo     Stop: press Ctrl+C here, then answer Y.
echo.
if defined OPEN_BROWSER start "" /b powershell -NoProfile -NonInteractive -Command "$u='%DASHBOARD_URL%'; for($i=0;$i -lt 60;$i++){ try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ Start-Process $u; exit 0 } } catch {}; Start-Sleep -Seconds 1 }"
pushd "%DASHBOARD_DIR%"
call npm run dev
popd
echo.
echo Dashboard stopped.
goto done

:require_file
if exist "%~1" exit /b 0
echo [ERROR] Missing required file: %~2
exit /b 1

:fail_repo
echo         The checkout looks incomplete. Check with:  git status
echo         The launcher does not modify the repository; restore the file yourself.
goto fail

:usage
echo Usage: START-DASHBOARD.bat [private^|synthetic^|check] [--no-browser]
goto done

:usage_fail
echo Usage: START-DASHBOARD.bat [private^|synthetic^|check] [--no-browser]
goto fail

:fail
echo.
if not defined ACASH_LAUNCHER_NO_PAUSE pause
endlocal & exit /b 1

:done
if not defined ACASH_LAUNCHER_NO_PAUSE pause
endlocal & exit /b 0
