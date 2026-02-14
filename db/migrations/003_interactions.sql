-- Silicon-Empire: interactions
-- CRM 交互记录 (关系中台)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS interactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_type     VARCHAR(20),
    contact_name     TEXT NOT NULL,
    channel          VARCHAR(20),
    direction        VARCHAR(10),
    summary          TEXT,
    embedding        VECTOR(1536),
    raw_content      TEXT,
    attachments      JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interactions_contact ON interactions(contact_type, contact_name);
CREATE INDEX idx_interactions_created ON interactions(created_at DESC);
