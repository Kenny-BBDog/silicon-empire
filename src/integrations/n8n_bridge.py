"""
n8n 编排桥 — Silicon-Empire ↔ n8n 双向通信

n8n 作为"外部编排调度器"：
- 定时任务 (每天早上品类扫描, 每周报告)
- 跨系统 Workflow (飞书 → LangGraph → 邮件 → Shopify)
- 人工 Trigger (通过 n8n UI 手动触发)

本模块提供:
1. 向 n8n 发送 webhook trigger
2. 接收 n8n 的回调
3. 预置 Workflow 模板 (导入 n8n 即可用)
"""

from __future__ import annotations

import os
import json
from typing import Any
from datetime import datetime, timezone

import httpx


N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/silicon-empire")


class N8nBridge:
    """
    n8n 双向桥接器。
    
    正向: Silicon-Empire → n8n (触发 Workflow)
    反向: n8n → Silicon-Empire (通过 FastAPI webhook)
    """

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or N8N_WEBHOOK_URL

    async def trigger_workflow(
        self,
        workflow_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        触发 n8n Workflow。
        
        workflow_name 示例:
        - "daily_scan"      → 每日品类扫描
        - "weekly_report"   → 每周汇总报告
        - "new_product"     → 新品上架全流程
        - "competitor_alert" → 竞品变动告警
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.webhook_url}/{workflow_name}",
                    json={
                        "triggered_by": "silicon-empire",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": payload,
                    },
                )
                return {
                    "success": resp.status_code == 200,
                    "workflow": workflow_name,
                    "response": resp.json() if resp.status_code == 200 else resp.text[:200],
                }
            except httpx.ConnectError:
                return {
                    "success": False,
                    "error": f"n8n unavailable at {self.webhook_url}",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def trigger_daily_scan(self, categories: list[str] | None = None) -> dict:
        """触发每日品类扫描。"""
        return await self.trigger_workflow("daily_scan", {
            "categories": categories or ["pet_supplies", "home_garden", "beauty"],
            "platforms": ["amazon", "tiktok"],
        })

    async def trigger_weekly_report(self) -> dict:
        """触发每周汇总报告。"""
        return await self.trigger_workflow("weekly_report", {
            "report_types": ["sales", "inventory", "competitor", "cost"],
        })

    async def trigger_new_product_flow(self, product_data: dict) -> dict:
        """触发新品上架全流程 (选品→文案→图片→成本→上架)。"""
        return await self.trigger_workflow("new_product", {
            "product": product_data,
            "steps": ["listing", "images", "cost_analysis", "publish"],
        })

    @staticmethod
    def generate_workflow_templates() -> dict[str, Any]:
        """
        生成 n8n Workflow JSON 模板。
        用户可以直接导入 n8n。
        """
        return {
            "daily_scan": {
                "name": "Silicon-Empire Daily Scan",
                "nodes": [
                    {
                        "type": "n8n-nodes-base.scheduleTrigger",
                        "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 24}]}},
                        "name": "每天 9:00 触发",
                    },
                    {
                        "type": "n8n-nodes-base.httpRequest",
                        "parameters": {
                            "url": "http://silicon-empire:8000/api/scan",
                            "method": "POST",
                            "body": {"categories": ["pet_supplies"]},
                        },
                        "name": "调用 Data Hunter",
                    },
                    {
                        "type": "n8n-nodes-base.httpRequest",
                        "parameters": {
                            "url": "http://silicon-empire:8000/api/analyze",
                            "method": "POST",
                        },
                        "name": "调用 Insight Analyst",
                    },
                    {
                        "type": "n8n-nodes-base.httpRequest",
                        "parameters": {
                            "url": "http://silicon-empire:8000/api/feishu/notify",
                            "method": "POST",
                        },
                        "name": "飞书通知结果",
                    },
                ],
                "connections": {
                    "每天 9:00 触发": {"main": [[{"node": "调用 Data Hunter"}]]},
                    "调用 Data Hunter": {"main": [[{"node": "调用 Insight Analyst"}]]},
                    "调用 Insight Analyst": {"main": [[{"node": "飞书通知结果"}]]},
                },
            },
            "new_product": {
                "name": "Silicon-Empire New Product Flow",
                "nodes": [
                    {"type": "n8n-nodes-base.webhook", "name": "Webhook 触发"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "文案生成"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "图片生成"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "成本计算"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "审批通知"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "Shopify 上架"},
                ],
            },
        }


# ─── Singleton ───

_bridge: N8nBridge | None = None


def get_n8n_bridge() -> N8nBridge:
    global _bridge
    if _bridge is None:
        _bridge = N8nBridge()
    return _bridge
