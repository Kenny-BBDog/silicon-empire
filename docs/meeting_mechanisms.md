# 🏛️ 会议机制详细设计

---

## 一、双运行模式

### 模式判定

L1 GM 解析 L0 意图后，根据 `intent_category` 选择模式：

| 意图类型 | 模式 | 示例 |
|:---|:---|:---|
| `NEW_CATEGORY` | 🔮 探索模式 | "进军宠物赛道" |
| `COMPLEX_STRATEGY` | 🔮 探索模式 | "要不要做品牌化" |
| `PRODUCT_LAUNCH` | ⚡ 执行模式 | "上架这款猫玩具" |
| `SOURCING` | ⚡ 执行模式 | "找供应商询价" |
| `TECH_FIX` | ⚡ 执行模式 (自愈) | "爬虫挂了" |

---

## 二、探索模式 (Exploration) — 发散思维

### 触发条件
L1 判定意图为 `NEW_CATEGORY` 或 `COMPLEX_STRATEGY`

### 运行逻辑
四位 C-Suite 进入 LangGraph SubGraph 模拟 GroupChat：

1. **CGO** 抛出机会洞察："我发现宠物智能玩具赛道有巨大空白..."
2. **CRO** 质疑风险："但宠物电子产品的退货率高达 15%，平台政策规定..."
3. **COO** 补充数据："从供应链角度看，深圳有成熟的宠物用品产业链..."
4. **CTO** 评估技术："TikTok Shop 上架 API 已就绪，但亚马逊需要 ASIN 匹配工具..."
5. **GM** 判定收敛：是否形成可提交的提案？

### 收敛条件
- 四方都至少发言 1 次
- GM 检测到核心分歧已明确
- 最多 5 轮，超出则 GM 强制汇总

### 输出
写入 `proposal_buffer` → 推送飞书 → L0 审批

---

## 三、执行模式 — 会议机制 1：异步联席会

### 适用场景
日常业务审批（上架、调价、补货等），L0 不需要介入

### 流程

```
CGO 生成提案 (调用中台)
    ↓
写入 proposal_buffer
    ↓
┌─────────────────┐
│  并行审查        │
│                 │
│  COO: 成本核算   │ → critique_logs.coo
│  CRO: 合规审查   │ → critique_logs.cro
│  CTO: 技术评估   │ → critique_logs.cto
│                 │
└─────────────────┘
    ↓
GM 汇总 → decision_matrix
    ↓
自动判定
    ↓
┌──────────────────────────────┐
│ 利润 > 20%      ✅/❌        │
│ 风险 ≤ 2 (LOW)  ✅/❌        │
│ 技术可行        ✅/❌        │
│ 全员共识        ✅/❌        │
└──────────────────────────────┘
    ↓
全 ✅ → AUTO_APPROVE → L3 执行
任一 ❌ → REVISE (max 3) 或 ESCALATE → 听证会
```

### 四位审查维度

| 角色 | 审查内容 | 数据来源 |
|:---|:---|:---|
| **COO** | 成本结构、利润率、物流方案、盈亏平衡点 | 业务中台·Cost Calculator |
| **CRO** | 平台政策合规、知产风险、违禁词检测 | 情报中台·数据检索 + mem_policies |
| **CTO** | API 就绪度、工具可用性、新工具开发需求 | 技术中台·tool_registry |
| **GM** | 综合汇总，计算 decision_matrix | 上述三方输出 |

### 自动判定代码

```python
def auto_judge(state: SiliconState) -> str:
    dm = state["decision_matrix"]
    
    if (dm["profit_pct"] > 20 
        and dm["risk_score"] <= 2
        and dm["tech_ready"] == True
        and dm["consensus"] == True):
        return "auto_approve"
    
    critiques = state["critique_logs"]
    vetoes = [k for k, v in critiques.items() if v.get("verdict") == "VETO"]
    if len(vetoes) >= 2:
        return "escalate"
    
    if state["iteration_count"] >= 3:
        return "escalate"
    
    return "revise"
```

---

## 四、执行模式 — 会议机制 2：对抗性听证会

### 适用场景
新赛道、大额投入（> $X）、高风险决策、联席会升级

### 流程：四轮回合制辩论

| 轮次 | 发言人 | 角色定位 | 必须包含 |
|:---|:---|:---|:---|
| **Round 1** | CGO (进攻方) | 机会利好报告 | 市场数据、增长预测、竞品空白、差异化策略 |
| **Round 2** | CRO (防守方) | 逐条反驳 CGO | **必须引用 `mem_policies` 具体条款**，封号案例 |
| **Round 3** | COO (仲裁方) | 基于双方论点算账 | 完整 P&L、盈亏平衡、资金占用、回本周期 |
| **Round 4** | CTO (技术方) | 技术可行性裁定 | 实现周期、所需工具、技术风险、中台就绪度 |

### GM 汇总 → 飞书决策卡片

```
┌──────────────────────────────────────┐
│ 🗳️ 听证会裁决：[议题名称]            │
├──────────────────────────────────────┤
│ 📈 CGO：[核心论点摘要]               │
│ 🛡️ CRO：[核心风险摘要]               │
│ 📊 COO：[财务摘要]                   │
│ ⚙️ CTO：[技术摘要]                   │
├──────────────────────────────────────┤
│ [✅ 批准激进方案]  [🔄 采纳保守建议]   │
│ [❌ 否决]         [💬 要求补充论证]   │
└──────────────────────────────────────┘
```

### L0 裁决选项

| 选项 | 后续动作 |
|:---|:---|
| ✅ 批准激进方案 | CGO 方案原样执行，进入 L3 中台 |
| 🔄 采纳保守建议 | 按 CRO/COO 修改后执行 |
| ❌ 否决 | 归档，不执行 |
| 💬 要求补充论证 | 回到 Round 1 开始新一轮 |

---

## 五、观察者断点 (interrupt_before)

### 断点规则

| 操作类型 | 是否断点 | 理由 |
|:---|:---|:---|
| RPA 操作 (上架/改价) | ✅ 强制挂起 | 不可逆 |
| 发外部邮件/DM | ✅ 强制挂起 | 不可逆 |
| 资金操作 (广告/采购) | ✅ 强制挂起 | 涉及资金 |
| 数据爬取 | ❌ 自动放行 | 只读操作 |
| 内部分析计算 | ❌ 自动放行 | 无副作用 |
| 生成草稿 | ❌ 自动放行 | 可随时丢弃 |

### 实现方式

```python
graph = graph.compile(
    checkpointer=PostgresSaver(conn),
    interrupt_before=["execute_physical"]
)
```

系统在断点处持久化 State 快照，向飞书推送包含完整上下文的审批卡片，等待 L0 回调唤醒。
