FROM python:3.11-bookworm

# System dependencies:
# - ffmpeg  : konversi MP3 (Edge-TTS) -> WAV 16 kHz untuk ESP32
# - curl/git: tooling dasar
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Container keeps running
CMD ["sleep", "infinity"]
