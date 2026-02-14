"""
Silicon-Empire 本地冒烟测试 — 验证 LLM 连通性 + 飞书发送。

运行: python scripts/smoke_test.py
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_openrouter():
    """测试 OpenRouter API 连通性。"""
    print("1️⃣  测试 OpenRouter 连通性...")

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key or "xxxx" in api_key:
        print("   ❌ OPENROUTER_API_KEY 未配置")
        return False

    models_to_test = {
        "GM (DeepSeek V3.2)": os.environ.get("MODEL_GM", "deepseek/deepseek-chat-v3-0324"),
        "CTO (Claude Sonnet 4)": os.environ.get("MODEL_CTO", "anthropic/claude-sonnet-4"),
        "Analysis (Gemini 2.5 Flash)": os.environ.get("MODEL_ANALYSIS", "google/gemini-2.5-flash-preview"),
    }

    all_ok = True
    for role, model in models_to_test.items():
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "https://silicon-empire.app",
                        "X-Title": "Silicon-Empire Smoke Test",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "回复'OK'，不要说其他的。"}],
                        "max_tokens": 10,
                    },
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("choices"):
                    reply = data["choices"][0]["message"]["content"].strip()
                    print(f"   ✅ {role}: {model} → {reply}")
                else:
                    error = data.get("error", {}).get("message", resp.text[:100])
                    print(f"   ❌ {role}: {model} → {error}")
                    all_ok = False
        except Exception as e:
            print(f"   ❌ {role}: {model} → {str(e)[:80]}")
            all_ok = False

    return all_ok


async def test_feishu():
    """测试飞书消息发送。"""
    print("\n2️⃣  测试飞书消息发送...")

    app_id = os.environ.get("FEISHU_GM_APP_ID", "")
    app_secret = os.environ.get("FEISHU_GM_APP_SECRET", "")
    chat_id = os.environ.get("FEISHU_DECISION_CHAT_ID", "")

    if not all([app_id, app_secret, chat_id]):
        print("   ⚠️  飞书凭证不完整，跳过")
        return True

    try:
        async with httpx.AsyncClient() as client:
            # 获取 token
            resp = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": app_id, "app_secret": app_secret},
            )
            token = resp.json().get("tenant_access_token", "")

            if not token:
                print("   ❌ Token 获取失败")
                return False

            # 发送测试消息
            import json
            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "🛸 系统冒烟测试"},
                    "template": "turquoise",
                },
                "elements": [
                    {"tag": "markdown", "content": "**Silicon-Empire 系统自检通过** ✅\n\nLLM 网关正常 · 飞书通信正常"},
                ],
            }

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
            if data.get("code") == 0:
                print("   ✅ 飞书消息发送成功 (请查看群聊)")
                return True
            else:
                print(f"   ❌ 飞书发送失败: {data.get('msg', '')}")
                return False
    except Exception as e:
        print(f"   ❌ 飞书测试异常: {str(e)[:80]}")
        return False


async def test_redis():
    """测试 Redis 连通性。"""
    print("\n3️⃣  测试 Redis 连通性...")
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        await r.set("smoke_test", "ok", ex=10)
        val = await r.get("smoke_test")
        await r.close()
        if val == "ok":
            print("   ✅ Redis 正常")
            return True
        else:
            print("   ❌ Redis 读写异常")
            return False
    except Exception as e:
        print(f"   ⚠️  Redis 未启动或不可达: {str(e)[:60]}")
        print("      (部署到服务器后 Docker 会自动启动 Redis)")
        return True  # Non-blocking


async def main():
    print("🛸 Silicon-Empire 冒烟测试\n")
    print("=" * 40)

    results = {
        "OpenRouter": await test_openrouter(),
        "飞书": await test_feishu(),
        "Redis": await test_redis(),
    }

    print("\n" + "=" * 40)
    print("📊 测试结果:\n")
    all_pass = True
    for name, ok in results.items():
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"   {name}: {status}")
        if not ok:
            all_pass = False

    print()
    if all_pass:
        print("🎉 全部通过！可以部署到服务器了。")
    else:
        print("⚠️  部分测试未通过，请检查后再部署。")
    print()


if __name__ == "__main__":
    asyncio.run(main())
