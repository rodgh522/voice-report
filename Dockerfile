FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
# ffmpeg is required for WhisperX audio processing
# git is required for installing dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . .

# Install the application and its dependencies
RUN pip install --no-cache-dir .

# Cache directories for HuggingFace and PyTorch models
ENV HF_HOME=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch

# Entrypoint for the CLI
EXPOSE 8501
ENTRYPOINT ["voice-report"]

# Default command
CMD ["--help"]
