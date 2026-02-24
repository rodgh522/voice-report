#!/bin/bash
# Wrapper script for voice-report Docker container

if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed or not in PATH."
    exit 1
fi

docker compose run --rm voice-report "$@"
