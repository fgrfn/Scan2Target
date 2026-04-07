# ── Stage 1: Frontend build ───────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SCAN2TARGET_DATABASE_PATH=/data/db/scan2target.db \
    SCAN2TARGET_DATA_DIR=/data \
    SCAN2TARGET_LOG_DIR=/var/log/scan2target \
    SCAN2TARGET_TEMP_DIR=/tmp/scan2target

RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-daemon avahi-utils \
    sane-utils sane-airscan \
    smbclient \
    ssh sshpass \
    imagemagick \
    libsane1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-builder /build/build ./frontend/build

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
