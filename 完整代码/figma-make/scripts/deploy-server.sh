#!/usr/bin/env bash
# 在远端服务器上执行：拉取最新代码并重启 FastAPI 服务
#
# 路径解析优先级（避免 SERVER_REPO_PATH 配错导致找不到 pyproject.toml）：
#   1. 环境变量 SERVER_DIR（绝对路径，需含 pyproject.toml）
#   2. 本脚本所在 figma-make/server（与仓库布局绑定，最可靠）
#   3. REPO_ROOT + SERVER_REL_PATH
#
# 环境变量：
#   REPO_ROOT / SERVER_REPO_PATH  git 仓库根（可选，默认从脚本位置推导）
#   GIT_BRANCH                    默认 main
#   GIT_REMOTE_URL                （推荐）origin 地址，如 git@github.com:zhuzaiBro/coding-agent-lesson.git
#   GIT_RETRY_MAX                 git 重试次数，默认 5
#   SYSTEMD_SERVICE               默认 figma-make-server
#   SKIP_GIT                      设为 1 则跳过 git pull
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIGMA_MAKE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_REPO_ROOT="$(cd "${FIGMA_MAKE_ROOT}/../.." && pwd)"
REPO_ROOT="${REPO_ROOT:-${SERVER_REPO_PATH:-${DEFAULT_REPO_ROOT}}}"
SERVER_REL_PATH="${SERVER_REL_PATH:-完整代码/figma-make/server}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_RETRY_MAX="${GIT_RETRY_MAX:-5}"
SYSTEMD_SERVICE="${SYSTEMD_SERVICE:-figma-make-server}"

log() { echo "[deploy-server] $*"; }

run_with_retry() {
  local label="$1"
  shift
  local attempt=1
  local delay=5
  while [[ "${attempt}" -le "${GIT_RETRY_MAX}" ]]; do
    if "$@"; then
      return 0
    fi
    if [[ "${attempt}" -eq "${GIT_RETRY_MAX}" ]]; then
      break
    fi
    log "WARN: ${label} 失败 (${attempt}/${GIT_RETRY_MAX})，${delay}s 后重试..."
    sleep "${delay}"
    attempt=$((attempt + 1))
    delay=$((delay * 2))
  done
  return 1
}

https_to_ssh_url() {
  local url="$1"
  if [[ "${url}" == https://github.com/* ]]; then
    echo "git@github.com:${url#https://github.com/}"
    return 0
  fi
  return 1
}

ensure_git_remote() {
  local repo_root="$1"
  cd "${repo_root}"
  if [[ -n "${GIT_REMOTE_URL:-}" ]]; then
    local current
    current="$(git remote get-url origin 2>/dev/null || true)"
    if [[ "${current}" != "${GIT_REMOTE_URL}" ]]; then
      log "设置 origin=${GIT_REMOTE_URL}"
      git remote set-url origin "${GIT_REMOTE_URL}"
    fi
  fi
}

git_pull_repo() {
  local repo_root="$1"
  cd "${repo_root}"
  ensure_git_remote "${repo_root}"
  git fetch origin "${GIT_BRANCH}"
  git checkout "${GIT_BRANCH}"
  git pull --ff-only origin "${GIT_BRANCH}"
}

git_pull_repo_with_fallback() {
  local repo_root="$1"
  if run_with_retry "git pull" git_pull_repo "${repo_root}"; then
    return 0
  fi

  local url ssh_url
  url="$(cd "${repo_root}" && git remote get-url origin)"
  if ssh_url="$(https_to_ssh_url "${url}")"; then
    log "HTTPS 不稳定，切换 origin 为 SSH 后重试: ${ssh_url}"
    cd "${repo_root}"
    git remote set-url origin "${ssh_url}"
    if run_with_retry "git pull (ssh)" git_pull_repo "${repo_root}"; then
      return 0
    fi
  fi

  log "ERROR: git pull 失败。建议在服务器配置 SSH 拉取："
  log "  1) ssh-keygen -t ed25519 -C deploy@$(hostname)"
  log "  2) 把 ~/.ssh/id_ed25519.pub 加到 GitHub → Settings → Deploy keys"
  log "  3) cd ${repo_root} && git remote set-url origin git@github.com:zhuzaiBro/coding-agent-lesson.git"
  log "  或在 GitHub Actions Secrets 设置 GIT_REMOTE_URL 为上述 SSH 地址"
  return 1
}

resolve_server_dir() {
  local candidate
  for candidate in \
    "${SERVER_DIR:-}" \
    "${FIGMA_MAKE_ROOT}/server" \
    "${REPO_ROOT}/${SERVER_REL_PATH}"; do
    [[ -n "${candidate}" ]] || continue
    if [[ -f "${candidate}/pyproject.toml" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

if [[ "${SKIP_GIT:-0}" != "1" ]]; then
  if [[ -d "${REPO_ROOT}/.git" ]]; then
    log "git pull @ ${REPO_ROOT} (branch=${GIT_BRANCH})"
    git_pull_repo_with_fallback "${REPO_ROOT}"
  else
    log "WARN: ${REPO_ROOT} 不是 git 根目录，跳过 pull（使用脚本路径 ${DEFAULT_REPO_ROOT}）"
    if [[ -d "${DEFAULT_REPO_ROOT}/.git" ]]; then
      log "git pull @ ${DEFAULT_REPO_ROOT} (branch=${GIT_BRANCH})"
      git_pull_repo_with_fallback "${DEFAULT_REPO_ROOT}"
      REPO_ROOT="${DEFAULT_REPO_ROOT}"
    fi
  fi
fi

if ! SERVER_DIR="$(resolve_server_dir)"; then
  log "ERROR: 找不到 pyproject.toml，请检查路径或设置 SERVER_DIR"
  log "  脚本推导 figma-make/server: ${FIGMA_MAKE_ROOT}/server"
  log "  REPO_ROOT 拼接路径: ${REPO_ROOT}/${SERVER_REL_PATH}"
  log "  REPO_ROOT=${REPO_ROOT}"
  if [[ -d "${FIGMA_MAKE_ROOT}/server" ]] && [[ -z "$(ls -A "${FIGMA_MAKE_ROOT}/server" 2>/dev/null || true)" ]]; then
    log "HINT: server 目录为空，常见原因是仓库里 server 被记为 submodule 但未 init。"
    log "      在仓库根执行: git submodule update --init --recursive"
    log "      或把 server 改为普通目录后重新 push。"
  fi
  exit 1
fi

log "server 目录: ${SERVER_DIR}"
log "uv sync @ ${SERVER_DIR}"
cd "${SERVER_DIR}"
uv sync

restart_service() {
  if command -v systemctl >/dev/null 2>&1 && systemctl cat "${SYSTEMD_SERVICE}" &>/dev/null; then
    log "systemctl restart ${SYSTEMD_SERVICE}"
    sudo systemctl restart "${SYSTEMD_SERVICE}"
    sudo systemctl --no-pager status "${SYSTEMD_SERVICE}" || true
    return 0
  fi
  if command -v supervisorctl >/dev/null 2>&1; then
    log "supervisorctl restart ${SYSTEMD_SERVICE}"
    sudo supervisorctl restart "${SYSTEMD_SERVICE}"
    return 0
  fi
  return 1
}

if ! restart_service; then
  UNIT_SRC="${FIGMA_MAKE_ROOT}/scripts/systemd/${SYSTEMD_SERVICE}.service"
  log "WARN: 未配置 systemd/supervisor，服务未自动重启。"
  log "      一次性安装（SSH 登录服务器后执行）："
  log "        sudo cp ${UNIT_SRC} /etc/systemd/system/"
  log "        sudo sed -i 's|/opt/coding-agent-lesson|${DEFAULT_REPO_ROOT}|g' /etc/systemd/system/${SYSTEMD_SERVICE}.service"
  log "        sudo sed -i 's|User=deploy|User=\$(whoami)|g' /etc/systemd/system/${SYSTEMD_SERVICE}.service"
  log "        sudo systemctl daemon-reload && sudo systemctl enable --now ${SYSTEMD_SERVICE}"
  log "      或临时手动启动："
  log "        cd ${SERVER_DIR} && PORT=7001 uv run uvicorn main:app --host 0.0.0.0 --port 7001"
fi

log "done"
