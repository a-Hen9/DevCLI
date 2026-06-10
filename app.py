"""DevCLI Textual TUI application."""
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Header, Input, RichLog, Static

from devcli.core.command_parser import CommandParser, CommandType
from devcli.core.lifecycle import LifecycleStateMachine
from devcli.core.model_gateway import ModelGateway
from devcli.core.session_manager import SessionManager
from devcli.db import database as db
from devcli.db.models import Stage


class DevCLIApp(App):
    """Main TUI application for DevCLI."""

    CSS = """
    #main-layout {
        layout: horizontal;
        height: 1fr;
    }
    #content {
        width: 100%;
        border: solid blue;
    }
    #stage-display {
        width: 20;
        border: solid yellow;
        padding: 0 1;
        content-align: center middle;
    }
    #status-bar {
        height: 3;
        border: solid red;
        content-align: center middle;
    }
    #input-area {
        height: 3;
        layout: horizontal;
    }
    #user-input {
        width: 1fr;
    }
    #send-btn {
        width: 10;
    }
    .stage-active {
        color: green;
        text-style: bold;
    }
    #markdown-view {
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "focus_input", "Focus Input"),
        ("n", "advance_stage", "Next Stage"),
        ("s", "show_status", "Status"),
    ]

    def __init__(self, session_id: str | None = None, project_dir: str | None = None, requirement: str = "") -> None:
        super().__init__()
        self.session_id = session_id
        self.project_dir = project_dir or str(Path.cwd())
        self.requirement = requirement
        self.session_manager = SessionManager()
        self.model_gateway = ModelGateway()
        self.command_parser = CommandParser()
        self.state_machine: LifecycleStateMachine | None = None
        self._current_stage = None

    async def on_mount(self) -> None:
        await db.init_db()
        if not self.session_id:
            self.session_id = await self.session_manager.create_session(
                project_dir=self.project_dir,
                requirement=self.requirement,
                name="New Project",
            )
        self.state_machine = LifecycleStateMachine(
            self.session_id, self.session_manager, self.model_gateway
        )
        self.set_timer(1.0, self._update_stage_display)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="content"):
                yield RichLog(id="main-log", markup=True, highlight=True, auto_scroll=True)
        with Horizontal(id="status-bar"):
            yield Static("Ready", id="status")
        with Horizontal(id="input-area"):
            yield Input(placeholder="Enter command or requirement...", id="user-input")
            yield Button("Send", id="send-btn", variant="primary")
            yield Static("", id="stage-display")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            await self._handle_input()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "user-input":
            await self._handle_input()

    async def _handle_input(self) -> None:
        input_widget = self.query_one("#user-input", Input)
        user_text = input_widget.value.strip()
        if not user_text:
            return
        input_widget.value = ""

        log = self.query_one("#main-log", RichLog)
        log.write(f"[bold cyan]User:[/bold cyan] {user_text}")

        session = await self.session_manager.get_session(self.session_id)
        if not session:
            log.write("[red]Error: Session not found[/red]")
            return

        # Store user message
        await self.session_manager.add_message(self.session_id, "user", user_text)

        command = await self.command_parser.parse(user_text, session)
        log.write(f"[dim]Command: {command.type.value}[/dim]")

        if command.type == CommandType.SHOW_PLAN:
            await self._show_plan(log)
        elif command.type == CommandType.MODIFY_REQUIREMENT:
            await self._handle_requirement(user_text, log)
        elif command.type == CommandType.ADD_FEATURE:
            await self._handle_add_feature(command.payload.get("description", ""), log)
        elif command.type == CommandType.ASK_QUESTION:
            await self._handle_question(command.payload.get("question", ""), log)
        elif command.type == CommandType.STOP:
            log.write("[yellow]Execution stopped.[/yellow]")
        elif command.type == CommandType.RETRY:
            await self._handle_retry(log)
        else:
            log.write("Command processed.")

    async def _show_plan(self, log: RichLog) -> None:
        tasks = await db.get_tasks_by_session(self.session_id)
        if tasks:
            for t in tasks:
                status_color = {
                    "completed": "green",
                    "in_progress": "yellow",
                    "failed": "red",
                    "pending": "white",
                    "skipped": "dim",
                }.get(t.status.value, "white")
                log.write(
                    f"  [{'status_color'}]{t.phase}:[/{'status_color'}] "
                    f"{t.description} ([{status_color}]{t.status.value}[/{status_color}])"
                )
        else:
            log.write("[dim]No tasks planned yet. Use /plan to generate a plan.[/dim]")

    async def _handle_requirement(self, text: str, log: RichLog) -> None:
        log.write("[cyan]Analyzing requirement...[/cyan]")
        session = await self.session_manager.get_session(self.session_id)
        if not session:
            return

        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Respond concisely.",
            },
            {"role": "user", "content": text},
        ]

        try:
            response = await self.model_gateway.chat(messages, stream=True)
            log.write(f"[bold green]Assistant:[/bold green]")
            full_response = ""
            async for chunk in response:
                full_response += chunk
                log.write(chunk)
            await self.session_manager.add_message(self.session_id, "assistant", full_response)
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    async def _handle_add_feature(self, description: str, log: RichLog) -> None:
        log.write(f"[cyan]Adding feature: {description}[/cyan]")
        session = await self.session_manager.get_session(self.session_id)
        if not session:
            return

        messages = [
            {
                "role": "system",
                "content": "You are a technical lead. Analyze the feature request and suggest implementation steps.",
            },
            {"role": "user", "content": description},
        ]

        try:
            response = await self.model_gateway.chat(messages, stream=True)
            log.write("[bold green]Assistant:[/bold green]")
            full_response = ""
            async for chunk in response:
                full_response += chunk
                log.write(chunk)
            await self.session_manager.add_message(self.session_id, "assistant", full_response)
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    async def _handle_question(self, question: str, log: RichLog) -> None:
        log.write(f"[cyan]Answering: {question}[/cyan]")

        messages = [
            {
                "role": "system",
                "content": "You are a helpful technical assistant. Answer the user's question concisely.",
            },
            {"role": "user", "content": question},
        ]

        try:
            response = await self.model_gateway.chat(messages, stream=True)
            log.write("[bold green]Assistant:[/bold green]")
            full_response = ""
            async for chunk in response:
                full_response += chunk
                log.write(chunk)
            await self.session_manager.add_message(self.session_id, "assistant", full_response)
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    async def _handle_retry(self, log: RichLog) -> None:
        log.write("[cyan]Retrying last failed task...[/cyan]")
        tasks = await db.get_tasks_by_session(self.session_id)
        failed = [t for t in tasks if t.status.value == "failed"]
        if not failed:
            log.write("[dim]No failed tasks to retry.[/dim]")
            return
        last_failed = failed[-1]
        log.write(f"  Retrying: {last_failed.description}")
        await db.update_task_status(last_failed.id, __import__("devcli.db.models", fromlist=["TaskStatus"]).TaskStatus.PENDING)
        log.write("[green]Task reset to pending.[/green]")

    async def _update_stage_display(self) -> None:
        """Update stage display with current stage."""
        session = await self.session_manager.get_session(self.session_id)
        if not session:
            return

        current_stage = session.current_stage
        display = self.query_one("#stage-display", Static)
        display.update(f"[bold green]▶ {current_stage.value}[/bold green]")

        status = self.query_one("#status", Static)
        status.update(f"Session: {self.session_id} | Stage: [bold]{current_stage.value}[/bold]")

        self._current_stage = current_stage

    async def action_advance_stage(self) -> None:
        """Advance to the next stage."""
        if not self.state_machine:
            return
        log = self.query_one("#main-log", RichLog)
        try:
            next_stage = await self.state_machine.advance()
            log.write(f"[green]Advanced to stage: {next_stage.value}[/green]")
            await self._update_stage_display()
        except Exception as e:
            log.write(f"[red]Cannot advance stage: {e}[/red]")

    async def action_show_status(self) -> None:
        """Show current status."""
        log = self.query_one("#main-log", RichLog)
        session = await self.session_manager.get_session(self.session_id)
        if not session:
            log.write("[red]No active session.[/red]")
            return

        log.write(f"[bold]Session:[/bold] {self.session_id}")
        log.write(f"[bold]Stage:[/bold] {session.current_stage.value}")
        log.write(f"[bold]Project:[/bold] {session.project_dir}")

        tasks = await db.get_tasks_by_session(self.session_id)
        if tasks:
            log.write(f"[bold]Tasks:[/bold] {len(tasks)} total")
            for t in tasks:
                log.write(f"  [{t.status.value}] {t.description}")
        else:
            log.write("[dim]No tasks yet.[/dim]")

        usage = self.model_gateway.get_usage()
        log.write(f"[bold]Token Usage:[/bold] {usage.get('total_tokens', 0)} total")

    def action_focus_input(self) -> None:
        self.query_one("#user-input", Input).focus()
