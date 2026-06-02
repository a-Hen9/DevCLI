"""Git tools with async execution."""
import asyncio

from devcli.tools.base import Tool, ToolContext, ToolResult


class GitTool(Tool):
    name = "git"

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        action = params.get("action")
        timeout = params.get("timeout", 30)

        if action == "init":
            return await self._run(["init"], context, timeout)
        if action == "status":
            return await self._run(["status", "--porcelain"], context, timeout)
        if action == "commit":
            msg = params.get("message", "DevCLI commit")
            return await self._run(["add", "-A"], context, timeout) or await self._run(
                ["commit", "-m", msg], context, timeout
            )
        if action == "diff":
            return await self._run(["diff"], context, timeout)
        if action == "log":
            n = params.get("n", 10)
            return await self._run(["log", f"-{n}", "--oneline"], context, timeout)
        if action == "branch":
            return await self._run(["branch"], context, timeout)
        if action == "checkout":
            branch = params.get("branch", "")
            if not branch:
                return ToolResult(success=False, error="Branch name required for checkout")
            return await self._run(["checkout", branch], context, timeout)
        return ToolResult(success=False, error=f"Unknown action: {action}")

    async def _run(self, args: list[str], context: ToolContext, timeout: int = 30) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=context.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return ToolResult(
                success=proc.returncode == 0,
                output=stdout.decode("utf-8", errors="replace"),
                error=stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Git command timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, error="Git not found in PATH")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
