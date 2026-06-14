from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Return the writable StudyMind root for source and frozen runs."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return app_root() / "data"


def exports_dir() -> Path:
    return app_root() / "exports"


def uploads_dir() -> Path:
    return app_root() / "uploads"


def voices_dir() -> Path:
    return app_root() / "voices"


def ensure_runtime_dirs() -> None:
    for path in (data_dir(), exports_dir(), uploads_dir(), voices_dir()):
        path.mkdir(parents=True, exist_ok=True)
