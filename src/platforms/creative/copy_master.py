"""
内容中台 — Copy Master 文案大师 (L3)

职责：
- 生成商品标题/描述/五点卖点 (Amazon, Shopify, TikTok)
- 广告创意文案 (Google Ads, FB Ads)
- SEO 关键词优化
- A/B 测试文案变体
- 多语种本地化
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class CopyMasterAgent(PlatformWorker):
    """L3 内容中台 — 文案大师"""

    ROLE = "l3_copy_master"
    DISPLAY_NAME = "文案大师 (Copy Master)"
    LLM_ROLE = "creative"   # 用 Claude — 创意文案更擅长
    PLATFORM = "creative"

    async def generate_listing(
        self,
        product_info: dict[str, Any],
        platform: str = "amazon",
        language: str = "en",
    ) -> dict[str, Any]:
        """
        生成商品 Listing (标题 + 五点 + 描述)。
        跨平台适配: Amazon / Shopify / TikTok。
        """
        await self.initialize()

        platform_rules = {
            "amazon": "标题≤200字符, 五点卖点, A+ 描述, 后端关键词",
            "shopify": "SEO 标题, 长描述, 标签",
            "tiktok": "短标题≤80字, 卖点简洁, 带 emoji",
        }

        prompt = (
            f"为以下产品生成 {platform.upper()} 平台的完整 Listing。\n\n"
            f"## 产品信息\n{product_info}\n\n"
            f"## 平台规则\n{platform_rules.get(platform, platform_rules['amazon'])}\n\n"
            f"## 语言\n{language}\n\n"
            f"## 输出要求\n"
            f"1. **标题** — 包含核心关键词，自然读感\n"
            f"2. **五点卖点** (Bullet Points) — 每点以大写特性开头\n"
            f"3. **描述** — 吸引力强，SEO 友好\n"
            f"4. **后端关键词** — 250 字符以内，不重复标题词\n"
            f"5. **搜索词建议** — 5 个长尾关键词\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"为 {product_info.get('title', '?')[:40]} 生成了 {platform} listing",
            importance=5,
        )

        return {
            "platform": platform,
            "language": language,
            "listing": response,
        }

    async def generate_ad_copy(
        self,
        product_info: dict[str, Any],
        ad_platform: str = "facebook",
        variants: int = 3,
    ) -> dict[str, Any]:
        """生成广告创意文案 (多变体 A/B 测试)。"""
        await self.initialize()

        prompt = (
            f"为以下产品生成 {variants} 个 {ad_platform.upper()} 广告文案变体。\n\n"
            f"## 产品\n{product_info}\n\n"
            f"## 每个变体包含\n"
            f"- headline (≤30 字符)\n"
            f"- primary_text (正文)\n"
            f"- call_to_action\n"
            f"- targeting_suggestion (受众建议)\n\n"
            f"## 风格\n"
            f"变体 1: 痛点驱动 | 变体 2: 利益驱动 | 变体 3: 社交证明\n"
        )

        response = await self._llm_think(prompt, {})
        return {"ad_platform": ad_platform, "variants": response}

    async def localize(
        self,
        content: str,
        source_lang: str = "en",
        target_langs: list[str] | None = None,
    ) -> dict[str, Any]:
        """多语种本地化 (不只是翻译，还要文化适配)。"""
        await self.initialize()

        if target_langs is None:
            target_langs = ["de", "fr", "ja", "es"]

        prompt = (
            f"将以下电商内容本地化到 {', '.join(target_langs)}。\n\n"
            f"## 原文 ({source_lang})\n{content}\n\n"
            f"## 要求\n"
            f"- 不是机械翻译，要文化适配\n"
            f"- 保留营销语气和冲击力\n"
            f"- 适配目标市场的搜索习惯\n"
        )

        response = await self._llm_think(prompt, {})
        return {"source_lang": source_lang, "localized": response}
