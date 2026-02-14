# 🛸 Silicon-Empire 技术架构白皮书 v4

> AI 原生一人跨国电商集团 · 落地级架构 · **已确认版**

---

## 一、框架选型：LangGraph ✅

| 维度 | LangGraph (单框架) | CrewAI + AutoGen (双框架) |
|:---|:---|:---|
| **状态图支持** | ⭐ 原生状态机设计 | ❌ CrewAI 线性，需硬凑 |
| **与项目契合** | ⭐ Red Teaming 和 Self-Healing 本质就是状态图 | ⚠️ 两套范式，需胶水代码 |
| **人工审批** | ⭐ 内置 `interrupt_before` / Checkpointer | ⚠️ CrewAI 受限，AutoGen 需自建 |
| **状态持久化** | ⭐ 内置 Checkpointer (Postgres/Redis) | ❌ 需自行实现 |
| **条件路由** | ⭐ `conditional_edges` | ⚠️ Router 功能有限 |
| **调试可观测** | ⭐ LangSmith 全链路 | ⚠️ 两套日志 |
| **依赖复杂度** | ⭐ 一套依赖 | ❌ 两套框架 + 集成层 |
| **GroupChat 能力** | ⭐ 可用子图实现多 Agent 讨论 | ⭐ AutoGen 原生支持 |

---

## 二、技术栈

| 组件 | 选型 | 备注 |
|:---|:---|:---|
| **Agent 编排** | LangGraph | 唯一框架，覆盖探索+执行双模式 |
| **LLM 网关** | OpenRouter | 统一 Key，按角色切模型 |
| **编排总线** | n8n (Self-hosted) | 飞书 ↔ Agent 桥梁 |
| **消息队列** | Redis | Agent 间通信 + 短期记忆 |
| **结构化 DB** | Supabase PostgreSQL | 决策/CRM/工具注册 |
| **向量 DB** | Supabase pgvector | RAG 知识库 |
| **RPA** | Playwright → FastAPI | 封装为微服务 |
| **人类界面** | 飞书 Lark | 三频道 |
| **可观测** | LangSmith | 全链路 trace |

### OpenRouter 模型分配

```python
MODELS = {
    "gm":       "openai/gpt-4o",               # 统筹仲裁
    "cgo":      "openai/gpt-4o",               # 增长决策
    "coo":      "openai/gpt-4o",               # 运营决策
    "cro":      "openai/gpt-4o",               # 风控决策
    "cto":      "anthropic/claude-3.5-sonnet",  # 技术/代码
    "creative": "anthropic/claude-3.5-sonnet",  # 文案
    "analysis": "google/gemini-flash-1.5",      # 海量分析(低成本)
}
```

---

## 三、组织架构

### 前台决策层 (L2 C-Suite)

| 角色 | 定位 | 目标 | Prompt 性格 |
|:---|:---|:---|:---|
| **CGO** | 激进派 | GMV 最大化 | 选品/测品/流量，忽略小风险追求规模 |
| **COO** | 务实派 | 利润率与周转率 | 成本核算/物流匹配/严谨算账 |
| **CRO** | 批判派 | 风险归零 | 平台政策/知产检测/财务红线，信任零引用规则 |
| **CTO** | 赋能派 | 工具稳定性 | 管理技术中台/解决API/RPA瓶颈，技术可行性评估 |

### 公共能力中台 (L3 Shared Platform)

| 中台 | 岗位 | 能力 |
|:---|:---|:---|
| **情报中台** | Data Hunter, Insight Analyst | 爬虫、数据清洗、趋势分析 |
| **内容中台** | Copy Master, Visual Artisan, Clip Editor | 文案、生图、视频 |
| **业务中台** | Store Operator, Cost Calculator, Inventory | RPA上架、精算、库存 |
| **关系中台** | Sourcing Liaison, Customer Success | 供应商SRM、客户CRM |
| **技术中台** | Architect, AutoGen Team (L4) | 造工具、自愈修复 |

### 能力调用方式

> 调用不是硬编码，而是 **Capability-based Request**：Agent 发出能力需求描述 → 路由层匹配最佳中台服务。

---

## 四、统一状态定义 (State Graph)

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class SiliconState(TypedDict):
    # ─── 元数据 ───
    trace_id: str                          # 全链路追踪
    mode: str                              # EXPLORATION | EXECUTION
    phase: str                             # 当前状态机阶段
    
    # ─── 意图层 ───
    strategic_intent: str                  # L0 原始目标
    intent_category: str                   # NEW_CATEGORY | PRODUCT_LAUNCH | SOURCING | TECH_FIX
    
    # ─── 提案层 ───
    proposal_buffer: list[dict]            # CGO 草案 + 修正版本历史
    
    # ─── 评审层 ───
    critique_logs: dict                    # {
                                           #   "coo": { "cost_analysis": ..., "verdict": ... },
                                           #   "cro": { "risk_report": ..., "verdict": ... },
                                           #   "cto": { "tech_feasibility": ..., "verdict": ... }
                                           # }
    
    # ─── 决策层 ───
    decision_matrix: dict                  # { "profit_pct": 35, "risk_score": 2,
                                           #   "tech_ready": True, "consensus": True }
    l0_verdict: str                        # PENDING | APPROVED | REJECTED | REVISE
    
    # ─── 执行层 ───
    execution_plan: list[dict]             # L3 中台任务分派清单
    execution_results: list[dict]          # 各中台执行结果
    artifacts: list[dict]                  # 产物（文案/图片/报告链接）
    
    # ─── 会议记录 ───
    messages: Annotated[list, add_messages] # 全量对话历史
    meeting_transcript: list[dict]          # 结构化会议纪要
    
    # ─── 系统层 ───
    checkpoint: str                        # Checkpointer 快照 ID
    error_log: dict | None                 # Self-Healing 触发时的错误信息
    iteration_count: int                   # 当前循环次数 (防无限)
```

---

## 五、双运行模式

### 模式判定

- **探索模式 (Exploration)**：L1 判定意图为 `NEW_CATEGORY` 或复杂战略 → 四人 GroupChat 自由讨论 → 涌现提案 → L0 审批
- **执行模式 (Execution)**：确定性任务 → 严格 DAG 流转 → 进入会议机制之一

---

## 六、会议机制（四位 C-Suite 全员参与）

### 会议 1：异步联席会 (Async Joint Session) — 日常审批

**流程**：CGO 提案 → COO/CRO/CTO 并行审查 → GM 汇总 → 自动判定

**自动通过条件**（全部满足才放行）：
- 利润 > 20%
- 风险 = LOW (score ≤ 2)
- 技术可行 = True
- 全员共识 = True（无 VETO）

不满足则修改（max 3次）或升级为听证会。

### 会议 2：对抗性听证会 (Adversarial Hearing) — 重大决策

**四轮回合制辩论**：

| 轮次 | 发言人 | 角色 | 必须包含 |
|:---|:---|:---|:---|
| Round 1 | CGO | 进攻方 | 市场数据、增长预测、竞品空白 |
| Round 2 | CRO | 防守方 | 逐条反驳，引用 mem_policies 政策条款 |
| Round 3 | COO | 仲裁方 | 完整 P&L 模型 |
| Round 4 | CTO | 技术方 | 实现周期、所需工具、技术风险、中台就绪度 |

→ GM 汇总 → 飞书卡片 → L0 四选一（批准/保守/否决/补充论证）

---

## 七、观察者断点 (Human-in-the-Loop)

物理层操作（RPA/发邮件/花钱）前强制 `interrupt_before` 挂起；
内部操作（爬数据/生成草稿/分析）自动放行。

---

## 八、Self-Healing 自愈闭环

L3 异常 → CTO 诊断 → 临时故障重试 / 逻辑错误 → AutoLab 生成修复代码 → 沙盒测试 → 更新 tool_registry → 恢复

---

## 九、服务器配置

| 配置项 | 推荐 |
|:---|:---|
| CPU | 4 核 |
| 内存 | 8 GB |
| 存储 | 80 GB SSD |
| 系统 | Ubuntu 22.04 LTS |
| 网络 | 国际线路 |
| 供应商 | Hetzner / DigitalOcean / Contabo (~$20-40/月) |

---

## 十、4 周开发计划

| 模块 | 天数 | 核心交付 |
|:---|:---|:---|
| M0 | 3 | 环境搭建 (Docker/Supabase/OpenRouter) |
| M1 | 3 | State + 协议 + 总线 |
| M2 | 4 | 双模式 + 两大会议 + L1/L2 |
| M3 | 4 | 数据中台 |
| M4 | 4 | 内容+业务+关系中台 |
| M5 | 3 | CTO + 自愈闭环 |
| M6 | 4 | 飞书 + n8n 全链路 |
| M7 | 3 | 强化 + 部署 |
