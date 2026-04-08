#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="scan2target"
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

# Run a command as RUN_USER.  Works whether sudo is installed or not.
run_as_user() {
    if [[ "$(id -un)" == "${RUN_USER}" ]]; then
        "$@"
    elif command -v sudo &>/dev/null; then
        sudo -u "${RUN_USER}" "$@"
    else
        su -s /bin/bash "${RUN_USER}" -c "cd $(pwd) && $(printf '%q ' "$@")"
    fi
}

install_packages() {
    echo "[+] Installing system dependencies via apt..."
    apt-get update -y
    # curl is needed first for the NodeSource setup script
    apt-get install -y curl
    # NodeSource provides Node.js with npm bundled. The Debian-packaged nodejs
    # does not ship npm and conflicts with it, so we add NodeSource if npm is absent.
    if ! command -v npm &>/dev/null; then
        echo "[+] Setting up NodeSource Node.js 20.x repository..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    fi
    apt-get install -y \
        python3 python3-venv python3-pip \
        avahi-daemon sane-utils sane-airscan \
        smbclient ssh sshpass imagemagick \
        nodejs
    systemctl enable avahi-daemon
    systemctl start avahi-daemon
}

setup_venv() {
    echo "[+] Creating virtual environment in ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip
    pip install -r "${APP_DIR}/backend/requirements.txt"
}

setup_webui() {
    echo "[+] Building Web UI..."
    local FRONTEND_DIR="${APP_DIR}/frontend"
    if [[ -d "${FRONTEND_DIR}" && -f "${FRONTEND_DIR}/package.json" ]]; then
        cd "${FRONTEND_DIR}"
        run_as_user npm ci
        run_as_user npm run build
        cd "${APP_DIR}"
        echo "[✓] Web UI built → frontend/build/"
    else
        echo "[!] frontend/ directory not found; skipping Web UI build" >&2
    fi
}

create_dirs() {
    echo "[+] Creating data directories..."
    mkdir -p "${APP_DIR}/data/db" /var/log/scan2target /tmp/scan2target
    chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}/data" /var/log/scan2target
}

create_service() {
    echo "[+] Writing systemd unit to ${SERVICE_FILE}..."
    cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=Scan2Target - Network Scanner Hub
Documentation=https://github.com/fgrfn/Scan2Target
After=network.target avahi-daemon.service
Wants=avahi-daemon.service

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_USER}
WorkingDirectory=${APP_DIR}/backend
Environment="VIRTUAL_ENV=${VENV_DIR}"
Environment="PATH=${VENV_DIR}/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=${APP_DIR}/backend"
Environment="SCAN2TARGET_DATABASE_PATH=${APP_DIR}/data/db/scan2target.db"
Environment="SCAN2TARGET_DATA_DIR=${APP_DIR}/data"
Environment="SCAN2TARGET_LOG_DIR=/var/log/scan2target"
# Encryption key is auto-generated on first start and stored in ${APP_DIR}/data/.scan2target/encryption.key
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
Restart=on-failure
RestartSec=5
StartLimitBurst=3
StartLimitInterval=300

StandardOutput=journal
StandardError=journal
SyslogIdentifier=scan2target

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

print_info() {
    local IP
    IP="$(hostname -I | awk '{print $1}')"
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           Scan2Target Installation Complete               ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "✓ Web UI:      http://${IP}:8000/"
    echo "✓ API docs:    http://${IP}:8000/docs"
    echo "✓ Health:      http://${IP}:8000/health"
    echo ""
    echo "Default credentials: admin / admin"
    echo "⚠  Change the default password (admin / admin) after first login."
    echo ""
    echo "Service management:"
    echo "  sudo systemctl start|stop|restart|status ${SERVICE_NAME}"
    echo "  sudo journalctl -u ${SERVICE_NAME} -f"
    echo ""
}

main() {
    require_root
    install_packages
    setup_venv
    setup_webui
    create_dirs
    create_service
    enable_service
    print_info
}

main "$@"
