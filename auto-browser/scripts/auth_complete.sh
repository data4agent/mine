#!/usr/bin/env bash
# AUTH_COMPLETE - 完成登录流程
# 用法: bash auth_complete.sh [--wait-user | --timeout SECONDS]
# 例如: bash auth_complete.sh --wait-user  (等待用户说"done")
# 例如: bash auth_complete.sh --timeout 300 (轮询300秒)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HOME/.openclaw/vrd-data/state.json"

MODE="${1:-timeout}"
TIMEOUT="${2:-300}"

TOKEN=$(python3 -c "import json; print(json.load(open('$STATE')).get('SWITCH_TOKEN',''))" 2>/dev/null || echo "")

if [ "$MODE" = "--wait-user" ]; then
  # 由调用者在用户说"done"后调用此脚本
  echo "[AUTH] 用户已完成登录" >&2
elif [ "$MODE" = "--timeout" ]; then
  # 轮询模式
  echo "[AUTH] 等待用户完成登录(超时${TIMEOUT}秒)..." >&2
  if [ -n "$TOKEN" ]; then
    curl -s "http://127.0.0.1:6090/continue/poll?token=$TOKEN&after=0&timeout=$TIMEOUT" >/dev/null 2>&1 || true
  else
    sleep "$TIMEOUT"
  fi
else
  echo "用法: $0 [--wait-user | --timeout SECONDS]" >&2
  exit 1
fi

# 清除引导消息
if [ -n "$TOKEN" ]; then
  curl -s -X DELETE "http://127.0.0.1:6090/guide?token=$TOKEN" >/dev/null 2>&1 || true
fi

# 捕获cookie快照
echo "[AUTH] 捕获登录状态..." >&2
agent-browser --cdp 9222 --session vrd snapshot >/dev/null 2>&1 || true

echo "[AUTH] 登录完成" >&2
exit 0
