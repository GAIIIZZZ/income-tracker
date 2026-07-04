@echo off
cd /d "%~dp0"

echo Starting backend and frontend, each in its own window...
echo.

start "Income Tracker - BACKEND" cmd /k "%~dp0start_backend.bat"
timeout /t 4 /nobreak >nul

start "Income Tracker - FRONTEND" cmd /k "%~dp0start_frontend.bat"
timeout /t 2 /nobreak >nul

start "" "http://localhost:3000"

echo.
echo Two new windows opened (backend + frontend) and your browser should open
echo to http://localhost:3000 automatically.
echo.
echo If the page doesn't load, wait a few seconds and refresh - the backend can
echo take a moment to start the first time.
echo.
echo This window can be closed - it's just the launcher. Close the BACKEND and
echo FRONTEND windows when you're done using the app.
pause
