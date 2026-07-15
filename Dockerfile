# Multi-stage Dockerfile for Scan2Target
FROM node:20-slim AS frontend-builder
WORKDIR /app/web
COPY app/web/package*.json ./
RUN npm ci
COPY app/web/ ./
RUN npm run build

FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-daemon \
    avahi-utils \
    dbus \
    sane-utils \
    sane-airscan \
    smbclient \
    openssh-client \
    sshpass \
    imagemagick \
    libsane1 \
    libsane-dev \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 scan2target \
    && useradd --system --uid 10001 --gid scan2target --home-dir /app --shell /usr/sbin/nologin scan2target \
    && usermod -aG scanner,lp scan2target 2>/dev/null || true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./
COPY --from=frontend-builder /app/web/dist ./web/dist

RUN mkdir -p /data/scans /data/db /data/auth /data/logs /tmp/scan2target/scans \
    && chown -R scan2target:scan2target /app /data /tmp/scan2target

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    SCAN2TARGET_DATA_DIR=/data \
    SCAN2TARGET_DATABASE_PATH=/data/db/scan2target.db \
    SCAN2TARGET_RUN_USER=scan2target

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
