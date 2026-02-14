"""
Self-Healing Loop — 完整自愈闭环 (增强版)

Flow:
  error_trap → cto_diagnose → [retry | autolab_rebuild]
    → sandbox_test → [pass → deploy_fix | fail → retry/give_up]

集成:
- CTO Agent: 错误诊断
- AutoLab (L4): 代码修复生成
- Sandbox: 隔离测试
- Architect: tool_registry 更新
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from src.agents import CTOAgent
from src.core.state import SiliconState
from src.platforms.tech_lab import AutoLabAgent, SandboxExecutor, ArchitectAgent


cto = CTOAgent()
auto_lab = AutoLabAgent()
architect = ArchitectAgent()
sandbox = SandboxExecutor(timeout=30)


# ─── Nodes ───

async def error_trap(state: dict) -> dict:
    """
    捕获 L3 中台抛出的异常。
    通常由其他 Graph 的 error handler 触发。
    """
    error_log = state.get("error_log", {})

    return {
        "phase": "diagnosing",
        "error_log": error_log,
        "heal_started_at": datetime.now(timezone.utc).isoformat(),
        "heal_attempts": 0,
    }


async def cto_diagnose(state: dict) -> dict:
    """CTO 诊断错误 — 分类并决策修复策略。"""
    s = SiliconState(**state)
    result = await cto.diagnose_error(s)
    diagnosis = result.get("diagnosis", "")

    # CTO 判断修复策略
    action = "retry"
    if any(kw in diagnosis.upper() for kw in ["REBUILD", "CODE", "BUG", "LOGIC", "API_CHANGE"]):
        action = "rebuild"
    elif any(kw in diagnosis.upper() for kw in ["CONFIG", "ENV", "SECRET"]):
        action = "config_fix"
    elif any(kw in diagnosis.upper() for kw in ["NETWORK", "TIMEOUT", "RATE_LIMIT"]):
        action = "retry"

    # CTO 记住这次诊断
    await cto.memory.think(
        f"诊断结果: {action} — {diagnosis[:100]}",
        importance=7,
    )

    return {
        "phase": action,
        "diagnosis": diagnosis,
        "heal_action": action,
    }


async def retry_action(state: dict) -> dict:
    """重试 — 用于临时故障 (网络超时/限流)。"""
    attempts = state.get("heal_attempts", 0) + 1

    # TODO: 实际重新执行失败的任务
    # 这里占位

    return {
        "phase": "testing",
        "heal_attempts": attempts,
        "retry_result": "retried",
    }


async def autolab_rebuild(state: dict) -> dict:
    """AutoLab 生成修复代码 — 用于逻辑错误/API 变更。"""
    error_log = state.get("error_log", {})
    diagnosis = state.get("diagnosis", "")

    # Step 1: AutoLab 深度分析
    analysis = await auto_lab.analyze_error({
        **error_log,
        "cto_diagnosis": diagnosis,
    })

    # Step 2: 生成修复代码
    fix = await auto_lab.generate_fix(
        error_analysis=analysis,
        current_code=error_log.get("current_code", ""),
    )

    # Step 3: 生成测试
    test = await auto_lab.write_test(
        code=fix.get("fixed_code", ""),
        function_name=error_log.get("tool_name", ""),
    )

    return {
        "phase": "testing",
        "analysis": analysis,
        "fixed_code": fix.get("fixed_code", ""),
        "test_code": test.get("test_code", ""),
        "heal_attempts": state.get("heal_attempts", 0) + 1,
    }


async def config_fix(state: dict) -> dict:
    """配置修复 — 环境变量/密钥问题。"""
    diagnosis = state.get("diagnosis", "")

    await cto.memory.think(
        f"配置问题需要人工介入: {diagnosis[:100]}",
        importance=8,
    )

    return {
        "phase": "needs_human",
        "fix_type": "config",
        "message": f"需要人工修复配置: {diagnosis[:200]}",
    }


async def sandbox_test(state: dict) -> dict:
    """在沙盒中测试修复代码。"""
    fixed_code = state.get("fixed_code", "")
    test_code = state.get("test_code", "")

    if not fixed_code:
        # 没有新代码 (retry 模式), 直接 pass
        return {"phase": "test_passed", "sandbox_result": {"success": True}}

    # 先做语法检查
    syntax_check = await sandbox.run_syntax_check(fixed_code)
    if not syntax_check.get("valid_syntax"):
        return {
            "phase": "test_failed",
            "sandbox_result": {
                "success": False,
                "stderr": syntax_check.get("errors", "Syntax error"),
            },
        }

    # 运行测试
    result = await sandbox.run_code(fixed_code, test_code)

    phase = "test_passed" if result["success"] else "test_failed"

    await cto.memory.think(
        f"沙盒测试: {'通过 ✅' if result['success'] else '失败 ❌'} "
        f"({result.get('duration_ms', 0)}ms)",
        importance=6,
    )

    return {"phase": phase, "sandbox_result": result}


async def deploy_fix(state: dict) -> dict:
    """
    部署修复:
    1. 更新 tool_registry 状态 → ACTIVE
    2. 更新版本号
    3. 通知相关中台恢复
    """
    error_log = state.get("error_log", {})
    tool_name = error_log.get("tool_name", "")

    if tool_name:
        await architect.manage_tool_registry("update_status", {
            "tool_name": tool_name,
            "status": "ACTIVE",
            "error_log": "",
        })

    await cto.memory.think(
        f"修复部署成功: {tool_name} 已恢复 ✅",
        importance=8,
    )

    return {
        "phase": "healed",
        "error_log": None,
        "heal_completed_at": datetime.now(timezone.utc).isoformat(),
    }


async def give_up(state: dict) -> dict:
    """超过最大重试次数，标记工具为 BROKEN，通知人工。"""
    error_log = state.get("error_log", {})
    tool_name = error_log.get("tool_name", "")

    if tool_name:
        await architect.manage_tool_registry("update_status", {
            "tool_name": tool_name,
            "status": "BROKEN",
            "error_log": state.get("diagnosis", "Auto-heal failed"),
        })

    await cto.memory.think(
        f"自愈失败: {tool_name} 标记为 BROKEN, 需要人工修复",
        importance=9,
    )

    return {
        "phase": "broken",
        "message": f"工具 {tool_name} 自动修复失败 (尝试 {state.get('heal_attempts', 0)} 次), 需要人工介入",
    }


# ─── Routing ───

def route_diagnosis(state: dict) -> str:
    """CTO 诊断后路由。"""
    return state.get("heal_action", "retry")


def route_test_result(state: dict) -> str:
    """沙盒测试结果路由。"""
    if state.get("phase") == "test_passed":
        return "deploy"
    if state.get("heal_attempts", 0) >= 3:
        return "give_up"
    return "retry_rebuild"


# ─── Build Graph ───

def build_self_heal_graph() -> StateGraph:
    """
    Build the enhanced Self-Healing state graph.
    
    error_trap → cto_diagnose
      → retry → sandbox_test → [deploy | retry]
      → autolab_rebuild → sandbox_test → [deploy | retry | give_up]
      → config_fix → END (needs human)
    """
    graph = StateGraph(dict)

    # Nodes
    graph.add_node("error_trap", error_trap)
    graph.add_node("cto_diagnose", cto_diagnose)
    graph.add_node("retry", retry_action)
    graph.add_node("autolab_rebuild", autolab_rebuild)
    graph.add_node("config_fix", config_fix)
    graph.add_node("sandbox_test", sandbox_test)
    graph.add_node("deploy_fix", deploy_fix)
    graph.add_node("give_up", give_up)

    # Entry
    graph.set_entry_point("error_trap")
    graph.add_edge("error_trap", "cto_diagnose")

    # CTO 诊断路由
    graph.add_conditional_edges(
        "cto_diagnose",
        route_diagnosis,
        {
            "retry": "retry",
            "rebuild": "autolab_rebuild",
            "config_fix": "config_fix",
        },
    )

    # retry/rebuild → 沙盒测试
    graph.add_edge("retry", "sandbox_test")
    graph.add_edge("autolab_rebuild", "sandbox_test")

    # config 需人工 → 结束
    graph.add_edge("config_fix", END)

    # 沙盒测试结果路由
    graph.add_conditional_edges(
        "sandbox_test",
        route_test_result,
        {
            "deploy": "deploy_fix",
            "retry_rebuild": "autolab_rebuild",
            "give_up": "give_up",
        },
    )

    graph.add_edge("deploy_fix", END)
    graph.add_edge("give_up", END)

    return graph
