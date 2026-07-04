@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Income Tracker - First-time setup
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo Install Python 3.12+ from https://www.python.org/downloads/ and re-run this script.
    echo IMPORTANT: during Python install, check "Add python.exe to PATH".
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on your PATH.
    echo Install the LTS version from https://nodejs.org/ and re-run this script.
    pause
    exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Ollama was not found on your PATH.
    echo This app will NOT work without it. Install it from https://ollama.com
    echo Then open a terminal and run:   ollama pull qwen2.5:1.5b
    echo You can continue this setup now and install Ollama before first use.
    echo.
    pause
)

echo [1/3] Setting up the Python virtual environment...
cd backend
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/3] Installing Python dependencies...
echo   NOTE: this downloads EasyOCR + PyTorch, roughly 1-2 GB. First time only,
echo   and it can take several minutes depending on your internet connection.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed - see the error above. Common causes:
    echo   - No internet connection
    echo   - Python version too old ^(need 3.10+^)
    pause
    exit /b 1
)
cd ..

echo [3/3] Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed - see the error above.
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo IMPORTANT - before running the app, double check:
echo   1. Ollama is installed and running in the background
echo   2. You have pulled the required model with this command:
echo        ollama pull qwen2.5:1.5b
echo.
echo Once that's done, double-click start_all.bat to launch the app.
echo.
pause
