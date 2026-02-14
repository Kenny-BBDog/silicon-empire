-- 011: 决策结果追踪 + 能力评分
CREATE TABLE IF NOT EXISTS decision_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID,               -- 关联 decisions 表
    agent_role VARCHAR(30) NOT NULL,
    prediction TEXT,                -- 当时的预测
    actual_result TEXT,             -- 实际结果
    accuracy_score FLOAT,           -- 0-1 准确度
    lessons_learned TEXT,           -- 自动提炼的教训
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outcome_agent ON decision_outcomes(agent_role, created_at DESC);
CREATE INDEX idx_outcome_decision ON decision_outcomes(decision_id);

-- 能力分快照表
CREATE TABLE IF NOT EXISTS agent_capability_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_role VARCHAR(30) NOT NULL,
    dimension VARCHAR(50) NOT NULL,  -- accuracy / speed / collaboration / innovation
    score FLOAT NOT NULL,            -- 0-100
    sample_count INTEGER DEFAULT 0,
    trend VARCHAR(10) DEFAULT 'stable',  -- rising / falling / stable
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cap_role ON agent_capability_scores(agent_role, snapshot_at DESC);

-- 自治级别记录
CREATE TABLE IF NOT EXISTS autonomy_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_level INTEGER DEFAULT 0,  -- 0-3
    upgrade_reason TEXT,
    downgrade_reason TEXT,
    approved_by VARCHAR(30) DEFAULT 'L0',
    effective_at TIMESTAMPTZ DEFAULT NOW()
);
