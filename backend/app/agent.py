"""
LangGraph Agent 工作流: 自动化日报/周报生成器。

流程: 收集数据(查询工作日志/指标) → 生成图表配置 → LLM 撰写报告(流式) → 发送报告

流式输出:
- step 事件: 每个节点的执行过程(通过 get_stream_writer, stream_mode="custom")
- token 事件: 报告生成过程中的逐字输出(流式 LLM)
"""
import json
from typing import Optional, TypedDict

import httpx
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from .config import settings
from .mcp_client import MCPClient

REPORT_PROMPT_TEMPLATE = """你是一名 AI 应用开发工程师，请根据下面的工作日志和量化指标，撰写一份{report_type}。

## 工作日志
{worklog}

## 量化指标
{metrics}

要求：
1. 使用 Markdown 格式，包含四个部分：一、核心工作内容；二、主要成果；三、问题与风险；四、{plan_title}；
2. 内容要结合具体数据，突出与 AI 应用开发（RAG 知识库、Agent、大模型应用）相关的工作；
3. 语言简洁专业，避免空话套话，总字数 400-600 字。
"""


class AgentState(TypedDict):
    report_type: str   # daily / weekly
    period: str        # 报告期间描述，如 "2026-08-20"
    days: int          # 统计天数
    worklog: str
    metrics: str
    chart_config: str
    report: str
    email_result: str


def build_graph(client: MCPClient):
    """构造 LangGraph 工作流。client 为共享的 MCP 客户端。"""

    async def collect_data(state: AgentState):
        writer = get_stream_writer()
        days = state["days"]
        writer({"type": "step", "icon": "🔎", "title": "收集工作数据",
                "detail": f"正在通过 MCP 工具服务查询最近 {days} 天的工作日志与量化指标..."})
        worklog = await client.call_tool("query_worklog", {"days": days})
        writer({"type": "data", "source": "worklog", "content": worklog})
        metrics = await client.call_tool("fetch_metrics", {"days": days})
        writer({"type": "data", "source": "metrics", "content": metrics})
        writer({"type": "step", "icon": "📥", "title": "数据收集完成",
                "detail": f"获取工作日志与指标数据成功，共 {len(worklog.splitlines())} 行数据"})
        return {"worklog": worklog, "metrics": metrics}

    async def generate_chart(state: AgentState):
        writer = get_stream_writer()
        writer({"type": "step", "icon": "📈", "title": "生成趋势图表",
                "detail": "调用 generate_chart 工具，生成最近几天的工时与代码提交趋势图..."})
        chart_config = await client.call_tool("generate_chart", {"days": state["days"]})
        try:
            chart = json.loads(chart_config)
            n = len(chart.get("xAxis", {}).get("data", []))
            writer({"type": "step", "icon": "📊", "title": "图表生成完成",
                    "detail": f"已生成包含 {n} 个时间点的双轴趋势图（工时柱状 + 提交折线）"})
        except Exception:
            writer({"type": "step", "icon": "📊", "title": "图表生成完成", "detail": "已生成趋势图配置"})
        return {"chart_config": chart_config}

    async def write_report(state: AgentState):
        writer = get_stream_writer()
        writer({"type": "step", "icon": "✍️", "title": "LLM 撰写报告",
                "detail": "调用大模型，结合工作日志与指标生成结构化报告（流式输出中...）"})
        report_type_label = "日报" if state["report_type"] == "daily" else "周报"
        prompt = REPORT_PROMPT_TEMPLATE.format(
            report_type=report_type_label,
            worklog=state["worklog"],
            metrics=state["metrics"],
            plan_title="明日计划" if state["report_type"] == "daily" else "下周计划",
        )
        report = await _stream_llm(prompt, writer)
        if not report:
            report = _fallback_report(state, report_type_label)
            writer({"type": "step", "icon": "⚠️", "title": "使用离线模板生成",
                    "detail": "未配置 API Key 或调用失败，已用规则模板生成报告（配置 DEEPSEEK_API_KEY 可获取 AI 生成版本）"})
        return {"report": report}

    async def send_email(state: AgentState):
        writer = get_stream_writer()
        report_type_label = "日报" if state["report_type"] == "daily" else "周报"
        writer({"type": "step", "icon": "📧", "title": "发送报告",
                "detail": f"通过 send_report_email 工具投递{report_type_label}..."})
        email_result = await client.call_tool(
            "send_report_email",
            {"report": state["report"], "report_type": report_type_label, "period": state["period"]},
        )
        writer({"type": "step", "icon": "✅", "title": "报告投递完成", "detail": email_result})
        return {"email_result": email_result}

    graph = StateGraph(AgentState)
    graph.add_node("collect_data", collect_data)
    graph.add_node("generate_chart", generate_chart)
    graph.add_node("write_report", write_report)
    graph.add_node("send_email", send_email)
    graph.add_edge(START, "collect_data")
    graph.add_edge("collect_data", "generate_chart")
    graph.add_edge("generate_chart", "write_report")
    graph.add_edge("write_report", "send_email")
    graph.add_edge("send_email", END)
    return graph.compile()


async def _stream_llm(prompt: str, writer) -> str:
    """调用 OpenAI 兼容接口（DeepSeek），流式返回报告文本。失败返回空字符串。"""
    if not settings.deepseek_api_key:
        return ""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    report = ""
    try:
        async with httpx.AsyncClient(timeout=120) as http:
            async with http.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"]
                        text = delta.get("content") or ""
                    except Exception:
                        continue
                    if text:
                        report += text
                        writer({"type": "token", "token": text})
    except Exception as e:
        print(f"[agent] LLM 调用失败: {e}")
        return ""
    return report


def _fallback_report(state: AgentState, report_type_label: str) -> str:
    """无 API Key 时的离线兜底报告（规则生成）。"""
    days = state["days"]
    period = state["period"]
    worklog = state["worklog"] or ""
    lines = [l for l in worklog.splitlines() if "|" in l and "日期" not in l]
    total_hours = 0.0
    done = blocked = 0
    for l in lines:
        try:
            total_hours += float(l.split("|")[3].strip())
        except Exception:
            pass
        if "阻塞" in l:
            blocked += 1
        elif "完成" in l or "进行中" in l:
            done += 1
    return (
        f"# {report_type_label}（{period}）\n\n"
        f"## 一、核心工作内容\n"
        f"最近 {days} 天累计工作 {total_hours:.1f} 小时，共 {len(lines)} 项任务，"
        f"主要集中在 RAG 知识库问答、Agent 工具调用优化、对话流式输出等 AI 应用开发工作。\n\n"
        f"## 二、主要成果\n"
        f"- 完成 {done} 项开发/测试任务，其中知识库问答接口与流式输出功能已上线联调\n"
        f"- 修复 Agent 工具调用超时问题，多轮对话稳定性提升\n"
        f"- 指标数据：详见系统内量化指标汇总\n\n"
        f"## 三、问题与风险\n"
        f"- 存在 {blocked} 项阻塞任务，等待上游接口支持\n"
        f"- 向量检索召回率仍有优化空间\n\n"
        f"## 四、后续计划\n"
        f"- 继续优化 RAG 召回效果，完善评测集\n"
        f"- 推进 Agent 工具服务（MCP）更多能力接入\n"
    )
