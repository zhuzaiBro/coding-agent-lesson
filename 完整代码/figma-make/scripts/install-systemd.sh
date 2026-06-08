#!/usr/bin/env bash
# 在服务器上运行：按真实路径生成 systemd unit（uv 必须用绝对路径）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIGMA_MAKE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVER_DIR="${FIGMA_MAKE_ROOT}/server"
SERVICE_NAME="${SYSTEMD_SERVICE:-figma-make-server}"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

log() { echo "[install-systemd] $*"; }

if [[ ! -f "${SERVER_DIR}/pyproject.toml" ]]; then
  echo "ERROR: 找不到 ${SERVER_DIR}/pyproject.toml" >&2
  exit 1
fi

UV_PATH="${UV_PATH:-$(bash -lc 'command -v uv' 2>/dev/null || true)}"
UV_PATH="${UV_PATH:-/root/.local/bin/uv}"
if [[ ! -x "${UV_PATH}" ]]; then
  echo "ERROR: 找不到 uv（尝试过 ${UV_PATH}）" >&2
  exit 1
fi

UV_BIN_DIR="$(dirname "${UV_PATH}")"
log "SERVER_DIR=${SERVER_DIR}"
log "UV_PATH=${UV_PATH}"

sudo tee "${UNIT_PATH}" >/dev/null <<EOF
[Unit]
Description=Figma Make FastAPI Server (uvicorn :7001)
After=network.target

[Service]
Type=simple
WorkingDirectory=${SERVER_DIR}
Environment=PORT=7001
Environment=PATH=${UV_BIN_DIR}:/usr/local/bin:/usr/bin:/bin
ExecStart=${UV_PATH} run uvicorn main:app --host 0.0.0.0 --port 7001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"
sudo systemctl status "${SERVICE_NAME}" --no-pager

log "done"
