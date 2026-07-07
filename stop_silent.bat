@echo off
rem Stops the backend and frontend started by start_silent.vbs (they run
rem hidden, so there's no window to Ctrl+C - this finds whatever is
rem listening on ports 8000/3000 and stops it instead).

echo Stopping Income Tracker...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Done. Both servers stopped.
pause
