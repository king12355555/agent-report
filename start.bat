@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo  AI Agent 自动化日报/周报生成器 - 一键启动
echo ==========================================
echo.
echo [1/3] 启动 MCP 工具服务 (端口 8001) ...
start "MCP-Server" cmd /k "cd /d %~dp0backend && python -m mcp_server.server"

echo [2/3] 启动后端 FastAPI (端口 8000) ...
start "Backend" cmd /k "cd /d %~dp0backend && python -m app.main"

echo [3/3] 启动前端 Vue3 (端口 5173) ...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 全部启动完成，浏览器访问: http://localhost:5173
echo 关闭时直接关闭对应窗口即可。
timeout /t 3 >nul
