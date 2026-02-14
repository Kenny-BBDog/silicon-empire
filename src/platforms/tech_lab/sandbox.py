"""
技术中台 — Sandbox 沙盒执行器

安全地运行 AutoLab 生成的修复代码：
- 隔离执行环境 (subprocess + tempdir)
- 超时控制
- 输出/错误捕获
- 成功/失败判定
"""

from __future__ import annotations

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


class SandboxExecutor:
    """
    Safe code execution sandbox.
    
    所有代码在临时目录中运行，与主系统隔离。
    超时后自动 kill。
    """

    def __init__(self, timeout: int = 30, max_memory_mb: int = 256):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

    async def run_code(self, code: str, test_code: str = "") -> dict[str, Any]:
        """
        在沙盒中执行代码 + 测试。
        
        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "duration_ms": int,
            }
        """
        with tempfile.TemporaryDirectory(prefix="silicon_sandbox_") as tmpdir:
            # 写入代码
            code_path = os.path.join(tmpdir, "fix.py")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 写入测试
            if test_code:
                test_path = os.path.join(tmpdir, "test_fix.py")
                with open(test_path, "w", encoding="utf-8") as f:
                    f.write(test_code)

            # 执行
            if test_code:
                result = await self._run_pytest(tmpdir)
            else:
                result = await self._run_python(code_path)

            return result

    async def run_syntax_check(self, code: str) -> dict[str, Any]:
        """只做语法检查，不执行。"""
        with tempfile.TemporaryDirectory(prefix="silicon_syntax_") as tmpdir:
            code_path = os.path.join(tmpdir, "check.py")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)

            result = await self._run_command(
                ["python", "-m", "py_compile", code_path],
                cwd=tmpdir,
            )

            return {
                "valid_syntax": result["exit_code"] == 0,
                "errors": result["stderr"],
            }

    async def _run_python(self, code_path: str) -> dict[str, Any]:
        """Execute a Python file."""
        return await self._run_command(
            ["python", code_path],
            cwd=os.path.dirname(code_path),
        )

    async def _run_pytest(self, directory: str) -> dict[str, Any]:
        """Run pytest in the directory."""
        return await self._run_command(
            ["python", "-m", "pytest", "-v", "--tb=short", directory],
            cwd=directory,
        )

    async def _run_command(
        self, cmd: list[str], cwd: str
    ) -> dict[str, Any]:
        """Execute a command with timeout."""
        start = datetime.now(timezone.utc)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"TIMEOUT: exceeded {self.timeout}s limit",
                    "exit_code": -1,
                    "duration_ms": self.timeout * 1000,
                }

            elapsed = (datetime.now(timezone.utc) - start).total_seconds()

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5000],
                "exit_code": proc.returncode,
                "duration_ms": int(elapsed * 1000),
            }

        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Sandbox error: {str(e)}",
                "exit_code": -2,
                "duration_ms": 0,
            }
