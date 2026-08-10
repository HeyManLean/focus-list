#!/bin/bash
# 专注清单 · 启动脚本
cd "$(dirname "$0")/../app"
exec python3 server.py
