"""
获取飞书群 chat_id — 运行后会列出机器人所在的所有群聊。
用法: python scripts/get_chat_id.py
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def get_token(app_id: str, app_secret: str) -> str:
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    return resp.json().get("tenant_access_token", "")

def list_chats(token: str) -> list:
    resp = httpx.get(
        "https://open.feishu.cn/open-apis/im/v1/chats",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    return data.get("data", {}).get("items", [])

def main():
    # 用 GM 机器人的凭证
    app_id = os.environ.get("FEISHU_GM_APP_ID", "cli_a90cfc15eef8dbdf")
    app_secret = os.environ.get("FEISHU_GM_APP_SECRET", "gVf7ZVqzxOC58PpZZlrAndYAP7zTRxHK")
    
    print("正在获取 token...")
    token = get_token(app_id, app_secret)
    
    if not token:
        print("❌ 获取 token 失败，请检查 app_id 和 app_secret")
        return
    
    print(f"✅ Token 获取成功\n")
    print("正在列出机器人所在的群聊...\n")
    
    chats = list_chats(token)
    
    if not chats:
        print("❌ 没有找到群聊。请确认:")
        print("   1. 机器人已被拉入群聊")
        print("   2. 机器人已开启 im:chat:readonly 权限")
        return
    
    print(f"找到 {len(chats)} 个群聊:\n")
    for chat in chats:
        print(f"  群名: {chat.get('name', '未命名')}")
        print(f"  chat_id: {chat.get('chat_id', '未知')}")
        print(f"  描述: {chat.get('description', '无')}")
        print(f"  人数: {chat.get('user_count', '?')}")
        print()
    
    # 如果只有一个群，直接提示
    if len(chats) == 1:
        cid = chats[0].get("chat_id", "")
        print(f"💡 只有一个群，建议直接填入 .env:")
        print(f"   FEISHU_DECISION_CHAT_ID={cid}")
        print(f"   FEISHU_EXECUTION_CHAT_ID={cid}")
        print(f"   FEISHU_ALERT_CHAT_ID={cid}")

if __name__ == "__main__":
    main()
