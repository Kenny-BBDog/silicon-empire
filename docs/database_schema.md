# 🗄️ 数据库 Schema 设计

> Supabase PostgreSQL + pgvector

---

## 结构化表 (6 张)

### 001: strategic_decisions — 决策记录

```sql
CREATE TABLE strategic_decisions (
    decision_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id         UUID NOT NULL,
    mode             VARCHAR(20),  -- EXPLORATION / EXECUTION
    meeting_type     VARCHAR(30),  -- ASYNC_JOINT / ADVERSARIAL_HEARING
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
```

### 002: tool_registry — 工具注册 (CTO 管理)

```sql
CREATE TABLE tool_registry (
    tool_name        VARCHAR(100) PRIMARY KEY,
    function_schema  JSONB NOT NULL,
    code_path        TEXT NOT NULL,
    status           VARCHAR(20) CHECK (status IN ('ACTIVE','DEPRECATED','BROKEN')),
    version          INTEGER DEFAULT 1,
    last_error_log   TEXT,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### 003: interactions — CRM 交互 (关系中台)

```sql
CREATE TABLE interactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_type     VARCHAR(20),  -- SUPPLIER / CUSTOMER / KOL
    contact_name     TEXT NOT NULL,
    channel          VARCHAR(20),  -- email / dm / phone
    direction        VARCHAR(10),  -- inbound / outbound
    summary          TEXT,
    embedding        VECTOR(1536),
    raw_content      TEXT,
    attachments      JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### 004: products — 产品库

```sql
CREATE TABLE products (
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
```

### 005: suppliers — 供应商库

```sql
CREATE TABLE suppliers (
    supplier_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    contact_email    TEXT,
    products         TEXT[],
    tone_profile     TEXT,         -- 商务正式 / 轻松友好
    negotiation_log  JSONB,
    embedding        VECTOR(1536),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### 006: platform_policies — 平台规则

```sql
CREATE TABLE platform_policies (
    policy_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform         TEXT NOT NULL,  -- Amazon, TikTok, Shopify
    category         TEXT,
    rule_text        TEXT NOT NULL,
    severity         VARCHAR(10) CHECK (severity IN ('BAN','WARNING','INFO')),
    embedding        VECTOR(1536),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 向量集合 (pgvector)

| 集合 | 对应表 | 内容 | 主要使用者 |
|:---|:---|:---|:---|
| `mem_products` | products.embedding | 产品卖点/差评 | CGO 选品, CRO 查侵权 |
| `mem_suppliers` | suppliers.embedding + interactions.embedding | 供应商沟通记忆 | 关系中台 |
| `mem_policies` | platform_policies.embedding | 合规规则 | CRO 风控引用 |
| `mem_sop` | (独立集合) | 历史成功流程/会议纪要 | 全员经验复用 |
