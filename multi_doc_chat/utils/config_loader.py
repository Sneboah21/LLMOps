"""
Load config.yaml and return it as a Python dictionary.
"""

from pathlib import Path
import os
import yaml


def _project_root() -> Path:
    """
    Returns:
        D:/LLMOps/multi_doc_chat
    """
    return Path(__file__).resolve().parents[1]


def load_config(config_path: str | None = None) -> dict:
    """
    Resolve config path reliably irrespective of CWD.

    Priority:
        1. Explicit argument
        2. CONFIG_PATH environment variable
        3. <project_root>/config/config.yaml
    """

    env_path = os.getenv("CONFIG_PATH")

    if config_path is None:
        config_path = env_path or str(
            _project_root()
            / "config"
            / "config.yaml"
        )

    path = Path(config_path)

    if not path.is_absolute():
        path = _project_root() / path

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found at resolved path: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}