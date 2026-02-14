"""
Skill Loader and Executor.

Loads SKILL.yaml definitions and executes multi-step workflows.
Each Skill is a structured SOP that an Agent can trigger based on intent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SkillStep(BaseModel):
    """A single step in a Skill workflow."""

    id: str
    name: str
    action: str              # llm_think | call_mcp | delegate
    prompt: str = ""         # For llm_think
    server: str = ""         # For call_mcp — which MCP server
    tool: str = ""           # For call_mcp — which tool
    to: str = ""             # For delegate — target agent role
    skill: str = ""          # For delegate — which skill to invoke
    params: dict[str, Any] = Field(default_factory=dict)
    context: list[str] = Field(default_factory=list)  # Keys from previous step outputs
    template: str = ""       # Markdown template path
    output: str = ""         # Key name to store result
    write_to: str = ""       # State field to write final result to


class Skill(BaseModel):
    """A loaded Skill definition."""

    name: str
    display_name: str = ""
    owner: str = ""                  # Which agent owns this skill
    version: str = "1.0"
    description: str = ""
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    requires_mcp: list[str] = Field(default_factory=list)
    steps: list[SkillStep] = Field(default_factory=list)
    base_path: str = ""             # Filesystem path of the skill directory

    def matches_intent(self, intent_category: str) -> bool:
        """Check if this skill should be triggered by the given intent."""
        for trigger in self.triggers:
            if trigger.get("intent") == intent_category:
                return True
        return False

    def matches_keyword(self, text: str) -> bool:
        """Check if this skill should be triggered by keywords in the text."""
        for trigger in self.triggers:
            keywords = trigger.get("keyword", [])
            if any(kw in text for kw in keywords):
                return True
        return False


def load_skill(skill_dir: str | Path) -> Skill:
    """Load a single Skill from its directory."""
    skill_dir = Path(skill_dir)
    yaml_path = skill_dir / "SKILL.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"SKILL.yaml not found in {skill_dir}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    steps = [SkillStep(**s) for s in raw.get("steps", [])]

    return Skill(
        name=raw.get("name", skill_dir.name),
        display_name=raw.get("display_name", raw.get("name", "")),
        owner=raw.get("owner", ""),
        version=raw.get("version", "1.0"),
        description=raw.get("description", ""),
        triggers=raw.get("triggers", []),
        requires_mcp=raw.get("requires_mcp", []),
        steps=steps,
        base_path=str(skill_dir),
    )


def load_skills_for_role(role: str, skills_root: str | Path = "src/skills") -> dict[str, Skill]:
    """Load all Skills for a specific role."""
    skills_root = Path(skills_root)
    role_dir = skills_root / role.lower()

    if not role_dir.exists():
        return {}

    skills: dict[str, Skill] = {}

    for subdir in role_dir.iterdir():
        if subdir.is_dir() and (subdir / "SKILL.yaml").exists():
            try:
                skill = load_skill(subdir)
                skills[skill.name] = skill
            except Exception as e:
                print(f"Warning: Failed to load skill {subdir}: {e}")

    # Also load shared skills
    shared_dir = skills_root / "shared"
    if shared_dir.exists():
        for subdir in shared_dir.iterdir():
            if subdir.is_dir() and (subdir / "SKILL.yaml").exists():
                try:
                    skill = load_skill(subdir)
                    skills[f"shared.{skill.name}"] = skill
                except Exception:
                    pass

    return skills


def match_skill(
    skills: dict[str, Skill],
    intent_category: str,
    user_text: str = "",
) -> Skill | None:
    """Find the best-matching Skill for the given intent or text."""
    # Priority 1: Intent match
    for skill in skills.values():
        if skill.matches_intent(intent_category):
            return skill

    # Priority 2: Keyword match
    if user_text:
        for skill in skills.values():
            if skill.matches_keyword(user_text):
                return skill

    return None


class SkillExecutor:
    """
    Executes a Skill's step sequence.
    Coordinates between LLM calls, MCP tool invocations, and agent delegation.
    """

    def __init__(self, llm_func=None, mcp_client=None):
        """
        Args:
            llm_func: Async function(prompt, context) -> str for llm_think steps.
            mcp_client: MCP MultiServerClient for call_mcp steps.
        """
        self.llm_func = llm_func
        self.mcp_client = mcp_client

    async def execute(
        self,
        skill: Skill,
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute all steps in a Skill sequentially.

        Returns:
            Dict of {step.output: result} for all steps.
        """
        context = dict(initial_context or {})

        for step in skill.steps:
            result = await self._execute_step(step, context)
            if step.output:
                context[step.output] = result

        return context

    async def _execute_step(self, step: SkillStep, context: dict[str, Any]) -> Any:
        """Execute a single step."""
        if step.action == "llm_think":
            return await self._step_llm_think(step, context)
        elif step.action == "call_mcp":
            return await self._step_call_mcp(step, context)
        elif step.action == "delegate":
            return await self._step_delegate(step, context)
        else:
            raise ValueError(f"Unknown step action: {step.action}")

    async def _step_llm_think(self, step: SkillStep, context: dict[str, Any]) -> str:
        """Execute an LLM thinking step."""
        if not self.llm_func:
            return f"[MOCK] LLM think: {step.name}"

        # Build prompt with context
        prompt = step.prompt
        for ctx_key in step.context:
            if ctx_key in context:
                prompt += f"\n\n### {ctx_key}\n{context[ctx_key]}"

        # If template specified, load it
        if step.template:
            template_path = Path(step.template)
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    prompt += f"\n\n### Output Template\n{f.read()}"

        return await self.llm_func(prompt, context)

    async def _step_call_mcp(self, step: SkillStep, context: dict[str, Any]) -> Any:
        """Execute an MCP tool call."""
        if not self.mcp_client:
            return {"mock": True, "step": step.name, "tool": step.tool}

        # Resolve template variables in params
        params = self._resolve_params(step.params, context)

        tools = self.mcp_client.get_tools()
        for tool in tools:
            if tool.name == step.tool:
                return await tool.ainvoke(params)

        return {"error": f"Tool {step.tool} not found on server {step.server}"}

    async def _step_delegate(self, step: SkillStep, context: dict[str, Any]) -> Any:
        """Delegate to another agent's skill (placeholder — resolved by orchestrator)."""
        return {
            "delegated": True,
            "to": step.to,
            "skill": step.skill,
            "params": self._resolve_params(step.params, context),
        }

    def _resolve_params(
        self, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve {{variable}} templates in params using context."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and "{{" in value:
                # Simple template resolution: {{scope_definition.keywords}}
                import re
                def replacer(match):
                    path = match.group(1).strip()
                    parts = path.split(".")
                    obj = context
                    for part in parts:
                        if isinstance(obj, dict) and part in obj:
                            obj = obj[part]
                        else:
                            return match.group(0)  # Keep original if not found
                    return str(obj)

                resolved[key] = re.sub(r"\{\{(.+?)\}\}", replacer, value)
            else:
                resolved[key] = value
        return resolved
