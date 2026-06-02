"""Session Manager for persisting project development state."""
import uuid
from datetime import datetime

from devcli.config import DB_PATH
from devcli.db import database as db
from devcli.db.models import Artifact, Message, MessageType, Session, Stage, Task, TaskStatus


class SessionManager:
    async def create_session(self, project_dir: str, requirement: str, name: str = "") -> str:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        session = Session(
            id=session_id,
            name=name or session_id,
            project_dir=project_dir,
            requirement=requirement,
            current_stage=Stage.REQUIREMENT,
            created_at=now,
            updated_at=now,
        )
        await db.create_session(session)
        return session_id

    async def load_session(self, session_id: str) -> Session | None:
        return await db.get_session(session_id)

    async def save_progress(self, session_id: str, stage: Stage, data: dict) -> None:
        await db.update_session_stage(session_id, stage)
        if data:
            artifact = Artifact(
                session_id=session_id,
                stage=stage.value,
                type=data.get("type", "generic"),
                content=data.get("content", ""),
                file_path=data.get("file_path", ""),
                created_at=datetime.now().isoformat(),
            )
            await db.save_artifact(artifact)

    async def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        await db.update_task_status(task_id, status)

    async def get_session(self, session_id: str) -> Session | None:
        return await db.get_session(session_id)

    async def add_message(self, session_id: str, role: str, content: str, msg_type: str = "chat") -> None:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            type=MessageType(msg_type) if msg_type in [m.value for m in MessageType] else MessageType.CHAT,
            timestamp=datetime.now().isoformat(),
        )
        await db.add_message(msg)

    async def get_messages(self, session_id: str) -> list[Message]:
        return await db.get_messages_by_session(session_id)
