-- Silicon-Empire: agent_memories
-- 每个 Agent 的个人长期记忆表
-- 每条记忆都有向量嵌入，支持语义联想式回忆

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_memories (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         VARCHAR(50) NOT NULL,    -- e.g. "cgo", "l3_intel_hunter", "l4_autolab"
    content          TEXT NOT NULL,            -- 记忆的文本内容
    memory_type      VARCHAR(30) NOT NULL      -- observation | reflection | insight | interaction | preference
                     CHECK (memory_type IN ('observation','reflection','insight','interaction','preference')),
    emotional_tone   VARCHAR(20) DEFAULT 'neutral'
                     CHECK (emotional_tone IN ('positive','negative','neutral','curious','frustrated','excited')),
    related_agents   TEXT[],                   -- 涉及的其他 Agent
    related_task     TEXT DEFAULT '',          -- 关联的 trace_id
    importance       INTEGER DEFAULT 5         -- 1-10, 影响排序
                     CHECK (importance BETWEEN 1 AND 10),
    embedding        VECTOR(1536),            -- 语义向量
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 索引: 按 Agent 快速查询
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent
    ON agent_memories (agent_id, importance DESC, created_at DESC);

-- 索引: 按记忆类型
CREATE INDEX IF NOT EXISTS idx_agent_memories_type
    ON agent_memories (agent_id, memory_type);

-- 索引: 向量相似度 (HNSW for fast ANN search)
CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding
    ON agent_memories USING hnsw (embedding vector_cosine_ops);

-- RPC: 语义检索函数 (个人记忆的回忆功能)
CREATE OR REPLACE FUNCTION search_agent_memories(
    p_agent_id TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    agent_id VARCHAR,
    content TEXT,
    memory_type VARCHAR,
    emotional_tone VARCHAR,
    related_agents TEXT[],
    importance INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        am.id,
        am.agent_id,
        am.content,
        am.memory_type,
        am.emotional_tone,
        am.related_agents,
        am.importance,
        1 - (am.embedding <=> query_embedding) AS similarity
    FROM agent_memories am
    WHERE am.agent_id = p_agent_id
        AND am.embedding IS NOT NULL
    ORDER BY
        (1 - (am.embedding <=> query_embedding)) * 0.6   -- 60% 语义相关度
        + (am.importance::FLOAT / 10.0) * 0.4             -- 40% 重要性权重
    DESC
    LIMIT match_count;
END;
$$;
