#!/usr/bin/env bash
# 一键启动 (macOS / Linux / Git Bash)
set -e
cd "$(dirname "$0")"

echo "[1/3] 启动 MCP 工具服务 (端口 8001) ..."
(cd backend && PYTHONIOENCODING=utf-8 python -m mcp_server.server > /tmp/mcp.log 2>&1 &)

echo "[2/3] 启动后端 FastAPI (端口 8000) ..."
(cd backend && PYTHONIOENCODING=utf-8 python -m app.main > /tmp/backend.log 2>&1 &)

echo "[3/3] 启动前端 Vue3 (端口 5173) ..."
(cd frontend && npm run dev > /tmp/vite.log 2>&1 &)

sleep 5
echo ""
echo "全部启动完成，浏览器访问: http://localhost:5173"
echo "停止: 运行 stop.sh"
