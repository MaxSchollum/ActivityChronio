import os
from pathlib import Path
from typing import Optional


def screenshot_root() -> Path:
    configured = os.environ.get("CHRONIO_SCREENSHOT_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Library" / "Application Support" / "ActivityChronio" / "screenshots"


def screenshot_path(file_key: str) -> Optional[Path]:
    if not file_key:
        return None

    root = screenshot_root().resolve()
    path = (root / file_key).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path
