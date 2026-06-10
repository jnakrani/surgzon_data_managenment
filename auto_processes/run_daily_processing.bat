@echo off
REM ============================================================
REM  Daily auto-processing for Surgzon
REM  Runs both AI processing scripts sequentially every day.
REM  Scheduled via Windows Task Scheduler (see setup notes).
REM ============================================================

setlocal

set "PROJECT_DIR=D:\Surgzon\auto_processes"
set "PYTHON=D:\Surgzon\venv\Scripts\python.exe"
set "LOG_DIR=%PROJECT_DIR%\logs"

REM Build a timestamp like 2026-06-03_10-00 (locale-independent via PowerShell)
set "STAMP="
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "STAMP=%%i"
if not defined STAMP set "STAMP=latest"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOGFILE=%LOG_DIR%\daily_run_%STAMP%.log"

cd /d "%PROJECT_DIR%"

echo ============================================================ >> "%LOGFILE%" 2>&1
echo  Daily run started: %DATE% %TIME% >> "%LOGFILE%" 2>&1
echo ============================================================ >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%" 2>&1
echo [1/2] Running review_rating_threaded.py ... >> "%LOGFILE%" 2>&1
"%PYTHON%" "%PROJECT_DIR%\review_rating_threaded.py" >> "%LOGFILE%" 2>&1
echo [1/2] review_rating_threaded.py finished with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%" 2>&1
echo [2/2] Running extract_main_threaded.py ... >> "%LOGFILE%" 2>&1
"%PYTHON%" "%PROJECT_DIR%\extract_main_threaded.py" >> "%LOGFILE%" 2>&1
echo [2/2] extract_main_threaded.py finished with exit code %ERRORLEVEL% >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%" 2>&1
echo  Daily run completed: %DATE% %TIME% >> "%LOGFILE%" 2>&1

endlocal
