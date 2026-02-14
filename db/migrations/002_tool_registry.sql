-- Silicon-Empire: tool_registry
-- 工具注册表 (CTO 管理)

CREATE TABLE IF NOT EXISTS tool_registry (
    tool_name        VARCHAR(100) PRIMARY KEY,
    function_schema  JSONB NOT NULL,
    code_path        TEXT NOT NULL,
    status           VARCHAR(20) CHECK (status IN ('ACTIVE','DEPRECATED','BROKEN')),
    version          INTEGER DEFAULT 1,
    last_error_log   TEXT,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tools_status ON tool_registry(status);
