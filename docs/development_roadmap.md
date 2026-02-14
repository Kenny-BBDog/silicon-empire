# 📅 Silicon-Empire 开发路线图

> 4 周 · 7 模块 · 逐模块交付

---

## Module 0: 环境搭建 (Day 1-3)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| 项目初始化 (uv/Poetry) | `pyproject.toml` | ⬜ |
| Docker Compose (Redis + n8n) | `docker-compose.yml` | ⬜ |
| Supabase 建表 (6 张) | `db/migrations/*.sql` | ⬜ |
| 环境变量模板 | `.env.example` | ⬜ |
| OpenRouter 连通性测试 | `tests/test_openrouter.py` | ⬜ |

---

## Module 1: 核心骨架 (Day 4-6)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| 统一 State 定义 (SiliconState) | `src/core/state.py` | ⬜ |
| 双层协议 (Header JSON + Body MD) | `src/core/envelope.py` | ⬜ |
| 三级记忆管理 (Redis/pgvector/PG) | `src/core/memory.py` | ⬜ |
| Redis Streams 消息总线 | `src/core/bus.py` | ⬜ |
| 单元测试 | `tests/test_core.py` | ⬜ |

**✅ 里程碑**：State 创建 → 消息发送 → Redis 持久化 → 读取验证

---

## Module 2: 决策大脑 + 双模式 (Day 7-10)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| L1 GM (路由 + 仲裁 + 汇总) | `src/agents/l1_gm.py` | ⬜ |
| L2 CGO / COO / CRO / CTO | `src/agents/l2_*.py` | ⬜ |
| 5 个角色 System Prompt | `src/prompts/*.md` | ⬜ |
| 探索模式 (GroupChat SubGraph) | `src/graphs/exploration.py` | ⬜ |
| 异步联席会 (自动判定) | `src/graphs/async_session.py` | ⬜ |
| 对抗性听证会 (四轮辩论) | `src/graphs/adversarial_hearing.py` | ⬜ |
| 主路由 (模式判定) | `src/graphs/main_router.py` | ⬜ |
| CLI 审批界面 | `src/interfaces/cli.py` | ⬜ |
| 端到端测试 | `tests/test_meetings.py` | ⬜ |

**✅ 里程碑**：
- 探索模式：输入"进军宠物赛道" → 四人讨论 → 涌现提案 → CLI 审批
- 联席会：输入"上架猫玩具" → 四人并行审查 → 自动通过/驳回
- 听证会：输入"投入$10万做品牌" → 四轮辩论 → 飞书卡片格式输出

---

## Module 3: 数据中台 (Day 11-14)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| Data Hunter (Playwright 爬虫框架) | `src/platforms/data_intel/hunter.py` | ⬜ |
| Insight Analyst (数据分析) | `src/platforms/data_intel/analyst.py` | ⬜ |
| Memory Keeper (pgvector RAG) | `src/platforms/data_intel/memory_keeper.py` | ⬜ |
| Amazon/TikTok 爬虫适配器 | `src/platforms/data_intel/adapters/` | ⬜ |
| RPA FastAPI 微服务 | `src/rpa/server.py` | ⬜ |

**✅ 里程碑**：CGO 调用 Data Hunter 抓 Amazon 数据 → Analyst 分析 → 存入 pgvector

---

## Module 4: 内容 + 业务 + 关系中台 (Day 15-18)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| Copy Master (多语言文案) | `src/platforms/creative/copywriter.py` | ⬜ |
| Visual Artisan (生图) | `src/platforms/creative/visual.py` | ⬜ |
| Cost Calculator (成本精算) | `src/platforms/bizops/calculator.py` | ⬜ |
| Store Operator (Shopify API) | `src/platforms/bizops/store_operator.py` | ⬜ |
| Sourcing Liaison (供应商邮件) | `src/platforms/relationship/sourcing.py` | ⬜ |
| Customer Success (客户) | `src/platforms/relationship/customer.py` | ⬜ |
| Gmail API 集成 | `src/integrations/gmail.py` | ⬜ |

**✅ 里程碑**：完整选品流程 — 爬数据 → 生成文案+图片 → 计算成本 → 供应商询价邮件

---

## Module 5: 技术中台 + 自愈 (Day 19-21)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| L2 CTO Agent | `src/agents/l2_cto.py` (增强) | ⬜ |
| Code Sandbox (安全执行) | `src/platforms/tech_lab/sandbox.py` | ⬜ |
| AutoLab (代码生成+测试) | `src/platforms/tech_lab/autolab.py` | ⬜ |
| Self-Healing 状态图 | `src/graphs/self_heal.py` | ⬜ |
| tool_registry CRUD | `src/platforms/tech_lab/registry.py` | ⬜ |

**✅ 里程碑**：模拟爬虫报错 → CTO 诊断 → AutoLab 自动修复 → 沙盒测试 → 热更新

---

## Module 6: 飞书 + n8n 全链路 (Day 22-25)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| 飞书 Bot 配置文档 | `docs/feishu_setup.md` | ⬜ |
| 三频道推送引擎 | `src/integrations/feishu.py` | ⬜ |
| 审批交互卡片 | `src/integrations/feishu_cards.py` | ⬜ |
| n8n Webhook 工作流 | `n8n/workflows/*.json` | ⬜ |
| 飞书回调 → LangGraph resume | `src/interfaces/feishu_handler.py` | ⬜ |

**✅ 里程碑**：飞书收到审批卡片 → 点批准 → Agent 自动执行后续流程

---

## Module 7: 强化 + 部署 (Day 26-28)

| 任务 | 产出文件 | 状态 |
|:---|:---|:---|
| 全链路 trace_id | 贯穿所有模块 | ⬜ |
| Token 用量监控 | `src/core/cost_tracker.py` | ⬜ |
| 速率限制 + 权限隔离 | `src/core/guards.py` | ⬜ |
| 生产 Docker Compose | `docker-compose.prod.yml` | ⬜ |
| 部署脚本 | `scripts/deploy.sh` | ⬜ |
| 运维手册 | `docs/ops_manual.md` | ⬜ |

**✅ 里程碑**：生产环境上线，全功能可用
