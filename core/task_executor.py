"""Task Executor: runs individual tasks with generate-test-fix loop."""
import asyncio
import json
from dataclasses import dataclass, field

from devcli.core.model_gateway import ModelGateway
from devcli.core.session_manager import SessionManager
from devcli.db.models import Session, Task, TaskStatus
from devcli.tools.filesystem import FileSystemTool
from devcli.tools.shell import ShellTool
from devcli.tools.lint import LintTool
from devcli.tools.test import TestTool
from devcli.tools.base import ToolContext
from devcli.config import MAX_TASK_RETRIES


@dataclass
class TaskResult:
    success: bool
    files_generated: list[str] = field(default_factory=list)
    test_output: str = ""
    lint_output: str = ""
    error: str = ""
    attempts: int = 0


class TaskExecutor:
    CODE_GEN_PROMPT = (
        "You are a senior full-stack developer. Generate production-ready code for the following task. "
        "Return ONLY the code, no explanations or markdown fences. "
        "The code must be complete and ready to run."
    )

    FIX_PROMPT = (
        "The following code has errors. Fix them and return the corrected code. "
        "Return ONLY the corrected code, no explanations or markdown fences.\n\n"
        "Original code:\n{code}\n\nErrors:\n{errors}"
    )

    def __init__(self, gateway: ModelGateway, manager: SessionManager):
        self.gateway = gateway
        self.manager = manager
        self.fs = FileSystemTool()
        self.shell = ShellTool()
        self.lint = LintTool()
        self.test = TestTool()

    async def execute_task(self, task: Task, session: Session) -> TaskResult:
        await self.manager.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        context = ToolContext(work_dir=session.project_dir, session_id=session.id)
        files_generated: list[str] = []

        for attempt in range(MAX_TASK_RETRIES + 1):
            try:
                code = await self._generate_code(task, session, attempt)
                files = await self._write_code(code, task, context)
                files_generated.extend(files)

                lint_result = await self._run_lint(files, context)
                if not lint_result.success:
                    if attempt < MAX_TASK_RETRIES:
                        continue
                    return TaskResult(
                        success=False,
                        files_generated=files_generated,
                        lint_output=lint_result.output,
                        error=f"Lint failed after {MAX_TASK_RETRIES} retries: {lint_result.error}",
                        attempts=attempt + 1,
                    )

                test_result = await self._run_tests(task, context)
                if not test_result.success:
                    if attempt < MAX_TASK_RETRIES:
                        continue
                    return TaskResult(
                        success=False,
                        files_generated=files_generated,
                        test_output=test_result.output,
                        error=f"Tests failed after {MAX_TASK_RETRIES} retries: {test_result.error}",
                        attempts=attempt + 1,
                    )

                await self.manager.update_task_status(task.id, TaskStatus.COMPLETED)
                return TaskResult(
                    success=True,
                    files_generated=files_generated,
                    test_output=test_result.output,
                    lint_output=lint_result.output,
                    attempts=attempt + 1,
                )
            except Exception as e:
                if attempt == MAX_TASK_RETRIES:
                    await self.manager.update_task_status(task.id, TaskStatus.FAILED)
                    return TaskResult(
                        success=False,
                        files_generated=files_generated,
                        error=str(e),
                        attempts=attempt + 1,
                    )

        await self.manager.update_task_status(task.id, TaskStatus.FAILED)
        return TaskResult(success=False, error="Max retries exceeded", attempts=MAX_TASK_RETRIES + 1)

    async def _generate_code(self, task: Task, session: Session, attempt: int) -> str:
        prompt = f"Task: {task.description}\n\nProject context: {session.requirement}"
        if attempt > 0:
            prompt += f"\n\nThis is attempt {attempt + 1}. Previous attempts failed. Please try a different approach."

        messages = [
            {"role": "system", "content": self.CODE_GEN_PROMPT},
            {"role": "user", "content": prompt},
        ]
        model = self.gateway.route_model("generation")
        response = await self.gateway.chat(messages, model=model, stream=False)
        return response

    async def _write_code(self, code: str, task: Task, context: ToolContext) -> list[str]:
        files = []
        if hasattr(task, "file_paths") and task.file_paths:
            for path in task.file_paths:
                result = await self.fs.write_file(path, code, context)
                if result.success:
                    files.append(path)
        else:
            filename = f"generated_{task.id}.py"
            result = await self.fs.write_file(filename, code, context)
            if result.success:
                files.append(filename)
        return files

    async def _run_lint(self, files: list[str], context: ToolContext) -> "ToolResult":
        from devcli.tools.base import ToolResult
        if not files:
            return ToolResult(success=True, output="No files to lint")
        is_python = any(f.endswith(".py") for f in files)
        tool_name = "ruff" if is_python else "eslint"
        return await self.lint.execute({"tool": tool_name, "path": "."}, context)

    async def _run_tests(self, task: Task, context: ToolContext) -> "ToolResult":
        from devcli.tools.base import ToolResult
        test_type = "pytest" if task.phase == "backend" else "vitest"
        return await self.test.execute({"test_type": test_type, "path": "."}, context)

    async def run_tests(self, test_type: str, session: Session) -> dict:
        context = ToolContext(work_dir=session.project_dir, session_id=session.id)
        result = await self.test.execute({"test_type": test_type, "path": "."}, context)
        return {"passed": 0, "failed": 0, "output": result.output, "success": result.success}
