@echo off
REM PISAG Startup Batch Script for Windows
REM Provides easy double-click execution

echo ============================================
echo Starting PISAG POCSAG Pager Server
echo ============================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if PowerShell script exists
if not exist "start.ps1" (
    echo ERROR: start.ps1 not found in current directory
    echo Please ensure you're running this from the PISAG installation directory
    pause
    exit /b 1
)

REM Run PowerShell script with execution policy bypass
echo Starting application via PowerShell...
echo.
powershell -ExecutionPolicy Bypass -File "start.ps1"

REM Pause to show any error messages
pause
