"""
飞书多机器人客户端 — 6 Bot Multi-Agent Communication

每个 L2 Agent 对应一个独立飞书机器人：
- GM / CGO / CRO / COO / CTO 各一个
- System 机器人负责 L3 日志和系统告警

每个机器人拥有独立的头像和名字，
群聊中看起来就像真正的多人讨论。
"""

from __future__ import annotations

import os
import time
import json
import asyncio
from typing import Any
from dataclasses import dataclass, field

import httpx


# ─── Bot Config ───

@dataclass
class FeishuBot:
    """One Feishu bot = one L2 Agent identity."""
    role: str
    app_id: str
    app_secret: str
    display_name: str
    emoji: str
    card_color: str            # 消息卡片头部颜色
    _token: str = ""
    _token_expires: float = 0

    async def get_token(self) -> str:
        """获取 tenant_access_token (自动缓存/续期)。"""
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = resp.json()
            self._token = data.get("tenant_access_token", "")
            self._token_expires = time.time() + data.get("expire", 7200)

        return self._token


# ─── Bot Registry ───

def _load_bots() -> dict[str, FeishuBot]:
    """从环境变量加载 6 个机器人配置。"""
    bot_configs = {
        "gm": {
            "display_name": "总经理 (GM)",
            "emoji": "🎖️",
            "card_color": "grey",
        },
        "cgo": {
            "display_name": "首席增长官 (CGO)",
            "emoji": "🏴‍☠️",
            "card_color": "orange",
        },
        "cro": {
            "display_name": "首席风控官 (CRO)",
            "emoji": "🛡️",
            "card_color": "blue",
        },
        "coo": {
            "display_name": "首席运营官 (COO)",
            "emoji": "📦",
            "card_color": "green",
        },
        "cto": {
            "display_name": "首席技术官 (CTO)",
            "emoji": "🔧",
            "card_color": "purple",
        },
        "system": {
            "display_name": "系统助手 (System)",
            "emoji": "⚙️",
            "card_color": "turquoise",
        },
    }

    bots = {}
    for role, config in bot_configs.items():
        app_id = os.environ.get(f"FEISHU_{role.upper()}_APP_ID", "")
        app_secret = os.environ.get(f"FEISHU_{role.upper()}_APP_SECRET", "")
        if app_id and app_secret:
            bots[role] = FeishuBot(
                role=role,
                app_id=app_id,
                app_secret=app_secret,
                **config,
            )

    return bots


# ─── Channels ───

@dataclass
class FeishuChannels:
    """三频道配置。"""
    decision: str = ""    # 决策频道 — L2 开会
    execution: str = ""   # 执行频道 — L3 日志
    alert: str = ""       # 告警频道 — 自愈 + 审批

    @classmethod
    def from_env(cls) -> FeishuChannels:
        return cls(
            decision=os.environ.get("FEISHU_DECISION_CHAT_ID", ""),
            execution=os.environ.get("FEISHU_EXECUTION_CHAT_ID", ""),
            alert=os.environ.get("FEISHU_ALERT_CHAT_ID", ""),
        )


# ─── Card Builder ───

class CardBuilder:
    """飞书消息卡片构建器。"""

    @staticmethod
    def build_agent_message(
        emoji: str,
        title: str,
        content: str,
        color: str = "blue",
        fields: list[dict] | None = None,
        actions: list[dict] | None = None,
    ) -> dict:
        """
        构建 Agent 发言卡片。
        
        看起来像:
        ┌──────────────────────────┐
        │ 🏴‍☠️ CGO · 选品提案          │ (彩色头部)
        ├──────────────────────────┤
        │ 内容正文...               │
        │                          │
        │ 指标1: xxx  |  指标2: xxx │ (可选字段)
        │                          │
        │ [按钮1]  [按钮2]          │ (可选操作)
        └──────────────────────────┘
        """
        elements = [
            {
                "tag": "markdown",
                "content": content,
            }
        ]

        # 字段区
        if fields:
            field_elements = []
            for f in fields:
                field_elements.append({
                    "tag": "markdown",
                    "content": f"**{f['label']}**\n{f['value']}",
                })
            elements.append({
                "tag": "column_set",
                "columns": [
                    {"tag": "column", "width": "weighted", "weight": 1, "elements": [fe]}
                    for fe in field_elements
                ],
            })

        # 操作按钮区
        if actions:
            action_elements = []
            for a in actions:
                action_elements.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": a["text"]},
                    "type": a.get("type", "primary"),
                    "value": a.get("value", {}),
                })
            elements.append({
                "tag": "action",
                "actions": action_elements,
            })

        return {
            "type": "template",
            "data": {
                "template_id": "",  # 不使用模板，用动态卡片
                "template_variable": {},
            },
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"{emoji} {title}"},
                "template": color,
            },
            "elements": elements,
        }

    @staticmethod
    def build_approval_card(
        title: str,
        proposal: str,
        trace_id: str,
    ) -> dict:
        """构建审批卡片 (带 同意/驳回 按钮)。"""
        return CardBuilder.build_agent_message(
            emoji="📋",
            title=f"审批请求 · {title}",
            content=proposal,
            color="red",
            actions=[
                {
                    "text": "✅ 同意",
                    "type": "primary",
                    "value": {"action": "approve", "trace_id": trace_id},
                },
                {
                    "text": "❌ 驳回",
                    "type": "danger",
                    "value": {"action": "reject", "trace_id": trace_id},
                },
                {
                    "text": "💬 追加意见",
                    "type": "default",
                    "value": {"action": "comment", "trace_id": trace_id},
                },
            ],
        )

    @staticmethod
    def build_alert_card(
        level: str,
        title: str,
        detail: str,
    ) -> dict:
        """构建告警卡片。"""
        color_map = {"critical": "red", "warning": "orange", "info": "blue"}
        emoji_map = {"critical": "🔴", "warning": "🟡", "info": "🔵"}

        return CardBuilder.build_agent_message(
            emoji=emoji_map.get(level, "🔵"),
            title=f"告警 · {title}",
            content=detail,
            color=color_map.get(level, "blue"),
        )


# ─── Main Client ───

class FeishuMultiBot:
    """
    飞书多机器人客户端。
    
    Usage:
        client = FeishuMultiBot()
        await client.send_as("cgo", "decision", "我发现了一个好品类！")
        await client.send_approval("decision", "上架提案", proposal, trace_id)
    """

    def __init__(self):
        self.bots = _load_bots()
        self.channels = FeishuChannels.from_env()
        self._api_base = "https://open.feishu.cn/open-apis"

    def _get_channel_id(self, channel: str) -> str:
        """Map channel name to chat_id."""
        channel_map = {
            "decision": self.channels.decision,
            "execution": self.channels.execution,
            "alert": self.channels.alert,
        }
        return channel_map.get(channel, channel)

    async def send_as(
        self,
        role: str,
        channel: str,
        content: str,
        title: str = "",
        fields: list[dict] | None = None,
    ) -> dict:
        """
        以指定角色的机器人身份发送消息。
        
        Args:
            role: "gm" | "cgo" | "cro" | "coo" | "cto" | "system"
            channel: "decision" | "execution" | "alert"
            content: Markdown 正文
            title: 卡片标题 (默认用 display_name)
        """
        bot = self.bots.get(role)
        if not bot:
            return {"error": f"Bot not found: {role}"}

        chat_id = self._get_channel_id(channel)
        if not chat_id:
            return {"error": f"Channel not configured: {channel}"}

        card = CardBuilder.build_agent_message(
            emoji=bot.emoji,
            title=title or bot.display_name,
            content=content,
            color=bot.card_color,
            fields=fields,
        )

        return await self._send_card(bot, chat_id, card)

    async def send_approval(
        self,
        channel: str,
        title: str,
        proposal: str,
        trace_id: str,
    ) -> dict:
        """发送审批卡片 (用 System 机器人)。"""
        bot = self.bots.get("system")
        if not bot:
            return {"error": "System bot not configured"}

        chat_id = self._get_channel_id(channel)
        card = CardBuilder.build_approval_card(title, proposal, trace_id)
        return await self._send_card(bot, chat_id, card)

    async def send_alert(
        self,
        level: str,
        title: str,
        detail: str,
    ) -> dict:
        """发送告警到告警频道 (用 System 机器人)。"""
        bot = self.bots.get("system")
        if not bot:
            return {"error": "System bot not configured"}

        chat_id = self._get_channel_id("alert")
        card = CardBuilder.build_alert_card(level, title, detail)
        return await self._send_card(bot, chat_id, card)

    async def broadcast_meeting(
        self,
        messages: list[dict[str, str]],
        channel: str = "decision",
        delay: float = 0.5,
    ) -> list[dict]:
        """
        广播会议对话 — 多个 Agent 依次发言。
        
        messages: [{"role": "cgo", "content": "...", "title": "选品提案"}, ...]
        delay: 每条消息间的延迟 (模拟真实对话节奏)
        """
        results = []
        for msg in messages:
            result = await self.send_as(
                role=msg["role"],
                channel=channel,
                content=msg["content"],
                title=msg.get("title", ""),
            )
            results.append(result)
            if delay > 0:
                await asyncio.sleep(delay)
        return results

    async def _send_card(self, bot: FeishuBot, chat_id: str, card: dict) -> dict:
        """底层: 用指定机器人发送卡片消息。"""
        token = await bot.get_token()

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._api_base}/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "receive_id": chat_id,
                    "msg_type": "interactive",
                    "content": json.dumps(card, ensure_ascii=False),
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": data.get("code") == 0,
                    "msg_id": data.get("data", {}).get("message_id", ""),
                    "bot": bot.role,
                }
            else:
                return {
                    "success": False,
                    "error": resp.text[:200],
                    "status": resp.status_code,
                    "bot": bot.role,
                }

    async def receive_events(self, event_data: dict) -> dict:
        """
        处理飞书事件回调 (Webhook)。
        
        支持:
        - 用户 @机器人 → 触发对话
        - 审批按钮点击 → 路由到 LangGraph
        - 消息接收 → 转为 Envelope 传入 Bus
        """
        event_type = event_data.get("header", {}).get("event_type", "")

        if event_type == "im.message.receive_v1":
            return await self._handle_message(event_data)
        elif event_type == "card.action.trigger":
            return await self._handle_card_action(event_data)

        return {"handled": False, "event_type": event_type}

    async def _handle_message(self, event_data: dict) -> dict:
        """处理收到的消息 (用户指令)。"""
        event = event_data.get("event", {})
        message = event.get("message", {})

        content = message.get("content", "{}")
        try:
            content_obj = json.loads(content)
            text = content_obj.get("text", "")
        except (json.JSONDecodeError, AttributeError):
            text = str(content)

        # 去掉 @机器人 的部分
        for mention in message.get("mentions", []):
            text = text.replace(f"@{mention.get('key', '')}", "").strip()

        return {
            "handled": True,
            "type": "user_command",
            "text": text,
            "chat_id": message.get("chat_id", ""),
            "sender": event.get("sender", {}).get("sender_id", {}).get("open_id", ""),
            "message_id": message.get("message_id", ""),
        }

    async def _handle_card_action(self, event_data: dict) -> dict:
        """处理卡片按钮点击 (审批)。"""
        action = event_data.get("event", {}).get("action", {})
        value = action.get("value", {})

        return {
            "handled": True,
            "type": "approval_action",
            "action": value.get("action", ""),
            "trace_id": value.get("trace_id", ""),
            "operator": event_data.get("event", {}).get("operator", {}).get("open_id", ""),
        }


# ─── Singleton ───

_client: FeishuMultiBot | None = None


def get_feishu_client() -> FeishuMultiBot:
    global _client
    if _client is None:
        _client = FeishuMultiBot()
    return _client
