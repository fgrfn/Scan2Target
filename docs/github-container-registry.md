# GitHub Container Registry (GHCR) Setup

## Overview

Docker images for Scan2Target are automatically built and published to the GitHub Container Registry (GHCR) at `ghcr.io/fgrfn/scan2target`.

## Automated Publishing

The repository uses GitHub Actions to automatically build and publish Docker images:

### Workflow: `.github/workflows/docker-build.yml`

**Triggers:**
- Push to `main` or `master` branch
- Push of version tags (`v*.*.*`)
- Manual workflow dispatch
- Pull requests (build only, no push)

**Features:**
- 🏗️ Multi-platform builds: `linux/amd64`, `linux/arm64`
- 🏷️ Automatic tagging:
  - `latest` - Always points to the latest main branch build
  - `main` - Latest build from main branch
  - `v1.2.3` - Semantic version tags
  - `v1.2` - Major.minor version tags
  - `v1` - Major version tags
- 🔒 Authenticated with `GITHUB_TOKEN` (automatic)
- 🛡️ Docker Scout CVE scanning for security vulnerabilities
- ⚡ Build caching for faster builds

## Using Pre-built Images

### Pull the latest image:

```bash
docker pull ghcr.io/fgrfn/scan2target:latest
```

### Pull a specific version:

```bash
docker pull ghcr.io/fgrfn/scan2target:v1.0.0
```

### Run the container:

```bash
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

### Use with Docker Compose:

```yaml
services:
  scan2target:
    image: ghcr.io/fgrfn/scan2target:latest
    container_name: scan2target
    network_mode: host
    volumes:
      - scan2target-data:/data
      - /dev/bus/usb:/dev/bus/usb
    devices:
      - /dev/bus/usb
    environment:
      - SCAN2TARGET_SECRET_KEY=${SCAN2TARGET_SECRET_KEY}
      - SCAN2TARGET_REQUIRE_AUTH=true
    restart: unless-stopped

volumes:
  scan2target-data:
```

## Image Information

### Available Tags

- `latest` - Latest stable release from main branch
- `main` - Latest build from main branch (same as latest currently)
- `v*.*.*` - Specific version tags (e.g., v1.0.0, v1.0.1)
- `v*.*` - Major.minor version (e.g., v1.0, v1.1)
- `v*` - Major version (e.g., v1, v2)

### Platforms

Images are built for multiple architectures:
- `linux/amd64` - x86_64 (Intel/AMD)
- `linux/arm64` - ARM64 (Raspberry Pi 4/5, Apple Silicon, etc.)

Docker automatically pulls the correct architecture for your platform.

## Visibility

The images are published as **public packages**, meaning anyone can pull and use them without authentication:

```bash
# No login required for public images
docker pull ghcr.io/fgrfn/scan2target:latest
```

To view published images, visit:
- https://github.com/fgrfn/Scan2Target/pkgs/container/scan2target

## Build Process

### Local Development

To build the image locally:

```bash
# Build for your current platform
docker build -t scan2target:dev .

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t scan2target:dev \
  .
```

### CI/CD Pipeline

When code is pushed to the main branch:

1. **Checkout** - Repository code is checked out
2. **Setup Docker Buildx** - Multi-platform build support
3. **Login to GHCR** - Authenticate using `GITHUB_TOKEN`
4. **Extract Metadata** - Generate tags and labels
5. **Build & Push** - Build for multiple platforms and push to GHCR
6. **Security Scan** - Run Docker Scout CVE scan

## Troubleshooting

### Image not found

If you get "image not found" errors:

```bash
# Make sure you're using lowercase repository name
docker pull ghcr.io/fgrfn/scan2target:latest  # ✓ Correct
docker pull ghcr.io/fgrfn/Scan2Target:latest  # ✗ Wrong (case-sensitive)
```

### Authentication issues

Public images don't require authentication. If you need to pull private images:

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull image
docker pull ghcr.io/fgrfn/scan2target:latest
```

### Check available tags

View all available tags at:
- https://github.com/fgrfn/Scan2Target/pkgs/container/scan2target

## Security

### CVE Scanning

All images are automatically scanned for security vulnerabilities using Docker Scout:
- Critical and high severity issues are reported
- Scan results are available in GitHub Actions workflow logs

### Best Practices

1. **Use specific version tags** in production instead of `latest`
2. **Pin major/minor versions** to avoid unexpected breaking changes
3. **Monitor security advisories** and update regularly
4. **Set strong encryption keys** in production deployments

## Maintenance

### Creating a New Release

To publish a new version:

1. Tag the commit with a semantic version:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. GitHub Actions automatically:
   - Builds the Docker image
   - Pushes to GHCR with multiple tags:
     - `v1.0.0`
     - `v1.0`
     - `v1`
     - `latest` (if default branch)

### Manual Workflow Trigger

You can manually trigger a build from GitHub:

1. Go to **Actions** → **Docker Build and Publish**
2. Click **Run workflow**
3. Select branch and click **Run workflow**

## References

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Semantic Versioning](https://semver.org/)
