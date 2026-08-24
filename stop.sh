#!/usr/bin/env bash
# 停止所有服务 (macOS / Linux / Git Bash)
pkill -f "mcp_server.server" 2>/dev/null || true
pkill -f "app.main" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
echo "已停止全部服务"
