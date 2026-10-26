#!/usr/bin/env python3
"""PostToolUse hook of the workflow agents: the activity log, written for them.

Usage, in an agent's frontmatter: flow_hook.py <agent>

Appends one line per tool call to kent-flow.log in the workflow's state
folder (see minime.state_dir), tagged [<agent>], so the user can follow the
whole flow with `tail -f` and no agent spends a call on logging. Reads
and searches are not logged. The agents still use `flow-log` for what a call
does not show: a verdict, a decision, the step they are at.
"""
import datetime
import json
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "common", "lib"),
                os.path.expanduser("~/.local/share/minime/lib")]
from minime import FLOW_LOG  # noqa: E402

WIDTH = 160


def one_line(text):
    text = " ".join(str(text).split())
    return text if len(text) <= WIDTH else text[:WIDTH - 1] + "…"


def describe(tool, args, response):
    if tool == "Bash":
        command = args.get("command", "")
        if command.split()[:1] == ["flow-log"]:
            return None  # it logs itself
        return args.get("description") or command.splitlines()[0]
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return f"{tool.lower()} {args.get('file_path') or args.get('notebook_path')}"
    if tool == "Agent":
        return f"launch {args.get('subagent_type', 'agent')}: {args.get('description', '')}"
    if tool == "SendMessage":
        return f"message to {args.get('to', '?')}: {args.get('message', '')}"
    if tool == "AskUserQuestion":
        questions = args.get("questions") or [{}]
        return f"ask the user: {questions[0].get('question', '')}"
    return None


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else "agent"
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("agent_type") and payload["agent_type"] != agent:
        return 0  # a sub-agent's call, seen by the main thread's hook
    line = describe(payload.get("tool_name"), payload.get("tool_input") or {}, payload.get("tool_response"))
    if line:
        line = line.removeprefix(f"[{agent}] ")
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            with open(FLOW_LOG, "a") as log:
                log.write(f"{stamp} [{agent}] {one_line(line)}\n")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
