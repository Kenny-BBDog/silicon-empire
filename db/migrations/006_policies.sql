-- Silicon-Empire: platform_policies
-- 平台规则库

CREATE TABLE IF NOT EXISTS platform_policies (
    policy_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform         TEXT NOT NULL,
    category         TEXT,
    rule_text        TEXT NOT NULL,
    severity         VARCHAR(10) CHECK (severity IN ('BAN','WARNING','INFO')),
    embedding        VECTOR(1536),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_policies_platform ON platform_policies(platform);
CREATE INDEX idx_policies_severity ON platform_policies(severity);
