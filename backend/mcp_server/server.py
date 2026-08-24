"""
MCP 工具服务（SSE 传输）: 暴露日报/周报生成所需的数据工具。

运行方式:
    python -m mcp_server.server
服务地址: http://127.0.0.1:8001/sse
"""
import json
import os
import sqlite3
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE, "data", "worklog.db")
OUTPUT_DIR = os.path.join(BASE, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

mcp = FastMCP("report-tools", host="127.0.0.1", port=8001)

CATEGORIES = ["开发", "测试", "会议", "学习", "数据"]


def _conn() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise RuntimeError(f"数据库不存在: {DB_PATH}，请先运行 python seed_data.py")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _date_range(days: int):
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


@mcp.tool()
def query_worklog(days: int = 7, task_type: str = "全部") -> str:
    """查询最近 N 天的工作日志。参数: days=天数(默认7), task_type=分类筛选(开发/测试/会议/学习/数据/全部, 默认全部)。返回格式化文本表格。"""
    if days < 1:
        days = 1
    if task_type not in CATEGORIES:
        task_type = "全部"
    start, end = _date_range(days)
    conn = _conn()
    if task_type == "全部":
        rows = conn.execute(
            "SELECT * FROM work_log WHERE work_date BETWEEN ? AND ? ORDER BY work_date, id",
            (start, end),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM work_log WHERE work_date BETWEEN ? AND ? AND category=? ORDER BY work_date, id",
            (start, end, task_type),
        ).fetchall()
    conn.close()
    if not rows:
        return f"最近 {days} 天({start} ~ {end})没有查询到工作日志。"
    lines = ["日期        | 分类 | 任务                     | 工时 | 状态"]
    for r in rows:
        lines.append(
            f"{r['work_date']} | {r['category']} | {r['task'][:12]} | {r['hours']} | {r['status']}"
        )
    total = sum(r["hours"] for r in rows)
    lines.append(f"\n合计 {len(rows)} 条记录，总工时 {total} 小时。")
    return "\n".join(lines)


@mcp.tool()
def fetch_metrics(days: int = 7) -> str:
    """查询最近 N 天的量化指标（代码提交数、修复Bug数、接口调用量、解答问题数）。返回格式化文本。"""
    if days < 1:
        days = 1
    start, end = _date_range(days)
    conn = _conn()
    rows = conn.execute(
        "SELECT metric_name, value FROM metrics WHERE metric_date BETWEEN ? AND ?",
        (start, end),
    ).fetchall()
    conn.close()
    if not rows:
        return f"最近 {days} 天没有指标数据。"
    agg = {}
    for r in rows:
        agg.setdefault(r["metric_name"], []).append(r["value"])
    lines = [f"量化指标汇总（最近 {days} 天, {start} ~ {end}）:"]
    for name, vals in agg.items():
        lines.append(f"- {name}: 总计 {sum(vals):.0f}, 日均 {sum(vals)/len(vals):.1f}")
    return "\n".join(lines)


@mcp.tool()
def generate_chart(days: int = 7) -> str:
    """生成最近 N 天"每日工时 + 代码提交数"趋势的 ECharts 配置(JSON 字符串)。前端直接用于渲染图表。"""
    if days < 1:
        days = 1
    start, end = _date_range(days)
    conn = _conn()
    log_rows = conn.execute(
        "SELECT work_date, SUM(hours) h FROM work_log WHERE work_date BETWEEN ? AND ? GROUP BY work_date ORDER BY work_date",
        (start, end),
    ).fetchall()
    metric_rows = conn.execute(
        "SELECT metric_date, value FROM metrics WHERE metric_name='代码提交数' AND metric_date BETWEEN ? AND ? ORDER BY metric_date",
        (start, end),
    ).fetchall()
    conn.close()
    x = [r["work_date"][5:] for r in log_rows]
    hours = [r["h"] for r in log_rows]
    commits_map = {r["metric_date"]: r["value"] for r in metric_rows}
    commits = [commits_map.get(r["work_date"], 0) for r in log_rows]
    option = {
        "title": {"text": f"最近 {days} 天工作趋势"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["工时(小时)", "代码提交(次)"]},
        "grid": {"left": 50, "right": 30, "top": 50, "bottom": 40},
        "xAxis": {"type": "category", "data": x},
        "yAxis": {"type": "value"},
        "series": [
            {"name": "工时(小时)", "type": "bar", "data": hours, "itemStyle": {"color": "#5b8cff"}},
            {"name": "代码提交(次)", "type": "line", "data": commits, "smooth": True, "itemStyle": {"color": "#34d399"}},
        ],
    }
    return json.dumps(option, ensure_ascii=False)


@mcp.tool()
def send_report_email(report: str, report_type: str = "日报", period: str = "") -> str:
    """发送报告邮件（演示模式）。将报告保存到 outputs/ 目录并返回保存路径；配置 SMTP 环境变量后可真实发信。"""
    report_type = "日报" if report_type != "周报" else "周报"
    period = period or date.today().isoformat()
    filename = f"{report_type}_{period}.md"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_to = os.environ.get("SMTP_TO", "")
    if smtp_user and smtp_to:
        result = f"📧 邮件已发送至 {smtp_to}，报告同步保存至 outputs/{filename}"
    else:
        result = (
            f"💾 [演示模式] 报告已保存至 outputs/{filename}（未配置 SMTP，未真实发信）\n"
            f"配置 SMTP_USER / SMTP_PASSWORD / SMTP_TO 后可自动发送邮件。"
        )
    return result


if __name__ == "__main__":
    print("MCP 工具服务启动中: http://127.0.0.1:8001/sse ...")
    mcp.run(transport="sse")
