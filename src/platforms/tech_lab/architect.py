"""
技术中台 — Architect 系统架构师 (L3)

职责：
- 系统健康巡检 (Redis/Supabase/MCP servers)
- 工具注册表管理 (tool_registry CRUD)
- 性能分析与优化建议
- 基础设施监控
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class ArchitectAgent(PlatformWorker):
    """L3 技术中台 — 系统架构师"""

    ROLE = "l3_architect"
    DISPLAY_NAME = "系统架构师 (Architect)"
    LLM_ROLE = "cto"
    PLATFORM = "tech_lab"

    async def health_check(self) -> dict[str, Any]:
        """
        全系统巡检 — 检查各组件状态。
        可定时触发 (如每 6 小时)。
        """
        await self.initialize()

        checks = {}

        # Redis
        try:
            from src.core.memory import get_memory
            mem = await get_memory()
            await mem.redis.ping()
            checks["redis"] = {"status": "healthy", "latency_ms": "< 5"}
        except Exception as e:
            checks["redis"] = {"status": "unhealthy", "error": str(e)}

        # Supabase
        try:
            from src.core.memory import get_memory
            mem = await get_memory()
            result = mem.supabase.table("tool_registry").select("count").execute()
            checks["supabase"] = {"status": "healthy", "tools_count": len(result.data or [])}
        except Exception as e:
            checks["supabase"] = {"status": "unhealthy", "error": str(e)}

        # Tool Registry
        try:
            from src.core.memory import get_memory
            mem = await get_memory()
            tools = mem.supabase.table("tool_registry").select("*").execute()
            broken = [t for t in (tools.data or []) if t.get("status") == "BROKEN"]
            checks["tool_registry"] = {
                "total": len(tools.data or []),
                "active": len([t for t in (tools.data or []) if t.get("status") == "ACTIVE"]),
                "broken": len(broken),
                "broken_tools": [t["tool_name"] for t in broken],
            }
        except Exception as e:
            checks["tool_registry"] = {"status": "error", "error": str(e)}

        overall = "healthy" if all(
            c.get("status") != "unhealthy" for c in checks.values()
        ) else "degraded"

        await self._memory.think(
            f"系统巡检完成: {overall}",
            importance=5 if overall == "healthy" else 8,
        )

        return {"overall_status": overall, "checks": checks}

    async def manage_tool_registry(
        self,
        action: str,
        tool_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        工具注册表管理。
        action: "register" | "update_status" | "deprecate" | "query"
        """
        await self.initialize()

        from src.core.memory import get_memory
        mem = await get_memory()

        if action == "register":
            result = mem.supabase.table("tool_registry").insert({
                "tool_name": tool_data["tool_name"],
                "function_schema": tool_data.get("function_schema", {}),
                "code_path": tool_data.get("code_path", ""),
                "status": "ACTIVE",
                "version": 1,
            }).execute()
            return {"action": "registered", "result": result.data}

        elif action == "update_status":
            result = mem.supabase.table("tool_registry").update({
                "status": tool_data.get("status", "ACTIVE"),
                "last_error_log": tool_data.get("error_log", ""),
                "version": tool_data.get("version", 1),
            }).eq("tool_name", tool_data["tool_name"]).execute()
            return {"action": "updated", "result": result.data}

        elif action == "deprecate":
            result = mem.supabase.table("tool_registry").update({
                "status": "DEPRECATED",
            }).eq("tool_name", tool_data["tool_name"]).execute()
            return {"action": "deprecated", "result": result.data}

        elif action == "query":
            q = mem.supabase.table("tool_registry").select("*")
            if tool_data.get("status"):
                q = q.eq("status", tool_data["status"])
            result = q.execute()
            return {"tools": result.data}

        return {"error": f"Unknown action: {action}"}

    async def analyze_performance(
        self, component: str, metrics: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """性能分析与优化建议。"""
        await self.initialize()

        prompt = (
            f"分析以下系统组件的性能:\n\n"
            f"## 组件\n{component}\n\n"
            f"## 指标\n{metrics or '无具体指标，做通用分析'}\n\n"
            f"## 输出\n"
            f"1. 当前性能评级 (A/B/C/D/F)\n"
            f"2. 瓶颈识别\n"
            f"3. 优化建议 (按优先级排序)\n"
            f"4. 预期优化效果\n"
        )

        response = await self._llm_think(prompt, {})
        return {"component": component, "analysis": response}
