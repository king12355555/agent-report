@echo off
chcp 936 >nul
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"

echo ==========================================
echo  AI Agent 自动化日报/周报生成器 - 一键启动
echo ==========================================
echo.

REM 若端口已被占用（服务已在运行）则跳过启动，避免重复窗口报错
echo [1/3] 检查 MCP 工具服务 (端口 8001) ...
netstat -an | findstr /c:":8001" | findstr "LISTEN" >nul
if errorlevel 1 (
    echo       未运行，正在启动 ...
    start "MCP-Server" cmd /k "cd /d ""%~dp0backend"" && set PYTHONIOENCODING=utf-8 && python -m mcp_server.server"
) else (
    echo       已在运行，跳过启动
)

echo [2/3] 检查后端 FastAPI (端口 8000) ...
netstat -an | findstr /c:":8000" | findstr "LISTEN" >nul
if errorlevel 1 (
    echo       未运行，正在启动 ...
    start "Backend" cmd /k "cd /d ""%~dp0backend"" && set PYTHONIOENCODING=utf-8 && python -m app.main"
) else (
    echo       已在运行，跳过启动
)

echo [3/3] 检查前端 Vue3 (端口 5173) ...
netstat -an | findstr /c:":5173" | findstr "LISTEN" >nul
if errorlevel 1 (
    echo       未运行，正在启动 ...
    start "Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
) else (
    echo       已在运行，跳过启动
)

echo.
echo [4/4] 等待前端就绪，将自动打开浏览器 ...
set /a tries=0
:wait_front
netstat -an | findstr /c:":5173" | findstr "LISTEN" >nul && goto open_browser
set /a tries+=1
ping -n 2 127.0.0.1 >nul
if %tries% lss 20 goto wait_front
:open_browser
start "" "http://localhost:5173"
echo 已自动打开浏览器: http://localhost:5173
echo 若未弹出窗口，请手动访问上述地址；关闭时直接关闭对应窗口即可。
ping -n 4 127.0.0.1 >nul
endlocal
