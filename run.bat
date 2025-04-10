@echo off
REM Run script for CareCompanion Multi-Agent System on Windows

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH. Please install Python and try again.
    exit /b 1
)

REM Check if pip is installed
where pip >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip is not installed or not in PATH. Please install pip and try again.
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
pip install -r requirements.txt

REM Check if data directory exists
if not exist "data" (
    echo Error: data directory not found. Please ensure the data directory exists with the required CSV files.
    exit /b 1
)

REM Check if CSV files exist
set FILES_MISSING=0
if not exist "data\safety_monitoring.csv" set FILES_MISSING=1
if not exist "data\health_monitoring.csv" set FILES_MISSING=1
if not exist "data\daily_reminder.csv" set FILES_MISSING=1

if %FILES_MISSING% EQU 1 (
    echo Error: Required CSV files not found in data directory.
    echo Please ensure the following files exist:
    echo   - data\safety_monitoring.csv
    echo   - data\health_monitoring.csv
    echo   - data\daily_reminder.csv
    exit /b 1
)

REM Check command-line arguments
set MODE=backend
if not "%~1"=="" set MODE=%~1

REM Run in the appropriate mode
if "%MODE%"=="dashboard" (
    echo Starting CareCompanion Dashboard...
    streamlit run ui/dashboard.py
) else if "%MODE%"=="backend" (
    echo Starting CareCompanion backend with data simulation...
    python app.py --simulate
) else if "%MODE%"=="help" (
    echo CareCompanion Multi-Agent System
    echo.
    echo Usage: run.bat [mode]
    echo.
    echo Modes:
    echo   backend    Start the backend system with data simulation ^(default^)
    echo   dashboard  Start the Streamlit dashboard UI
    echo   help       Show this help message
    echo.
    echo Examples:
    echo   run.bat backend    # Start the backend with simulation
    echo   run.bat dashboard  # Start the Streamlit dashboard
) else (
    echo Error: Unknown mode '%MODE%'. Use 'backend', 'dashboard', or 'help'.
    exit /b 1
)