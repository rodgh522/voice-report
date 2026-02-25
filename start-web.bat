@echo off
REM Wrapper script for voice-report Docker container (Web GUI)

cd /d "%~dp0"

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: docker is not installed or not in PATH.
    pause
    exit /b 1
)

echo Starting Voice Report Web GUI on http://localhost:8501 ...
echo (Keep this window open. Press Ctrl+C to stop the server^)
docker compose run --rm -p 8501:8501 voice-report web

pause
