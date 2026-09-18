# =====================================================================
# MONARCH — MULTI-AGENT PLATFORM DOCKERFILE
# Production Docker container for Multimodal RAG, Vision, & Multi-Agent API
# =====================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PDF parsing, Word documents, & Image OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    tesseract-ocr \
    poppler-utils \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code into container
COPY . .

# Expose FastAPI backend port
EXPOSE 8000

# Health check to ensure the container API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command: Start production FastAPI backend server
CMD ["python", "main.py", "--serve-api"]
