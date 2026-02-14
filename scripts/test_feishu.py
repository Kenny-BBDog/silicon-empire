"""
发送测试消息到飞书群 — 验证 6 个机器人都能发言。
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# 直接用 httpx 调飞书 API 测试
import httpx
import json
import time


async def get_token(app_id: str, app_secret: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        return resp.json().get("tenant_access_token", "")


async def send_card(token: str, chat_id: str, title: str, content: str, color: str):
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": [
            {"tag": "markdown", "content": content},
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
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
        data = resp.json()
        success = data.get("code") == 0
        return success, data.get("msg", "ok")


async def main():
    chat_id = "oc_0f555cce0141c81028ddb85c6977bd4c"

    bots = [
        ("GM",     "🎖️ 总经理 (GM)",       os.environ["FEISHU_GM_APP_ID"],     os.environ["FEISHU_GM_APP_SECRET"],     "grey"),
        ("CGO",    "🏴‍☠️ 首席增长官 (CGO)",  os.environ["FEISHU_CGO_APP_ID"],    os.environ["FEISHU_CGO_APP_SECRET"],    "orange"),
        ("CRO",    "🛡️ 首席风控官 (CRO)",   os.environ["FEISHU_CRO_APP_ID"],    os.environ["FEISHU_CRO_APP_SECRET"],    "blue"),
        ("COO",    "📦 首席运营官 (COO)",    os.environ["FEISHU_COO_APP_ID"],    os.environ["FEISHU_COO_APP_SECRET"],    "green"),
        ("CTO",    "🔧 首席技术官 (CTO)",    os.environ["FEISHU_CTO_APP_ID"],    os.environ["FEISHU_CTO_APP_SECRET"],    "purple"),
        ("System", "⚙️ 系统助手 (System)",   os.environ["FEISHU_SYSTEM_APP_ID"], os.environ["FEISHU_SYSTEM_APP_SECRET"], "turquoise"),
    ]

    print("🛸 Silicon-Empire 飞书测试\n")

    for role, title, app_id, app_secret, color in bots:
        token = await get_token(app_id, app_secret)
        if not token:
            print(f"  ❌ {role}: Token 获取失败")
            continue

        success, msg = await send_card(
            token, chat_id,
            title=title,
            content=f"**{role} 上线报到！** Silicon-Empire 系统测试 ✅",
            color=color,
        )

        if success:
            print(f"  ✅ {role}: 发送成功")
        else:
            print(f"  ❌ {role}: {msg}")

        await asyncio.sleep(1)  # 模拟逐个发言

    print("\n🎉 测试完成！请查看飞书群消息。")


if __name__ == "__main__":
    asyncio.run(main())
