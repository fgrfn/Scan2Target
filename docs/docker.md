# Docker Deployment Guide

This guide covers deploying Scan2Target using Docker and Docker Compose.

## Quick Start

### Prerequisites

- Docker 20.10+ or Docker Desktop
- Docker Compose v2.0+ (included with Docker Desktop)
- Network scanner (USB or network/eSCL) connected to your system

### Basic Deployment

```bash
# 1. Clone repository
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# 2. Generate secure encryption key
cat > .env << 'EOF'
SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)
SCAN2TARGET_REQUIRE_AUTH=true
EOF

# 3. Start the application
docker compose up -d

# 4. View logs
docker compose logs -f

# 5. Access the application
# Open: http://localhost:8000
# Default login: admin / admin
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with these settings:

```env
# Required: Encryption key for sensitive data
SCAN2TARGET_SECRET_KEY=your-generated-key-here

# Force authentication (recommended)
SCAN2TARGET_REQUIRE_AUTH=true

# Optional: SMTP settings for email targets
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Generate a secure key:**
```bash
openssl rand -base64 32
```

### Volume Mapping

⚠️ **CRITICAL: Never mount volumes to `/app`**

The application code resides in `/app`. Mounting a volume to this path will overwrite the code and cause startup failures.

**CORRECT:** Use `/data` for persistent storage ✅
```yaml
volumes:
  - scan2target-data:/data
```

**INCORRECT:** Do NOT mount to `/app` ❌
```yaml
volumes:
  - ./mydata:/app  # THIS WILL BREAK THE APPLICATION!
```

To use a local directory instead of a named volume:

```yaml
volumes:
  - ./data:/data
```

### Network Configuration

The container uses `host` network mode by default to enable:
- Scanner discovery via mDNS/Avahi
- Network scanner access (eSCL/AirScan)

**Alternative:** If you don't need network scanner discovery, you can use bridge mode:

```yaml
network_mode: bridge
ports:
  - "8000:8000"
```

### USB Scanner Support

For USB scanners, the container needs access to USB devices:

```yaml
volumes:
  - /dev/bus/usb:/dev/bus/usb
devices:
  - /dev/bus/usb
```

If you encounter permission issues, you may need to run in privileged mode:

```yaml
privileged: true
```

## Pre-built Images

Pre-built images are available from GitHub Container Registry:

```bash
# Pull latest version
docker pull ghcr.io/fgrfn/scan2target:latest

# Pull specific version
docker pull ghcr.io/fgrfn/scan2target:v0.1.0

# Run pre-built image
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  -v /dev/bus/usb:/dev/bus/usb \
  --device /dev/bus/usb \
  -e SCAN2TARGET_SECRET_KEY="$(openssl rand -base64 32)" \
  -e SCAN2TARGET_REQUIRE_AUTH=true \
  ghcr.io/fgrfn/scan2target:latest
```

## Building from Source

### Build Image

```bash
# Build with default tag
docker build -t scan2target:latest .

# Build with custom tag
docker build -t scan2target:custom .
```

### Multi-platform Build

```bash
# Set up buildx (one time)
docker buildx create --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t scan2target:latest \
  --push \
  .
```

## Service Management

### Docker Compose Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View status
docker compose ps

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f scan2target

# Update to latest image
docker compose pull
docker compose up -d

# Remove everything (including volumes)
docker compose down -v
```

### Docker CLI Commands

```bash
# Start container
docker start scan2target

# Stop container
docker stop scan2target

# Restart container
docker restart scan2target

# View status
docker ps

# View logs
docker logs -f scan2target

# Execute command in container
docker exec -it scan2target /bin/bash

# View resource usage
docker stats scan2target
```

## Troubleshooting

### Error: "Could not import module 'main'"

**Problem:** Container fails to start with:
```
ERROR: Error loading ASGI app. Could not import module "main".
```

**Cause:** A volume is mounted to `/app`, overwriting the application code.

**Solution:**
1. Check your volume mappings
2. Remove any mapping to `/app`
3. Use `/data` for persistent storage

**Example fix for docker-compose.yml:**
```yaml
volumes:
  - ./mydata:/data  # ✅ Correct
  # NOT: - ./mydata:/app  # ❌ Wrong - will break application
```

**Example fix for Docker CLI:**
```bash
docker run -v /path/to/data:/data ...  # ✅ Correct
# NOT: docker run -v /path/to/data:/app ...  # ❌ Wrong
```

**For Unraid users:**
- Container Path should be: `/data`
- Do NOT set Container Path to: `/app`

### Scanner Not Found

**Problem:** Scanners are not being discovered.

**Solutions:**
1. Ensure `network_mode: host` is set in docker-compose.yml
2. Check USB permissions: `ls -l /dev/bus/usb/`
3. Verify scanner is powered on and connected
4. Check container logs: `docker compose logs -f`

### Permission Denied on USB Devices

**Problem:** Cannot access USB scanner.

**Solutions:**
1. Add user to dialout/lp group on host:
   ```bash
   sudo usermod -aG dialout,lp $USER
   ```
2. Use privileged mode in docker-compose.yml:
   ```yaml
   privileged: true
   ```

### Database Errors

**Problem:** Database errors on startup.

**Solutions:**
1. Check volume permissions:
   ```bash
   docker compose down
   docker volume rm scan2target_scan2target-data
   docker compose up -d
   ```
2. Verify SCAN2TARGET_DB_PATH is set correctly

### Connection Refused

**Problem:** Cannot connect to http://localhost:8000

**Solutions:**
1. Check if container is running: `docker compose ps`
2. Check logs for errors: `docker compose logs -f`
3. Verify port is not in use: `netstat -tulpn | grep 8000`
4. Check firewall settings

## Security Best Practices

### Production Deployment

1. **Generate strong encryption key:**
   ```bash
   openssl rand -base64 32
   ```

2. **Enable authentication:**
   ```yaml
   environment:
     - SCAN2TARGET_REQUIRE_AUTH=true
   ```

3. **Change default password immediately:**
   - Login with admin/admin
   - Go to Settings
   - Change password

4. **Use HTTPS with reverse proxy:**
   ```nginx
   server {
       listen 443 ssl;
       server_name scan.example.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       # WebSocket support
       location /api/v1/ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

5. **Regular updates:**
   ```bash
   docker compose pull
   docker compose up -d
   ```

## Backup and Restore

### Backup Data

```bash
# Backup database and scans
docker run --rm \
  -v scan2target_scan2target-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/scan2target-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore Data

```bash
# Stop container
docker compose down

# Restore backup
docker run --rm \
  -v scan2target_scan2target-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/scan2target-backup-YYYYMMDD.tar.gz -C /

# Start container
docker compose up -d
```

## Performance Tuning

### Resource Limits

Add resource limits to docker-compose.yml:

```yaml
services:
  scan2target:
    # ... other settings ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Logging Configuration

Limit log file size:

```yaml
services:
  scan2target:
    # ... other settings ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Advanced Configuration

### Custom Configuration File

Mount a custom configuration file:

```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro
```

### Multiple Instances

Run multiple instances with different ports:

```bash
# Instance 1
docker run -d \
  --name scan2target-1 \
  -p 8001:8000 \
  -v scan2target-data-1:/data \
  ghcr.io/fgrfn/scan2target:latest

# Instance 2
docker run -d \
  --name scan2target-2 \
  -p 8002:8000 \
  -v scan2target-data-2:/data \
  ghcr.io/fgrfn/scan2target:latest
```

## Integration with Other Services

### Reverse Proxy (Traefik)

```yaml
services:
  scan2target:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.scan2target.rule=Host(`scan.example.com`)"
      - "traefik.http.routers.scan2target.entrypoints=websecure"
      - "traefik.http.routers.scan2target.tls.certresolver=letsencrypt"
```

### Home Assistant Add-on

See [Home Assistant integration documentation](homeassistant.md) for add-on configuration.

## Support

- **Issues:** https://github.com/fgrfn/Scan2Target/issues
- **Discussions:** https://github.com/fgrfn/Scan2Target/discussions
- **Documentation:** https://github.com/fgrfn/Scan2Target/tree/main/docs
