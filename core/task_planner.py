"""Task Planner: breaks a technical design into ordered tasks."""
import json
import uuid
from datetime import datetime

from devcli.core.model_gateway import ModelGateway
from devcli.core.session_manager import SessionManager
from devcli.db import database as db
from devcli.db.models import Session, Task, TaskStatus


class TaskPlanner:
    SYSTEM_PROMPT = (
        "You are a senior full-stack technical lead. "
        "Break the following technical design into a JSON array of atomic tasks. "
        "Each task must have: description (string), phase ('backend' or 'frontend'), "
        "file_paths (list of strings), and optionally dependencies (list of task indices). "
        "Backend tasks should come before frontend tasks.\n"
        "Return ONLY the JSON array, no markdown."
    )

    def __init__(self, gateway: ModelGateway, manager: SessionManager):
        self.gateway = gateway
        self.manager = manager

    async def generate_plan(self, session: Session) -> list[Task]:
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": session.requirement},
        ]
        response = await self.gateway.chat(messages, stream=False)
        try:
            tasks_data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback: empty plan
            tasks_data = []

        tasks = []
        for i, item in enumerate(tasks_data):
            task = Task(
                id=f"task_{uuid.uuid4().hex[:6]}",
                session_id=session.id,
                description=item.get("description", "Unnamed task"),
                phase=item.get("phase", "backend"),
                file_paths=item.get("file_paths", []),
                status=TaskStatus.PENDING,
                order_index=i,
                dependencies=item.get("dependencies", []),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            tasks.append(task)
            await db.create_task(task)
        return tasks
