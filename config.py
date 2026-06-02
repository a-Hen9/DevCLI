"""DevCLI configuration."""
import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_DB_DIR = Path.home() / ".devcli"
DB_PATH = DEFAULT_DB_DIR / "devcli.db"

# Model settings
DEFAULT_MODEL = "qwen3.6-27b"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ROUTING = {
    "code_fix": "qwen3.6-27b",
    "design": "qwen3.6-27b",
    "generation": "qwen3.6-27b",
    "debug": "qwen3.6-27b",
    "plan": "qwen3.6-27b",
    "default": "qwen3.6-27b",
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# Task execution
MAX_TASK_RETRIES = 5

# Encryption key (derive from env or prompt user)
MASTER_KEY_ENV = "DEVCLI_MASTER_KEY"


def get_api_key() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY")
