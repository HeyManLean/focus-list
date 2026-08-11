#!/bin/bash
# 专注清单 · 启动脚本
cd "$(dirname "$0")/../app"
if curl -s -m 2 http://127.0.0.1:8765/api/info >/dev/null 2>&1; then
  echo "专注清单服务已在运行"
  open "http://127.0.0.1:8765"
  exit 0
fi
exec python3 server.py
