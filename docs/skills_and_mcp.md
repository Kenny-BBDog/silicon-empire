# 🔌 Skills + MCP 能力增强设计

> 把 L2 从"只有人设 Prompt"升级为"拥有可执行技能 + 外部工具连接"的全能首席

---

## 一、概念：三层能力模型

当前 Agent 只有 `Prompt`（人设），相当于一个只有性格但没有手的人。加入 **Skill** 和 **MCP** 后：

| 层级 | 类比 | 内容 | 示例 |
|:---|:---|:---|:---|
| **Prompt** | 性格/价值观 | 角色定位、输出格式、决策原则 | "你是激进的CGO" |
| **Skill** | 工作经验/SOP | 可复用的多步骤工作流 | "选品调研六步法" |
| **MCP** | 工具/手脚 | 实时连接外部系统的标准接口 | "查 Supabase 数据库" |

```
┌─────────────────────────────────┐
│          L2 Agent               │
│  ┌───────────────────────────┐  │
│  │   🧠 Prompt (性格/原则)   │  │
│  ├───────────────────────────┤  │
│  │   📚 Skills (工作流 SOP)  │  │ ← 可执行的多步骤技能
│  ├───────────────────────────┤  │
│  │   🔌 MCP Tools (外部连接) │  │ ← 实时数据/操作能力
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## 二、Skill 设计

### 2.1 什么是 Skill？

Skill 是**结构化的工作流程**，定义了一个具体任务"怎么做"的步骤序列。与 Prompt 不同，Skill 不是自然语言描述，而是**可解析、可执行的 YAML + Python 模块**。

### 2.2 Skill 文件结构

```
src/skills/
├── cgo/                           # CGO 专属技能
│   ├── product_research/          # 技能：选品调研
│   │   ├── SKILL.yaml             # 技能定义 (元数据 + 步骤)
│   │   ├── steps.py               # 步骤实现 (Python)
│   │   └── templates/             # 输出模板
│   │       └── research_report.md
│   ├── trend_hunting/             # 技能：趋势捕猎
│   │   ├── SKILL.yaml
│   │   └── steps.py
│   └── campaign_planning/         # 技能：大促策划
│       ├── SKILL.yaml
│       └── steps.py
│
├── coo/                           # COO 专属技能
│   ├── cost_analysis/             # 技能：成本精算
│   ├── pnl_modeling/              # 技能：P&L 建模
│   └── inventory_planning/        # 技能：库存规划
│
├── cro/                           # CRO 专属技能
│   ├── compliance_audit/          # 技能：合规审计
│   ├── ip_detection/              # 技能：侵权检测
│   └── risk_scoring/              # 技能：风险评分
│
├── cto/                           # CTO 专属技能
│   ├── tool_diagnosis/            # 技能：工具诊断
│   ├── code_review/               # 技能：代码审查
│   └── infra_health_check/        # 技能：基础设施巡检
│
└── shared/                        # 全员共享技能
    ├── data_query/                # 查询中台数据
    └── meeting_protocol/          # 会议发言规范
```

### 2.3 SKILL.yaml 示例

```yaml
# src/skills/cgo/product_research/SKILL.yaml
name: product_research
display_name: "选品调研六步法"
owner: CGO
version: "1.0"
description: |
  对目标品类进行系统性调研，产出选品报告。
  覆盖市场规模、竞品分析、差评痛点、利润空间、合规风险。

triggers:
  - intent: "PRODUCT_LAUNCH"
  - intent: "NEW_CATEGORY"
  - keyword: ["选品", "调研", "找产品"]

requires_mcp:
  - supabase    # 查询产品库/历史数据
  - playwright  # 爬取实时数据
  - openrouter  # LLM 分析

steps:
  - id: define_scope
    name: "界定范围"
    action: llm_think
    prompt: |
      基于用户意图，确定：
      1. 目标品类关键词 (3-5个)
      2. 目标平台 (Amazon/TikTok/Shopify)
      3. 目标市场 (US/EU/Global)
    output: scope_definition

  - id: gather_data
    name: "数据采集"
    action: call_mcp
    server: playwright
    tool: scrape_category
    params:
      keywords: "{{scope_definition.keywords}}"
      platform: "{{scope_definition.platform}}"
    output: raw_data

  - id: historical_check
    name: "历史数据比对"
    action: call_mcp
    server: supabase
    tool: query_products
    params:
      category: "{{scope_definition.category}}"
    output: historical_data

  - id: analyze
    name: "深度分析"
    action: llm_think
    prompt: |
      基于采集数据和历史数据，分析：
      - 市场容量和增长趋势
      - 竞品价格区间
      - 差评痛点 TOP 5
      - 差异化机会
    context: [raw_data, historical_data]
    output: analysis

  - id: cost_estimate
    name: "成本预估"
    action: delegate
    to: COO
    skill: cost_analysis
    params:
      product_type: "{{scope_definition.category}}"
      target_price: "{{analysis.suggested_price}}"
    output: cost_report

  - id: generate_report
    name: "生成报告"
    action: llm_think
    template: templates/research_report.md
    context: [scope_definition, analysis, cost_report]
    output: final_report
    write_to: proposal_buffer
```

### 2.4 四位首席的 Skill 清单

| 角色 | Skill 名称 | 触发条件 | 调用的 MCP |
|:---|:---|:---|:---|
| **CGO** | `product_research` 选品调研 | PRODUCT_LAUNCH / NEW_CATEGORY | playwright, supabase |
| **CGO** | `trend_hunting` 趋势捕猎 | 周期性 / "什么在火" | playwright, openrouter |
| **CGO** | `campaign_planning` 大促策划 | "大促" / "黑五" / "万圣节" | supabase, openrouter |
| **COO** | `cost_analysis` 成本精算 | 被其他 Agent delegate 调用 | supabase |
| **COO** | `pnl_modeling` P&L 建模 | 新品评估 / 季度复盘 | supabase |
| **COO** | `inventory_planning` 库存规划 | 备货季 / 库存预警触发 | supabase, shopify_mcp |
| **CRO** | `compliance_audit` 合规审计 | 任何新品/新文案提交时 | supabase (mem_policies) |
| **CRO** | `ip_detection` 侵权检测 | 新品图片/设计提交时 | playwright (图搜), supabase |
| **CRO** | `risk_scoring` 风险评分 | 联席会/听证会中 | supabase, openrouter |
| **CTO** | `tool_diagnosis` 工具诊断 | L3 报错时 | supabase (tool_registry) |
| **CTO** | `code_review` 代码审查 | AutoLab 产出新代码时 | filesystem, sandbox |
| **CTO** | `infra_health_check` 巡检 | 周期性 / 手动触发 | supabase, redis_mcp |

---

## 三、MCP 服务设计

### 3.1 什么是 MCP？

MCP (Model Context Protocol) 是 Anthropic 发起的**开放标准**，为 AI Agent 提供统一的外部工具/数据接口。它就像"AI 的 USB-C 接口"——所有外部系统用同一种协议接入，Agent 不需要为每个 API 写专门的适配代码。

### 3.2 LangGraph 接入方式

```python
# 通过 langchain-mcp-adapters 库，LangGraph 原生消费 MCP 工具
from langchain_mcp_adapters.client import MultiServerMCPClient

async with MultiServerMCPClient({
    "supabase": {"command": "python", "args": ["mcp_servers/supabase_server.py"]},
    "playwright": {"command": "python", "args": ["mcp_servers/playwright_server.py"]},
    "gmail": {"command": "python", "args": ["mcp_servers/gmail_server.py"]},
}) as client:
    tools = client.get_tools()  # 所有 MCP 工具自动转为 LangGraph Tools
    agent = create_react_agent(llm, tools)
```

### 3.3 MCP Server 清单

```
src/mcp_servers/
├── supabase_server.py      # 数据库读写 (products/suppliers/policies/decisions)
├── playwright_server.py    # 浏览器自动化 (爬虫/RPA)
├── gmail_server.py         # 邮件收发
├── redis_server.py         # 缓存/消息队列操作
├── filesystem_server.py    # 代码文件读写 (CTO 专用)
├── shopify_server.py       # Shopify API 操作
└── feishu_server.py        # 飞书消息/卡片推送
```

### 3.4 各 MCP Server 提供的 Tools

#### `supabase_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `query_products` | 按条件查询产品库 | CGO, CRO |
| `search_products_vector` | 语义搜索产品 (pgvector) | CGO |
| `query_suppliers` | 查询供应商 | COO, 关系中台 |
| `search_supplier_memory` | 搜索供应商沟通记忆 | 关系中台 |
| `query_policies` | 按平台/类别查规则 | CRO |
| `search_policies_vector` | 语义搜索合规政策 | CRO |
| `read_decisions` | 查询历史决策 | GM, 全员 |
| `write_decision` | 写入决策记录 | GM |
| `read_tool_registry` | 查询工具状态 | CTO |
| `update_tool_registry` | 更新工具注册 | CTO |
| `log_interaction` | 记录 CRM 交互 | 关系中台 |
| `insert_product` | 写入新产品 | 情报中台 |

#### `playwright_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `scrape_amazon_category` | 抓取 Amazon 品类 Top N | CGO, 情报中台 |
| `scrape_tiktok_trending` | 抓取 TikTok 热门商品 | CGO |
| `check_image_originality` | 反向图搜 (侵权检测) | CRO |
| `operate_shopify_admin` | Shopify 后台 RPA 操作 | 业务中台 |
| `screenshot_page` | 截图取证 | CRO |

#### `gmail_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `send_email` | 发送邮件 (需 L0 审批) | 关系中台 |
| `read_inbox` | 读取收件箱 | 关系中台 |
| `parse_attachment` | 解析 PDF/Excel 附件 | 关系中台, 情报中台 |
| `search_emails` | 搜索历史邮件 | 关系中台 |

#### `redis_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `publish_message` | 发布到消息频道 | 全员 |
| `read_context` | 读取当前会话上下文 | GM |
| `write_context` | 写入临时思维链 | 全员 |

#### `filesystem_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `read_file` | 读取代码/配置文件 | CTO |
| `write_file` | 写入文件 (沙盒内) | CTO, AutoLab |
| `list_directory` | 列出目录内容 | CTO |

#### `shopify_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `create_product` | 创建商品 | 业务中台 |
| `update_inventory` | 更新库存 | 业务中台, COO |
| `get_orders` | 获取订单 | COO |
| `update_price` | 修改价格 | 业务中台 |

#### `feishu_server.py`

| Tool Name | 描述 | 主要使用者 |
|:---|:---|:---|
| `send_card` | 发送交互卡片 | GM |
| `send_message` | 发送 Markdown 消息 | 全员 |
| `send_alert` | 发送紧急通知 | CRO, CTO |

### 3.5 L2 首席的 MCP 权限矩阵

| MCP Server | CGO | COO | CRO | CTO | GM |
|:---|:---|:---|:---|:---|:---|
| `supabase` | 读 products/suppliers | 读 all, 写 decisions | 读 policies/products | 读写 tool_registry | 读写 decisions |
| `playwright` | 调用爬虫 | ❌ | 调用检测 | 调用调试 | ❌ |
| `gmail` | ❌ | ❌ | ❌ | ❌ | ❌ (经关系中台) |
| `redis` | 读写 | 读写 | 读写 | 读写 | 读写 |
| `filesystem` | ❌ | ❌ | ❌ | ✅ 完全权限 | ❌ |
| `shopify` | ❌ | 读 orders | ❌ | ❌ | ❌ (经业务中台) |
| `feishu` | ❌ | ❌ | 发 alert | 发 alert | 发 card/message |

---

## 四、集成到 LangGraph 的方式

### Agent 初始化

```python
# src/agents/l2_cgo.py
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.skills.loader import load_skills

class CGOAgent:
    def __init__(self):
        # 1. 加载 Prompt (性格)
        self.prompt = load_prompt("src/prompts/cgo.md")
        
        # 2. 加载 Skills (工作流)
        self.skills = load_skills("src/skills/cgo/")
        # → { "product_research": Skill(...), "trend_hunting": Skill(...) }
        
        # 3. 连接 MCP (工具)
        self.mcp = MultiServerMCPClient({
            "supabase": {...},   # 读 products, suppliers
            "playwright": {...},  # 爬虫
        })
    
    async def invoke(self, state: SiliconState):
        # 4. 根据意图匹配 Skill
        skill = self.match_skill(state["intent_category"])
        
        if skill:
            # 按 Skill 步骤执行
            return await skill.execute(state, self.mcp)
        else:
            # 无匹配 Skill → 自由推理
            tools = await self.mcp.get_tools()
            return await self.think(state, tools)
```

### Skill 执行引擎

```python
# src/skills/loader.py
class SkillExecutor:
    async def execute(self, skill: Skill, state: SiliconState, mcp: MCPClient):
        context = {}
        
        for step in skill.steps:
            if step.action == "llm_think":
                result = await self.llm_think(step, context)
            elif step.action == "call_mcp":
                result = await mcp.call_tool(step.server, step.tool, step.params)
            elif step.action == "delegate":
                result = await self.delegate_to_agent(step.to, step.skill, step.params)
            
            context[step.output] = result
        
        return context[skill.steps[-1].output]
```

---

## 五、升级后的目录结构（新增部分）

```diff
 e:\燧石数科\silicon-empire\
 └── src/
+    ├── skills/                      # 🆕 技能工作流
+    │   ├── loader.py                # Skill 解析器 + 执行引擎
+    │   ├── cgo/
+    │   │   ├── product_research/
+    │   │   │   ├── SKILL.yaml
+    │   │   │   ├── steps.py
+    │   │   │   └── templates/
+    │   │   ├── trend_hunting/
+    │   │   └── campaign_planning/
+    │   ├── coo/
+    │   │   ├── cost_analysis/
+    │   │   ├── pnl_modeling/
+    │   │   └── inventory_planning/
+    │   ├── cro/
+    │   │   ├── compliance_audit/
+    │   │   ├── ip_detection/
+    │   │   └── risk_scoring/
+    │   ├── cto/
+    │   │   ├── tool_diagnosis/
+    │   │   ├── code_review/
+    │   │   └── infra_health_check/
+    │   └── shared/
+    │       ├── data_query/
+    │       └── meeting_protocol/
+    │
+    ├── mcp_servers/                  # 🆕 MCP 服务端
+    │   ├── supabase_server.py        # 数据库 (12 tools)
+    │   ├── playwright_server.py      # 浏览器 (5 tools)
+    │   ├── gmail_server.py           # 邮件 (4 tools)
+    │   ├── redis_server.py           # 缓存 (3 tools)
+    │   ├── filesystem_server.py      # 文件 (3 tools)
+    │   ├── shopify_server.py         # 电商 (4 tools)
+    │   └── feishu_server.py          # 飞书 (3 tools)
     │
     ├── agents/                      # (已有, 增强)
     ├── prompts/                     # (已有, 保留为性格层)
     └── ...
```

---

## 六、对开发计划的影响

| 原模块 | 变化 | 新增工作量 |
|:---|:---|:---|
| **M1 核心骨架** | +Skill 加载器 + MCP 客户端初始化 | +1 天 |
| **M2 决策大脑** | L2 Agent 从纯 Prompt → Prompt+Skill+MCP | +1 天 |
| **M3 数据中台** | 拆成 `playwright_server.py` + `supabase_server.py` (MCP 化) | 复杂度不变，结构更清晰 |
| **M4 中台** | 拆成各 MCP Server | 同上 |
| **新增** | 编写 12 个 SKILL.yaml + steps.py | +2 天 |

> 总计增加约 **4 天**，4 周计划仍可覆盖。
