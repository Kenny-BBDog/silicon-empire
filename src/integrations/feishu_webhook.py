"""
飞书事件接收 — 长连接模式 (WebSocket)

使用飞书官方 SDK lark-oapi 的长连接客户端。
优势:
- 无需公网域名/IP
- 无需开端口
- 无需配置加密/验签
- 本地开发环境也能接收事件

启动方式:
    python -m src.integrations.feishu_webhook

飞书后台配置:
    事件订阅 → 订阅方式 → 选择「长连接」
    添加事件: im.message.receive_v1
"""

from __future__ import annotations

import json
import os
from functools import partial

import lark_oapi as lark
from lark_oapi.adapter.flask import *
from dotenv import load_dotenv

from src.integrations.feishu_client import get_feishu_client

load_dotenv()


# ─── 角色映射 ───

ROLE_DISPLAY = {
    "gm": "GM",
    "cgo": "CGO",
    "coo": "COO",
    "cro": "CRO",
    "cto": "CTO",
    "system": "System",
}


# ─── 事件处理器 ───

def make_message_handler(bot_role: str):
    """
    为每个 bot 创建独立的消息处理器。
    这样当用户 @CTO 时，handler 知道自己是 CTO。
    """
    def handle_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        event = data.event
        message = event.message
        sender = event.sender

        # 解析消息内容
        content = message.content or "{}"
        try:
            content_obj = json.loads(content)
            text = content_obj.get("text", "")
        except (json.JSONDecodeError, AttributeError):
            text = str(content)

        # 去掉 @机器人 的部分
        if message.mentions:
            for mention in message.mentions:
                text = text.replace(f"@_{mention.key}", "").strip()

        chat_id = message.chat_id
        sender_id = sender.sender_id.open_id if sender.sender_id else ""

        print(f"📨 [{ROLE_DISPLAY.get(bot_role, bot_role)}] 收到消息: [{sender_id}] {text}")

        # 异步处理
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_route_message(bot_role, text, chat_id))
        finally:
            loop.close()

    return handle_message


async def _route_message(bot_role: str, text: str, chat_id: str):
    """
    消息路由 — 两种模式:

    1. Slash 命令 → 触发工作流 (和以前一样)
    2. 自由文本 → 和被 @ 的 Agent 1:1 对话 (新!)
    """
    # ── Slash 命令 ──
    if text.startswith("/"):
        await _dispatch_command(text, chat_id)
        return

    # ── 自由文本 → 1:1 对话 ──
    await _chat_with_agent(bot_role, text, chat_id)


async def _chat_with_agent(role: str, text: str, chat_id: str):
    """和对应 Agent 自由聊天 — 不触发任何工作流。"""
    feishu = get_feishu_client()

    # 发送"正在思考"
    display = ROLE_DISPLAY.get(role, role)

    try:
        from src.graphs.direct_chat import chat_with_agent
        reply = await chat_with_agent(role, text, chat_id)

        # 用对应 Agent 的身份回复
        send_role = role if role != "system" else "gm"
        await feishu.send_as(send_role, "decision",
            reply,
            title=f"{display} 回复",
        )
    except Exception as e:
        await feishu.send_as("system", "alert",
            f"对话出错: {e}",
            title="系统错误",
        )


async def _dispatch_command(text: str, chat_id: str):
    """
    路由 Slash 命令。

    /选品 {关键词}  → 触发探索流程
    /开会            → 触发联席会
    /巡检            → 触发系统巡检
    /放假 {话题}     → 触发放假模式
    /进化            → 触发集体进化讨论 (新!)
    """
    feishu = get_feishu_client()

    if text.startswith("/选品"):
        keywords = text.replace("/选品", "").strip()
        await feishu.send_as("system", "decision",
            f"📥 收到选品指令: **{keywords or '(自动发现)'}**\n正在启动探索模式...",
            title="任务接收",
        )
        # TODO: 触发 build_exploration_graph

    elif text.startswith("/开会"):
        await feishu.send_as("system", "decision",
            "📅 收到开会指令，正在召集全员联席会...",
            title="会议召集",
        )
        # TODO: 触发 build_async_session_graph

    elif text.startswith("/巡检"):
        await feishu.send_as("system", "alert",
            "🔍 收到巡检指令，正在进行全系统检查...",
            title="系统巡检",
        )
        # TODO: 触发 ArchitectAgent.health_check()

    elif text.startswith("/放假"):
        topic = text.replace("/放假", "").strip()
        await feishu.send_as("system", "decision",
            f"🏖️ 放假模式启动！话题: **{topic or '自由闲聊'}**",
            title="放假模式",
        )
        # TODO: 触发 build_holiday_graph

    elif text.startswith("/进化"):
        topic = text.replace("/进化", "").strip()
        await feishu.send_as("system", "decision",
            f"🧬 进化模式启动！\n"
            f"各首席正在自省，寻找改进机会...\n"
            f"{'议题: **' + topic + '**' if topic else ''}",
            title="集体进化",
        )
        # TODO: 触发 build_evolution_graph

    else:
        # 未知命令
        await feishu.send_as("gm", "decision",
            f"未知命令: `{text.split()[0]}`\n\n"
            f"可用命令:\n"
            f"- `/选品 关键词` — 启动选品探索\n"
            f"- `/开会` — 召集联席会\n"
            f"- `/巡检` — 系统巡检\n"
            f"- `/放假 话题` — 自由讨论\n"
            f"- `/进化` — 集体进化讨论\n"
            f"\n或者直接发消息和我聊天 💬",
            title="命令帮助",
        )


def handle_card_action(data) -> dict:
    """处理卡片按钮点击 (审批同意/驳回)。"""
    action = data.event.action
    value = action.value or {}

    act = value.get("action", "")
    trace_id = value.get("trace_id", "")

    print(f"🔘 卡片操作: {act} (trace: {trace_id})")

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_handle_approval(act, trace_id))
    finally:
        loop.close()

    return {}


async def _handle_approval(action: str, trace_id: str):
    feishu = get_feishu_client()

    if action == "approve":
        await feishu.send_as("system", "decision",
            f"✅ 提案 `{trace_id}` 已批准！正在执行...",
            title="审批通过",
        )
    elif action == "reject":
        await feishu.send_as("system", "decision",
            f"❌ 提案 `{trace_id}` 已驳回。",
            title="审批驳回",
        )


# ─── 长连接客户端 ───

def create_ws_clients() -> list[lark.ws.Client]:
    """
    为每个机器人创建长连接客户端。

    关键改动: 每个 bot 有自己的 event_handler，
    handler 知道自己的 role，这样 @CTO 的消息
    会由 CTO 的人格来回复，而不是全部交给 GM。
    """
    bot_configs = {
        "gm": (os.environ.get("FEISHU_GM_APP_ID", ""), os.environ.get("FEISHU_GM_APP_SECRET", "")),
        "cgo": (os.environ.get("FEISHU_CGO_APP_ID", ""), os.environ.get("FEISHU_CGO_APP_SECRET", "")),
        "cro": (os.environ.get("FEISHU_CRO_APP_ID", ""), os.environ.get("FEISHU_CRO_APP_SECRET", "")),
        "coo": (os.environ.get("FEISHU_COO_APP_ID", ""), os.environ.get("FEISHU_COO_APP_SECRET", "")),
        "cto": (os.environ.get("FEISHU_CTO_APP_ID", ""), os.environ.get("FEISHU_CTO_APP_SECRET", "")),
        "system": (os.environ.get("FEISHU_SYSTEM_APP_ID", ""), os.environ.get("FEISHU_SYSTEM_APP_SECRET", "")),
    }

    clients = []
    for role, (app_id, app_secret) in bot_configs.items():
        if not app_id or not app_secret:
            continue

        # 每个 bot 有独立的 handler，知道自己的身份
        handler = make_message_handler(role)
        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(handler)
            .build()
        )

        client = lark.ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )
        clients.append(client)
        print(f"  ✅ {ROLE_DISPLAY.get(role, role)} 机器人长连接已准备")

    return clients


def main():
    """启动所有机器人的长连接。"""
    print("🛸 Silicon-Empire 飞书长连接启动中...\n")

    clients = create_ws_clients()

    if not clients:
        print("❌ 没有找到任何机器人凭证，请检查 .env")
        return

    print(f"\n🚀 共 {len(clients)} 个机器人已连接")
    print("💬 @任何机器人 发消息即可聊天")
    print("📋 使用 /选品 /开会 /巡检 /放假 /进化 触发工作流\n")

    # 启动所有客户端
    # 每个 bot 独立处理自己的消息
    import threading
    for client in clients[1:]:
        t = threading.Thread(target=client.start, daemon=True)
        t.start()

    # 主线程启动第一个 (阻塞)
    clients[0].start()


if __name__ == "__main__":
    main()
