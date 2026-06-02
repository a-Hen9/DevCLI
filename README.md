# DevCLI

AI-powered full-stack development agent with a terminal UI. Generate complete React + FastAPI + SQLite projects from natural language descriptions.

## Overview

DevCLI guides you through a 7-stage development lifecycle:

```
Requirement → Design → Planning → Implementation → Integration → Launch → Delivery
```

Each stage is driven by LLM reasoning (DashScope / Tongyi models) with real-time streaming output in a polished TUI.

## Features

- **Natural language input** — describe your project in Chinese or English, let AI plan and build it
- **TUI interface** — file tree with git status, streaming LLM output, stage navigation panel
- **7-stage lifecycle** — structured progression from requirement analysis to final delivery
- **Generate-Test-Fix loop** — automatic lint, test, and self-correction (up to 5 retries per task)
- **Model routing** — tasks are routed to different models by complexity (`qwen-turbo` / `qwen-plus`) for cost optimization
- **Local-only** — all code generation and testing runs on your machine, no cloud dependencies
- **Encrypted secrets** — API keys stored with Fernet symmetric encryption
- **SQLite persistence** — all session state, tasks, and artifacts survive restarts

## Installation

```bash
# Requires Python 3.11+
git clone https://github.com/a-Heng9/DevCLI.git
cd DevCLI
pip install -r requirements.txt
```

Or install as an editable package:

```bash
pip install -e .
```

## Configuration

Set your DashScope API key as an environment variable:

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

## Usage

### Launch the TUI

```bash
python -m devcli
```

Or with an initial requirement:

```bash
python -m devcli --requirement "Build a todo web app with user authentication"
python -m devcli --project-dir /path/to/output --requirement "Create a blog with markdown support"
```

### TUI Controls

| Key / Action | Description |
|---|---|
| Type + Enter | Send command or requirement |
| `q` | Quit |
| `r` | Focus input area |
| `n` | Advance to next stage |
| `s` | Show current status |

### Slash Commands

| Command | Description |
|---|---|
| `/plan` | Show generated task plan |
| `/status` | Show session, stage, tasks, and token usage |
| `/stop` | Stop current execution |
| `/retry` | Retry last failed task |

You can also use natural language: type "show plan", "stop", "retry", or ask questions like "how does this work?"

## Project Structure

```
DevCLI/
├── devcli/
│   ├── app.py              # Textual TUI application
│   ├── main.py             # CLI entry point
│   ├── config.py           # Model routing, retry, DB path config
│   ├── core/
│   │   ├── command_parser.py   # Natural language / slash command parsing
│   │   ├── lifecycle.py        # 7-stage state machine
│   │   ├── model_gateway.py    # LLM communication with streaming & retry
│   │   ├── session_manager.py  # Session & message persistence
│   │   ├── task_executor.py    # Generate → lint → test → fix loop
│   │   └── task_planner.py     # Design → ordered task list
│   ├── db/
│   │   ├── database.py         # SQLite CRUD operations
│   │   └── models.py           # Dataclass definitions
│   ├── tools/
│   │   ├── base.py             # Tool / ToolResult / ToolContext abstractions
│   │   ├── code.py             # tree-sitter AST parsing & code patching
│   │   ├── filesystem.py       # Sandboxed file read/write/list/delete
│   │   ├── git.py              # Async git operations
│   │   ├── lint.py             # ruff / black / eslint / prettier
│   │   ├── shell.py            # Sandeled shell execution
│   │   └── test.py             # pytest / vitest / playwright runners
│   └── utils/
│       └── crypto.py           # Fernet encryption for API keys
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Architecture

```
Textual TUI ──→ CommandParser ──→ LifecycleStateMachine
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ModelGateway      TaskPlanner       TaskExecutor
              (DashScope)     (design → tasks)   (gen → lint → test)
                    │                 │                 │
                    ▼                 ▼                 ▼
              SessionManager ←─── SQLite DB ───→ ToolContext
```

### Technology Stack

| Component | Choice |
|---|---|
| Runtime | Python 3.11+ |
| TUI | Textual |
| Database | SQLite + aiosqlite (WAL mode) |
| LLM | DashScope OpenAI-compatible API |
| Code Parsing | tree-sitter (Python, TypeScript) |
| Testing | pytest, Vitest, Playwright |
| Lint/Format | Ruff, Black, ESLint, Prettier |

### Model Routing

| Task Type | Model |
|---|---|
| Simple tasks / default | qwen-turbo |
| Design, generation, planning | qwen-plus |
| Complex debugging | qwen-plus |

### Generated Project Structure

Projects produced by DevCLI follow this layout:

```
<project-name>/
├── server/              # FastAPI backend
│   ├── src/             # models, routes, services, schemas
│   ├── tests/           # pytest
│   ├── alembic.ini
│   └── requirements.txt
├── client/              # React + Vite + TypeScript frontend
│   ├── src/             # components, pages, hooks, api
│   ├── tests/           # vitest
│   └── package.json
├── e2e/                 # Playwright E2E tests
├── README.md
├── DEV_PLAN.md
└── start.sh / start.bat
```

## License

MIT
