@echo off
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [ERROR] Frontend dependencies not installed. Run setup.bat first.
    pause
    exit /b 1
)

echo Starting frontend on http://localhost:3000 ...
echo ^(Keep this window open while using the app. Press Ctrl+C to stop.^)
echo.
node server.js

echo.
echo Frontend stopped.
pause
