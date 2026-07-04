@echo off
cd /d "%~dp0backend"

if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8

echo Starting backend on http://localhost:8000 ...
echo ^(Keep this window open while using the app. Press Ctrl+C to stop.^)
echo.
uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Backend stopped.
pause
