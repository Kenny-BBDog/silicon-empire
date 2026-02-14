-- Silicon-Empire: suppliers
-- 供应商库

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    contact_email    TEXT,
    products         TEXT[],
    tone_profile     TEXT,
    negotiation_log  JSONB,
    embedding        VECTOR(1536),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_suppliers_name ON suppliers(name);
