"""
FastAPI 后端: 启动时连接 MCP 工具服务，提供 SSE 流式接口给前端实时展示 Agent 执行过程。

运行方式:
    python -m app.main          # 或 uvicorn app.main:app --port 8000
接口:
    GET /api/report/stream?type=daily|weekly
"""
import asyncio
import importlib.util
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .agent import build_graph
from .config import PROJECT_ROOT, settings
from .mcp_client import MCPClient

DB_PATH = PROJECT_ROOT / "data" / "worklog.db"


def _run_seed():
    """重新生成最近 14 天演示数据（等价于手动执行 python seed_data.py）。"""
    seed_path = PROJECT_ROOT / "seed_data.py"
    spec = importlib.util.spec_from_file_location("seed_data", seed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()  # 注意: 模块内 main() 受 __name__ == "__main__" 保护，必须显式调用


def ensure_demo_db():
    """确保演示数据库可用：
    1. 不存在时自动生成（方便首次运行直接体验）；
    2. 数据过期（最新记录不是今天）时自动重新播种最近 14 天数据。
    否则日报/周报会查不到数据，导致图表为空、报告内容缺失。
    幂等：数据已覆盖今天时不做任何事，可在启动时与每次生成前重复调用。
    """
    if not DB_PATH.exists():
        print("[main] 未找到演示数据库，正在生成最近 14 天演示数据...")
        _run_seed()
        return
    try:
        import sqlite3
        from datetime import date
        conn = sqlite3.connect(DB_PATH)
        newest = conn.execute("SELECT MAX(work_date) FROM work_log").fetchone()[0]
        conn.close()
        today = date.today().isoformat()
        if newest and newest < today:
            print(f"[main] 演示数据已过期（最新记录 {newest}，今天是 {today}），正在重新生成最近 14 天演示数据...")
            _run_seed()
    except Exception as e:
        print(f"[main] 演示数据状态检查失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_demo_db()
    client = MCPClient(settings.mcp_url)
    try:
        await client.connect()
        print(f"[main] MCP 工具服务已连接: {settings.mcp_url}")
    except Exception as e:
        print(f"[main] 警告: MCP 连接失败({e})，请先启动 MCP 服务: python -m mcp_server.server")
        client = None
    app.state.mcp_client = client
    yield
    if client:
        await client.close()


app = FastAPI(title="AI Agent 自动化日报生成器", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    mcp_ok = app.state.mcp_client is not None
    return {"status": "ok", "mcp_connected": mcp_ok}


async def _run_agent_stream(report_type: str, client: MCPClient, days: int, period: str):
    graph = build_graph(client)
    initial = {
        "report_type": report_type,
        "period": period,
        "days": days,
        "worklog": "",
        "metrics": "",
        "chart_config": "",
        "report": "",
        "email_result": "",
    }
    final_state: dict = {}
    try:
        async for item in graph.astream(
            initial,
            config={"recursion_limit": 50},
            stream_mode=["updates", "custom"],
        ):
            # langgraph >= 1.0: 事件为 (mode, payload) 元组
            mode, payload = item
            if mode == "custom":
                if payload.get("type") == "token":
                    yield {"event": "report_token", "data": json.dumps({"token": payload["token"]})}
                elif payload.get("type") == "step":
                    yield {"event": "agent_step", "data": json.dumps(payload, ensure_ascii=False)}
                elif payload.get("type") == "data":
                    yield {"event": "agent_data", "data": json.dumps(payload, ensure_ascii=False)}
            elif mode == "updates":
                for node, update in payload.items():
                    final_state.update(update)
        yield {
            "event": "done",
            "data": json.dumps({
                "report": final_state.get("report", ""),
                "chart_config": final_state.get("chart_config", ""),
                "email_result": final_state.get("email_result", ""),
            }, ensure_ascii=False),
        }
    except Exception as e:
        print(f"[main] Agent 运行失败: {e}")
        yield {"event": "error", "data": json.dumps({"message": str(e)}, ensure_ascii=False)}


@app.get("/api/report/stream")
async def report_stream(type: str = Query("daily", pattern="^(daily|weekly)$")):
    """SSE 流式接口: 实时推送 Agent 步骤、报告 token、最终结果。"""
    # 每次生成前确保演示数据覆盖到今天（后端跨天运行/数据过期时自动重新播种），
    # 避免日报/周报因查不到数据而图表为空。
    ensure_demo_db()
    client = app.state.mcp_client
    if client is None:
        return {"error": "MCP 工具服务未连接，请先启动: cd backend && python -m mcp_server.server"}

    from datetime import date, timedelta
    today = date.today()
    if type == "weekly":
        days = 7
        start = today - timedelta(days=6)
        period = f"{start.isoformat()}~{today.isoformat()}"
    else:
        days = 1
        period = today.isoformat()

    return EventSourceResponse(
        _run_agent_stream(type, client, days=days, period=period),
        ping=15,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
