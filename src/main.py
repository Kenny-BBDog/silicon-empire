"""
Silicon-Empire Main API Server
──────────────────────────────
入口 FastAPI 应用，暴露所有 LangGraph 流程为 REST API。

启动方式:
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

API 路由:
    POST /api/explore        → 探索模式 (选品)
    POST /api/meeting        → 联席会
    POST /api/hearing        → 听证会
    POST /api/holiday        → 放假聊天
    POST /api/data-intel     → 情报采集
    POST /api/self-heal      → 自愈修复
    POST /api/health-check   → 系统巡检
    POST /api/feishu/notify  → 飞书通知
    GET  /health             → 健康检查
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()


# ─── Lifespan ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown."""
    # Startup
    from src.core.memory import get_memory
    mem = await get_memory()
    print("🛸 Silicon-Empire — 系统已启动")
    print(f"   Redis: {'✅' if mem.redis else '❌'}")
    print(f"   Supabase: {'✅' if mem.supabase else '❌'}")

    yield

    # Shutdown
    print("🛸 Silicon-Empire — 系统已关闭")


app = FastAPI(
    title="Silicon-Empire",
    description="AI 原生一人跨国电商集团",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Models ───

class ExploreRequest(BaseModel):
    topic: str = Field(..., description="探索主题 (如 '宠物智能喂食器')")
    depth: str = Field(default="standard", description="深度: quick / standard / deep")


class MeetingRequest(BaseModel):
    proposal: str = Field(..., description="提案摘要")
    context: dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="EXPLORATION", description="EXPLORATION / EXECUTION")


class HearingRequest(BaseModel):
    proposal: str = Field(..., description="待审议提案")
    objections: list[str] = Field(default_factory=list, description="预设反对意见")


class HolidayRequest(BaseModel):
    topic: str = Field(default="", description="聊天话题 (空 = 自由闲聊)")
    max_rounds: int = Field(default=10)


class DataIntelRequest(BaseModel):
    task_type: str = Field(default="market_research", description="market_research / competitor_monitor / trend_discovery / review_analysis")
    keywords: list[str] = Field(default_factory=list)
    platform: str = Field(default="amazon")
    category: str = Field(default="")


class SelfHealRequest(BaseModel):
    tool_name: str = Field(default="")
    error_message: str = Field(default="")
    code_path: str = Field(default="")


class FeishuNotifyRequest(BaseModel):
    role: str = Field(default="system")
    channel: str = Field(default="decision")
    content: str = Field(...)
    title: str = Field(default="")


# ─── API Routes ───

@app.post("/api/explore")
async def explore(req: ExploreRequest):
    """触发探索模式 — 选品调研。"""
    from src.graphs import build_exploration_graph

    trace_id = f"explore-{uuid.uuid4().hex[:8]}"
    graph = build_exploration_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "topic": req.topic,
        "trace_id": trace_id,
        "mode": "EXPLORATION",
        "phase": "START",
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/meeting")
async def meeting(req: MeetingRequest):
    """触发联席会。"""
    from src.graphs import build_async_session_graph

    trace_id = f"meeting-{uuid.uuid4().hex[:8]}"
    graph = build_async_session_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "proposal": req.proposal,
        "trace_id": trace_id,
        "mode": req.mode,
        "phase": "START",
        **req.context,
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/hearing")
async def hearing(req: HearingRequest):
    """触发听证会 (对抗审查)。"""
    from src.graphs import build_adversarial_hearing_graph

    trace_id = f"hearing-{uuid.uuid4().hex[:8]}"
    graph = build_adversarial_hearing_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "proposal": req.proposal,
        "trace_id": trace_id,
        "phase": "START",
        "red_team_objections": req.objections,
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/holiday")
async def holiday(req: HolidayRequest):
    """触发放假模式。"""
    from src.graphs import build_holiday_graph

    trace_id = f"holiday-{uuid.uuid4().hex[:8]}"
    graph = build_holiday_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "topic": req.topic,
        "trace_id": trace_id,
        "max_rounds": req.max_rounds,
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/data-intel")
async def data_intel(req: DataIntelRequest):
    """触发情报采集。"""
    from src.platforms.data_intel.graph import build_data_intel_graph

    trace_id = f"intel-{uuid.uuid4().hex[:8]}"
    graph = build_data_intel_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "task_type": req.task_type,
        "keywords": req.keywords,
        "platform": req.platform,
        "category": req.category,
        "trace_id": trace_id,
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/self-heal")
async def self_heal(req: SelfHealRequest):
    """触发自愈修复。"""
    from src.graphs import build_self_heal_graph

    trace_id = f"heal-{uuid.uuid4().hex[:8]}"
    graph = build_self_heal_graph()
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "error_log": {
            "tool_name": req.tool_name,
            "error_message": req.error_message,
            "code_path": req.code_path,
        },
        "trace_id": trace_id,
    })

    return {"trace_id": trace_id, "result": result}


@app.post("/api/health-check")
async def health_check_api():
    """系统巡检 API。"""
    from src.platforms.tech_lab import ArchitectAgent

    architect = ArchitectAgent()
    result = await architect.health_check()
    return result


@app.post("/api/feishu/notify")
async def feishu_notify(req: FeishuNotifyRequest):
    """直接发飞书消息。"""
    from src.integrations.feishu_client import get_feishu_client

    feishu = get_feishu_client()
    result = await feishu.send_as(
        role=req.role,
        channel=req.channel,
        content=req.content,
        title=req.title,
    )
    return result


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "silicon-empire",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
