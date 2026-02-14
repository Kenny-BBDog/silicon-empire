"""
Multi-Provider LLM Factory — 三级路由: Google AI Studio → gptgod.cloud → OpenRouter.

策略:
  1. 如果角色配置了 Google AI Studio Key → 直连 Gemini (免费)
  2. 如果配置了 THIRDPARTY_API_KEY → 走 gptgod.cloud (便宜, 410 个模型)
  3. 否则 → 走 OpenRouter (付费兜底)
"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.settings import get_settings, get_models

# ─── 角色 → Google Key 映射 ───
_ROLE_GOOGLE_KEY_MAP = {
    "gm": "GOOGLE_AI_KEY_1",
    "cgo": "GOOGLE_AI_KEY_2",
    "cro": "GOOGLE_AI_KEY_3",
    "coo": "GOOGLE_AI_KEY_4",
    "creative": "GOOGLE_AI_KEY_5",
    "analysis": "GOOGLE_AI_KEY_6",
    "cto": "GOOGLE_AI_KEY_CTO",
}


def _get_google_key(role: str) -> str | None:
    """获取角色对应的 Google AI Studio Key, 无则返回 None."""
    env_var = _ROLE_GOOGLE_KEY_MAP.get(role)
    if not env_var:
        return None
    key = os.environ.get(env_var, "")
    return key if key else None


def get_llm(role: str, temperature: float = 0.7, **kwargs):
    """
    Create an LLM instance for the given role.

    三级路由:
      1. GOOGLE_AI_KEY_{N} 有值 → ChatGoogleGenerativeAI (免费)
      2. THIRDPARTY_API_KEY 有值 → ChatOpenAI via gptgod (便宜)
      3. 否则 → ChatOpenAI via OpenRouter (兜底)
    """
    settings = get_settings()
    models = get_models()
    model_name = getattr(models, role, models.gm)

    # ── Route 1: Google AI Studio (免费) ──
    google_key = _get_google_key(role)
    if google_key:
        gemini_model = os.environ.get("GOOGLE_AI_MODEL", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=google_key,
            temperature=temperature,
            convert_system_message_to_human=True,
            **kwargs,
        )

    # ── Route 2: 第三方 API - gptgod.cloud (便宜) ──
    tp_key = os.environ.get("THIRDPARTY_API_KEY", "")
    tp_base = os.environ.get("THIRDPARTY_BASE_URL", "")
    if tp_key and tp_base:
        return ChatOpenAI(
            model=model_name,
            openai_api_key=tp_key,
            openai_api_base=tp_base,
            temperature=temperature,
            **kwargs,
        )

    # ── Route 3: OpenRouter (兜底) ──
    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        default_headers={
            "HTTP-Referer": f"https://{settings.openrouter_app_name}.app",
            "X-Title": settings.openrouter_app_name,
        },
        temperature=temperature,
        **kwargs,
    )


# Pre-built role accessors for convenience
def llm_gm(**kw):
    return get_llm("gm", temperature=0.3, **kw)


def llm_cgo(**kw):
    return get_llm("cgo", temperature=0.8, **kw)


def llm_coo(**kw):
    return get_llm("coo", temperature=0.2, **kw)


def llm_cro(**kw):
    return get_llm("cro", temperature=0.2, **kw)


def llm_cto(**kw):
    return get_llm("cto", temperature=0.4, **kw)


def llm_creative(**kw):
    return get_llm("creative", temperature=0.9, **kw)


def llm_analysis(**kw):
    return get_llm("analysis", temperature=0.1, **kw)
