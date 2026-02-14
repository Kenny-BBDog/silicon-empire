-- Silicon-Empire: products
-- 产品库

CREATE TABLE IF NOT EXISTS products (
    product_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT NOT NULL,
    category         TEXT,
    source_platform  TEXT,
    price_range      JSONB,
    selling_points   TEXT[],
    risk_flags       TEXT[],
    embedding        VECTOR(1536),
    raw_data         JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_platform ON products(source_platform);
CREATE INDEX idx_products_created ON products(created_at DESC);
