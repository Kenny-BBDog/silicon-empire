"""
Three-tier Memory Manager — 本地 PostgreSQL 版本.

Tier 1 — Redis: Short-term (session context, active conversation).
Tier 2 — pgvector: Long-term semantic (product knowledge, policies, CRM memories).
Tier 3 — PostgreSQL: Persistent structured (decisions, tool registry).

替代 Supabase 方案:
- psycopg (async) 替代 supabase-py client
- 直连本地 PostgreSQL, 零网络延迟
- pgvector 扩展提供向量搜索
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
import psycopg
from psycopg.rows import dict_row

from src.config.settings import get_settings


class MemoryManager:
    """Unified interface for all three memory tiers."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._db: psycopg.AsyncConnection | None = None

    async def init(self) -> None:
        """Initialize connections. Call once at startup."""
        settings = get_settings()
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._db = await psycopg.AsyncConnection.connect(
            settings.database_url,
            row_factory=dict_row,
            autocommit=True,
        )

    async def close(self) -> None:
        """Gracefully close connections."""
        if self._redis:
            await self._redis.close()
        if self._db:
            await self._db.close()

    @property
    def redis(self) -> aioredis.Redis:
        assert self._redis is not None, "MemoryManager not initialized. Call .init() first."
        return self._redis

    @property
    def db(self) -> psycopg.AsyncConnection:
        assert self._db is not None, "MemoryManager not initialized. Call .init() first."
        return self._db

    # 向后兼容: 旧代码引用 self.supabase 的地方不再可用
    # 会抛出明确错误引导修改
    @property
    def supabase(self):
        raise AttributeError(
            "Supabase 已移除, 请使用 self.db (psycopg) 或相应的 query/insert 方法"
        )        

    # ─── Tier 1: Redis (Short-term) ───

    async def set_context(self, trace_id: str, key: str, value: Any, ttl: int = 3600) -> None:
        """Store session-scoped context in Redis."""
        redis_key = f"ctx:{trace_id}:{key}"
        await self.redis.set(redis_key, json.dumps(value, default=str), ex=ttl)

    async def get_context(self, trace_id: str, key: str) -> Any | None:
        """Retrieve session-scoped context from Redis."""
        redis_key = f"ctx:{trace_id}:{key}"
        raw = await self.redis.get(redis_key)
        return json.loads(raw) if raw else None

    async def clear_context(self, trace_id: str) -> None:
        """Clear all context for a trace."""
        pattern = f"ctx:{trace_id}:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)

    # ─── Tier 2: pgvector (Semantic Search) ───

    async def vector_search(
        self, table: str, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Semantic search against a pgvector-enabled table.
        Uses the search_<table> RPC function (same SQL as before).
        """
        async with self.db.cursor() as cur:
            await cur.execute(
                f"SELECT * FROM search_{table}(%s::vector, %s)",
                [str(query_embedding), top_k],
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def insert_with_embedding(
        self, table: str, data: dict[str, Any], embedding: list[float]
    ) -> dict[str, Any]:
        """Insert a row with its embedding vector."""
        data["embedding"] = str(embedding)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        values = list(data.values())

        async with self.db.cursor() as cur:
            await cur.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *",
                values,
            )
            row = await cur.fetchone()
            return dict(row) if row else {}

    # ─── Tier 3: PostgreSQL (Structured) ───

    async def query_table(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        order_by: str = "created_at",
        ascending: bool = False,
    ) -> list[dict[str, Any]]:
        """Query a PostgreSQL table with optional filters."""
        sql = f"SELECT * FROM {table}"
        params: list[Any] = []

        if filters:
            conditions = []
            for col, val in filters.items():
                conditions.append(f"{col} = %s")
                params.append(val)
            sql += " WHERE " + " AND ".join(conditions)

        direction = "ASC" if ascending else "DESC"
        sql += f" ORDER BY {order_by} {direction} LIMIT %s"
        params.append(limit)

        async with self.db.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def insert_row(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a row into a PostgreSQL table."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        values = list(data.values())

        async with self.db.cursor() as cur:
            await cur.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *",
                values,
            )
            row = await cur.fetchone()
            return dict(row) if row else {}

    async def update_row(
        self, table: str, match: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update rows matching the given filter."""
        set_clauses = []
        params: list[Any] = []
        for col, val in data.items():
            set_clauses.append(f"{col} = %s")
            params.append(val)

        where_clauses = []
        for col, val in match.items():
            where_clauses.append(f"{col} = %s")
            params.append(val)

        sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)} RETURNING *"

        async with self.db.cursor() as cur:
            await cur.execute(sql, params)
            row = await cur.fetchone()
            return dict(row) if row else {}


# Singleton
_memory: MemoryManager | None = None


async def get_memory() -> MemoryManager:
    """Get or create the global MemoryManager singleton."""
    global _memory
    if _memory is None:
        _memory = MemoryManager()
        await _memory.init()
    return _memory
