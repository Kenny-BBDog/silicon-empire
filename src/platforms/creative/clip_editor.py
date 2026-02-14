"""
内容中台 — Clip Editor 短视频编辑 (L3)

职责：
- 生成短视频脚本 (TikTok / Reels / YouTube Shorts)
- 视频分镜/画面描述
- 字幕文案 + Hook 设计
- 音乐/音效建议
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class ClipEditorAgent(PlatformWorker):
    """L3 内容中台 — 短视频编辑"""

    ROLE = "l3_clip_editor"
    DISPLAY_NAME = "短视频编辑 (Clip Editor)"
    LLM_ROLE = "creative"
    PLATFORM = "creative"

    async def generate_video_script(
        self,
        product_info: dict[str, Any],
        platform: str = "tiktok",
        duration: int = 30,
        style: str = "product_review",
    ) -> dict[str, Any]:
        """
        生成短视频脚本。
        
        style: "product_review" | "unboxing" | "tutorial" | "trend_hook" | "ugc"
        """
        await self.initialize()

        style_guides = {
            "product_review": "真实测评风格，先展示痛点再展示解决方案",
            "unboxing": "开箱体验，制造惊喜感和期待感",
            "tutorial": "教程式，展示产品使用方法和效果",
            "trend_hook": "蹭热点，用当前流行 BGM 和转场",
            "ugc": "用户生成内容风格，自然真实",
        }

        prompt = (
            f"生成 {platform.upper()} 短视频脚本。\n\n"
            f"## 产品\n{product_info}\n\n"
            f"## 参数\n"
            f"- 时长: {duration} 秒\n"
            f"- 风格: {style} — {style_guides.get(style, '')}\n\n"
            f"## 输出格式\n"
            f"1. **Hook** (前 3 秒) — 必须抓眼球\n"
            f"2. **分镜表** — 每个镜头:\n"
            f"   - 时间码 (如 00:00-00:03)\n"
            f"   - 画面描述\n"
            f"   - 旁白/字幕\n"
            f"   - 镜头类型 (特写/全景/POV)\n"
            f"3. **CTA** (最后 3 秒) — 行动号召\n"
            f"4. **BGM 建议** — 风格 + 节奏\n"
            f"5. **字幕样式** — 字体/颜色/动画\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"生成了 {duration}s {style} 视频脚本",
            importance=5,
        )

        return {
            "platform": platform,
            "duration": duration,
            "style": style,
            "script": response,
        }

    async def generate_thumbnail(
        self, video_topic: str, style: str = "bold"
    ) -> dict[str, Any]:
        """生成视频封面/缩略图设计方案。"""
        await self.initialize()

        prompt = (
            f"设计视频封面缩略图:\n\n"
            f"## 主题\n{video_topic}\n\n"
            f"## 风格: {style}\n\n"
            f"## 输出\n"
            f"1. 布局描述 (人物位置/产品位置/文字位置)\n"
            f"2. 色彩方案\n"
            f"3. 标题文字 (≤6 个单词，大写)\n"
            f"4. 表情/情绪建议 (如果有人物)\n"
            f"5. AI 绘图 Prompt\n"
        )

        response = await self._llm_think(prompt, {})
        return {"topic": video_topic, "thumbnail_design": response}
