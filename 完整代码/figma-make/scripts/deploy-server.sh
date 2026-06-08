#!/usr/bin/env bash
# 远端部署：拉代码 → uv sync → 重装/重启 systemd
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIGMA_MAKE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${FIGMA_MAKE_ROOT}/../.." && pwd)"
SERVER_DIR="${FIGMA_MAKE_ROOT}/server"
GIT_BRANCH="${GIT_BRANCH:-main}"
SYSTEMD_SERVICE="${SYSTEMD_SERVICE:-figma-make-server}"

log() { echo "[deploy-server] $*"; }

if [[ "${SKIP_GIT:-0}" != "1" && -d "${REPO_ROOT}/.git" ]]; then
  log "git pull @ ${REPO_ROOT} (branch=${GIT_BRANCH})"
  cd "${REPO_ROOT}"
  git pull --ff-only origin "${GIT_BRANCH}" || {
    log "WARN: git pull 失败（网络问题可稍后手动 pull），继续部署当前代码"
  }
fi

log "uv sync @ ${SERVER_DIR}"
cd "${SERVER_DIR}"
uv sync

if command -v systemctl >/dev/null 2>&1 && bash -lc 'command -v uv' &>/dev/null; then
  log "安装/更新 systemd（写入 uv 绝对路径）"
  bash -l "${SCRIPT_DIR}/install-systemd.sh"
else
  log "WARN: 跳过 systemd。手动启动："
  log "  cd ${SERVER_DIR} && uv run uvicorn main:app --host 0.0.0.0 --port 7001"
fi

log "done"
