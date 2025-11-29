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
        cups \
        cups-browsed \
        avahi-daemon \
        sane-utils \
        sane-airscan \
        smbclient \
        cifs-utils
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

create_service() {
    echo "[+] Writing systemd unit to ${SERVICE_FILE}..."
    cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=RaspScan FastAPI server
After=network.target cups.service
Wants=cups.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
Environment="VIRTUAL_ENV=${VENV_DIR}"
Environment="PATH=${VENV_DIR}/bin:/usr/bin:/bin"
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
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
    systemctl status "${SERVICE_NAME}" --no-pager --full || true
}

main() {
    require_root
    install_packages
    setup_venv
    create_service
    enable_service
    echo "[+] Installation complete. RaspScan should now be running on port 8000."
}

main "$@"
