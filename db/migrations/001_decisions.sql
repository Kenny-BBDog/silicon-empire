-- Silicon-Empire: strategic_decisions
-- 决策记录表

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS strategic_decisions (
    decision_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id         UUID NOT NULL,
    mode             VARCHAR(20),
    meeting_type     VARCHAR(30),
    proposal_summary TEXT NOT NULL,
    cgo_vote         BOOLEAN,
    coo_vote         BOOLEAN,
    cro_vote         BOOLEAN,
    cto_vote         BOOLEAN,
    l0_verdict       VARCHAR(20) CHECK (l0_verdict IN ('APPROVED','REJECTED','REVISE','PENDING','AUTO_APPROVED')),
    decision_matrix  JSONB,
    meeting_transcript JSONB,
    artifacts_link   JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_trace ON strategic_decisions(trace_id);
CREATE INDEX idx_decisions_verdict ON strategic_decisions(l0_verdict);
CREATE INDEX idx_decisions_created ON strategic_decisions(created_at DESC);
