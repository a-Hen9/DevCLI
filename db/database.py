"""Database initialization and CRUD operations."""
import json
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

from devcli.config import DB_PATH
from devcli.db.models import Artifact, Message, Session, Stage, Task, TaskStatus

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_dir TEXT NOT NULL,
    requirement TEXT,
    tech_stack TEXT,
    current_stage TEXT NOT NULL DEFAULT 'requirement',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    phase TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    order_index INTEGER NOT NULL,
    dependencies TEXT,
    file_paths TEXT DEFAULT '[]',
    attempts INTEGER DEFAULT 0,
    result TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'chat',
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT,
    file_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_session_status ON tasks(session_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_session_order ON tasks(session_id, order_index);
CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_artifacts_session_stage ON artifacts(session_id, stage);
"""


async def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        await _migrate_db(db)
        await db.commit()


async def _migrate_db(db: aiosqlite.Connection) -> None:
    """Apply incremental migrations for existing databases."""
    cursor = await db.execute("PRAGMA user_version")
    version = (await cursor.fetchone())[0]

    if version < 2:
        try:
            await db.execute(
                "ALTER TABLE tasks ADD COLUMN file_paths TEXT DEFAULT '[]'"
            )
        except Exception:
            pass
        await db.execute("PRAGMA user_version = 2;")


async def create_session(session: Session) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, name, project_dir, requirement, tech_stack, current_stage, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.id,
                session.name,
                session.project_dir,
                session.requirement,
                json.dumps(session.tech_stack),
                session.current_stage.value,
                session.created_at,
                session.updated_at,
            ),
        )
        await db.commit()


async def get_session(session_id: str) -> Session | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Session(
                id=row["id"],
                name=row["name"],
                project_dir=row["project_dir"],
                requirement=row["requirement"] or "",
                tech_stack=json.loads(row["tech_stack"] or "{}"),
                current_stage=Stage(row["current_stage"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


async def update_session_stage(session_id: str, stage: Stage) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET current_stage = ?, updated_at = ? WHERE id = ?",
            (stage.value, datetime.now().isoformat(), session_id),
        )
        await db.commit()


async def create_task(task: Task) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks (id, session_id, description, phase, status, order_index, dependencies, file_paths, attempts, result, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task.id,
                task.session_id,
                task.description,
                task.phase,
                task.status.value,
                task.order_index,
                json.dumps(task.dependencies),
                json.dumps(getattr(task, "file_paths", [])),
                task.attempts,
                json.dumps(task.result),
                task.created_at,
                task.updated_at,
            ),
        )
        await db.commit()


async def get_tasks_by_session(session_id: str) -> list[Task]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE session_id = ? ORDER BY order_index ASC",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Task(
                    id=row["id"],
                    session_id=row["session_id"],
                    description=row["description"],
                    phase=row["phase"],
                    status=TaskStatus(row["status"]),
                    order_index=row["order_index"],
                    dependencies=json.loads(row["dependencies"] or "[]"),
                    file_paths=json.loads(row["file_paths"] if row["file_paths"] else "[]") if "file_paths" in dict(row) else [],
                    attempts=row["attempts"],
                    result=json.loads(row["result"] or "{}"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]


async def update_task_status(task_id: str, status: TaskStatus) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, datetime.now().isoformat(), task_id),
        )
        await db.commit()


async def add_message(message: Message) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, type, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                message.session_id,
                message.role,
                message.content,
                message.type.value,
                message.timestamp,
            ),
        )
        await db.commit()


async def get_messages_by_session(session_id: str) -> list[Message]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Message(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    type=row["type"],
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]


async def save_artifact(artifact: Artifact) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO artifacts (id, session_id, stage, type, content, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                artifact.id or f"artf_{uuid.uuid4().hex[:8]}",
                artifact.session_id,
                artifact.stage,
                artifact.type,
                artifact.content,
                artifact.file_path,
                artifact.created_at or datetime.now().isoformat(),
            ),
        )
        await db.commit()


async def get_artifacts_by_session_and_stage(session_id: str, stage: str) -> list[Artifact]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM artifacts WHERE session_id = ? AND stage = ? ORDER BY created_at DESC",
            (session_id, stage),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Artifact(
                    id=row["id"],
                    session_id=row["session_id"],
                    stage=row["stage"],
                    type=row["type"],
                    content=row["content"],
                    file_path=row["file_path"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat()),
        )
        await db.commit()
