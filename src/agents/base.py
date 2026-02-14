"""
Base Agent — shared foundation for all L1/L2/L3/L4 agents.

Four-layer capability model:
1. Prompt — personality, output format, decision principles (loaded from .md)
2. Personal Memory — short-term scratchpad + long-term episodic memory (per agent)
3. Skills — executable multi-step workflows (loaded from SKILL.yaml)
4. MCP — real-time external tool connections (via langchain-mcp-adapters)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.config.models import get_llm
from src.core.state import SiliconState
from src.core.personal_memory import PersonalMemory, MemoryEntry
from src.skills.loader import load_skills_for_role, match_skill, Skill, SkillExecutor
from src.skills.mcp_manager import MCPManager


class BaseAgent:
    """
    Base class for all Silicon-Empire agents.
    
    Four-layer capability model:
    1. Prompt — personality, output format, decision principles (loaded from .md)
    2. Personal Memory — each agent's own brain (scratchpad, mood, episodic, impressions)
    3. Skills — executable multi-step workflows (loaded from SKILL.yaml)
    4. MCP — real-time external tool connections (via langchain-mcp-adapters)
    """

    ROLE: str = ""           # Override in subclass: "gm", "cgo", etc.
    DISPLAY_NAME: str = ""   # Override: "总经理 (GM)"
    LLM_ROLE: str = ""       # Override: key for get_llm()

    def __init__(self) -> None:
        self._prompt: str = ""
        self._skills: dict[str, Skill] = {}
        self._mcp: MCPManager = MCPManager()
        self._skill_executor: SkillExecutor | None = None
        self._memory: PersonalMemory = PersonalMemory(agent_id="", display_name="")
        self._initialized = False

    async def initialize(self) -> None:
        """Load prompt, personal memory, skills, and connect MCP servers."""
        if self._initialized:
            return

        # Layer 1: Load Prompt
        self._prompt = self._load_prompt()

        # Layer 2: Initialize Personal Memory
        self._memory = PersonalMemory(agent_id=self.ROLE, display_name=self.DISPLAY_NAME)
        try:
            from src.core.memory import get_memory
            mem_mgr = await get_memory()
            await self._memory.init(mem_mgr.redis, mem_mgr.db)
        except Exception:
            pass  # Memory backends not available yet (e.g. during testing)

        # Layer 3: Load Skills
        self._skills = load_skills_for_role(self.ROLE)

        # Layer 4: Connect MCP (don't fail if MCP not available yet)
        try:
            mcp_tools = await self._mcp.connect(self.ROLE)
        except Exception:
            mcp_tools = []

        # Build Skill executor with LLM and MCP
        self._skill_executor = SkillExecutor(
            llm_func=self._llm_think,
            mcp_client=self._mcp if mcp_tools else None,
        )

        self._initialized = True

    async def cleanup(self) -> None:
        """Archive personal memory and clean up MCP connections."""
        # 下班: 归档重要的短期记忆为长期记忆
        try:
            archived = await self._memory.archive_working_memory()
            if archived > 0:
                await self._memory.remember(MemoryEntry(
                    content=f"会话结束，归档了 {archived} 条重要记忆。",
                    memory_type="reflection",
                    importance=3,
                ))
        except Exception:
            pass
        await self._mcp.disconnect()

    @property
    def memory(self) -> PersonalMemory:
        """Public access to this agent's personal memory."""
        return self._memory

    # ─── Core Invocation ───

    async def invoke(self, state: SiliconState) -> dict[str, Any]:
        """
        Main entry point. Called by LangGraph as a node function.
        
        1. Try to match a Skill for the current intent
        2. If matched → execute Skill workflow
        3. If not → free-form LLM reasoning with MCP tools
        """
        await self.initialize()

        # 开工前: 记一下在做什么
        await self._memory.think(
            f"收到任务: {state.strategic_intent[:100]}",
            importance=4,
        )

        # Try Skill match
        skill = match_skill(
            self._skills,
            state.intent_category,
            state.strategic_intent,
        )

        if skill:
            result = await self._execute_skill(skill, state)
            await self._memory.think(
                f"使用了 Skill [{skill.name}] 完成任务",
                importance=5,
            )
            return result
        else:
            return await self._free_think(state)

    async def _execute_skill(self, skill: Skill, state: SiliconState) -> dict[str, Any]:
        """Execute a matched Skill."""
        assert self._skill_executor is not None

        initial_context = {
            "strategic_intent": state.strategic_intent,
            "intent_category": state.intent_category,
            "proposals": state.proposal_buffer,
            "critiques": {k: v.model_dump() for k, v in state.critique_logs.items()},
        }

        result = await self._skill_executor.execute(skill, initial_context)
        return {"skill_used": skill.name, "result": result}

    async def _free_think(self, state: SiliconState) -> dict[str, Any]:
        """Free-form reasoning when no Skill matches."""
        context = self._build_context(state)
        response = await self._llm_think(context, {})
        return {"thinking": response}

    # ─── Meeting Participation ───

    async def review_proposal(self, state: SiliconState) -> dict[str, Any]:
        """
        Review a proposal in the context of a Joint Session.
        Override in subclass for role-specific review logic.
        """
        await self.initialize()

        prompt = self._build_review_prompt(state)
        response = await self._llm_think(prompt, {})

        # 记住这次审查经历
        await self._memory.think(
            f"审查了提案 v{len(state.proposal_buffer)}, 我的判断: {response[:80]}",
            importance=6,
        )

        return {"review": response, "reviewer": self.ROLE}

    async def debate(self, state: SiliconState, round_num: int) -> dict[str, Any]:
        """
        Participate in an Adversarial Hearing round.
        Override in subclass for role-specific debate behavior.
        """
        await self.initialize()

        prompt = self._build_debate_prompt(state, round_num)
        response = await self._llm_think(prompt, {})

        # 记住辩论经历
        await self._memory.think(
            f"听证会 Round {round_num} 发言, 议题: {state.strategic_intent[:60]}",
            importance=7,
        )

        return {
            "round": round_num,
            "speaker": self.DISPLAY_NAME,
            "content": response,
        }

    # ─── Holiday Mode: Free Chat ───

    async def chat_freely(self, topic: str, conversation_history: list[dict]) -> dict[str, Any]:
        """
        放假模式: 自由聊天。没有任务压力，可以聊业务想法、吐槽、闲聊。
        
        Args:
            topic: 讨论主题 (可以为空 = 纯闲聊)
            conversation_history: 之前的对话记录
        """
        await self.initialize()

        # 获取个人记忆上下文
        memory_ctx = await self._memory.build_memory_context(topic)

        # 获取当前情绪
        mood = await self._memory.get_mood()

        # 构建聊天 prompt
        history_text = "\n".join(
            f"**{msg['speaker']}**: {msg['content']}" for msg in conversation_history[-10:]
        )

        prompt = (
            f"现在是放假时间，你不需要做任何工作任务。\n"
            f"你可以自由地表达想法、提建议、吐槽、聊天。\n"
            f"不用遵守输出格式模板，像同事之间聊天一样说话。\n\n"
        )

        if topic:
            prompt += f"## 聊天话题\n{topic}\n\n"
        else:
            prompt += "没有特定话题，随便聊聊。\n\n"

        if history_text:
            prompt += f"## 之前的对话\n{history_text}\n\n"

        prompt += (
            f"你当前的情绪: {mood}\n"
            f"请用你自己的风格和性格来回应，简短自然即可。"
        )

        # 用个人记忆增强 system prompt
        system = self._prompt + memory_ctx

        llm = get_llm(self.LLM_ROLE, temperature=0.9)  # 放假时更放松
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
        response = await llm.ainvoke(messages)
        chat_content = response.content

        # 记住这次聊天中自己说的话 (可能产生洞察)
        await self._memory.think(
            f"放假闲聊: {chat_content[:100]}",
            importance=4,
        )

        return {
            "speaker": self.DISPLAY_NAME,
            "role": self.ROLE,
            "content": chat_content,
            "mood": mood,
        }

    # ─── LLM Interface ───

    async def _llm_think(self, prompt: str, context: dict[str, Any]) -> str:
        """Invoke LLM with system prompt + personal memory context."""
        llm = get_llm(self.LLM_ROLE)

        # 注入个人记忆: 让 Agent "记起自己的经历"
        memory_ctx = ""
        try:
            memory_ctx = await self._memory.build_memory_context()
        except Exception:
            pass

        system_with_memory = self._prompt + memory_ctx

        messages = [
            SystemMessage(content=system_with_memory),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        return response.content

    # ─── Context Building ───

    def _build_context(self, state: SiliconState) -> str:
        """Build a context string from state for free-form thinking."""
        parts = [f"## 当前任务\n{state.strategic_intent}"]

        if state.proposal_buffer:
            latest = state.proposal_buffer[-1]
            parts.append(f"## 最新提案\n{latest.get('content', '')}")

        if state.meeting_transcript:
            recent = state.meeting_transcript[-3:]
            transcript = "\n".join(
                f"**{t['speaker']}**: {t['content'][:200]}..." for t in recent
            )
            parts.append(f"## 近期讨论\n{transcript}")

        return "\n\n".join(parts)

    def _build_review_prompt(self, state: SiliconState) -> str:
        """Build prompt for joint session review. Override in subclass."""
        proposal = state.proposal_buffer[-1] if state.proposal_buffer else {}
        return (
            f"请审查以下提案，从你的专业角度给出意见。\n\n"
            f"## 提案\n{proposal.get('content', '无提案')}\n\n"
            f"## 你的任务\n按照你的输出格式模板回复。"
        )

    def _build_debate_prompt(self, state: SiliconState, round_num: int) -> str:
        """Build prompt for adversarial hearing. Override in subclass."""
        transcript = "\n".join(
            f"**Round {t['round']} ({t['speaker']})**: {t['content']}"
            for t in state.meeting_transcript
        )
        return (
            f"这是对抗性听证会的第 {round_num} 轮。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## 已有发言\n{transcript or '（你是第一个发言者）'}\n\n"
            f"## 你的任务\n请按照你在听证会中的角色发言。"
        )

    # ─── Prompt Loading ───

    def _load_prompt(self) -> str:
        """Load system prompt from src/prompts/{role}.md"""
        prompt_path = Path(f"src/prompts/{self.ROLE}.md")
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        return f"你是 Silicon-Empire 的 {self.DISPLAY_NAME}。请按照你的职责行事。"
