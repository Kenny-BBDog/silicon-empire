"""
进化执行引擎 — CTO 的进化核心能力。

职责:
- 扫描各角色 Skill 覆盖
- 部署新 Agent
- 创建新中台部门
- 为其他首席写 Skill
- 管理服务器
- 搜索学习新方案
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from src.platforms.base_worker import PlatformWorker


class EvolutionEngine(PlatformWorker):
    """L3 技术中台 — 进化引擎"""

    ROLE = "l3_evolution"
    DISPLAY_NAME = "进化引擎 (Evolution)"
    LLM_ROLE = "cto"
    PLATFORM = "tech_lab"

    # ─── 扫描能力 ───

    async def scan_skills(self) -> dict[str, Any]:
        """
        扫描各角色 Skill 覆盖率。
        统计每个角色已有多少 Skill，发现缺口。
        """
        await self.initialize()

        skills_root = Path("src/skills")
        coverage = {}

        for role_dir in skills_root.iterdir():
            if role_dir.is_dir() and not role_dir.name.startswith("_"):
                role = role_dir.name
                skills = [
                    d.name for d in role_dir.iterdir()
                    if d.is_dir() and (d / "SKILL.yaml").exists()
                ]
                coverage[role] = {
                    "count": len(skills),
                    "skills": skills,
                }

        # LLM 分析缺口
        prompt = (
            f"分析以下各角色的 Skill 覆盖情况，找出缺口:\n\n"
            f"{coverage}\n\n"
            f"对于每个角色，建议最需要补充的 1-2 个 Skill，"
            f"说明原因和预期价值。简洁回复。"
        )
        analysis = await self._llm_think(prompt, {})

        return {"coverage": coverage, "analysis": analysis}

    async def scan_infrastructure(self) -> dict[str, Any]:
        """
        检测服务器和基础设施状态。
        """
        await self.initialize()

        checks = {}

        # Check disk
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            checks["disk"] = {
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "usage_pct": round(used / total * 100, 1),
            }
        except Exception as e:
            checks["disk"] = {"error": str(e)}

        # Check memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            checks["memory"] = {
                "total_gb": round(mem.total / (1024**3), 1),
                "used_pct": mem.percent,
            }
        except ImportError:
            checks["memory"] = {"note": "psutil not installed"}

        return {"checks": checks}

    # ─── 部署能力 ───

    async def deploy_agent(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        创建并注册新 Agent。

        spec:
            name: "price_comparator"
            display_name: "比价专员"
            level: "l3"  or "l4"
            parent: "cgo"  # 上级首席
            platform: "data_intel"  # 所属中台
            description: "自动比较供应商价格"
        """
        await self.initialize()

        name = spec.get("name", "new_agent")
        display_name = spec.get("display_name", name)
        level = spec.get("level", "l3")
        parent = spec.get("parent", "gm")
        platform = spec.get("platform", "")
        description = spec.get("description", "")

        # LLM 生成 Agent 代码
        prompt = (
            f"为 Silicon-Empire 系统生成一个新的 Agent Python 文件。\n\n"
            f"规格:\n"
            f"- 类名: {name.title().replace('_', '')}Agent\n"
            f"- 显示名: {display_name}\n"
            f"- 级别: {level}\n"
            f"- 上级: {parent}\n"
            f"- 所属中台: {platform}\n"
            f"- 功能描述: {description}\n\n"
            f"参考现有 Agent 结构 (继承 BaseAgent 或 PlatformWorker)。\n"
            f"生成完整可运行的 Python 代码。"
        )

        code = await self._llm_think(prompt, {})

        await self._memory.think(
            f"生成新Agent: {display_name} ({level}) → 等待部署",
            importance=8,
        )

        return {
            "agent_name": name,
            "code": code,
            "status": "generated",
            "needs_approval": True,
        }

    async def author_skill(
        self, role: str, skill_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """
        为指定角色生成 SKILL.yaml。

        skill_spec:
            name: "auto_pricing"
            description: "自动定价策略"
            triggers: ["定价", "价格"]
        """
        await self.initialize()

        prompt = (
            f"为 {role} 角色生成一个 SKILL.yaml 文件。\n\n"
            f"Skill 规格:\n"
            f"- 名称: {skill_spec.get('name', '')}\n"
            f"- 描述: {skill_spec.get('description', '')}\n"
            f"- 触发词: {skill_spec.get('triggers', [])}\n\n"
            f"参考格式:\n"
            f"```yaml\n"
            f"name: skill_name\n"
            f"display_name: 技能显示名\n"
            f"owner: {role}\n"
            f"version: '1.0'\n"
            f"description: ...\n"
            f"triggers:\n"
            f"  - intent: category_name\n"
            f"  - keyword: ['关键词1', '关键词2']\n"
            f"steps:\n"
            f"  - id: step1\n"
            f"    action: llm_think\n"
            f"    prompt: '...'\n"
            f"```\n\n"
            f"生成完整的 SKILL.yaml 内容。"
        )

        yaml_content = await self._llm_think(prompt, {})

        return {
            "role": role,
            "skill_name": skill_spec.get("name", ""),
            "yaml": yaml_content,
            "status": "generated",
        }

    async def create_department(self, spec: dict[str, Any]) -> dict[str, Any]:
        """
        创建新中台部门。

        spec:
            name: "logistics"
            display_name: "物流中台"
            parent_chief: "coo"
            workers: ["tracker", "optimizer"]
        """
        await self.initialize()

        prompt = (
            f"设计一个新的中台部门结构:\n\n"
            f"- 部门名: {spec.get('display_name', '')}\n"
            f"- 目录: src/platforms/{spec.get('name', '')}/\n"
            f"- 上级首席: {spec.get('parent_chief', 'coo')}\n"
            f"- 需要的 Worker: {spec.get('workers', [])}\n\n"
            f"为每个 Worker 生成简要的职责描述和文件名。\n"
            f"输出每个文件的功能概述。"
        )

        design = await self._llm_think(prompt, {})

        return {
            "department": spec.get("name", ""),
            "design": design,
            "status": "designed",
            "needs_approval": True,
        }

    # ─── 研究能力 ───

    async def research_topic(self, query: str) -> dict[str, Any]:
        """
        研究新技术/方案 — 通过 LLM 内置知识。
        未来可接入 Web Search MCP。
        """
        await self.initialize()

        prompt = (
            f"你是技术研究员。深入研究以下课题:\n\n"
            f"**{query}**\n\n"
            f"给出:\n"
            f"1. 技术概述 (简洁)\n"
            f"2. 对 Silicon-Empire 系统的价值\n"
            f"3. 实施方案 (具体步骤)\n"
            f"4. 风险和注意事项\n"
            f"5. 推荐优先级 (P0/P1/P2)\n"
        )

        research = await self._llm_think(prompt, {})

        await self._memory.think(
            f"研究课题: {query[:60]}",
            importance=5,
        )

        return {"query": query, "research": research}
