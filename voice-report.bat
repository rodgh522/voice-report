@echo off
REM Wrapper script for voice-report Docker container

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: docker is not installed or not in PATH.
    exit /b 1
)

docker compose run --rm voice-report %*
