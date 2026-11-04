@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem ACASH market-data credential setup. Interactive, read-only with respect to the repository:
rem no git pull/reset/merge, no broker access, no orders, no trading endpoints.
rem Secrets are typed with hidden input and stored in Windows Credential Manager under the current
rem Windows user only. Nothing is written to .env, plaintext JSON, logs, or Git.
rem Usage: SETUP-MARKET-DATA.bat
rem Set ACASH_LAUNCHER_NO_PAUSE=1 to skip the final pause (scripted runs).

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

where uv >nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv was not found on PATH. Run SETUP.bat first.
  if not defined ACASH_LAUNCHER_NO_PAUSE pause
  exit /b 1
)

uv run --quiet python -m acash.market_data.credentials_setup
set "RC=%ERRORLEVEL%"

if not defined ACASH_LAUNCHER_NO_PAUSE (
  echo.
  if "%RC%"=="0" (echo Done.) else (echo [ERROR] Setup exited with code %RC%.)
  pause
)
exit /b %RC%
