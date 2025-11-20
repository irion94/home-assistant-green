# Wake-Word Detection Service
# Optimized for Raspberry Pi 5 with ReSpeaker 4 Mic Array

FROM python:3.11-slim

# Install system dependencies for audio and build tools
RUN apt-get update && apt-get install -y \
    alsa-utils \
    portaudio19-dev \
    libsndfile1 \
    wget \
    gcc \
    g++ \
    make \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create OpenWakeWord models directory and set permissions
# This allows the wakeword user to copy models at runtime
RUN mkdir -p /usr/local/lib/python3.11/site-packages/openwakeword/resources/models && \
    chmod -R 777 /usr/local/lib/python3.11/site-packages/openwakeword/resources/models

# Copy application code
COPY app/ ./app/

# Create directories for models and sounds
RUN mkdir -p ./models ./sounds

# Copy sounds (required)
COPY sounds/ ./sounds/

# Copy entrypoint script
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Create non-root user for security (not used currently - need root for USB reset)
RUN useradd -m -u 1000 wakeword && \
    chown -R wakeword:wakeword /app

# Note: Running as root to allow USB device reset
# In production, consider alternative approaches

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the wake-word detection service with audio device check
CMD ["./entrypoint.sh"]
