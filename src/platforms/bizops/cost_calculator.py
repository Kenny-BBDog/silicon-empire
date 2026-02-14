"""
业务中台 — Cost Calculator 成本精算师 (L3)

职责：
- P&L 建模 (产品级/品类级/整体)
- FOB + FBA + 运费 + 广告费计算
- 盈亏平衡点分析
- 定价策略建议 (成本加成 / 竞品对标 / 价值定价)
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class CostCalculatorAgent(PlatformWorker):
    """L3 业务中台 — 成本精算师"""

    ROLE = "l3_cost_calculator"
    DISPLAY_NAME = "成本精算师 (Cost Calculator)"
    LLM_ROLE = "analysis"   # 用分析模型，大量计算
    PLATFORM = "bizops"

    async def build_pnl_model(
        self,
        product_info: dict[str, Any],
        cost_inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        构建产品级 P&L 模型。
        
        cost_inputs 示例:
        {
            "fob_cost": 3.50,        # 出厂价 USD
            "shipping_cost": 1.20,   # 头程运费/件
            "fba_fee": 4.50,         # FBA 费用
            "referral_pct": 15,      # 平台佣金 %
            "ad_cost_ratio": 20,     # 广告占比 %
            "target_price": 24.99,   # 目标售价
        }
        """
        await self.initialize()

        prompt = (
            f"为以下产品建立完整的 P&L 模型。\n\n"
            f"## 产品信息\n{product_info}\n\n"
            f"## 成本输入\n{cost_inputs or '请基于品类估算'}\n\n"
            f"## 输出要求 (必须包含数字)\n"
            f"1. **成本分解表**\n"
            f"   - FOB (出厂价)\n"
            f"   - 头程运费\n"
            f"   - FBA / 配送费\n"
            f"   - 平台佣金\n"
            f"   - 广告费\n"
            f"   - 退货损耗 (按 5% 计)\n"
            f"   - 其他 (保险/仓储)\n"
            f"   - **总成本**\n\n"
            f"2. **利润分析**\n"
            f"   - 建议售价区间\n"
            f"   - 毛利率 / 净利率\n"
            f"   - 每单利润\n"
            f"   - 盈亏平衡点 (日/月)\n\n"
            f"3. **敏感性分析**\n"
            f"   - FOB ±20% 时利润变化\n"
            f"   - 售价 ±10% 时利润变化\n"
            f"   - 广告费 ±30% 时利润变化\n\n"
            f"4. **定价建议**: 成本加成 / 竞品对标 / 价值定价\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"完成 P&L 建模: {product_info.get('title', '?')[:40]}",
            importance=7,
        )

        return {"pnl_model": response, "product": product_info.get("title", "")}

    async def compare_suppliers(
        self, quotes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """比较多个供应商报价，输出综合评分。"""
        await self.initialize()

        prompt = (
            f"比较以下 {len(quotes)} 个供应商的报价:\n\n"
            f"## 报价列表\n{quotes}\n\n"
            f"## 评分维度\n"
            f"- 单价 (权重 40%)\n"
            f"- MOQ 最低起订量 (权重 15%)\n"
            f"- 交期 (权重 20%)\n"
            f"- 付款条件 (权重 10%)\n"
            f"- 质量认证 (权重 15%)\n\n"
            f"输出: 评分排名 + 推荐选择 + 谈判建议\n"
        )

        response = await self._llm_think(prompt, {})
        return {"comparison": response, "quote_count": len(quotes)}

    async def forecast_inventory(
        self,
        product_id: str,
        sales_history: list[dict] | None = None,
        lead_time_days: int = 30,
    ) -> dict[str, Any]:
        """库存预测 — 根据销售历史预估补货时间和数量。"""
        await self.initialize()

        prompt = (
            f"为产品 {product_id} 做库存预测:\n\n"
            f"## 销售历史\n{sales_history or '无历史，按新品估算'}\n\n"
            f"## 供应链参数\n"
            f"- 生产交期: {lead_time_days} 天\n"
            f"- 海运周期: 25 天 (中国→美国)\n"
            f"- 安全库存天数: 14 天\n\n"
            f"## 输出\n"
            f"1. 日均销量预测\n"
            f"2. 建议补货数量\n"
            f"3. 建议下单日期\n"
            f"4. 资金占用估算\n"
        )

        response = await self._llm_think(prompt, {})
        return {"product_id": product_id, "forecast": response}
