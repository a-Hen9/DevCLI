"""Test runner tools for pytest, vitest, and playwright."""
import asyncio
from pathlib import Path

from devcli.tools.base import Tool, ToolContext, ToolResult


class TestTool(Tool):
    name = "test"

    TEST_COMMANDS = {
        "pytest": "python -m pytest {path} -v --tb=short 2>&1",
        "vitest": "npx vitest run {path} --reporter=verbose 2>&1",
        "playwright": "npx playwright test {path} --reporter=list 2>&1",
    }

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        test_type = params.get("test_type", "pytest")
        path = params.get("path", ".")
        timeout = params.get("timeout", 120)

        if test_type not in self.TEST_COMMANDS:
            return ToolResult(success=False, error=f"Unknown test type: {test_type}")

        command = self.TEST_COMMANDS[test_type].format(path=path)
        return await self._run_test(command, context, timeout)

    async def _run_test(self, command: str, context: ToolContext, timeout: int) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=context.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")
            return ToolResult(
                success=proc.returncode == 0,
                output=output,
                error=error,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Test timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, error=f"Test runner not found for command: {command}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
