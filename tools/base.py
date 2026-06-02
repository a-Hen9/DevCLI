"""Base Tool abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolContext:
    work_dir: str
    session_id: str


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""


class Tool(ABC):
    name: str = "base"

    @abstractmethod
    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        ...
