# --------- Builder Stage ---------
FROM python:3.10-slim AS builder

# Install build dependencies for opuslib_next, sherpa-onnx, llama-cpp-python, and other native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus-dev \
    pkg-config \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Copy only requirements file for better layer caching
COPY requirements.txt .

# Create virtual environment and install dependencies
# Using --compile optimizes bytecode, improving startup time
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /app/.venv/bin/pip install --no-cache-dir --compile -r requirements.txt

# --------- Final Stage ---------
FROM python:3.10-slim

# Install runtime dependencies (libopus for opuslib_next, libomp for torchaudio, ffmpeg for pydub)
# Also install Node.js and Chromium for NotebookLM MCP support
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus0 \
    libomp-dev \
    ffmpeg \
    curl \
    ca-certificates \
    # Chromium dependencies for puppeteer/notebooklm-mcp
    chromium \
    chromium-sandbox \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS for NotebookLM MCP
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g npm@latest

# Set Puppeteer to use system Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Create a non-root user for security
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Create necessary directories with proper permissions
RUN mkdir -p /app/src/logs /app/tmp /app/data/.notebooklm && \
    chown -R app:app /app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy only necessary application code (exclude tests, docs, examples via .dockerignore)
COPY --chown=app:app src /app/src
COPY --chown=app:app run.py /app/

# Ensure the virtual environment is in the PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to the non-root user
USER app

# Set the working directory to src for proper imports
WORKDIR /app/src

# Production mode by default (override in docker-compose for dev)
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5"]
