#!/usr/bin/env python3
"""Stop hook of the workflow agents (Claude Code turns it into SubagentStop).

Usage, in an agent's frontmatter: signal_stop.py --expect NAME[,NAME…]

When the agent runs as a subagent of kent, its final message must end with a
valid signal block: the hook runs `signal-check --expect …` on
`last_assistant_message` (or on the message of the SubagentHandback call
that ended the turn) and, on any problem, blocks the stop, so the agent
receives the problems as its next instruction and ends its turn again. Run
as the main thread (`claude --agent <name>`, hook event Stop) the agent talks
to the user directly and nothing is checked.

Every subagent stop is appended to kent-events.jsonl in the workflow's state
folder (see minime.state_dir), one JSON object per line: time, agent type and
id, transcript path, signal and whether it passed, what replays the turn
(working directory, branch, HEAD, session id, and the launch prompt on the
agent's first turn) and the model's usage in the turn (requests and tokens).
joshua reads it as the list of events to audit. A signal that fails is also
appended to kent-errors.jsonl (kind "signal").
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "common", "lib"),
                os.path.expanduser("~/.local/share/minime/lib")]
from minime import ERRORS_LOG, EVENTS_LOG, append_jsonl  # noqa: E402

TOKENS = {"input": "input_tokens", "cache_write": "cache_creation_input_tokens",
          "cache_read": "cache_read_input_tokens", "output": "output_tokens"}


def signal_check(text, expect):
    command = shutil.which("signal-check") or os.path.expanduser("~/.local/bin/signal-check")
    try:
        run = subprocess.run([command, "--expect", expect], input=text, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"signal-check could not run: {error}"
    output = (run.stdout + run.stderr).strip()
    return run.returncode, output


def handback_message(path):
    """The message of the SubagentHandback call that ended the turn, if any.

    The CLI may deliver a subagent's report through that tool call instead of
    a final text message; `last_assistant_message` is then empty.
    """
    if not path:
        return None
    try:
        with open(path) as transcript:
            lines = transcript.read().splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "SubagentHandback":
                text = (block.get("input") or {}).get("message")
                return text if isinstance(text, str) else None
        return None
    return None


def transcript_rows(path):
    try:
        with open(path) as transcript:
            lines = transcript.read().splitlines()
    except (OSError, TypeError):
        return []
    rows = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            rows.append(entry)
    return rows


def launch_prompt(rows):
    for entry in rows:
        message = entry.get("message")
        if entry.get("type") == "user" and isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            texts = [b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]
            return "\n".join(texts) or None
    return None


def previous_calls(agent_id):
    """The model requests counted by the agent's earlier turns."""
    total = 0
    try:
        with open(EVENTS_LOG) as log:
            for line in log:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("agent_id") == agent_id:
                    total = (row.get("usage") or {}).get("calls_total", total)
    except OSError:
        pass
    return total


def usage(rows, agent_id):
    """The model's usage since the agent's last stop: one entry per request
    (the transcript repeats a message for each of its blocks), in order."""
    requests = {}
    for entry in rows:
        message = entry.get("message")
        if entry.get("type") != "assistant" or not isinstance(message, dict):
            continue
        if not message.get("id") or message.get("model") == "<synthetic>" or not message.get("usage"):
            continue
        requests[message["id"]] = message
    turn = list(requests.values())[previous_calls(agent_id):]
    total = {"model": turn[-1].get("model") if turn else None, "calls": len(turn),
             "calls_total": len(requests)}
    for name, key in TOKENS.items():
        total[name] = sum(m["usage"].get(key) or 0 for m in turn)
    return total


def git_state(cwd):
    def ask(*args):
        try:
            run = subprocess.run(["git", "-C", cwd or ".", *args], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return run.stdout.strip() if run.returncode == 0 else None
    return ask("branch", "--show-current"), ask("rev-parse", "--short", "HEAD")


def log_event(payload, signal, ok, problems):
    path = payload.get("agent_transcript_path")
    rows = transcript_rows(path)
    used = usage(rows, payload.get("agent_id"))
    branch, head = git_state(payload.get("cwd"))
    entry = {
        "time": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agent": payload.get("agent_type"),
        "agent_id": payload.get("agent_id"),
        "transcript": path,
        "signal": signal,
        "ok": ok,
        "session_id": payload.get("session_id"),
        "cwd": payload.get("cwd"),
        "branch": branch,
        "head": head,
        "usage": used,
    }
    if used["calls_total"] == used["calls"]:
        entry["launch"] = launch_prompt(rows)
    if problems:
        entry["problems"] = problems
        append_jsonl(ERRORS_LOG, {"time": entry["time"], "kind": "signal", "agent": entry["agent"],
                                  "agent_id": entry["agent_id"], "head": head, "problems": problems})
    append_jsonl(EVENTS_LOG, entry)


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

    text = handback_message(payload.get("agent_transcript_path"))
    if text is None:
        text = payload.get("last_assistant_message") or ""
    status, output = signal_check(text, args.expect)
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
            "came before the block, then the corrected block. If you hand your "
            "report back with SubagentHandback, its message is that whole message, "
            "the block last."
        ),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
