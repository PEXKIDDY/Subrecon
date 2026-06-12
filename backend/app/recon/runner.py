"""Safe wrapper around external recon binaries.

Every tool is optional: if a binary is not installed, the runner reports it
unavailable and the orchestrator skips that stage instead of crashing. This is
what lets the platform run in a minimal container (passive HTTP sources only)
and scale up as you install the ProjectDiscovery toolchain.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache

from app.config import settings


@dataclass
class ToolResult:
    ok: bool
    stdout: str
    stderr: str
    available: bool


@lru_cache(maxsize=128)
def tool_available(binary: str) -> bool:
    return shutil.which(binary) is not None


def run_tool(
    binary: str,
    args: list[str],
    stdin_data: str | None = None,
    timeout: int | None = None,
) -> ToolResult:
    """Run ``binary args`` and capture output. Never raises on tool failure."""
    if not tool_available(binary):
        return ToolResult(ok=False, stdout="", stderr=f"{binary} not installed", available=False)

    try:
        proc = subprocess.run(
            [binary, *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout or settings.RECON_TOOL_TIMEOUT,
        )
        return ToolResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            available=True,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, stdout="", stderr="timeout", available=True)
    except Exception as exc:  # pragma: no cover - defensive
        return ToolResult(ok=False, stdout="", stderr=str(exc), available=True)


def lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]
