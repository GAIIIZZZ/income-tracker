@echo off
cd /d "%~dp0backend"

if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8

echo Watching OCR\inbox for new images (optional - the website upload works without this).
echo ^(Keep this window open while using this feature. Press Ctrl+C to stop.^)
echo.
python -m app.watcher

pause
