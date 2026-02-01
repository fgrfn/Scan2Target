# Multi-stage Dockerfile for Scan2Target
# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/web

# Copy package files
COPY app/web/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY app/web/ ./

# Build frontend
RUN npm run build

# Stage 2: Build final image
FROM python:3.12-slim

# Avoid debconf warnings during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    avahi-daemon \
    avahi-utils \
    dbus \
    sane-utils \
    sane-airscan \
    smbclient \
    ssh \
    sshpass \
    imagemagick \
    libsane1 \
    libsane-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code directly to /app
COPY app/ ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/web/dist ./web/dist

# Create necessary directories
RUN mkdir -p /data/scans /data/db /tmp/scan2target/scans

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SCAN2TARGET_DATA_DIR=/data
ENV SCAN2TARGET_DATABASE_PATH=/app/scan2target.db
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Set PYTHONPATH to /app for module resolution
ENV PYTHONPATH=/app

# Use entrypoint script to start Avahi and application
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
