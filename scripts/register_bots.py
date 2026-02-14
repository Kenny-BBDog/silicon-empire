"""
飞书长连接注册脚本 — 用多进程方式同时启动 6 个机器人。

步骤:
1. 运行: python scripts/register_bots.py
2. 保持脚本运行
3. 去飞书后台每个机器人 → 事件订阅 → 选「长连接」→ 保存
4. 全部成功后 Ctrl+C 停止
"""

import os
import sys
import subprocess
import time

from dotenv import load_dotenv
load_dotenv()


SINGLE_BOT_SCRIPT = '''
import sys
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

def handler(data):
    print(f"  收到事件")

event_handler = (
    lark.EventDispatcherHandler
    .builder("", "")
    .register_p2_im_message_receive_v1(handler)
    .build()
)

client = lark.ws.Client(
    app_id=sys.argv[1],
    app_secret=sys.argv[2],
    event_handler=event_handler,
    log_level=lark.LogLevel.INFO,
)

print(f"  ✅ {sys.argv[3]} 长连接已建立，保持运行中...")
client.start()
'''


def main():
    bots = {
        "GM": (os.environ.get("FEISHU_GM_APP_ID", ""), os.environ.get("FEISHU_GM_APP_SECRET", "")),
        "CGO": (os.environ.get("FEISHU_CGO_APP_ID", ""), os.environ.get("FEISHU_CGO_APP_SECRET", "")),
        "CRO": (os.environ.get("FEISHU_CRO_APP_ID", ""), os.environ.get("FEISHU_CRO_APP_SECRET", "")),
        "COO": (os.environ.get("FEISHU_COO_APP_ID", ""), os.environ.get("FEISHU_COO_APP_SECRET", "")),
        "CTO": (os.environ.get("FEISHU_CTO_APP_ID", ""), os.environ.get("FEISHU_CTO_APP_SECRET", "")),
        "System": (os.environ.get("FEISHU_SYSTEM_APP_ID", ""), os.environ.get("FEISHU_SYSTEM_APP_SECRET", "")),
    }

    print("🛸 Silicon-Empire — 飞书长连接注册 (多进程)\n")

    processes = []
    for role, (app_id, app_secret) in bots.items():
        if not app_id or not app_secret:
            print(f"  ⚠️  {role} 凭证缺失，跳过")
            continue

        print(f"  🔌 启动 {role}...")
        p = subprocess.Popen(
            [sys.executable, "-c", SINGLE_BOT_SCRIPT, app_id, app_secret, role],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append((role, p))
        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"✅ {len(processes)} 个机器人进程已启动")
    print()
    print("📋 现在去飞书后台:")
    print("   每个机器人 → 事件订阅 → 选「长连接」→ 保存")
    print()
    print("   全部保存成功后，按 Ctrl+C 停止")
    print(f"{'='*50}\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止所有机器人...")
        for role, p in processes:
            p.terminate()
            print(f"  ✅ {role} 已停止")
        print("👋 完成")


if __name__ == "__main__":
    main()
