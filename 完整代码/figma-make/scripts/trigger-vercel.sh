#!/usr/bin/env bash
# 触发 Vercel Deploy Hook 重新构建 frontend
# 用法: VERCEL_DEPLOY_HOOK_URL=https://api.vercel.com/... ./trigger-vercel.sh
set -euo pipefail

HOOK_URL="${VERCEL_DEPLOY_HOOK_URL:-}"
if [[ -z "${HOOK_URL}" ]]; then
  echo "ERROR: 请设置 VERCEL_DEPLOY_HOOK_URL" >&2
  exit 1
fi

echo "[trigger-vercel] POST deploy hook..."
HTTP_CODE="$(curl -sS -o /tmp/vercel-hook-response.json -w "%{http_code}" -X POST "${HOOK_URL}")"
cat /tmp/vercel-hook-response.json
echo ""
if [[ "${HTTP_CODE}" -ge 200 && "${HTTP_CODE}" -lt 300 ]]; then
  echo "[trigger-vercel] ok (HTTP ${HTTP_CODE})"
else
  echo "[trigger-vercel] failed (HTTP ${HTTP_CODE})" >&2
  exit 1
fi
