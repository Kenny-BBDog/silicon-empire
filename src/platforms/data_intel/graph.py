"""
Data Intelligence Graph — 情报中台自动化流水线 (LangGraph).

将 Hunter 采集 → Analyst 分析 → RAG 入库 串成状态机，
可被 L2 (主要是 CGO) 通过 Skill delegate 触发。

Flow:
  receive_task → hunt_data → analyze_data → index_knowledge → deliver_report
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from src.platforms.data_intel import DataHunterAgent, InsightAnalystAgent, get_rag
from src.core.personal_memory import MemoryEntry


# Singleton agents
_hunter = DataHunterAgent()
_analyst = InsightAnalystAgent()


# ─── State ───

class DataIntelState(dict):
    """State for the data intelligence pipeline."""
    pass


# ─── Nodes ───

async def receive_task(state: dict) -> dict:
    """接收 L2 委派的情报任务，解析参数。"""
    task_type = state.get("task_type", "market_research")
    keywords = state.get("keywords", [])
    platform = state.get("platform", "amazon")
    category = state.get("category", "")

    return {
        "phase": "hunting",
        "task_type": task_type,
        "keywords": keywords,
        "platform": platform,
        "category": category or (keywords[0] if keywords else "general"),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


async def hunt_data(state: dict) -> dict:
    """Hunter 出动采集数据。"""
    task_type = state.get("task_type", "market_research")

    if task_type == "trend_discovery":
        result = await _hunter.discover_trends(state.get("category", ""))
    elif task_type == "competitor_monitor":
        result = await _hunter.monitor_competitor(
            state.get("competitor_url", ""),
            state.get("check_items", None),
        )
    elif task_type == "review_analysis":
        result = await _hunter.extract_reviews(
            state.get("product_url", ""),
            state.get("focus", "negative"),
        )
    else:  # default: category scrape
        result = await _hunter.scrape_category(
            platform=state.get("platform", "amazon"),
            keywords=state.get("keywords", []),
            top_n=state.get("top_n", 20),
        )

    return {
        "raw_data": result,
        "phase": "analyzing",
    }


async def analyze_data(state: dict) -> dict:
    """Analyst 深度分析采集的数据。"""
    raw_data = state.get("raw_data", {})
    category = state.get("category", "")
    task_type = state.get("task_type", "market_research")

    # 市场分析
    analysis = await _analyst.analyze_market(category, raw_data)

    # 根据任务类型生成对应报告
    report_type_map = {
        "market_research": "selection",
        "competitor_monitor": "competitor",
        "trend_discovery": "trend",
        "review_analysis": "risk",
    }
    report_type = report_type_map.get(task_type, "selection")

    report = await _analyst.generate_report(
        topic=category,
        data={**raw_data, **analysis},
        report_type=report_type,
    )

    return {
        "analysis": analysis,
        "report": report,
        "phase": "indexing",
    }


async def index_knowledge(state: dict) -> dict:
    """将有价值的数据存入知识库 (向量化)。"""
    raw_data = state.get("raw_data", {})

    indexed_count = 0
    try:
        # 如果爬取了产品数据，逐条入库
        data_items = raw_data.get("data", [])
        if isinstance(data_items, list):
            for item in data_items[:10]:  # 最多入库 10 条
                if isinstance(item, dict) and item.get("title"):
                    await _analyst.ingest_and_index("product", item)
                    indexed_count += 1
    except Exception:
        pass

    return {
        "indexed_count": indexed_count,
        "phase": "delivering",
    }


async def deliver_report(state: dict) -> dict:
    """打包最终报告，交还给委派的 L2。"""
    report = state.get("report", {})

    return {
        "phase": "completed",
        "deliverable": {
            "report": report.get("report", ""),
            "report_type": report.get("report_type", ""),
            "category": state.get("category", ""),
            "indexed_count": state.get("indexed_count", 0),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


# ─── Build Graph ───

def build_data_intel_graph() -> StateGraph:
    """
    Build the data intelligence pipeline graph.
    
    receive_task → hunt_data → analyze_data → index_knowledge → deliver_report
    """
    graph = StateGraph(dict)

    graph.add_node("receive_task", receive_task)
    graph.add_node("hunt_data", hunt_data)
    graph.add_node("analyze_data", analyze_data)
    graph.add_node("index_knowledge", index_knowledge)
    graph.add_node("deliver_report", deliver_report)

    graph.set_entry_point("receive_task")
    graph.add_edge("receive_task", "hunt_data")
    graph.add_edge("hunt_data", "analyze_data")
    graph.add_edge("analyze_data", "index_knowledge")
    graph.add_edge("index_knowledge", "deliver_report")
    graph.add_edge("deliver_report", END)

    return graph
