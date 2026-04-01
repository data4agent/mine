#!/usr/bin/env bash
# AUTH_HELPER - 简化的登录辅助工具
# 用法: bash auth_helper.sh <platform_domain>
# 例如: bash auth_helper.sh linkedin.com

set -euo pipefail

PLATFORM_DOMAIN="${1:-}"
if [ -z "$PLATFORM_DOMAIN" ]; then
  echo "用法: $0 <platform_domain>" >&2
  echo "例如: $0 linkedin.com" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VRD="$SCRIPT_DIR/vrd.py"
STATE="$HOME/.openclaw/vrd-data/state.json"

# 映射常见平台到登录URL
get_login_url() {
  case "$1" in
    linkedin.com|www.linkedin.com)
      echo "https://www.linkedin.com/login"
      ;;
    amazon.com|www.amazon.com)
      echo "https://www.amazon.com/ap/signin"
      ;;
    twitter.com|www.twitter.com|x.com|www.x.com)
      echo "https://twitter.com/login"
      ;;
    *)
      echo "https://$1/login"
      ;;
  esac
}

# Step 1: 尝试静默导入cookie
echo "[AUTH] 尝试导入已有cookie..." >&2
if agent-browser --cdp 9222 --session vrd cookie-import --domain "$PLATFORM_DOMAIN" 2>/dev/null; then
  echo "[AUTH] Cookie导入成功" >&2
  exit 0
fi

echo "[AUTH] 无可用cookie，准备启动VNC..." >&2

# Step 2: 启动VNC (如果未运行)
if ! python3 "$VRD" status >/dev/null 2>&1; then
  echo "[AUTH] 启动VNC栈..." >&2
  KASM_BIND=0.0.0.0 python3 "$VRD" start >/tmp/vrd-start.log 2>&1
  sleep 3
fi

# 获取PUBLIC_URL
PUBLIC_URL=$(python3 -c "import json; print(json.load(open('$STATE')).get('PUBLIC_URL',''))" 2>/dev/null || echo "")
if [ -z "$PUBLIC_URL" ]; then
  echo "[ERROR] 无法获取PUBLIC_URL，VNC可能未正确启动" >&2
  exit 1
fi

# Step 3: 打开登录页面
LOGIN_URL=$(get_login_url "$PLATFORM_DOMAIN")
echo "[AUTH] 打开登录页面: $LOGIN_URL" >&2
agent-browser --cdp 9222 --session vrd open "$LOGIN_URL" >/dev/null 2>&1 || true

# 设置引导消息
TOKEN=$(python3 -c "import json; print(json.load(open('$STATE')).get('SWITCH_TOKEN',''))" 2>/dev/null || echo "")
if [ -n "$TOKEN" ]; then
  curl -s -X POST "http://127.0.0.1:6090/guide?token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"text":"Please login, then click Done below","kind":"action"}' >/dev/null 2>&1 || true
fi

# 输出cloudflare链接给用户
echo "$PUBLIC_URL"

# Step 4: 等待用户完成 (在调用者脚本中处理)
# 调用者应该等待用户说"done"或者轮询 /continue/poll

# 导出成功标志
exit 0
