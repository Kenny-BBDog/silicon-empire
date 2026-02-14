-- 009_evolution.sql — 集体进化看板

-- 进化提案表
CREATE TABLE IF NOT EXISTS evolution_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposer VARCHAR(20) NOT NULL,         -- cgo/coo/cro/cto/gm
    category VARCHAR(50) NOT NULL,         -- new_agent / new_skill / new_department / optimize / infra / memory
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(10) DEFAULT 'P2',     -- P0/P1/P2
    status VARCHAR(20) DEFAULT 'draft',    -- draft/discussed/approved/executing/done/rejected
    votes JSONB DEFAULT '{}',              -- {"cgo":"support","coo":"neutral","cto":"lead"}
    discussion_log JSONB DEFAULT '[]',     -- [{"role":"cgo","content":"我需要..."},...]
    execution_plan TEXT,                   -- CTO 的技术方案
    result TEXT,                           -- 执行结果
    created_at TIMESTAMPTZ DEFAULT NOW(),
    discussed_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

-- 首席自省记录
CREATE TABLE IF NOT EXISTS chief_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_role VARCHAR(20) NOT NULL,
    reflection TEXT NOT NULL,              -- 自省内容
    identified_gaps TEXT[],                -- 发现的不足
    proposed_improvements TEXT[],          -- 建议的改进
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_evo_status ON evolution_proposals(status);
CREATE INDEX IF NOT EXISTS idx_evo_proposer ON evolution_proposals(proposer);
CREATE INDEX IF NOT EXISTS idx_reflection_role ON chief_reflections(agent_role);
CREATE INDEX IF NOT EXISTS idx_reflection_time ON chief_reflections(created_at DESC);
