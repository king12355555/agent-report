"""
初始化演示数据库：为最近 14 天生成工作日志与量化指标。

运行方式:
    python seed_data.py
"""
import os
import random
import sqlite3
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "worklog.db")

# 以“AI 应用开发工程师”为视角的演示数据，保证生成的报告贴合 AI 应用开发主题
TASKS = {
    "开发": [
        "完成 RAG 知识库问答接口开发",
        "修复 Agent 工具调用超时问题",
        "实现对话流式输出前端联调",
        "开发日报自动生成功能",
        "接入 MCP 工具服务",
        "优化向量检索召回率",
        "实现知识库文档增量更新",
        "开发多轮对话记忆模块",
    ],
    "测试": [
        "编写 RAG 链路自动化测试",
        "回归测试 Agent 多轮对话",
        "压测问答接口响应时间",
        "验收小程序真机适配",
        "编写 Prompt 评测用例",
    ],
    "会议": [
        "每日站会",
        "AI 方案设计讨论",
        "需求评审会",
        "周会进度同步",
        "技术分享会",
    ],
    "学习": [
        "学习 LangGraph 源码",
        "研究 MCP 协议规范",
        "阅读 RAG 相关论文",
        "Docker/K8s 实战练习",
        "学习向量数据库原理",
    ],
    "数据": [
        "构建问答评测集",
        "标注训练数据",
        "分析召回效果数据",
        "统计接口调用量",
    ],
}

random.seed(42)
today = date.today()
days = 14


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS work_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            task TEXT NOT NULL,
            category TEXT NOT NULL,
            hours REAL NOT NULL,
            status TEXT NOT NULL DEFAULT '完成',
            detail TEXT DEFAULT ''
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_date TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL
        )
        """
    )

    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        # 周末工作量减少，便于生成图表时看出趋势
        n = random.randint(2, 4) if d.weekday() >= 5 else random.randint(4, 6)
        cats = random.choices(list(TASKS.keys()), weights=[0.4, 0.2, 0.15, 0.15, 0.1], k=n)
        for cat in cats:
            task = random.choice(TASKS[cat])
            status = random.choices(
                ["完成", "完成", "完成", "进行中", "阻塞"], weights=[0.5, 0.2, 0.15, 0.1, 0.05]
            )[0]
            hours = round(random.uniform(1.0, 3.5), 1)
            detail = {
                "完成": "完成并提交代码",
                "进行中": "进行中，进度约 70%",
                "阻塞": "等待上游接口",
            }[status]
            cur.execute(
                "INSERT INTO work_log (work_date, task, category, hours, status, detail) VALUES (?,?,?,?,?,?)",
                (d.isoformat(), task, cat, hours, status, detail),
            )
        # 量化指标
        weekend = 1.0 if d.weekday() >= 5 else 1.0
        metrics = {
            "代码提交数": round(random.uniform(3, 14) * weekend, 0),
            "修复Bug数": round(random.uniform(0, 5) * weekend, 0),
            "接口调用量": round(random.uniform(800, 3000) * weekend, 0),
            "解答问题数": round(random.uniform(2, 10) * weekend, 0),
        }
        for name, value in metrics.items():
            cur.execute(
                "INSERT INTO metrics (metric_date, metric_name, value) VALUES (?,?,?)",
                (d.isoformat(), name, value),
            )

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM work_log").fetchone()[0]
    cur.close()
    conn.close()
    print(f"[OK] 演示数据已生成: {total} 条工作日志 + 指标数据, 数据库: {DB_PATH}")


if __name__ == "__main__":
    main()
