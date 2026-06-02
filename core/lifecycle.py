"""Lifecycle State Machine for controlling the development flow."""
from devcli.core.model_gateway import ModelGateway
from devcli.core.session_manager import SessionManager
from devcli.core.task_planner import TaskPlanner
from devcli.core.task_executor import TaskExecutor
from devcli.db.models import Session, Stage


class StageTransitionError(Exception):
    pass


class LifecycleStateMachine:
    STAGES = [
        Stage.REQUIREMENT,
        Stage.DESIGN,
        Stage.PLANNING,
        Stage.IMPLEMENTATION,
        Stage.INTEGRATION,
        Stage.LAUNCH,
        Stage.DELIVERY,
    ]

    def __init__(
        self,
        session_id: str,
        manager: SessionManager,
        gateway: ModelGateway | None = None,
    ):
        self.session_id = session_id
        self.manager = manager
        self.gateway = gateway or ModelGateway()
        self.planner = TaskPlanner(self.gateway, manager)
        self.executor = TaskExecutor(self.gateway, manager)
        self._current: Stage | None = None

    async def get_current(self) -> Stage:
        if self._current is None:
            session = await self.manager.get_session(self.session_id)
            self._current = session.current_stage if session else Stage.REQUIREMENT
        return self._current

    async def advance(self) -> Stage:
        current = await self.get_current()
        idx = self.STAGES.index(current)
        if idx >= len(self.STAGES) - 1:
            raise StageTransitionError("Already at the final stage.")
        next_stage = self.STAGES[idx + 1]
        await self._transition_to(next_stage)
        self._current = next_stage
        return next_stage

    async def goto_stage(self, stage: Stage) -> Stage:
        if stage not in self.STAGES:
            raise StageTransitionError(f"Invalid stage: {stage}")
        current = await self.get_current()
        current_idx = self.STAGES.index(current)
        target_idx = self.STAGES.index(stage)
        if target_idx < current_idx:
            raise StageTransitionError("Cannot go backwards through stages.")
        await self._transition_to(stage)
        self._current = stage
        return stage

    async def _transition_to(self, stage: Stage) -> None:
        session = await self.manager.get_session(self.session_id)
        if not session:
            raise StageTransitionError("Session not found.")

        entry_action = self._get_entry_action(stage)
        artifact = await entry_action(session)
        await self.manager.save_progress(
            self.session_id,
            stage,
            {"type": stage.value, "content": artifact},
        )

    def _get_entry_action(self, stage: Stage):
        actions = {
            Stage.REQUIREMENT: self._analyze_requirement,
            Stage.DESIGN: self._generate_design,
            Stage.PLANNING: self._generate_plan,
            Stage.IMPLEMENTATION: self._execute_tasks,
            Stage.INTEGRATION: self._run_integration,
            Stage.LAUNCH: self._prepare_launch,
            Stage.DELIVERY: self._deliver,
        }
        return actions[stage]

    async def _analyze_requirement(self, session: Session) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a product analyst. Analyze the user's requirement and produce "
                    "a structured requirements document with: user stories, acceptance criteria, "
                    "and functional/non-functional requirements. Return as plain text."
                ),
            },
            {"role": "user", "content": session.requirement},
        ]
        return await self.gateway.chat(messages, stream=False)

    async def _generate_design(self, session: Session) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior software architect. Based on the requirements, produce "
                    "a technical design document including: architecture overview, API design, "
                    "database schema, and technology choices. Return as plain text."
                ),
            },
            {"role": "user", "content": session.requirement},
        ]
        return await self.gateway.chat(
            messages, model=self.gateway.route_model("design"), stream=False
        )

    async def _generate_plan(self, session: Session) -> str:
        tasks = await self.planner.generate_plan(session)
        lines = []
        for t in tasks:
            lines.append(f"- [{t.phase}] {t.description} (status: {t.status.value})")
        return "\n".join(lines)

    async def _execute_tasks(self, session: Session) -> str:
        from devcli.db.database import get_tasks_by_session

        tasks = await get_tasks_by_session(self.session_id)
        results = []
        for task in tasks:
            if task.status.value == "completed":
                continue
            result = await self.executor.execute_task(task, session)
            status = "OK" if result.success else "FAIL"
            results.append(f"[{status}] {task.description}")
        return "\n".join(results)

    async def _run_integration(self, session: Session) -> str:
        result = await self.executor.run_tests("pytest", session)
        return f"Integration tests: {result.get('output', 'no output')}"

    async def _prepare_launch(self, session: Session) -> str:
        return "Launch preparation complete. Run manual checks before deployment."

    async def _deliver(self, session: Session) -> str:
        return "Project delivered successfully."

    def can_advance(self) -> bool:
        return True
