"""
Personal Memory — Every agent has its own brain.

每个 Agent（无论 L1/L2/L3/L4）都拥有独立的：
- 短期记忆 (Working Memory): 当前工作会话中的思考碎片、临时笔记
- 长期记忆 (Episodic Memory): 跨会话持久化的经验、反思、对他人的看法
- 情感/偏好记忆 (Personality): 随时间进化的性格特征与偏好

存储方式：
- 短期: Redis Hash (带 TTL，会话结束后归档)
- 长期: Supabase agent_memories 表 + pgvector 语义检索
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory record."""

    content: str                          # 记忆内容
    memory_type: str = "observation"      # observation | reflection | insight | interaction | preference
    emotional_tone: str = "neutral"       # positive | negative | neutral | curious | frustrated
    related_agents: list[str] = Field(default_factory=list)   # 涉及的其他 Agent
    related_task: str = ""                # 关联的 trace_id
    importance: int = 5                   # 1-10, 影响 retrieval 排序
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PersonalMemory:
    """
    每个 Agent 独有的记忆系统。
    
    内存结构 (Redis):
        agent:{agent_id}:working     → Hash  (短期工作区)
        agent:{agent_id}:scratchpad  → List  (思考便利贴)
        agent:{agent_id}:mood        → String (当前情绪状态)
    
    持久化 (Supabase):
        agent_memories 表 + embedding 列 → 语义检索
    """

    def __init__(self, agent_id: str, display_name: str = "") -> None:
        self.agent_id = agent_id
        self.display_name = display_name or agent_id
        self._redis = None
        self._supabase = None

    async def init(self, redis_client, supabase_client) -> None:
        """Inject storage backends. Called by BaseAgent.initialize()."""
        self._redis = redis_client
        self._supabase = supabase_client

    # ════════════════════════════════════════
    # 短期记忆 (Working Memory) — Redis
    # ════════════════════════════════════════

    async def think(self, thought: str, importance: int = 3) -> None:
        """
        随手记一个想法 (scratchpad，像便利贴)。
        工作中产生的碎片想法，会话结束后可以归档为长期记忆。
        """
        entry = {
            "thought": thought,
            "importance": importance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        key = f"agent:{self.agent_id}:scratchpad"
        await self._redis.rpush(key, json.dumps(entry, ensure_ascii=False))
        await self._redis.expire(key, 86400)  # 24h TTL

    async def get_thoughts(self, limit: int = 10) -> list[dict[str, Any]]:
        """读取最近的思考便利贴。"""
        key = f"agent:{self.agent_id}:scratchpad"
        raw_list = await self._redis.lrange(key, -limit, -1)
        return [json.loads(r) for r in raw_list] if raw_list else []

    async def set_working_context(self, key: str, value: Any) -> None:
        """在工作区存储一个临时变量 (类似人的短期工作记忆)。"""
        redis_key = f"agent:{self.agent_id}:working"
        await self._redis.hset(redis_key, key, json.dumps(value, default=str, ensure_ascii=False))
        await self._redis.expire(redis_key, 14400)  # 4h TTL

    async def get_working_context(self, key: str) -> Any | None:
        """取出工作区的一个临时变量。"""
        redis_key = f"agent:{self.agent_id}:working"
        raw = await self._redis.hget(redis_key, key)
        return json.loads(raw) if raw else None

    async def set_mood(self, mood: str) -> None:
        """设置当前情绪 (影响回答语气和决策倾向)。"""
        key = f"agent:{self.agent_id}:mood"
        await self._redis.set(key, mood, ex=28800)  # 8h TTL

    async def get_mood(self) -> str:
        """获取当前情绪。"""
        key = f"agent:{self.agent_id}:mood"
        return await self._redis.get(key) or "neutral"

    # ════════════════════════════════════════
    # 长期记忆 (Episodic Memory) — Supabase
    # ════════════════════════════════════════

    async def remember(self, entry: MemoryEntry, embedding: list[float] | None = None) -> None:
        """
        将一段经历写入长期记忆。
        这就像人在睡前回顾今天的经历，把重要的事情记住。
        """
        data = {
            "agent_id": self.agent_id,
            "content": entry.content,
            "memory_type": entry.memory_type,
            "emotional_tone": entry.emotional_tone,
            "related_agents": entry.related_agents,
            "related_task": entry.related_task,
            "importance": entry.importance,
        }
        if embedding:
            data["embedding"] = embedding

        self._supabase.table("agent_memories").insert(data).execute()

    async def recall(
        self,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        memory_type: str | None = None,
        related_agent: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        回忆 — 从长期记忆中检索。
        
        支持两种回忆方式：
        1. 语义联想 (query_embedding) — "我之前遇到过类似的事吗？"
        2. 结构化查询 — "我和 COO 之间发生过什么？"
        """
        # 语义检索
        if query_embedding:
            result = self._supabase.rpc(
                "search_agent_memories",
                {
                    "p_agent_id": self.agent_id,
                    "query_embedding": query_embedding,
                    "match_count": limit,
                },
            ).execute()
            return result.data or []

        # 结构化检索
        q = self._supabase.table("agent_memories").select("*").eq("agent_id", self.agent_id)
        if memory_type:
            q = q.eq("memory_type", memory_type)
        if related_agent:
            q = q.contains("related_agents", [related_agent])
        q = q.order("importance", desc=True).order("created_at", desc=True).limit(limit)
        result = q.execute()
        return result.data or []

    async def reflect(self) -> str:
        """
        自我反思 — 回顾短期记忆中的便利贴，生成一段反思总结。
        这应该在 "下班前" 或 "放假开始时" 调用。
        返回的摘要可以由 LLM 生成后作为 reflection 记忆存入。
        """
        thoughts = await self.get_thoughts(limit=20)
        if not thoughts:
            return ""
        return "\n".join(f"- [{t['timestamp'][:16]}] {t['thought']}" for t in thoughts)

    async def archive_working_memory(self) -> int:
        """
        归档本次会话的工作记忆 → 长期记忆。
        将重要的便利贴 (importance >= 6) 自动存为长期记忆。
        返回归档条数。
        """
        thoughts = await self.get_thoughts(limit=50)
        archived = 0
        for t in thoughts:
            if t.get("importance", 0) >= 6:
                entry = MemoryEntry(
                    content=t["thought"],
                    memory_type="observation",
                    importance=t["importance"],
                )
                await self.remember(entry)
                archived += 1

        # 清空 scratchpad
        key = f"agent:{self.agent_id}:scratchpad"
        await self._redis.delete(key)
        return archived

    # ════════════════════════════════════════
    # 对他人的印象 (Peer Impressions)
    # ════════════════════════════════════════

    async def update_impression(self, peer_id: str, impression: str, tone: str = "neutral") -> None:
        """
        更新对某个同事的印象。
        例: CGO 觉得 CRO "总是太保守，但数据功底很扎实"。
        """
        entry = MemoryEntry(
            content=f"我对 {peer_id} 的看法: {impression}",
            memory_type="interaction",
            emotional_tone=tone,
            related_agents=[peer_id],
            importance=7,
        )
        await self.remember(entry)

    async def get_impression(self, peer_id: str) -> list[dict[str, Any]]:
        """获取对某个同事的所有印象记忆。"""
        return await self.recall(related_agent=peer_id, memory_type="interaction", limit=5)

    # ════════════════════════════════════════
    # 构建 LLM 注入上下文
    # ════════════════════════════════════════

    async def build_memory_context(self, task_hint: str = "") -> str:
        """
        构建注入 LLM system prompt 的个人记忆上下文。
        让 Agent 在每次说话前 "记起自己的经历"。
        """
        parts = []

        # 当前情绪
        mood = await self.get_mood()
        if mood != "neutral":
            parts.append(f"📊 你当前的情绪状态: {mood}")

        # 最近的思考
        thoughts = await self.get_thoughts(limit=5)
        if thoughts:
            thought_text = "\n".join(f"  - {t['thought']}" for t in thoughts[-3:])
            parts.append(f"💭 你最近的想法:\n{thought_text}")

        # 相关的长期记忆 (取最重要的几条)
        memories = await self.recall(memory_type=None, limit=5)
        if memories:
            memory_text = "\n".join(
                f"  - [{m.get('memory_type', '?')}] {m.get('content', '')[:150]}"
                for m in memories[:3]
            )
            parts.append(f"🧠 你的经验记忆:\n{memory_text}")

        if not parts:
            return ""

        return (
            f"\n\n---\n## 你的个人记忆 ({self.display_name})\n"
            + "\n\n".join(parts)
            + "\n---\n"
        )
