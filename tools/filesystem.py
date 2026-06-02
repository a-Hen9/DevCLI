"""File system tools."""
import os
from pathlib import Path

from devcli.tools.base import Tool, ToolContext, ToolResult


class FileSystemTool(Tool):
    name = "filesystem"

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        action = params.get("action")
        if action == "read":
            return await self.read_file(params["path"], context)
        if action == "write":
            return await self.write_file(params["path"], params["content"], context)
        if action == "list":
            return await self.list_directory(params["path"], context)
        if action == "delete":
            return await self.delete_file(params["path"], context)
        return ToolResult(success=False, error=f"Unknown action: {action}")

    @staticmethod
    def _resolve(path: str, context: ToolContext) -> Path:
        resolved = Path(context.work_dir) / path
        try:
            resolved.resolve().relative_to(Path(context.work_dir).resolve())
        except ValueError:
            raise PermissionError("Path escapes working directory")
        return resolved

    async def read_file(self, path: str, context: ToolContext) -> ToolResult:
        try:
            target = self._resolve(path, context)
            content = target.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def write_file(self, path: str, content: str, context: ToolContext) -> ToolResult:
        try:
            target = self._resolve(path, context)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Written {target}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def list_directory(self, path: str, context: ToolContext) -> ToolResult:
        try:
            target = self._resolve(path, context)
            entries = []
            for entry in target.iterdir():
                entries.append(f"{'D' if entry.is_dir() else 'F'} {entry.name}")
            return ToolResult(success=True, output="\n".join(entries))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def delete_file(self, path: str, context: ToolContext) -> ToolResult:
        try:
            target = self._resolve(path, context)
            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            else:
                target.unlink()
            return ToolResult(success=True, output=f"Deleted {target}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
