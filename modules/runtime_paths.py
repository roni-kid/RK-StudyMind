from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Console-safe logging (shared)
#
# StudyMind prints emoji in status/diagnostic messages. On a default Windows
# console (cp1252) a bare print("...") with emoji raises UnicodeEncodeError.
# Several of those prints live *inside* except blocks, where the encoding error
# would replace the original exception and surface as a Gradio 500. log()
# encodes defensively so a diagnostic message can never become the failure.
# ─────────────────────────────────────────────────────────────────────────────

def configure_stdio() -> None:
    """Force UTF-8 on stdout/stderr where the runtime allows it."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def log(message) -> None:
    """Print a message that can never raise UnicodeEncodeError."""
    try:
        text = str(message)
    except Exception:
        return
    try:
        print(text)
        return
    except Exception:
        pass
    try:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe)
    except Exception:
        # Logging must never be the reason a call fails.
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

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


def code_dir() -> Path:
    """Sidecar storage for the full source text of uploaded code files."""
    return data_dir() / "code"


def ensure_runtime_dirs() -> None:
    for path in (data_dir(), exports_dir(), uploads_dir(), voices_dir(), code_dir()):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log(f"[runtime_paths] Could not create {path}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Durable writes
#
# open(path, "w") truncates the target before the new bytes land. A crash,
# power loss or full disk mid-dump leaves a truncated file that json.load()
# rejects - which previously meant the entire document library was silently
# discarded. Write to a temp file in the SAME directory, fsync it, then
# os.replace() onto the target. os.replace is atomic for same-volume renames
# on Windows and POSIX alike.
# ─────────────────────────────────────────────────────────────────────────────

def atomic_write_json(path, payload, keep_backup: bool = True) -> None:
    """Atomically serialize `payload` to `path`. Raises on failure."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())

        if keep_backup and target.exists():
            backup = target.with_suffix(target.suffix + ".bak")
            try:
                os.replace(target, backup)
            except Exception as exc:
                log(f"[runtime_paths] Could not refresh backup for {target.name}: {exc}")

        os.replace(tmp_path, target)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise


def read_json_with_recovery(path, default=None):
    """
    Load JSON, falling back to the `.bak` generation if the primary file is
    unreadable. Returns (value, error_message). error_message is "" on a clean
    read so callers can surface real corruption in the UI instead of silently
    returning an empty state.
    """
    target = Path(path)
    if not target.exists():
        return default, ""

    try:
        with open(target, "r", encoding="utf-8") as handle:
            return json.load(handle), ""
    except Exception as primary_exc:
        backup = target.with_suffix(target.suffix + ".bak")
        if backup.exists():
            try:
                with open(backup, "r", encoding="utf-8") as handle:
                    value = json.load(handle)
                log(f"[runtime_paths] {target.name} was corrupt; recovered from .bak")
                return value, f"{target.name} was corrupt and was recovered from the previous backup."
            except Exception as backup_exc:
                log(f"[runtime_paths] {target.name} and its .bak are both unreadable: {backup_exc}")
                return default, (
                    f"{target.name} is corrupt and the backup could not be read either "
                    f"({backup_exc})."
                )
        log(f"[runtime_paths] Could not read {target.name}: {primary_exc}")
        return default, f"{target.name} could not be read ({primary_exc})."
