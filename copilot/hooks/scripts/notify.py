#!/usr/bin/env python3
"""notification/agentStop hook: a desktop popup (notify-send) when the user is
needed, the terminal bell when an agent finishes."""
import json
import os
import subprocess
import sys

NEEDS_USER = {"permission_prompt", "elicitation_dialog"}
AGENT_DONE = {"agent_completed", "agent_idle"}


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
        ["notify-send", "--app-name=Copilot", "--urgency=critical", title, message],
        check=False,
        timeout=5,
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    kind = payload.get("notification_type") or payload.get("notificationType")
    if kind in NEEDS_USER:
        popup(payload.get("title") or "Copilot needs you", payload.get("message") or kind)
        bell()
    elif kind in AGENT_DONE or "stopReason" in payload or "stop_reason" in payload:
        bell()


if __name__ == "__main__":
    main()
