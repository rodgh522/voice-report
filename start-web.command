#!/bin/bash
# Wrapper script for voice-report Docker container (Web GUI)

# Ensure the script runs in the directory where it's located
cd "$(dirname "$0")"

# When double-clicking in macOS, the PATH might not include homebrew/usr/local
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

if ! command -v docker &> /dev/null; then
    echo "Error: docker Desktop is not installed or not running."
    echo "Please install Docker Desktop and start it."
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
fi

echo "Starting Voice Report Web GUI on http://localhost:8501 ..."
echo "(Keep this window open. Press Ctrl+C to stop the server)"
docker compose run --rm -p 8501:8501 voice-report web

echo ""
echo "Server stopped. Press Enter to exit..."
read -r
