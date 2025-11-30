#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="raspscan"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${APP_DIR}/.venv"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
RUN_USER="${SUDO_USER:-$(whoami)}"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "[!] Please run this installer with sudo or as root." >&2
        exit 1
    fi
}

install_packages() {
    echo "[+] Installing system dependencies via apt..."
    apt-get update -y
    apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        avahi-daemon \
        sane-utils \
        sane-airscan \
        smbclient \
        ssh \
        sshpass \
        imagemagick \
        nodejs \
        npm
    
    # Enable and start services
    systemctl enable avahi-daemon
    systemctl start avahi-daemon
}

setup_venv() {
    echo "[+] Creating virtual environment in ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip
    if [[ -f "${APP_DIR}/requirements.txt" ]]; then
        pip install -r "${APP_DIR}/requirements.txt"
    else
        echo "[!] requirements.txt not found; skipping Python dependency installation" >&2
    fi
}

setup_webui() {
    echo "[+] Setting up Web UI..."
    local WEB_DIR="${APP_DIR}/app/web"
    if [[ -d "${WEB_DIR}" && -f "${WEB_DIR}/package.json" ]]; then
        cd "${WEB_DIR}"
        echo "[+] Installing npm dependencies..."
        sudo -u "${RUN_USER}" npm install
        echo "[+] Building Web UI for production..."
        sudo -u "${RUN_USER}" npm run build
        cd "${APP_DIR}"
        echo "[✓] Web UI built successfully"
    else
        echo "[!] Web UI directory not found; skipping Web UI setup" >&2
    fi
}

create_service() {
    echo "[+] Writing systemd unit to ${SERVICE_FILE}..."
    cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=RaspScan FastAPI server
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
Environment="VIRTUAL_ENV=${VENV_DIR}"
Environment="PATH=${VENV_DIR}/bin:/usr/bin:/bin"
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE
    chmod 644 "${SERVICE_FILE}"
}

enable_service() {
    echo "[+] Enabling and starting ${SERVICE_NAME} service..."
    systemctl daemon-reload
    systemctl enable --now "${SERVICE_NAME}"
    sleep 2
    systemctl status "${SERVICE_NAME}" --no-pager --full || true
}

setup_cleanup_cron() {
    echo "[+] Setting up automatic cleanup cron job..."
    local CLEANUP_SCRIPT="${APP_DIR}/scripts/cleanup.sh"
    
    # Make cleanup script executable
    if [[ -f "${CLEANUP_SCRIPT}" ]]; then
        chmod +x "${CLEANUP_SCRIPT}"
        
        # Add cron job for automatic cleanup (daily at 3 AM)
        local CRON_LINE="0 3 * * * ${CLEANUP_SCRIPT}"
        
        # Check if cron job already exists
        if sudo -u "${RUN_USER}" crontab -l 2>/dev/null | grep -q "${CLEANUP_SCRIPT}"; then
            echo "[✓] Cleanup cron job already exists"
        else
            # Add to user's crontab
            (sudo -u "${RUN_USER}" crontab -l 2>/dev/null || true; echo "${CRON_LINE}") | sudo -u "${RUN_USER}" crontab -
            echo "[✓] Cleanup cron job added (runs daily at 3 AM)"
        fi
        
        # Create log directory
        mkdir -p /var/log
        touch /var/log/raspscan-cleanup.log
        chown "${RUN_USER}:${RUN_USER}" /var/log/raspscan-cleanup.log
    else
        echo "[!] Cleanup script not found at ${CLEANUP_SCRIPT}; skipping cron setup" >&2
    fi
}

print_info() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                  RaspScan Installation Complete                  ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✓ RaspScan is running on: http://$(hostname -I | awk '{print $1}')"
    echo "✓ API Documentation: http://$(hostname -I | awk '{print $1}')/docs"
    echo "✓ Health Check: http://$(hostname -I | awk '{print $1}')/health"
    echo ""
    echo "Default Admin Credentials:"
    echo "  Username: admin"
    echo "  Password: admin"
    echo ""
    echo "⚠️  SECURITY WARNING:"
    echo "  1. Change the default admin password immediately!"
    echo "  2. Consider enabling authentication: export RASPSCAN_REQUIRE_AUTH=true"
    echo "  3. Set up HTTPS via reverse proxy (Caddy/nginx)"
    echo ""
    echo "Database Location: ${APP_DIR}/raspscan.db"
    echo ""
    echo "Service Management:"
    echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
    echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
    echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
    echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "Automatic Cleanup:"
    echo "  Scheduled: Daily at 3:00 AM"
    echo "  View cron: crontab -l"
    echo "  Manual run: cd ${APP_DIR} && python3 -m app.core.cleanup"
    echo "  Cleanup logs: tail -f /var/log/raspscan-cleanup.log"
    echo ""
    echo "Web UI:"
    echo "  Production build already served at: http://$(hostname -I | awk '{print $1}')/"
    echo "  For development with hot-reload:"
    echo "    cd ${APP_DIR}/app/web"
    echo "    npm run dev"
    echo ""
}

main() {
    require_root
    install_packages
    setup_venv
    setup_webui
    create_service
    setup_cleanup_cron
    enable_service
    print_info
}

main "$@"
