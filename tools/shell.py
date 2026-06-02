"""Shell execution tool."""
import asyncio

from devcli.tools.base import Tool, ToolContext, ToolResult


class ShellTool(Tool):
    name = "shell"

    DANGEROUS = {"rm", "dd", "mkfs", "format", "del", "format"}

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        command = params.get("command", "")
        cwd = params.get("cwd", context.work_dir)
        timeout = params.get("timeout", 60)

        # Security check
        parts = command.split()
        if parts and parts[0] in self.DANGEROUS:
            return ToolResult(success=False, error=f"Dangerous command blocked: {command}")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
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
            return ToolResult(success=False, error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
