"""
RAG Pipeline — Embedding + Vector Search + Context Assembly.

为整个 Silicon-Empire 提供"记忆检索"能力：
- 将文本转为向量 (via OpenRouter / OpenAI embeddings)
- 存入 Supabase pgvector
- 语义检索并组装上下文片段供 LLM 使用
"""

from __future__ import annotations

from typing import Any

from langchain_openai import OpenAIEmbeddings

from src.config.settings import get_settings


class RAGPipeline:
    """
    RAG (Retrieval Augmented Generation) pipeline.
    
    Flow: text → embed → store → query → assemble context → inject into LLM
    """

    def __init__(self) -> None:
        self._embeddings: OpenAIEmbeddings | None = None
        self._supabase = None

    async def init(self, supabase_client=None) -> None:
        """Initialize embeddings model and storage backend."""
        settings = get_settings()

        # Use OpenRouter-compatible embeddings endpoint
        self._embeddings = OpenAIEmbeddings(
            model="openai/text-embedding-3-small",
            openai_api_key=settings.openrouter_api_key,
            openai_api_base=settings.openrouter_base_url,
        )

        if supabase_client:
            self._supabase = supabase_client
        else:
            from src.core.memory import get_memory
            mem = await get_memory()
            self._supabase = mem.supabase

    # ════════════════════════════════════════
    # Embedding
    # ════════════════════════════════════════

    async def embed_text(self, text: str) -> list[float]:
        """Convert text to a 1536-dimensional vector."""
        return await self._embeddings.aembed_query(text)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embed multiple texts."""
        return await self._embeddings.aembed_documents(texts)

    # ════════════════════════════════════════
    # Store: 写入各知识库
    # ════════════════════════════════════════

    async def ingest_product(self, product_data: dict[str, Any]) -> dict:
        """
        将产品信息向量化后存入 products 表。
        CGO 选品、CRO 侵权检测都会用到。
        """
        text = self._product_to_text(product_data)
        embedding = await self.embed_text(text)

        data = {
            "title": product_data.get("title", ""),
            "category": product_data.get("category", ""),
            "source_platform": product_data.get("platform", ""),
            "price_range": product_data.get("price_range", {}),
            "selling_points": product_data.get("selling_points", []),
            "risk_flags": product_data.get("risk_flags", []),
            "raw_data": product_data,
            "embedding": embedding,
        }

        result = self._supabase.table("products").insert(data).execute()
        return result.data[0] if result.data else {}

    async def ingest_supplier(self, supplier_data: dict[str, Any]) -> dict:
        """将供应商信息向量化后存入 suppliers 表。"""
        text = self._supplier_to_text(supplier_data)
        embedding = await self.embed_text(text)

        data = {
            "name": supplier_data.get("name", ""),
            "contact_email": supplier_data.get("email", ""),
            "products": supplier_data.get("products", []),
            "tone_profile": supplier_data.get("tone", ""),
            "negotiation_log": supplier_data.get("negotiation_log", {}),
            "embedding": embedding,
        }

        result = self._supabase.table("suppliers").insert(data).execute()
        return result.data[0] if result.data else {}

    async def ingest_policy(self, policy_data: dict[str, Any]) -> dict:
        """将平台政策向量化后存入 platform_policies 表。CRO 合规检索核心。"""
        embedding = await self.embed_text(policy_data.get("rule_text", ""))

        data = {
            "platform": policy_data.get("platform", ""),
            "category": policy_data.get("category", ""),
            "rule_text": policy_data.get("rule_text", ""),
            "severity": policy_data.get("severity", "INFO"),
            "embedding": embedding,
        }

        result = self._supabase.table("platform_policies").insert(data).execute()
        return result.data[0] if result.data else {}

    async def ingest_interaction(self, interaction_data: dict[str, Any]) -> dict:
        """将 CRM 交互记忆向量化。关系中台用。"""
        text = f"{interaction_data.get('contact_name', '')}: {interaction_data.get('summary', '')}"
        embedding = await self.embed_text(text)

        data = {
            "contact_type": interaction_data.get("contact_type", ""),
            "contact_name": interaction_data.get("contact_name", ""),
            "channel": interaction_data.get("channel", ""),
            "direction": interaction_data.get("direction", ""),
            "summary": interaction_data.get("summary", ""),
            "raw_content": interaction_data.get("raw_content", ""),
            "attachments": interaction_data.get("attachments", {}),
            "embedding": embedding,
        }

        result = self._supabase.table("interactions").insert(data).execute()
        return result.data[0] if result.data else {}

    # ════════════════════════════════════════
    # Retrieve: 语义检索
    # ════════════════════════════════════════

    async def search_products(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索产品库 — CGO 选品、CRO 查侵权。"""
        embedding = await self.embed_text(query)
        result = self._supabase.rpc(
            "search_products",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return result.data or []

    async def search_policies(self, query: str, top_k: int = 10) -> list[dict]:
        """语义搜索合规政策 — CRO 风控引用。"""
        embedding = await self.embed_text(query)
        result = self._supabase.rpc(
            "search_policies",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return result.data or []

    async def search_suppliers(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索供应商 — 关系中台用。"""
        embedding = await self.embed_text(query)
        result = self._supabase.rpc(
            "search_suppliers",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return result.data or []

    async def search_interactions(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索 CRM 交互 — 关系中台用。"""
        embedding = await self.embed_text(query)
        result = self._supabase.rpc(
            "search_interactions",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return result.data or []

    # ════════════════════════════════════════
    # Assemble: 组装 RAG 上下文
    # ════════════════════════════════════════

    async def build_rag_context(
        self,
        query: str,
        sources: list[str] | None = None,
        top_k: int = 5,
    ) -> str:
        """
        一站式 RAG: 查询 → 检索 → 组装上下文字符串。
        
        Args:
            query: 自然语言查询
            sources: 要检索的知识库列表, 默认全部
                     可选: ["products", "policies", "suppliers", "interactions"]
            top_k: 每个库返回的最大条数
        """
        if sources is None:
            sources = ["products", "policies"]

        parts = []

        if "products" in sources:
            results = await self.search_products(query, top_k)
            if results:
                items = "\n".join(
                    f"- **{r.get('title', '?')}** ({r.get('category', '?')}) "
                    f"| 平台: {r.get('source_platform', '?')} "
                    f"| 卖点: {', '.join(r.get('selling_points', [])[:3])}"
                    for r in results
                )
                parts.append(f"### 相关产品 ({len(results)} 条)\n{items}")

        if "policies" in sources:
            results = await self.search_policies(query, top_k)
            if results:
                items = "\n".join(
                    f"- [{r.get('severity', '?')}] **{r.get('platform', '?')}** | "
                    f"{r.get('rule_text', '')[:150]}"
                    for r in results
                )
                parts.append(f"### 相关政策 ({len(results)} 条)\n{items}")

        if "suppliers" in sources:
            results = await self.search_suppliers(query, top_k)
            if results:
                items = "\n".join(
                    f"- **{r.get('name', '?')}** | 产品: {', '.join(r.get('products', [])[:3])}"
                    for r in results
                )
                parts.append(f"### 相关供应商 ({len(results)} 条)\n{items}")

        if "interactions" in sources:
            results = await self.search_interactions(query, top_k)
            if results:
                items = "\n".join(
                    f"- [{r.get('direction', '?')}] {r.get('contact_name', '?')} | "
                    f"{r.get('summary', '')[:100]}"
                    for r in results
                )
                parts.append(f"### 相关沟通记录 ({len(results)} 条)\n{items}")

        if not parts:
            return ""

        return "\n\n".join(["## 🔍 RAG 检索结果"] + parts)

    # ════════════════════════════════════════
    # Text Serialization helpers
    # ════════════════════════════════════════

    @staticmethod
    def _product_to_text(data: dict) -> str:
        parts = [data.get("title", "")]
        if data.get("category"):
            parts.append(f"品类: {data['category']}")
        if data.get("selling_points"):
            parts.append(f"卖点: {', '.join(data['selling_points'])}")
        if data.get("risk_flags"):
            parts.append(f"风险: {', '.join(data['risk_flags'])}")
        return " | ".join(parts)

    @staticmethod
    def _supplier_to_text(data: dict) -> str:
        parts = [data.get("name", "")]
        if data.get("products"):
            parts.append(f"产品: {', '.join(data['products'])}")
        if data.get("tone"):
            parts.append(f"风格: {data['tone']}")
        return " | ".join(parts)


# Singleton
_rag: RAGPipeline | None = None


async def get_rag() -> RAGPipeline:
    """Get or create the global RAG pipeline singleton."""
    global _rag
    if _rag is None:
        _rag = RAGPipeline()
        await _rag.init()
    return _rag
