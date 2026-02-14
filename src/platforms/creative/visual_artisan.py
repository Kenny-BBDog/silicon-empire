"""
内容中台 — Visual Artisan 视觉工匠 (L3)

职责：
- 生成商品主图/白底图/场景图的 Prompt
- 调用 DALL-E / Midjourney 生成图片
- 图片审核 (侵权风险、平台合规)
- A+ Content / Brand Story 图文排版
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class VisualArtisanAgent(PlatformWorker):
    """L3 内容中台 — 视觉工匠"""

    ROLE = "l3_visual_artisan"
    DISPLAY_NAME = "视觉工匠 (Visual Artisan)"
    LLM_ROLE = "creative"
    PLATFORM = "creative"

    async def generate_product_images(
        self,
        product_info: dict[str, Any],
        image_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        为产品生成各类图片 Prompt。
        
        image_types: ["main", "white_bg", "lifestyle", "infographic", "size_chart"]
        """
        await self.initialize()

        if image_types is None:
            image_types = ["main", "white_bg", "lifestyle"]

        type_descriptions = {
            "main": "主图 — 白底，产品居中，高质感，Amazon 合规",
            "white_bg": "纯白底图 — 产品占比 85%，无文字/logo",
            "lifestyle": "场景图 — 产品在使用场景中，有人物或环境",
            "infographic": "信息图 — 标注产品尺寸/特性/对比",
            "size_chart": "尺码表 — 清晰的尺寸对照表",
        }

        prompt = (
            f"为以下产品生成高质量图片的 AI 绘图 Prompt。\n\n"
            f"## 产品\n{product_info}\n\n"
            f"## 需要的图片类型\n"
        )
        for img_type in image_types:
            desc = type_descriptions.get(img_type, img_type)
            prompt += f"- **{img_type}**: {desc}\n"

        prompt += (
            f"\n## 输出格式\n"
            f"每种类型输出:\n"
            f"1. DALL-E Prompt (英文，详细描述)\n"
            f"2. Midjourney Prompt (英文，含参数)\n"
            f"3. 负面 Prompt (要避免的元素)\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"为 {product_info.get('title', '?')[:40]} 生成了 {len(image_types)} 类图片 Prompt",
            importance=5,
        )

        return {"image_types": image_types, "prompts": response}

    async def audit_image(
        self, image_url: str, platform: str = "amazon"
    ) -> dict[str, Any]:
        """图片合规审核 — 检查是否符合平台规则。"""
        await self.initialize()

        prompt = (
            f"审核以下图片是否符合 {platform.upper()} 平台的要求:\n\n"
            f"图片 URL: {image_url}\n\n"
            f"## 检查项\n"
            f"1. 白底要求 (主图必须纯白底 RGB 255,255,255)\n"
            f"2. 产品占比 ≥ 85%\n"
            f"3. 无水印/Logo/文字\n"
            f"4. 无网址/联系方式\n"
            f"5. 无侵权风险 (品牌商标/明星肖像)\n"
            f"6. 图片尺寸 ≥ 1000x1000px\n\n"
            f"输出: PASS / FAIL + 具体问题列表\n"
        )

        response = await self._llm_think(prompt, {})
        return {"image_url": image_url, "audit_result": response}

    async def design_aplus_content(
        self, product_info: dict[str, Any], brand_story: str = ""
    ) -> dict[str, Any]:
        """设计 A+ Content 图文排版方案。"""
        await self.initialize()

        prompt = (
            f"设计 Amazon A+ Content 排版方案:\n\n"
            f"## 产品\n{product_info}\n\n"
            f"{'## 品牌故事\\n' + brand_story if brand_story else ''}\n\n"
            f"## 输出\n"
            f"1. 模块布局顺序 (5-7 个模块)\n"
            f"2. 每个模块: 类型 + 标题 + 文案 + 图片描述\n"
            f"3. 模块类型: 对比图/特性列表/品牌故事/使用场景/FAQ\n"
        )

        response = await self._llm_think(prompt, {})
        return {"aplus_design": response}
