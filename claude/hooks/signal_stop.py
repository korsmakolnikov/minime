#!/usr/bin/env python3
"""Stop hook of the workflow agents (Claude Code turns it into SubagentStop).

Usage, in an agent's frontmatter: signal_stop.py --expect NAME[,NAME…]

When the agent runs as a subagent of kent, its final message must end with a
valid signal block: the hook runs `signal-check --expect …` on
`last_assistant_message` and, on any problem, blocks the stop, so the agent
receives the problems as its next instruction and ends its turn again. Run
as the main thread (`claude --agent <name>`, hook event Stop) the agent talks
to the user directly and nothing is checked.

Every subagent stop is appended to kent-events.jsonl under MINIME_STATE_DIR
(default /tmp), one JSON object
per line: time, agent type and id, transcript path, signal and whether it
passed. joshua reads it as the list of events to audit.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

EVENTS_LOG = os.path.join(os.environ.get("MINIME_STATE_DIR", "/tmp"), "kent-events.jsonl")


def signal_check(text, expect):
    command = shutil.which("signal-check") or os.path.expanduser("~/.local/bin/signal-check")
    try:
        run = subprocess.run([command, "--expect", expect], input=text, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"signal-check could not run: {error}"
    output = (run.stdout + run.stderr).strip()
    return run.returncode, output


def log_event(payload, signal, ok, problems):
    entry = {
        "time": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agent": payload.get("agent_type"),
        "agent_id": payload.get("agent_id"),
        "transcript": payload.get("agent_transcript_path"),
        "signal": signal,
        "ok": ok,
    }
    if problems:
        entry["problems"] = problems
    try:
        with open(EVENTS_LOG, "a") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect", required=True)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("hook_event_name") != "SubagentStop":
        return 0

    status, output = signal_check(payload.get("last_assistant_message") or "", args.expect)
    if status is None:
        # A broken checker must not trap the agent: log it and let it stop.
        log_event(payload, None, False, output)
        return 0
    signal = output.split()[1] if status == 0 and output.startswith("ok ") else None
    log_event(payload, signal, status == 0, None if status == 0 else output)
    if status == 0:
        return 0
    print(json.dumps({
        "decision": "block",
        "reason": (
            "Your turn must end with exactly one valid signal block "
            f"({args.expect.replace(',', ', ')}): a line with its name, one JSON object, "
            "a line with END_<name>, and nothing after it. signal-check reported:\n"
            f"{output}\n"
            "Fix the block and end your turn again with the whole message: whatever "
            "came before the block, then the corrected block."
        ),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
