#!/usr/bin/env bash
# 远端部署：拉代码 → uv sync → 重启服务
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

if command -v systemctl >/dev/null 2>&1 && systemctl cat "${SYSTEMD_SERVICE}" &>/dev/null; then
  log "systemctl restart ${SYSTEMD_SERVICE}"
  if ! sudo systemctl restart "${SYSTEMD_SERVICE}"; then
    log "WARN: restart 失败，在服务器执行一次："
    log "  bash ${FIGMA_MAKE_ROOT}/scripts/install-systemd.sh"
    sudo systemctl status "${SYSTEMD_SERVICE}" --no-pager || true
    sudo systemd-analyze verify "${SYSTEMD_SERVICE}.service" 2>&1 || true
  fi
else
  log "WARN: 未配置 systemd，跳过重启。安装服务："
  log "  bash ${FIGMA_MAKE_ROOT}/scripts/install-systemd.sh"
fi

log "done"
