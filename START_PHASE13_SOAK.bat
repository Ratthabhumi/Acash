@echo off
title ACASH PHASE 13 - STEP 5 SOAK START

rem ================================================================================
rem  ACASH PHASE 13 -- STEP 5 SOAK TEST LAUNCHER (CONVENIENCE WRAPPER)
rem ================================================================================
rem  Convenience batch launcher for Human Operator.
rem  Authoritative launcher & governance checks reside in:
rem    .\scripts\start_phase13_soak.ps1
rem ================================================================================

rem Change directory to the repository root where this BAT file resides
cd /d "%~dp0"

echo ================================================================================
echo  ACASH PHASE 13 - STEP 5 SOAK START
echo ================================================================================
echo Repository Root : %CD%
echo Target Launcher : .\scripts\start_phase13_soak.ps1
echo Invoking PowerShell launcher with execution policy bypass...
echo ================================================================================
echo.

powershell.exe -ExecutionPolicy Bypass -File ".\scripts\start_phase13_soak.ps1"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo ================================================================================
if %EXIT_CODE% equ 0 (
    echo [INFO] Launcher script completed successfully (Exit Code: 0).
    echo [NOTE] The 24-hour soak daemon is active in the background.
    echo        You may close this console window at any time.
) else (
    echo [ERROR] Launcher script exited with error code %EXIT_CODE%.
)
echo ================================================================================
echo.
pause
exit /b %EXIT_CODE%
