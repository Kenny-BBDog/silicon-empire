"""
Company Knowledge Base — 组织级共享智慧。

每个 Agent 学到的知识不再是私藏 — 它们流入公司知识库，
所有 Agent 都能检索、引用、验证。

知识类型:
- lesson: 从错误/成功中提炼的教训
- best_practice: 验证有效的最佳实践
- market_insight: 市场洞察 (趋势、竞品、客户行为)
- warning: 踩过的坑、风险提示
- decision_record: 重要决策及其理由

写入流: Agent 产出洞察 → learn() → 自动广播给相关 Agent
检索流: Agent 思考前 → recall() → 注入 LLM context
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("knowledge")


class KnowledgeBase:
    """组织级共享知识库。"""

    def __init__(self):
        self._db = None

    async def _get_db(self):
        if not self._db:
            from src.core.memory import get_memory
            mem = await get_memory()
            self._db = mem
        return self._db

    # ─── 写入 ───

    async def learn(
        self,
        category: str,
        title: str,
        content: str,
        source_agent: str,
        tags: list[str] | None = None,
        confidence: float = 0.8,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        写入一条新知识。

        category: lesson / best_practice / market_insight / warning / decision_record
        """
        mem = await self._get_db()

        data: dict[str, Any] = {
            "category": category,
            "title": title,
            "content": content,
            "source_agent": source_agent,
            "confidence": confidence,
            "tags": tags or [],
        }

        if embedding:
            return await mem.insert_with_embedding("company_knowledge", data, embedding)
        else:
            return await mem.insert_row("company_knowledge", data)

    # ─── 检索 ───

    async def recall(
        self,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        检索相关知识。

        支持:
        1. 语义检索 (query_embedding) — "和这个任务相关的知识"
        2. 分类检索 (category) — "所有市场洞察"
        3. 标签检索 (tags) — "和宠物相关的知识"
        """
        mem = await self._get_db()

        if query_embedding:
            return await mem.vector_search("company_knowledge", query_embedding, limit)

        # 结构化检索
        filters: dict[str, Any] = {}
        if category:
            filters["category"] = category
        return await mem.query_table("company_knowledge", filters=filters, limit=limit)

    async def recall_for_context(
        self,
        task_hint: str,
        limit: int = 3,
    ) -> str:
        """
        为 LLM 调用构建知识上下文。
        返回格式化的知识片段，直接注入 system prompt。
        """
        # 先尝试结构化检索（最重要的知识）
        knowledge = await self.recall(limit=limit)

        if not knowledge:
            return ""

        lines = ["## 公司知识库"]
        for k in knowledge:
            cat_emoji = {
                "lesson": "📖",
                "best_practice": "✅",
                "market_insight": "📊",
                "warning": "⚠️",
                "decision_record": "📋",
            }.get(k.get("category", ""), "💡")

            lines.append(
                f"- {cat_emoji} **{k.get('title', '')}**: "
                f"{k.get('content', '')[:150]}"
            )

        return "\n".join(lines)

    # ─── 广播 ───

    async def broadcast_insight(
        self,
        title: str,
        content: str,
        source_agent: str,
        category: str = "market_insight",
        tags: list[str] | None = None,
    ):
        """
        重要洞察自动广播:
        1. 写入知识库
        2. 通过 Agent Bus 广播给所有 Agent
        """
        await self.learn(
            category=category,
            title=title,
            content=content,
            source_agent=source_agent,
            tags=tags,
            confidence=0.7,
        )

        # 广播通知
        from src.core.agent_bus import broadcast
        await broadcast(
            source_agent,
            f"[知识共享] {title}: {content[:100]}",
        )


# ─── Singleton ───

_kb: KnowledgeBase | None = None


async def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例。"""
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
