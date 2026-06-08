#!/usr/bin/env bash
# 在远端服务器上执行：拉取最新代码并重启 FastAPI 服务
#
# 环境变量（可选，均有默认值）：
#   REPO_ROOT          仓库根目录，默认当前脚本向上两级再向上一级…见下方推导
#   GIT_BRANCH         默认 main
#   SERVER_REL_PATH    相对仓库根的 server 路径
#   SYSTEMD_SERVICE    systemd 单元名，默认 figma-make-server
#   SKIP_GIT           设为 1 则跳过 git pull（仅 sync + restart）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIGMA_MAKE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${FIGMA_MAKE_ROOT}/../.." && pwd)}"
SERVER_REL_PATH="${SERVER_REL_PATH:-完整代码/figma-make/server}"
GIT_BRANCH="${GIT_BRANCH:-main}"
SYSTEMD_SERVICE="${SYSTEMD_SERVICE:-figma-make-server}"
SERVER_DIR="${REPO_ROOT}/${SERVER_REL_PATH}"

log() { echo "[deploy-server] $*"; }

if [[ "${SKIP_GIT:-0}" != "1" ]]; then
  log "git pull @ ${REPO_ROOT} (branch=${GIT_BRANCH})"
  cd "${REPO_ROOT}"
  git fetch origin "${GIT_BRANCH}"
  git checkout "${GIT_BRANCH}"
  git pull --ff-only origin "${GIT_BRANCH}"
fi

if [[ ! -d "${SERVER_DIR}" ]]; then
  log "ERROR: server 目录不存在: ${SERVER_DIR}"
  exit 1
fi

log "uv sync @ ${SERVER_DIR}"
cd "${SERVER_DIR}"
if ! command -v uv >/dev/null 2>&1; then
  log "ERROR: 未安装 uv，请先: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
uv sync

if systemctl is-active --quiet "${SYSTEMD_SERVICE}" 2>/dev/null; then
  log "systemctl restart ${SYSTEMD_SERVICE}"
  sudo systemctl restart "${SYSTEMD_SERVICE}"
  sudo systemctl --no-pager status "${SYSTEMD_SERVICE}" || true
elif command -v supervisorctl >/dev/null 2>&1; then
  log "supervisorctl restart ${SYSTEMD_SERVICE}"
  sudo supervisorctl restart "${SYSTEMD_SERVICE}"
else
  log "WARN: 未找到 systemd/supervisor，请手动重启服务（PORT=7001 uv run main.py）"
fi

log "done"
