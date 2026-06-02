"""Database models for DevCLI."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Stage(Enum):
    REQUIREMENT = "requirement"
    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    INTEGRATION = "integration"
    LAUNCH = "launch"
    DELIVERY = "delivery"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class MessageType(Enum):
    CHAT = "chat"
    COMMAND = "command"
    SYSTEM = "system"


@dataclass
class Session:
    id: str
    name: str
    project_dir: str
    requirement: str = ""
    tech_stack: dict = field(default_factory=dict)
    current_stage: Stage = Stage.REQUIREMENT
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Task:
    id: str
    session_id: str
    description: str
    phase: str
    file_paths: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    order_index: int = 0
    dependencies: list = field(default_factory=list)
    attempts: int = 0
    result: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Message:
    id: int = 0
    session_id: str = ""
    role: str = ""
    content: str = ""
    type: MessageType = MessageType.CHAT
    timestamp: str = ""


@dataclass
class Artifact:
    id: str = ""
    session_id: str = ""
    stage: str = ""
    type: str = ""
    content: str = ""
    file_path: str = ""
    created_at: str = ""
