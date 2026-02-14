"""
技术中台 — AutoLab 自动修复团队 (L4)

最底层自治 Agent — 接收 CTO 的修复指令，自动：
1. 分析错误日志
2. 生成修复代码
3. 在沙盒中测试
4. 产出修复补丁

L4 是"机器人中的机器人"，不参与任何决策，只做技术修复。
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from src.platforms.base_worker import PlatformWorker


class AutoLabAgent(PlatformWorker):
    """L4 技术中台 — 自动修复实验室"""

    ROLE = "l4_auto_lab"
    DISPLAY_NAME = "自动修复实验室 (AutoLab)"
    LLM_ROLE = "cto"    # 用 Claude — 代码能力强
    PLATFORM = "tech_lab"

    async def analyze_error(self, error_log: dict[str, Any]) -> dict[str, Any]:
        """
        深度分析错误 — 比 CTO 的诊断更深入，直达代码层面。
        """
        await self.initialize()

        prompt = (
            f"深度分析以下错误，给出根因和修复方案。\n\n"
            f"## 错误日志\n```\n{error_log.get('error_message', '')}\n```\n\n"
            f"## 错误来源\n"
            f"- 工具: {error_log.get('tool_name', '未知')}\n"
            f"- 文件: {error_log.get('code_path', '未知')}\n"
            f"- 调用者: {error_log.get('caller', '未知')}\n\n"
            f"## 输出\n"
            f"1. **错误分类**: NETWORK / API_CHANGE / LOGIC_BUG / CONFIG / DEPENDENCY\n"
            f"2. **根因分析**: 具体到代码行级别\n"
            f"3. **影响范围**: 哪些功能受影响\n"
            f"4. **修复方案**: 至少 2 个方案，标注推荐\n"
            f"5. **修复难度**: EASY / MEDIUM / HARD\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"分析错误: {error_log.get('tool_name', '?')} — {error_log.get('error_message', '')[:60]}",
            importance=7,
        )

        return {"analysis": response, "tool_name": error_log.get("tool_name", "")}

    async def generate_fix(
        self,
        error_analysis: dict[str, Any],
        current_code: str = "",
    ) -> dict[str, Any]:
        """
        生成修复代码。
        产出 diff 补丁或完整替换文件。
        """
        await self.initialize()

        prompt = (
            f"基于以下错误分析，生成修复代码。\n\n"
            f"## 错误分析\n{error_analysis}\n\n"
            f"{'## 当前代码\\n```python\\n' + current_code + '\\n```\\n' if current_code else ''}\n\n"
            f"## 要求\n"
            f"1. 输出完整的修复后代码 (不是 diff)\n"
            f"2. 添加必要的错误处理\n"
            f"3. 添加日志记录\n"
            f"4. 添加简单的单元测试\n"
            f"5. 标注改动点 (用 # FIX: 注释)\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"生成了修复代码，等待沙盒测试",
            importance=6,
        )

        return {
            "fixed_code": response,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def write_test(
        self, code: str, function_name: str = ""
    ) -> dict[str, Any]:
        """为修复后的代码生成测试用例。"""
        await self.initialize()

        prompt = (
            f"为以下代码生成测试用例:\n\n"
            f"```python\n{code}\n```\n\n"
            f"{'测试重点: ' + function_name if function_name else ''}\n\n"
            f"## 要求\n"
            f"1. 使用 pytest\n"
            f"2. 覆盖正常路径和异常路径\n"
            f"3. Mock 外部依赖\n"
            f"4. 至少 3 个测试用例\n"
        )

        response = await self._llm_think(prompt, {})
        return {"test_code": response}
