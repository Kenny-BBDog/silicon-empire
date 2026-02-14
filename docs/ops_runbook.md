# 🛸 Silicon-Empire 运维手册

> AI 原生一人跨国电商集团 · 开发运维全档

---

## 一、基础设施

| 资源 | 地址 | 用途 |
|:---|:---|:---|
| **生产服务器** | `43.167.223.116` | 部署所有服务 |
| **API 端口** | `:8000` | Silicon-Empire 主 API |
| **n8n 端口** | `:5678` | 可视化工作流编排 |
| **Redis 端口** | `:6379` | 缓存 + 消息总线 |
| **飞书事件** | 长连接 (WebSocket) | 无需端口，SDK 主动连接飞书 |

---

## 二、飞书机器人凭证

| 角色 | App ID | App Secret | 群内显示名 |
|:---|:---|:---|:---|
| 🎖️ GM (总经理) | `cli_a90cfc15eef8dbdf` | `gVf7ZVqzxOC58PpZZlrAndYAP7zTRxHK` | 总经理 |
| 🏴‍☠️ CGO (增长官) | `cli_a91aad6e0078dcef` | `YKqc1nOI4fTnt2do9DuFOfQFrog0ixRa` | 首席增长官 |
| 🛡️ CRO (风控官) | `cli_a91aadb0cf789cc5` | `b0J3O1OnUJc4y5hcUjqg2eOpVNh3fPRE` | 首席风控官 |
| 📦 COO (运营官) | `cli_a91aae1122389cb1` | `vtfmBZi4c2zxznsyf1zxlg3Y54qDaWxV` | 首席运营官 |
| 🔧 CTO (技术官) | `cli_a91aae3a47781cc1` | `XfCMo9kYflNE5zxHcJhmagDe6CmA8e4E` | 首席技术官 |
| ⚙️ System (系统) | `cli_a91aae7138b89cca` | `TaaK26kGbD5bngiOEaKhibpVkOTojrZS` | 系统助手 |

### 飞书群聊

| 群名 | Chat ID | 用途 |
|:---|:---|:---|
| 燧石数科 | `oc_0f555cce0141c81028ddb85c6977bd4c` | 决策 + 执行 + 告警 (统一) |

### 飞书后台配置

1. **每个机器人都需要开启的权限**:
   - `im:message:send_as_bot` — 以机器人身份发消息
   - `im:message:receive` — 接收消息事件
   - `im:chat:readonly` — 读取群列表
   - `im:message` — 发送消息

2. **事件订阅** (每个机器人都要配):
   - 订阅方式 → 选择 **「长连接」**
   - 添加事件: `im.message.receive_v1`
   - **无需填 URL**，SDK 主动连接飞书服务器

---

## 三、项目结构

```
silicon-empire/
├── src/
│   ├── main.py                  # FastAPI 入口 (8 API routes)
│   ├── agents/                  # L1/L2 决策层
│   │   ├── base.py              # 4 层 BaseAgent (个人记忆 + MCP)
│   │   ├── gm.py                # L1 总经理
│   │   ├── cgo.py               # L2 首席增长官
│   │   ├── cro.py               # L2 首席风控官
│   │   ├── coo.py               # L2 首席运营官
│   │   └── cto.py               # L2 首席技术官
│   │
│   ├── core/                    # 核心引擎
│   │   ├── state.py             # SiliconState 状态机
│   │   ├── envelope.py          # JSON+MD 通信信封
│   │   ├── memory.py            # Redis + Supabase 记忆
│   │   ├── personal_memory.py   # 个人记忆 (大脑/情绪/印象)
│   │   ├── bus.py               # Redis Streams 消息总线
│   │   ├── cost_tracker.py      # Token 成本追踪
│   │   └── guards.py            # 安全守卫 (审批/权限)
│   │
│   ├── graphs/                  # LangGraph 状态图
│   │   ├── exploration.py       # 探索模式 (选品调研)
│   │   ├── async_session.py     # 联席会
│   │   ├── adversarial_hearing.py # 听证会 (Red Teaming)
│   │   ├── main_router.py       # 模式路由
│   │   ├── self_heal.py         # 自愈闭环 (CTO→AutoLab→沙盒)
│   │   └── holiday_chat.py      # 放假模式 (自由讨论)
│   │
│   ├── platforms/               # L3/L4 中台层
│   │   ├── base_worker.py       # L3 基类
│   │   ├── data_intel/          # 情报中台
│   │   │   ├── hunter.py        # 数据猎手 (爬虫)
│   │   │   ├── analyst.py       # 洞察分析师
│   │   │   ├── rag_pipeline.py  # RAG 引擎
│   │   │   └── graph.py         # 情报流水线
│   │   ├── creative/            # 内容中台
│   │   │   ├── copy_master.py   # 文案大师
│   │   │   ├── visual_artisan.py # 视觉工匠
│   │   │   └── clip_editor.py   # 短视频编辑
│   │   ├── bizops/              # 业务中台
│   │   │   ├── store_operator.py # 店铺运营
│   │   │   └── cost_calculator.py # 成本精算
│   │   ├── relationship/        # 关系中台
│   │   │   ├── sourcing_liaison.py # 采购联络
│   │   │   └── customer_success.py # 客户成功
│   │   └── tech_lab/            # 技术中台
│   │       ├── auto_lab.py      # L4 自动修复
│   │       ├── sandbox.py       # 沙盒执行器
│   │       └── architect.py     # 系统架构师
│   │
│   ├── integrations/            # 外部集成
│   │   ├── feishu_client.py     # 飞书 6-Bot 客户端
│   │   ├── feishu_webhook.py    # 飞书 Webhook 服务
│   │   └── n8n_bridge.py        # n8n 编排桥
│   │
│   ├── mcp_servers/             # MCP 工具服务 (7 个)
│   │   ├── supabase_server.py   # 数据库 (12 tools)
│   │   ├── playwright_server.py # 浏览器 (5 tools)
│   │   ├── feishu_server.py     # 飞书 (4 tools)
│   │   ├── gmail_server.py      # 邮件 (4 tools)
│   │   ├── shopify_server.py    # 电商 (4 tools)
│   │   ├── filesystem_server.py # 文件 (3 tools)
│   │   └── redis_server.py      # Redis (3 tools)
│   │
│   ├── prompts/                 # Agent 人设 Prompt
│   ├── skills/                  # 可热加载技能
│   └── config/                  # 配置
│
├── db/migrations/               # 数据库迁移
│   ├── 001_products.sql
│   ├── 002_suppliers.sql
│   ├── 003_policies.sql
│   ├── 004_decisions.sql
│   ├── 005_tools.sql
│   ├── 006_interactions.sql
│   ├── 007_agent_memories.sql
│   └── 008_vector_search_rpc.sql
│
├── docs/                        # 文档
│   ├── architecture.md          # 技术架构白皮书
│   └── skills_and_mcp.md        # 技能 + MCP 设计
│
├── .env                         # 环境变量 (含真实凭证)
├── .env.example                 # 环境变量模板
├── pyproject.toml               # Python 依赖
├── Dockerfile                   # 生产镜像
├── docker-compose.yml           # 开发环境
├── docker-compose.prod.yml      # 生产环境 (4 服务)
└── mcp_config.json              # MCP Server 注册表
```

---

## 四、API Reference

启动后访问 `http://43.167.223.116:8000`

| 方法 | 路径 | 说明 | 入参 |
|:---|:---|:---|:---|
| POST | `/api/explore` | 探索选品 | `{topic, depth}` |
| POST | `/api/meeting` | 联席会 | `{proposal, context, mode}` |
| POST | `/api/hearing` | 听证会 | `{proposal, objections[]}` |
| POST | `/api/holiday` | 放假闲聊 | `{topic, max_rounds}` |
| POST | `/api/data-intel` | 情报采集 | `{task_type, keywords[], platform}` |
| POST | `/api/self-heal` | 自愈修复 | `{tool_name, error_message}` |
| POST | `/api/health-check` | 系统巡检 | 无 |
| POST | `/api/feishu/notify` | 飞书消息 | `{role, channel, content, title}` |
| GET | `/health` | 健康检查 | 无 |

---

## 五、飞书群指令

在飞书群 @任意机器人 发送:

| 指令 | 效果 |
|:---|:---|
| `/选品 宠物智能喂食器` | 触发探索模式，全员调研 |
| `/开会` | 召集联席会 |
| `/巡检` | 系统全面检查 |
| `/放假 聊聊 AI 未来` | 放假模式自由讨论 |

---

## 六、部署操作

### 首次部署

```bash
# 1. 登录服务器
ssh root@43.167.223.116

# 2. 克隆项目
git clone <repo_url> /opt/silicon-empire
cd /opt/silicon-empire

# 3. 复制环境变量
cp .env.example .env
# 编辑 .env 填入真实凭证

# 4. 启动
docker-compose -f docker-compose.prod.yml up -d

# 5. 验证
curl http://localhost:8000/health
```

### 日常运维

```bash
# 查看日志
docker logs silicon-empire-api -f --tail 100

# 重启服务
docker-compose -f docker-compose.prod.yml restart silicon-empire

# 更新代码
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# 查看所有服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 防火墙端口

```bash
# 开放必要端口
ufw allow 8000/tcp   # API
ufw allow 5678/tcp   # n8n (可选, 仅调试时开)
# 飞书用长连接模式，无需开放端口
# Redis 6379 不要对外开放
```

---

## 七、架构层级

```
L0  人类 (你) ────── 飞书群 @机器人 / API 调用
      │
L1  GM (总经理) ──── 最终裁决、模式路由
      │
L2  CGO / CRO / COO / CTO ─── 四大首席、联席会、听证会
      │
L3  中台工人 ──────── 对应能力说明:
      │  情报: Hunter (爬虫) + Analyst (分析)
      │  内容: Copy Master + Visual Artisan + Clip Editor
      │  业务: Store Operator + Cost Calculator
      │  关系: Sourcing Liaison + Customer Success
      │  技术: Architect (巡检)
      │
L4  AutoLab ─────── 自动代码修复 (最底层)
```

---

## 八、依赖服务清单

| 服务 | 状态 | 说明 |
|:---|:---|:---|
| OpenRouter | ✅ 已配置 | LLM 网关 (已填入 API Key) |
| PostgreSQL + pgvector | ✅ Docker 自带 | 本地数据库, 替代 Supabase, 零延迟 |
| Redis | ✅ Docker 自带 | 缓存 + 消息总线 |
| n8n | ✅ Docker 自带 | 定时任务 + 工作流 |
| Shopify | ⬜ 可选 | 填入 store URL + Admin Token |
| Gmail | ⬜ 可选 | OAuth2 配置 |

---

## 九、MCP 工具总览 (35 tools)

| Server | Tools 数 | 核心工具 |
|:---|:---|:---|
| supabase | 12 | query/insert products, search vectors, read/write decisions |
| playwright | 5 | scrape amazon, tiktok trending, image originality, shopify RPA |
| feishu | 4 | send_agent_message, broadcast_meeting, send_approval, send_alert |
| gmail | 4 | send_email, read_inbox, search, parse_attachment |
| shopify | 4 | create_product, update_inventory, get_orders, update_price |
| filesystem | 3 | read_file, write_file, list_directory |
| redis | 3 | publish_message, read_context, write_context |

---

## 十、数据库表 (8 张)

| 表 | 迁移文件 | 说明 |
|:---|:---|:---|
| products | 001 | 产品库 (含 embedding) |
| suppliers | 002 | 供应商库 |
| platform_policies | 003 | 合规政策库 |
| strategic_decisions | 004 | 决策记录 |
| tool_registry | 005 | 工具注册表 |
| interactions | 006 | CRM 交互记录 |
| agent_memories | 007 | Agent 个人长期记忆 |
| *(RPC functions)* | 008 | 4 个语义搜索 RPC + HNSW 索引 |

---

*文档版本: v1.2 | 更新日期: 2026-02-14 | 飞书 6-Bot ✅ | 本地 PostgreSQL ✅*
