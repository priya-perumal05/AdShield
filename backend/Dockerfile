# ==============================================================================
# AdShield Backend - Production Dockerfile for Render Web Service
# ==============================================================================

# Base image: Official Python 3.9 slim Debian
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TESSERACT_CMD=/usr/bin/tesseract \
    HOST=0.0.0.0 \
    PORT=8000

# Install system dependencies: Tesseract OCR engine, English traineddata, and graphics libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set container working directory
WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only the application code (exclude .env, tests, and caches via .dockerignore)
COPY app/ ./app/

# Expose standard service port (Render dynamically overrides PORT at runtime)
EXPOSE 8000

# Health check instruction for container runtimes
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, os; port=os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/api/health')" || exit 1

# Start Uvicorn binding to 0.0.0.0 with dynamic $PORT expansion
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
