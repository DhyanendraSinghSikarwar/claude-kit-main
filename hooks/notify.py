#!/usr/bin/env python3
"""claude-kit notification and activity hook.

Reads a hook event payload as JSON on stdin and does two things:

  1. Appends a one-line JSON record to an activity log, so there is a durable
     trace of which tools ran, when, and in which session.
  2. Raises a desktop notification for the events worth interrupting a human
     for -- permission prompts, idle waits, and turn completion.

Design rules, in priority order:

  * Never break the session. Every failure path is swallowed and the process
    always exits 0. A broken notifier must not stop an agent from working.
  * Never block. Notifications are fired detached; this process does not wait
    for the toast to be dismissed.
  * No third-party dependencies. Standard library only, so it runs anywhere
    Python does without an install step.

Environment variables:

  CLAUDE_KIT_NOTIFY=0     disable desktop notifications (logging still happens)
  CLAUDE_KIT_LOG=0        disable the activity log (notifications still happen)
  CLAUDE_KIT_LOG_PATH     override the log location
  CLAUDE_KIT_TOOL_TOAST=1 also toast on every matched tool use (noisy; off by default)

Usage:

    python notify.py <EventName>          # payload arrives on stdin

Although the bundled hooks.json is Claude Code's format, this script is not
tied to it: any runner that can execute a command and pipe JSON to stdin can
use it. It also degrades gracefully if stdin is empty or is not JSON.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Events that are worth a desktop notification. Everything else is logged only.
# SubagentStop is deliberately absent: a single turn can spawn many subagents
# and toasting each one trains you to ignore all of them.
TOAST_EVENTS = {"Notification", "Stop"}

MAX_BODY = 220  # characters; longer bodies get silently truncated by most OSes


def _truthy(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _log_path() -> Path:
    override = os.environ.get("CLAUDE_KIT_LOG_PATH")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "claude-kit-activity.jsonl"


def read_payload() -> dict:
    """Read the hook payload from stdin. Returns {} on anything unexpected."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {"_unparsed": raw[:500]}
    return data if isinstance(data, dict) else {"_payload": data}


def summarise(event: str, payload: dict) -> tuple[str, str]:
    """Build a (title, body) pair for the given event.

    Kept deliberately short: a notification that does not fit on one line is a
    notification nobody reads.
    """
    tool = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    cwd = payload.get("cwd") or os.getcwd()
    project = Path(cwd).name or "session"

    if event == "Notification":
        # Claude Code puts the human-facing text here: a permission request or
        # an idle-waiting prompt. Pass it through rather than paraphrasing.
        body = payload.get("message") or "Claude needs your attention."
        return (f"Claude — {project}", body)

    if event == "Stop":
        return (f"Claude finished — {project}", "The turn is complete.")

    if event == "SubagentStop":
        return (f"Subagent finished — {project}", tool or "A subagent returned.")

    if event == "SessionStart":
        source = payload.get("source") or "start"
        return (f"Claude session — {project}", f"Session {source}.")

    if event == "PreToolUse":
        detail = ""
        if tool == "Bash":
            detail = str(tool_input.get("command", ""))
        elif tool in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            detail = str(tool_input.get("file_path", ""))
        elif tool == "Task":
            detail = str(tool_input.get("subagent_type") or tool_input.get("description") or "")
        return (f"{tool or 'Tool'} — {project}", detail or "(no detail)")

    return (f"Claude — {project}", event)


def write_log(event: str, payload: dict, title: str, body: str) -> None:
    if not _truthy("CLAUDE_KIT_LOG", True):
        return
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "session": payload.get("session_id") or payload.get("sessionId"),
            "cwd": payload.get("cwd"),
            "tool": payload.get("tool_name") or payload.get("toolName"),
            "detail": body[:500],
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # logging must never break the session


def _spawn(cmd: list[str]) -> None:
    """Fire and forget. Never wait, never raise."""
    try:
        kwargs: dict = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            # CREATE_NO_WINDOW keeps a console from flashing on screen.
            kwargs["creationflags"] = 0x08000000
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd, **kwargs)
    except Exception:
        pass


def _ps_quote(s: str) -> str:
    """Quote for a PowerShell single-quoted string literal."""
    return s.replace("'", "''")


def notify(title: str, body: str) -> None:
    title = title[:80]
    body = (body or "").strip().replace("\r", " ").replace("\n", " ")[:MAX_BODY]
    system = platform.system()

    if system == "Windows":
        # NotifyIcon balloon works on any Windows with .NET Framework present,
        # with no module to install. BurntToast would be prettier but is not
        # guaranteed, and this hook must not require setup.
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$n = New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon = [System.Drawing.SystemIcons]::Information;"
            f"$n.BalloonTipTitle = '{_ps_quote(title)}';"
            f"$n.BalloonTipText = '{_ps_quote(body)}';"
            "$n.Visible = $true;"
            "$n.ShowBalloonTip(6000);"
            "Start-Sleep -Seconds 7;"
            "$n.Dispose()"
        )
        _spawn([
            "powershell", "-NoProfile", "-NonInteractive",
            "-WindowStyle", "Hidden", "-Command", script,
        ])
        return

    if system == "Darwin":
        esc = body.replace("\\", "\\\\").replace('"', '\\"')
        esc_t = title.replace("\\", "\\\\").replace('"', '\\"')
        _spawn([
            "osascript", "-e",
            f'display notification "{esc}" with title "{esc_t}"',
        ])
        return

    # Linux and other Unix
    _spawn(["notify-send", "--app-name=Claude", title, body])


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    payload = read_payload()
    title, body = summarise(event, payload)

    write_log(event, payload, title, body)

    if _truthy("CLAUDE_KIT_NOTIFY", True):
        should_toast = event in TOAST_EVENTS or (
            event == "PreToolUse" and _truthy("CLAUDE_KIT_TOOL_TOAST", False)
        )
        if should_toast:
            notify(title, body)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Absolute last resort: a hook must never fail the session.
        sys.exit(0)
