"""
Agent Message Bus — 智能体之间的通信系统 (Redis 持久化)。

Agent 不再是孤岛 — 他们可以:
- 向其他 Agent 发消息/提问
- 委派任务给下属 (L2 → L3)
- 向上级汇报 (L3 → L2)
- 广播消息给所有 Agent

消息持久化到 Redis，重启不丢失。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


ALL_ROLES = ["gm", "cgo", "coo", "cro", "cto",
             "l3_data_hunter", "l3_insight_analyst", "l3_copy_master",
             "l3_architect", "l3_customer_success", "l3_sourcing_liaison",
             "l3_store_operator", "l4_autolab"]


def _make_message(
    sender: str,
    receiver: str,
    msg_type: str,
    content: str,
    context: dict[str, Any] | None = None,
) -> dict:
    return {
        "sender": sender,
        "receiver": receiver,
        "msg_type": msg_type,       # question / task / report / info / request
        "content": content,
        "context": context or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Redis-backed inbox ───

_INBOX_KEY = "agent:inbox:{role}"
_LOG_KEY = "agent:message_log"

# Fallback in-memory queues (when Redis unavailable)
_fallback_inbox: dict[str, list[dict]] = {}


async def _get_redis():
    """获取 Redis 连接。"""
    try:
        from src.core.memory import get_memory
        mem = await get_memory()
        return mem.redis
    except Exception:
        return None


async def send_message(msg: dict) -> None:
    """发送消息到目标 Agent 的收件箱 (Redis)。"""
    redis = await _get_redis()

    receivers = []
    if msg["receiver"] == "broadcast":
        receivers = [r for r in ALL_ROLES if r != msg["sender"]]
    else:
        receivers = [msg["receiver"]]

    msg_json = json.dumps(msg, ensure_ascii=False, default=str)

    for rcv in receivers:
        if redis:
            key = _INBOX_KEY.format(role=rcv)
            await redis.rpush(key, msg_json)
            # 保留最近1000条
            await redis.ltrim(key, -1000, -1)
        else:
            _fallback_inbox.setdefault(rcv, []).append(msg)

    # 写日志
    if redis:
        await redis.rpush(_LOG_KEY, msg_json)
        await redis.ltrim(_LOG_KEY, -500, -1)


async def get_inbox(role: str) -> list[dict]:
    """获取某个 Agent 的收件箱 (取出并清空)。"""
    redis = await _get_redis()
    if redis:
        key = _INBOX_KEY.format(role=role)
        pipe = redis.pipeline()
        pipe.lrange(key, 0, -1)
        pipe.delete(key)
        results = await pipe.execute()
        raw_list = results[0] or []
        return [json.loads(r) for r in raw_list]
    else:
        return _fallback_inbox.pop(role, [])


async def peek_inbox(role: str) -> list[dict]:
    """查看某个 Agent 的收件箱 (不清空)。"""
    redis = await _get_redis()
    if redis:
        key = _INBOX_KEY.format(role=role)
        raw_list = await redis.lrange(key, 0, -1)
        return [json.loads(r) for r in (raw_list or [])]
    else:
        return _fallback_inbox.get(role, [])


async def get_message_log(limit: int = 50) -> list[dict]:
    """获取最近的消息日志。"""
    redis = await _get_redis()
    if redis:
        raw_list = await redis.lrange(_LOG_KEY, -limit, -1)
        return [json.loads(r) for r in (raw_list or [])]
    return []


# ─── 便捷方法 ───

async def ask(sender: str, receiver: str, question: str) -> dict:
    """向其他 Agent 提问。"""
    msg = _make_message(sender, receiver, "question", question)
    await send_message(msg)
    return msg


async def delegate_task(sender: str, receiver: str, task_desc: str, params: dict | None = None) -> dict:
    """委派任务给下属。"""
    msg = _make_message(sender, receiver, "task", task_desc, params)
    await send_message(msg)
    return msg


async def report_up(sender: str, receiver: str, report: str) -> dict:
    """向上级汇报。"""
    msg = _make_message(sender, receiver, "report", report)
    await send_message(msg)
    return msg


async def broadcast(sender: str, info: str) -> dict:
    """广播消息给所有 Agent。"""
    msg = _make_message(sender, "broadcast", "info", info)
    await send_message(msg)
    return msg
