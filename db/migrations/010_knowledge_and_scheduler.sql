-- 010: 调度器任务日志
CREATE TABLE IF NOT EXISTS scheduled_task_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'success',  -- success / failed
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sched_job ON scheduled_task_log(job_name, created_at DESC);

-- 011: 公司共享知识库
CREATE TABLE IF NOT EXISTS company_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,      -- lesson / best_practice / market_insight / warning / decision_record
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    source_agent VARCHAR(30),           -- 谁贡献的
    confidence FLOAT DEFAULT 0.8,       -- 0-1 可信度
    tags TEXT[] DEFAULT '{}',
    embedding VECTOR(768),              -- 语义检索
    access_count INTEGER DEFAULT 0,     -- 被检索次数
    verified BOOLEAN DEFAULT FALSE,     -- 是否已验证
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_category ON company_knowledge(category);
CREATE INDEX idx_knowledge_tags ON company_knowledge USING GIN(tags);
CREATE INDEX idx_knowledge_source ON company_knowledge(source_agent);

-- 语义检索函数
CREATE OR REPLACE FUNCTION search_company_knowledge(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 5,
    p_category VARCHAR DEFAULT NULL
)
RETURNS TABLE(
    id UUID,
    category VARCHAR,
    title VARCHAR,
    content TEXT,
    source_agent VARCHAR,
    confidence FLOAT,
    tags TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ck.id, ck.category, ck.title, ck.content,
        ck.source_agent, ck.confidence, ck.tags,
        1 - (ck.embedding <=> query_embedding) AS similarity
    FROM company_knowledge ck
    WHERE ck.embedding IS NOT NULL
        AND (p_category IS NULL OR ck.category = p_category)
    ORDER BY ck.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
