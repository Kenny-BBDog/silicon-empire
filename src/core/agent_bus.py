"""
Agent Message Bus — 智能体之间的通信系统。

Agent 不再是孤岛 — 他们可以:
- 向其他 Agent 发消息/提问
- 委派任务给下属 (L2 → L3)
- 向上级汇报 (L3 → L2)
- 广播消息给所有 Agent
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from collections import defaultdict


# ─── 消息结构 ───

class AgentMessage:
    """Agent 之间传递的消息。"""

    def __init__(
        self,
        sender: str,
        receiver: str,
        msg_type: str,
        content: str,
        context: dict[str, Any] | None = None,
        expect_reply: bool = False,
    ):
        self.sender = sender
        self.receiver = receiver               # 具体角色 or "broadcast"
        self.msg_type = msg_type               # question / task / report / info / request
        self.content = content
        self.context = context or {}
        self.expect_reply = expect_reply
        self.reply: str | None = None
        self.timestamp = datetime.now(timezone.utc).isoformat()


# ─── 全局消息总线 ───

_inbox: dict[str, list[AgentMessage]] = defaultdict(list)
_message_log: list[AgentMessage] = []


def send_message(msg: AgentMessage) -> None:
    """发送消息到目标 Agent 的收件箱。"""
    if msg.receiver == "broadcast":
        # 广播给所有已知角色
        for role in ["gm", "cgo", "coo", "cro", "cto"]:
            if role != msg.sender:
                _inbox[role].append(msg)
    else:
        _inbox[msg.receiver].append(msg)
    _message_log.append(msg)


def get_inbox(role: str) -> list[AgentMessage]:
    """获取某个 Agent 的收件箱（并清空）。"""
    messages = _inbox.pop(role, [])
    return messages


def peek_inbox(role: str) -> list[AgentMessage]:
    """查看某个 Agent 的收件箱（不清空）。"""
    return _inbox.get(role, [])


def get_message_log(limit: int = 50) -> list[dict]:
    """获取最近的消息日志。"""
    recent = _message_log[-limit:]
    return [
        {
            "sender": m.sender,
            "receiver": m.receiver,
            "type": m.msg_type,
            "content": m.content[:200],
            "time": m.timestamp,
        }
        for m in recent
    ]


# ─── 便捷方法 (给 Agent 用) ───

def ask(sender: str, receiver: str, question: str) -> AgentMessage:
    """向其他 Agent 提问。"""
    msg = AgentMessage(
        sender=sender,
        receiver=receiver,
        msg_type="question",
        content=question,
        expect_reply=True,
    )
    send_message(msg)
    return msg


def delegate_task(sender: str, receiver: str, task_desc: str, params: dict | None = None) -> AgentMessage:
    """委派任务给下属。"""
    msg = AgentMessage(
        sender=sender,
        receiver=receiver,
        msg_type="task",
        content=task_desc,
        context=params or {},
        expect_reply=True,
    )
    send_message(msg)
    return msg


def report_up(sender: str, receiver: str, report: str) -> AgentMessage:
    """向上级汇报。"""
    msg = AgentMessage(
        sender=sender,
        receiver=receiver,
        msg_type="report",
        content=report,
    )
    send_message(msg)
    return msg


def broadcast(sender: str, info: str) -> AgentMessage:
    """广播消息给所有 Agent。"""
    msg = AgentMessage(
        sender=sender,
        receiver="broadcast",
        msg_type="info",
        content=info,
    )
    send_message(msg)
    return msg
