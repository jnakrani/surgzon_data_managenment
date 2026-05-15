@echo off
REM Setup Windows Task Scheduler for daily folder fetching and processing at 23:59 PM
REM This script creates a scheduled task that runs the complete automation pipeline

echo Setting up daily automated processing for Azure folders...

REM Get current directory
set CURRENT_DIR=%~dp0
set SCRIPT_PATH=%CURRENT_DIR%run_daily_processing.py

echo Current directory: %CURRENT_DIR%
echo Script path: %SCRIPT_PATH%

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if script exists
if not exist "%SCRIPT_PATH%" (
    echo ❌ Script not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

REM Create the scheduled task
echo Creating scheduled task...
schtasks /create /tn "Azure_Daily_Processing" /tr "python \"%SCRIPT_PATH%\"" /sc daily /st 23:59 /f

if %errorlevel% equ 0 (
    echo.
    echo ✅ Successfully created daily task "Azure_Daily_Processing"
    echo 📅 Task will run daily at 23:59 PM
    echo 📂 Script location: %SCRIPT_PATH%
    echo.
    echo 🤖 This task will automatically:
    echo    1. Fetch new folder names from Azure container
    echo    2. Update the processing script with new folders
    echo    3. Process all files in the new folders
    echo    4. Skip already processed files
    echo.
    echo 📋 Task Management Commands:
    echo    View task: schtasks /query /tn "Azure_Daily_Processing"
    echo    Run now:   schtasks /run /tn "Azure_Daily_Processing"
    echo    Delete:    schtasks /delete /tn "Azure_Daily_Processing" /f
    echo.
    echo 🧪 Test the automation manually:
    echo    python "%SCRIPT_PATH%"
) else (
    echo ❌ Failed to create scheduled task
    echo Please run this script as Administrator
)

echo.
pause