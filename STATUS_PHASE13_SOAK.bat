@echo off
title ACASH PHASE 13 - STEP 5 SOAK STATUS

rem ================================================================================
rem  ACASH PHASE 13 -- STEP 5 SOAK TEST STATUS MONITOR (CONVENIENCE WRAPPER)
rem ================================================================================
rem  Convenience batch wrapper for Human Operator.
rem  Authoritative status monitor & inspection logic reside in:
rem    .\scripts\status_phase13_soak.ps1
rem  Strictly NON-MUTATING and READ-ONLY: Never alters or stops running processes.
rem ================================================================================

rem Change directory to the repository root where this BAT file resides
cd /d "%~dp0"

echo ================================================================================
echo  ACASH PHASE 13 - STEP 5 SOAK STATUS
echo ================================================================================
echo Repository Root : %CD%
echo Status Script   : .\scripts\status_phase13_soak.ps1
echo Querying active status...
echo ================================================================================
echo.

powershell.exe -ExecutionPolicy Bypass -File ".\scripts\status_phase13_soak.ps1"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo ================================================================================
echo [INFO] Status check completed (Exit Code: %EXIT_CODE%).
echo ================================================================================
echo.
pause
exit /b %EXIT_CODE%
