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

import lark_oapi as lark
from lark_oapi.adapter.flask import *
from dotenv import load_dotenv

from src.integrations.feishu_client import get_feishu_client

load_dotenv()


# ─── 事件处理器 ───

def handle_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """
    处理收到的消息事件。
    当用户在群里 @机器人 发消息时触发。
    """
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

    print(f"📨 收到消息: [{sender_id}] {text}")

    # 异步处理指令
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_dispatch_command(text, chat_id))
    finally:
        loop.close()


async def _dispatch_command(text: str, chat_id: str):
    """
    路由用户指令。
    
    /选品 {关键词}  → 触发探索流程
    /开会            → 触发联席会
    /巡检            → 触发系统巡检
    /放假 {话题}     → 触发放假模式
    自由文本         → GM 回复
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

    else:
        await feishu.send_as("gm", "decision",
            f"收到你的消息，让我想想...\n\n> {text}",
            title="GM 回复",
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
    
    每个机器人独立连接飞书 WebSocket，
    这样当用户 @不同机器人 时，对应的机器人能收到事件。
    """
    bot_configs = {
        "gm": (os.environ.get("FEISHU_GM_APP_ID", ""), os.environ.get("FEISHU_GM_APP_SECRET", "")),
        "cgo": (os.environ.get("FEISHU_CGO_APP_ID", ""), os.environ.get("FEISHU_CGO_APP_SECRET", "")),
        "cro": (os.environ.get("FEISHU_CRO_APP_ID", ""), os.environ.get("FEISHU_CRO_APP_SECRET", "")),
        "coo": (os.environ.get("FEISHU_COO_APP_ID", ""), os.environ.get("FEISHU_COO_APP_SECRET", "")),
        "cto": (os.environ.get("FEISHU_CTO_APP_ID", ""), os.environ.get("FEISHU_CTO_APP_SECRET", "")),
        "system": (os.environ.get("FEISHU_SYSTEM_APP_ID", ""), os.environ.get("FEISHU_SYSTEM_APP_SECRET", "")),
    }

    # 事件处理器
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(handle_message)
        .build()
    )

    clients = []
    for role, (app_id, app_secret) in bot_configs.items():
        if not app_id or not app_secret:
            continue

        client = lark.ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )
        clients.append(client)
        print(f"  ✅ {role} 机器人长连接已准备")

    return clients


def main():
    """启动所有机器人的长连接。"""
    print("🛸 Silicon-Empire 飞书长连接启动中...\n")

    clients = create_ws_clients()

    if not clients:
        print("❌ 没有找到任何机器人凭证，请检查 .env")
        return

    print(f"\n🚀 共 {len(clients)} 个机器人已连接，等待事件...\n")

    # 启动所有客户端 (阻塞)
    # 只需要启动一个就行，因为同一个群里 @任意机器人 的消息
    # 可以由任一机器人的长连接接收
    # 这里启动第一个 (GM) 作为主接收者
    clients[0].start()


if __name__ == "__main__":
    main()
