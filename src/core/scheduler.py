"""
Background Scheduler — Agent 的「心跳」。

没有调度器，Agent 永远是被动等命令的 chat 模型。
有了调度器，Agent 才真正"活"起来 — 自己上班、自己巡检、自己汇报。

定时任务:
- 每 5 分钟: 处理所有 Agent 的 inbox (消息不积压)
- 每 6 小时: Data Hunter 扫描市场趋势
- 每 24 小时: 全员自省 + GM 整理需求报告
- 每 48 小时: 触发集体进化讨论
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger("scheduler")


# ─── 任务注册表 ───

class ScheduledJob:
    """一个定时任务。"""

    def __init__(
        self,
        name: str,
        func: Callable[..., Awaitable[Any]],
        interval_seconds: int,
        description: str = "",
        enabled: bool = True,
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.description = description
        self.enabled = enabled
        self.last_run: str | None = None
        self.run_count: int = 0
        self.last_error: str | None = None


_jobs: dict[str, ScheduledJob] = {}
_running = False
_task: asyncio.Task | None = None


def register_job(
    name: str,
    func: Callable[..., Awaitable[Any]],
    interval_seconds: int,
    description: str = "",
) -> None:
    """注册一个定时任务。"""
    _jobs[name] = ScheduledJob(
        name=name,
        func=func,
        interval_seconds=interval_seconds,
        description=description,
    )
    logger.info(f"Registered job: {name} (every {interval_seconds}s)")


def unregister_job(name: str) -> None:
    """取消一个定时任务。"""
    _jobs.pop(name, None)


def list_jobs() -> list[dict[str, Any]]:
    """列出所有定时任务及其状态。"""
    return [
        {
            "name": j.name,
            "interval": j.interval_seconds,
            "description": j.description,
            "enabled": j.enabled,
            "last_run": j.last_run,
            "run_count": j.run_count,
            "last_error": j.last_error,
        }
        for j in _jobs.values()
    ]


# ─── 调度循环 ───

async def _scheduler_loop():
    """主调度循环 — 每秒检查一次是否有任务到期。"""
    # 记录每个 job 上次运行的时间戳
    last_runs: dict[str, float] = {}

    while _running:
        now = asyncio.get_event_loop().time()

        for name, job in list(_jobs.items()):
            if not job.enabled:
                continue

            last = last_runs.get(name, 0)
            if now - last >= job.interval_seconds:
                last_runs[name] = now
                # 异步执行，不阻塞调度循环
                asyncio.create_task(_run_job(job))

        await asyncio.sleep(1)


async def _run_job(job: ScheduledJob):
    """安全执行一个定时任务。"""
    try:
        logger.info(f"Running job: {job.name}")
        await job.func()
        job.last_run = datetime.now(timezone.utc).isoformat()
        job.run_count += 1
        job.last_error = None
    except Exception as e:
        job.last_error = str(e)[:200]
        logger.error(f"Job {job.name} failed: {e}")


# ─── 启动/停止 ───

async def start_scheduler():
    """启动调度器。在应用启动时调用。"""
    global _running, _task
    if _running:
        return

    _running = True

    # 注册默认任务
    _register_default_jobs()

    _task = asyncio.create_task(_scheduler_loop())
    logger.info(f"Scheduler started with {len(_jobs)} jobs")


async def stop_scheduler():
    """停止调度器。"""
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    logger.info("Scheduler stopped")


# ─── 默认任务 ───

def _register_default_jobs():
    """注册系统默认的定时任务。"""

    # 1. 每 5 分钟: 处理 inbox
    register_job(
        "inbox_processor",
        _process_all_inboxes,
        interval_seconds=300,
        description="处理所有 Agent 的收件箱消息",
    )

    # 2. 每 6 小时: 趋势扫描
    register_job(
        "trend_scan",
        _trigger_trend_scan,
        interval_seconds=21600,
        description="Data Hunter 扫描市场趋势",
    )

    # 3. 每 24 小时: 全员自省
    register_job(
        "daily_reflection",
        _trigger_daily_reflection,
        interval_seconds=86400,
        description="全员自省 + GM 需求整理",
    )

    # 4. 每 48 小时: 进化讨论
    register_job(
        "evolution_cycle",
        _trigger_evolution,
        interval_seconds=172800,
        description="触发集体进化讨论",
    )


# ─── 默认任务实现 ───

async def _process_all_inboxes():
    """处理所有 Agent 的收件箱。"""
    from src.core.agent_bus import peek_inbox

    roles = ["gm", "cgo", "coo", "cro", "cto",
             "l3_data_hunter", "l3_insight_analyst", "l3_copy_master",
             "l3_architect", "l4_autolab"]

    for role in roles:
        messages = peek_inbox(role)
        if messages:
            logger.info(f"{role} has {len(messages)} pending messages")
            # 延迟导入避免循环依赖
            try:
                from src.agents import get_agent_by_role
                agent = get_agent_by_role(role)
                if agent:
                    await agent.check_inbox()
            except Exception as e:
                logger.error(f"inbox processing failed for {role}: {e}")


async def _trigger_trend_scan():
    """触发趋势扫描。"""
    try:
        from src.platforms.data_intel.hunter import DataHunterAgent
        hunter = DataHunterAgent()
        await hunter.discover_trends()
        logger.info("Trend scan completed")
    except Exception as e:
        logger.error(f"Trend scan failed: {e}")


async def _trigger_daily_reflection():
    """触发全员自省。"""
    try:
        from src.core.hooks import periodic_reflection_hook, compile_needs_report

        # 延迟导入
        from src.agents import get_all_chiefs
        chiefs = get_all_chiefs()

        for agent in chiefs:
            try:
                await agent.initialize()
                await periodic_reflection_hook(agent)
            except Exception as e:
                logger.error(f"Reflection failed for {agent.ROLE}: {e}")

        # GM 整理需求报告
        report = await compile_needs_report()
        if "没有待处理" not in report:
            logger.info(f"Needs report: {report[:200]}")
            # TODO: 推送到飞书

    except Exception as e:
        logger.error(f"Daily reflection failed: {e}")


async def _trigger_evolution():
    """触发集体进化。"""
    try:
        from src.graphs.evolution import build_evolution_graph
        graph = build_evolution_graph()
        result = await graph.ainvoke({
            "strategic_intent": "定期自省: 系统有哪些可以改进的地方？",
            "intent_category": "EVOLUTION",
        })
        logger.info(f"Evolution cycle completed")
    except Exception as e:
        logger.error(f"Evolution cycle failed: {e}")
