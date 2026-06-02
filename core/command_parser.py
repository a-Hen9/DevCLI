"""Command Parser for natural language and slash commands."""
from dataclasses import dataclass
from enum import Enum

from devcli.db.models import Session


class CommandType(Enum):
    MODIFY_REQUIREMENT = "modify_requirement"
    ADD_FEATURE = "add_feature"
    ASK_QUESTION = "ask_question"
    SHOW_PLAN = "show_plan"
    STOP = "stop"
    RETRY = "retry"
    UNKNOWN = "unknown"


@dataclass
class Command:
    type: CommandType
    payload: dict


class CommandParser:
    async def parse(self, user_input: str, session: Session) -> Command:
        text = user_input.strip()

        if text.startswith("/"):
            return self._parse_slash(text)

        # Simple keyword-based parsing for MVP
        lowered = text.lower()
        if any(k in lowered for k in ["plan", "计划", "任务"]):
            return Command(CommandType.SHOW_PLAN, {})
        if any(k in lowered for k in ["stop", "暂停", "停止"]):
            return Command(CommandType.STOP, {})
        if any(k in lowered for k in ["retry", "重试", "再来"]):
            return Command(CommandType.RETRY, {})
        if any(k in lowered for k in ["add", "增加", "添加"]):
            return Command(CommandType.ADD_FEATURE, {"description": text})
        if any(k in lowered for k in ["?", "怎么", "为什么", "what", "how", "why"]):
            return Command(CommandType.ASK_QUESTION, {"question": text})

        return Command(CommandType.MODIFY_REQUIREMENT, {"text": text})

    def _parse_slash(self, text: str) -> Command:
        parts = text[1:].split()
        cmd = parts[0].lower()

        if cmd == "plan":
            return Command(CommandType.SHOW_PLAN, {})
        if cmd == "status":
            return Command(CommandType.SHOW_PLAN, {})
        if cmd == "stop":
            return Command(CommandType.STOP, {})
        if cmd == "retry":
            return Command(CommandType.RETRY, {})

        return Command(CommandType.UNKNOWN, {"raw": text})
