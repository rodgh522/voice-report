#!/bin/bash
# Wrapper script for voice-report Docker container (Web GUI)

cd "$(dirname "$0")"

if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed or not in PATH."
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
