"""
Persistent Execution Loop — 让 Agent 不轻易放弃。

核心理念: Agent 不是 "问一次 LLM 就完事"。
它们会:
1. 自问自答 — "我的回答完整吗？有没有遗漏？"
2. 分解任务 — "这个太大了，拆成几步"
3. 求助其他 Agent — "这个我不擅长，问问 CRO"
4. 重试 — "失败了没关系，换个方式再来"
5. 持续工作 — 直到拿到具体、可交付的结果
"""

from __future__ import annotations

from typing import Any

MAX_RETRIES = 3           # 失败重试次数
MAX_REFINEMENT = 2        # 自我优化轮数
MIN_QUALITY_THRESHOLD = 0.6


async def persistent_think(agent, prompt: str, context: dict[str, Any]) -> str:
    """
    替代简单的一次性 LLM 调用。
    Agent 会持续思考直到产出高质量结果。

    Flow:
    1. 首次思考 → 得到初步结果
    2. 自检 → "我的回答质量如何？有没有遗漏？"
    3. 如果不够好 → 继续优化
    4. 如果需要其他 Agent 的输入 → 发消息
    5. 最多优化 MAX_REFINEMENT 轮
    """
    # Step 1: 首次思考
    result = await agent._llm_think(prompt, context)

    # Step 2: 自检 + 优化循环
    for round_num in range(MAX_REFINEMENT):
        quality_check = await _self_evaluate(agent, prompt, result)

        if quality_check["is_good_enough"]:
            break

        # 需要优化 — 根据自检反馈改进
        refinement_prompt = (
            f"你刚才的回答:\n{result[:1000]}\n\n"
            f"自检发现的问题:\n{quality_check['feedback']}\n\n"
            f"请改进你的回答，解决以上问题。\n"
            f"要求: 输出具体、可执行、完整的结果。"
        )
        result = await agent._llm_think(refinement_prompt, context)

    # Step 3: 检查是否需要其他 Agent 协助
    collab_result = await _check_collaboration_need(agent, prompt, result)
    if collab_result:
        result = result + "\n\n## 跨部门协作\n" + collab_result

    return result


async def persistent_execute(agent, task: dict[str, Any]) -> dict[str, Any]:
    """
    持久化执行任务 — 不轻易放弃。

    Flow:
    1. 分解任务 → 拆成子步骤
    2. 逐步执行 → 每步检查结果
    3. 失败重试 → 换策略再来
    4. 求助 → 委派给其他 Agent
    5. 直到拿到具体成果
    """
    # Step 1: 分析任务复杂度，决定是否需要分解
    decomposition = await _decompose_if_needed(agent, task)

    if decomposition["needs_split"]:
        # 多步骤执行
        results = []
        for step in decomposition["steps"]:
            step_result = await _execute_with_retry(agent, step)
            results.append(step_result)
        return {
            "status": "completed",
            "steps": results,
            "decomposed": True,
        }
    else:
        # 单步执行（带重试）
        return await _execute_with_retry(agent, task)


async def _self_evaluate(agent, original_prompt: str, result: str) -> dict:
    """Agent 自检: 评估自己的回答质量。"""
    eval_prompt = (
        f"你刚完成了以下任务:\n"
        f"任务: {original_prompt[:300]}\n\n"
        f"你的回答: {result[:500]}\n\n"
        f"自检:\n"
        f"1. 回答是否具体、可执行？(不是空泛的建议)\n"
        f"2. 是否有遗漏的关键点？\n"
        f"3. 数据/论据是否充分？\n"
        f"4. 是否需要其他部门的输入？\n\n"
        f"回复格式:\n"
        f"QUALITY: HIGH/MEDIUM/LOW\n"
        f"ISSUES: [具体问题，没有则写 NONE]\n"
        f"NEED_HELP_FROM: [需要哪个角色协助，没有则写 NONE]"
    )

    eval_result = await agent._llm_think(eval_prompt, {})

    is_good = "HIGH" in eval_result.upper()
    feedback = eval_result if not is_good else ""
    need_help = None
    if "NEED_HELP_FROM:" in eval_result:
        help_line = [l for l in eval_result.split("\n") if "NEED_HELP_FROM:" in l]
        if help_line and "NONE" not in help_line[0].upper():
            need_help = help_line[0].split(":")[-1].strip().lower()

    return {
        "is_good_enough": is_good,
        "feedback": feedback,
        "need_help_from": need_help,
    }


async def _check_collaboration_need(agent, prompt: str, result: str) -> str | None:
    """检查是否需要其他 Agent 协助。"""
    try:
        from src.core.agent_bus import ask, get_inbox

        # 快速检查 — 不是每次都需要
        check_prompt = (
            f"你的任务: {prompt[:200]}\n"
            f"你的回答: {result[:300]}\n\n"
            f"这个回答是否需要其他首席的意见/确认？\n"
            f"如果需要，回复: ASK|角色|问题\n"
            f"如果不需要，回复: NO\n"
            f"角色可选: gm/cgo/coo/cro/cto"
        )
        check = await agent._llm_think(check_prompt, {})

        if check.strip().startswith("ASK|"):
            parts = check.strip().split("|")
            if len(parts) >= 3:
                target_role = parts[1].strip()
                question = parts[2].strip()
                ask(agent.ROLE, target_role, question)
                return f"已向 {target_role} 发送询问: {question}"
    except Exception:
        pass
    return None


async def _decompose_if_needed(agent, task: dict[str, Any]) -> dict:
    """判断任务是否需要分解。"""
    task_desc = task.get("task_type", "") + ": " + str(task.get("params", {}))

    prompt = (
        f"分析以下任务的复杂度:\n{task_desc[:300]}\n\n"
        f"这个任务能一步完成吗？还是需要分成几步？\n"
        f"如果需要分步，列出步骤 (最多 5 步):\n"
        f"SINGLE (一步可完) 或 SPLIT:\n"
        f"STEP1: ...\nSTEP2: ...\n..."
    )

    result = await agent._llm_think(prompt, {})

    if "SPLIT" in result.upper():
        steps = []
        for line in result.split("\n"):
            if line.strip().startswith("STEP"):
                step_desc = line.split(":", 1)[-1].strip()
                steps.append({
                    "task_type": "sub_task",
                    "params": {"description": step_desc},
                    "delegated_by": agent.ROLE,
                })
        return {"needs_split": bool(steps), "steps": steps}

    return {"needs_split": False, "steps": []}


async def _execute_with_retry(agent, task: dict[str, Any]) -> dict:
    """带重试的任务执行。"""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            # 尝试执行
            if hasattr(agent, 'execute_task'):
                result = await agent.execute_task(task)
            else:
                prompt = (
                    f"执行任务:\n"
                    f"类型: {task.get('task_type', '未知')}\n"
                    f"参数: {task.get('params', {})}\n"
                    f"{'(第 ' + str(attempt+1) + ' 次尝试, 上次失败原因: ' + str(last_error) + ')' if attempt > 0 else ''}\n\n"
                    f"要求: 必须输出具体、可交付的成果。"
                )
                response = await agent._llm_think(prompt, {})
                result = {"result": response}

            return {"status": "success", "attempt": attempt + 1, **result}

        except Exception as e:
            last_error = str(e)
            # 记住失败经历
            try:
                await agent._memory.think(
                    f"任务失败 (第{attempt+1}次): {str(e)[:100]}",
                    importance=7,
                )
            except Exception:
                pass

    # 所有重试都失败 — 求助
    try:
        from src.core.agent_bus import report_up
        report_up(
            agent.ROLE, "cto",
            f"任务多次失败，需要技术支持: {task.get('task_type', '')} — {last_error}"
        )
    except Exception:
        pass

    return {"status": "failed", "attempts": MAX_RETRIES, "last_error": last_error}
