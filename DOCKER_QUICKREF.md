# Docker Quick Reference

Quick reference for common Docker commands with Scan2Target.

## Quick Start

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f

# Access: http://localhost:8000
```

## Common Commands

### Starting & Stopping
```bash
docker compose up -d              # Start in background
docker compose down               # Stop and remove
docker compose restart            # Restart services
```

### Monitoring
```bash
docker compose ps                 # Check status
docker compose logs -f            # Follow logs
docker compose logs --tail=100    # Last 100 lines
docker stats scan2target          # Resource usage
```

### Maintenance
```bash
docker compose pull               # Update images
docker compose build --no-cache   # Rebuild from scratch
docker compose down -v            # Remove with volumes (caution!)
```

### Troubleshooting
```bash
docker compose logs --tail=200    # Check recent logs
docker exec -it scan2target bash  # Shell access
docker compose restart            # Restart service
```

## Environment Setup

```bash
# Create .env file
cat > .env << 'EOF'
SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)
SCAN2TARGET_REQUIRE_AUTH=true
EOF

# Or copy from example
cp .env.example .env
# Edit: nano .env
```

## Backup & Restore

```bash
# Backup
docker run --rm -v scan2target_scan2target-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz /data

# Restore
docker compose down
docker run --rm -v scan2target_scan2target-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/backup.tar.gz -C /
docker compose up -d
```

## Pre-built Images

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/fgrfn/scan2target:latest

# Run
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  -e SCAN2TARGET_SECRET_KEY="$(openssl rand -base64 32)" \
  ghcr.io/fgrfn/scan2target:latest
```

## Useful URLs

- **Web UI:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Default Credentials

- **Username:** admin
- **Password:** admin
- ⚠️ **Change immediately after first login!**
