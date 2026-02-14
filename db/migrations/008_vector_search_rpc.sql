-- Silicon-Empire: pgvector 语义检索 RPC functions
-- 为 RAG Pipeline 提供各知识库的相似度搜索

-- ==========================================
-- 产品库语义搜索 (CGO 选品 / CRO 侵权)
-- ==========================================
CREATE OR REPLACE FUNCTION search_products(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    product_id UUID,
    title TEXT,
    category TEXT,
    source_platform TEXT,
    price_range JSONB,
    selling_points TEXT[],
    risk_flags TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.product_id,
        p.title,
        p.category,
        p.source_platform,
        p.price_range,
        p.selling_points,
        p.risk_flags,
        1 - (p.embedding <=> query_embedding) AS similarity
    FROM products p
    WHERE p.embedding IS NOT NULL
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ==========================================
-- 合规政策语义搜索 (CRO 风控)
-- ==========================================
CREATE OR REPLACE FUNCTION search_policies(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    policy_id UUID,
    platform TEXT,
    category TEXT,
    rule_text TEXT,
    severity VARCHAR,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.policy_id,
        pp.platform,
        pp.category,
        pp.rule_text,
        pp.severity,
        1 - (pp.embedding <=> query_embedding) AS similarity
    FROM platform_policies pp
    WHERE pp.embedding IS NOT NULL
    ORDER BY pp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ==========================================
-- 供应商语义搜索 (关系中台)
-- ==========================================
CREATE OR REPLACE FUNCTION search_suppliers(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    supplier_id UUID,
    name TEXT,
    contact_email TEXT,
    products TEXT[],
    tone_profile TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.supplier_id,
        s.name,
        s.contact_email,
        s.products,
        s.tone_profile,
        1 - (s.embedding <=> query_embedding) AS similarity
    FROM suppliers s
    WHERE s.embedding IS NOT NULL
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ==========================================
-- CRM 交互语义搜索 (关系中台)
-- ==========================================
CREATE OR REPLACE FUNCTION search_interactions(
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    contact_type VARCHAR,
    contact_name TEXT,
    channel VARCHAR,
    direction VARCHAR,
    summary TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.contact_type,
        i.contact_name,
        i.channel,
        i.direction,
        i.summary,
        1 - (i.embedding <=> query_embedding) AS similarity
    FROM interactions i
    WHERE i.embedding IS NOT NULL
    ORDER BY i.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ==========================================
-- HNSW 向量索引 (加速 ANN 检索)
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_products_embedding
    ON products USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_suppliers_embedding
    ON suppliers USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_policies_embedding
    ON platform_policies USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_interactions_embedding
    ON interactions USING hnsw (embedding vector_cosine_ops);
