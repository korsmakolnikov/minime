#!/usr/bin/env python3
"""notification/agentStop hook: a desktop popup (notify-send) when the user is
needed, the terminal bell when an agent finishes.

The popup fires only if the prompt is still unanswered after PROMPT_DELAY
seconds, judged from the session's events.jsonl: prompts resolved meanwhile
(answered at the terminal, or auto-approved) never raise a popup."""
import json
import os
import subprocess
import sys
import time

NEEDS_USER = {"permission_prompt", "elicitation_dialog"}
AGENT_DONE = {"agent_completed", "agent_idle"}
PROMPT_DELAY = float(os.environ.get("COPILOT_NOTIFY_DELAY", "2"))
SESSIONS = os.path.expanduser("~/.copilot/session-state")


def terminal():
    """The CLI's terminal: /dev/tty, else the first ancestor with a pts."""
    try:
        return open("/dev/tty", "w")
    except OSError:
        pass
    pid = os.getppid()
    while pid > 1:
        try:
            tty = os.readlink(f"/proc/{pid}/fd/1")
            if tty.startswith("/dev/pts/"):
                return open(tty, "w")
            with open(f"/proc/{pid}/stat") as stat:
                pid = int(stat.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return None
    return None


def bell():
    tty = terminal()
    if tty:
        with tty:
            tty.write("\a")


def popup(title, message):
    subprocess.run(
        ["notify-send", "--app-name=Copilot", "--urgency=normal", title, message],
        check=False,
        timeout=5,
    )


def events(session_id):
    path = os.path.join(SESSIONS, session_id or "", "events.jsonl")
    try:
        with open(path) as log:
            for line in log:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def pending(kind, session_id):
    """Whether a prompt of this kind is still waiting for the user. Unknown
    sessions count as pending, so a real prompt is never silenced."""
    if not session_id or not os.path.isfile(os.path.join(SESSIONS, session_id, "events.jsonl")):
        return True
    open_ids = set()
    for event in events(session_id):
        etype, data = event.get("type"), event.get("data") or {}
        if kind == "permission_prompt":
            if etype == "permission.requested" and not data.get("resolvedByHook"):
                open_ids.add(data.get("requestId"))
            elif etype == "permission.completed":
                open_ids.discard(data.get("requestId"))
        else:
            if etype == "tool.execution_start" and data.get("toolName") == "ask_user":
                open_ids.add(data.get("toolCallId"))
            elif etype in ("tool.execution_complete", "human_response.recorded"):
                open_ids.discard(data.get("toolCallId"))
    return bool(open_ids)


def detach():
    """Fork a daemon so the CLI is not held up while we wait; True in the child."""
    if os.fork():
        return False
    os.setsid()
    if os.fork():
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    return True


def prompt_user(payload, kind):
    tty = terminal()
    if not detach():
        return
    try:
        time.sleep(PROMPT_DELAY)
        if pending(kind, payload.get("sessionId") or payload.get("session_id")):
            popup(payload.get("title") or "Copilot needs you", payload.get("message") or kind)
            if tty:
                tty.write("\a")
                tty.flush()
    finally:
        os._exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    kind = payload.get("notification_type") or payload.get("notificationType")
    if kind in NEEDS_USER:
        prompt_user(payload, kind)
    elif kind in AGENT_DONE or "stopReason" in payload or "stop_reason" in payload:
        bell()


if __name__ == "__main__":
    main()
