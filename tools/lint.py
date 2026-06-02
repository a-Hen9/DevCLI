"""Lint and format tools using real subprocess execution."""
import asyncio

from devcli.tools.base import Tool, ToolContext, ToolResult


class LintTool(Tool):
    name = "lint"

    LINT_COMMANDS = {
        "ruff": "python -m ruff check {path} 2>&1",
        "black": "python -m black --check {path} 2>&1",
        "eslint": "npx eslint {path} 2>&1",
        "prettier": "npx prettier --check {path} 2>&1",
    }

    FIX_COMMANDS = {
        "ruff": "python -m ruff check --fix {path} 2>&1",
        "black": "python -m black {path} 2>&1",
        "eslint": "npx eslint --fix {path} 2>&1",
        "prettier": "npx prettier --write {path} 2>&1",
    }

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        tool = params.get("tool", "")
        path = params.get("path", ".")
        fix = params.get("fix", False)
        timeout = params.get("timeout", 60)

        if tool not in self.LINT_COMMANDS:
            return ToolResult(success=False, error=f"Unknown lint tool: {tool}")

        commands = self.FIX_COMMANDS if fix else self.LINT_COMMANDS
        command = commands[tool].format(path=path)
        return await self._run_command(command, context, timeout)

    async def _run_command(self, command: str, context: ToolContext, timeout: int) -> ToolResult:
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
            return ToolResult(success=False, error=f"Lint command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
