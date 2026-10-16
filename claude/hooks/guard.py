#!/usr/bin/env python3
"""PreToolUse hook of the workflow agents: the rules code can check.

Usage, in an agent's frontmatter: guard.py <agent>

Bash runs only the agent's tools: the commands in common/bin (and the few
others listed below), each with the subcommands the agent may use. Anything
else is refused: no agent improvises a shell command. Also refused, for
every agent: command substitution (`$(…)`, backticks, `<(…)`), a heredoc
whose delimiter is not quoted (its body would be expanded), and a redirect
or a file write outside the agent's own places. Edit, Write and NotebookEdit
are held to the same places.

Reading goes through the Read tool, limited only for an agent with "read"
places (hughes reads no code); searching through ripgrep (`rg`, without the
options that run other programs: --pre, --search-zip). Every refusal is appended to kent-guard.jsonl under
MINIME_STATE_DIR (default /tmp).

Approvals: a Bash call whose every command reads, or writes only the
workflow's own files under /tmp and .sources/ (AUTO_ALLOW), is approved
without a prompt. Commits, scaffolding, migrations, `make` and formatting
(`toolchain check --fix`) still reach the user's permission prompt, and so
do Edit and Write.

Output: a PreToolUse deny decision with the reason, an allow decision, or
nothing (the normal permission check goes on).
"""
import datetime
import json
import os
import re
import shlex
import subprocess
import sys

STATE_DIR = os.environ.get("MINIME_STATE_DIR", "/tmp")
GUARD_LOG = os.path.join(STATE_DIR, "kent-guard.jsonl")
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&"}
LINUS_READS = {"base", "range", "next", "check-message", "hunks", "--help", "-h", "help"}
MINIME = "~/code/minime"

# The workflow's own files, versioned on Claude Code (see workflow-files).
WORKFLOW_FILES = ["repo:.sources/", "repo:.documentation/", "repo:toolchain.yaml"]
LINUS_VALUE_FLAGS = {"--phase", "--model", "-F", "--scope", "--from", "--target"}

# Tool -> the subcommands allowed (None: any). Shared by most agents.
COMMON = {"flow-log": None, "git-read": None, "rg": None}
RG_REFUSED = ("--pre", "-z", "--search-zip")
SHOW = {"shopping-list": {"show", "path"}}
TESTS = {"toolchain": {"show", "build", "test", "related"}}

# Per agent: its tools (with the subcommands allowed), the linus subcommands
# it may write with (the read-only ones are always allowed), and where it may
# write. A place is a path under the repository root ("repo:<relative>"),
# "repo:" for the whole work tree, an absolute or ~ path, or
# "name:<file name>" for a file of that name anywhere in the repository. A
# trailing "/" makes it a folder; otherwise it is one file. Places in
# "except" are refused even inside an allowed one. A tool entry with spaces
# is an exact command prefix ("make -C ~/code/minime install").
AGENTS = {
    "kent": {
        "tools": {**COMMON, "shopping-list": None, "session-state": None, "scaffold": None,
                  "minime-migrate": None, "toolchain": {"show", "related"}, "spec-check": None},
        # kent commits the workflow's files between units, and nothing else
        "linus": {"stage", "commit"},
        "linus_paths": WORKFLOW_FILES,
        "edit": ["repo:toolchain.yaml"],
    },
    "hughes": {
        "tools": {"flow-log": None, **SHOW, "spec-check": None},
        "linus": set(),
        "edit": ["repo:.sources/spec.yaml"],
        # the domain comes from the shopping list and the user, not the code
        "read": ["repo:.sources/spec.yaml", "repo:.sources/shopping_lists/", "~/.claude/", "/tmp/"],
    },
    "ford": {
        "tools": {**COMMON, **SHOW, **TESTS, "spec-check": None, "adl-graph": None},
        "linus": {"stage", "stage-hunks", "unstage", "commit", "fixup"},
        "edit": ["repo:"],
        "except": ["repo:.sources/spec.yaml", "repo:.sources/shopping_lists/", "repo:.documentation/",
                   "repo:toolchain.yaml", "name:AGENTS.md", "name:CLAUDE.md"],
    },
    "unclebob": {
        "tools": {**COMMON, **SHOW, "toolchain": None, "spec-check": None},
        "linus": {"stage", "stage-hunks", "unstage", "commit", "amend", "fixup"},
        "edit": ["/tmp/", "repo:"],
        "except": ["repo:.sources/", "repo:.documentation/", "repo:toolchain.yaml",
                   "name:AGENTS.md", "name:CLAUDE.md"],
    },
    "martin": {
        "tools": {**COMMON, **SHOW, "toolchain": None, "spec-check": None},
        "linus": {"squash"},
        "edit": [],
    },
    "simon": {
        "tools": {**COMMON, **SHOW, "spec-check": None, "structurizr-cli": {"validate", "inspect"}},
        "linus": set(),
        "edit": ["repo:.documentation/"],
    },
    "joshua": {
        "tools": {**COMMON, **SHOW, "events-query": None, "audit-log": {"append", "pending", "show"},
                  "spec-check": None, "signal-check": None},
        "linus": set(),
        "edit": [],
    },
    "argyris": {
        "tools": {**COMMON, "events-query": None, "audit-log": {"pending", "show", "handled", "archive"},
                  f"make -C {MINIME} install": None, f"make -C {MINIME} clean-check": None},
        "linus": {"stage", "stage-hunks", "unstage", "commit"},
        "edit": [f"{MINIME}/"],
    },
    "marvin": {
        "tools": {**COMMON, **SHOW, "toolchain": {"show"}},
        "linus": {"stage", "commit"},
        "edit": ["name:AGENTS.md", "name:CLAUDE.md"],
    },
    "linus": {
        "tools": dict(COMMON),
        "linus": {"stage", "stage-hunks", "stage-patch", "unstage", "commit", "amend", "fixup", "squash"},
        "edit": ["/tmp/"],
    },
}
for _name, _rules in AGENTS.items():
    if _name != "hughes":  # hughes touches no git at all
        _rules["tools"]["linus"] = None


# Tool -> the subcommands approved without a prompt (None: any), once the
# agent's own rules allow the call.
AUTO_ALLOW = {
    "flow-log": None, "git-read": None, "rg": None, "spec-check": None, "signal-check": None,
    "events-query": None, "adl-graph": None,
    "toolchain": {"show", "build", "test", "related", "check"},
    "shopping-list": None, "session-state": None,
    "audit-log": {"append", "pending", "show", "handled", "archive"},
    "structurizr-cli": {"validate", "inspect"},
    "linus": {"base", "range", "next", "check-message", "hunks", "--help", "-h", "help"},
}


class Deny(Exception):
    """A call the agent may not make; the message tells it why."""


def repo_root(cwd):
    try:
        run = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def place(spec, root):
    """The absolute path of a place spec, or None when it needs a repository."""
    if spec.startswith("name:"):
        return None if root is None else (root + "/", spec[len("name:"):])
    if spec.startswith("repo:"):
        if root is None:
            return None
        rel = spec[len("repo:"):]
        return os.path.join(root, rel) if rel else root + "/"
    return os.path.expanduser(spec)


def inside(path, spec_path):
    if isinstance(spec_path, tuple):
        folder, name = spec_path
        return path.startswith(folder) and os.path.basename(path) == name
    if spec_path.endswith("/"):
        return path == spec_path.rstrip("/") or path.startswith(spec_path)
    return path == spec_path


def readable(specs):
    return ", ".join(s.replace("repo:", "<repo>/").replace("name:", "any ") or "<repo>" for s in specs) or "none"


def check_read(agent, rules, path, cwd, root):
    path = os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))
    if not any(p is not None and inside(path, p) for p in (place(s, root) for s in rules["read"])):
        raise Deny(f"{agent} may not read {path}: it reads only {readable(rules['read'])}.")


def check_write(agent, rules, path, cwd, root):
    path = os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))
    if path == "/dev/null":
        return
    specs = rules["edit"]
    allowed = any(p is not None and inside(path, p) for p in (place(s, root) for s in specs))
    refused = any(p is not None and inside(path, p) for p in (place(s, root) for s in rules.get("except", [])))
    if not allowed or refused:
        raise Deny(f"{agent} may not write {path}: its files are {readable(specs)}"
                   + (f", except {readable(rules['except'])}" if rules.get("except") else "") + ".")


def strip_heredocs(command):
    """Drops heredoc bodies (data for a tool's stdin), refusing unquoted ones."""
    lines, out, marker = command.replace("\\\n", " ").split("\n"), [], None
    for line in lines:
        if marker is not None:
            if line.strip() == marker:
                marker = None
            continue
        match = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        if match:
            if not match.group(1):
                raise Deny(f"quote the heredoc delimiter (<<'{match.group(2)}'), so its body is not expanded.")
            marker = match.group(2)
            line = line[:match.start()] + line[match.end():]
        out.append(line)
    return out


def simple_commands(lines):
    """Yields (words, redirect targets) of each simple command."""
    for line in lines:
        if re.search(r"\$\(|`|<\(|>\(", line):
            raise Deny("no command substitution ($(…), backticks, <(…)): run each tool as its own command.")
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        tokens = list(lexer)
        words, targets, i = [], [], 0
        while i <= len(tokens):
            token = tokens[i] if i < len(tokens) else ";"
            if token in SEPARATORS or i == len(tokens):
                if words:
                    yield words, targets
                words, targets = [], []
            elif token.isdigit() and i + 1 < len(tokens) and tokens[i + 1] in (">", ">>", ">&", "<"):
                pass  # the file descriptor of the redirect that follows
            elif token in (">", ">>", ">|", "&>", "&>>"):
                if i + 1 < len(tokens):
                    targets.append(tokens[i + 1])
                i += 1
            elif token in ("<", "<<", "<<<"):
                i += 1
            elif token == ">&" or (token.endswith(">") and token[:-1].isdigit()):
                if i + 1 < len(tokens) and not tokens[i + 1].isdigit():
                    targets.append(tokens[i + 1])
                i += 1
            else:
                words.append(token)
            i += 1


def strip_prefixes(words):
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        words = words[1:]
    return words


def check_linus_paths(agent, rules, args, cwd, root):
    paths, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in LINUS_VALUE_FLAGS:
            skip = True
        elif not arg.startswith("-"):
            paths.append(arg)
    if not paths:
        raise Deny(f"{agent} commits only named paths: {readable(rules['linus_paths'])}.")
    places = [place(s, root) for s in rules["linus_paths"]]
    for path in paths:
        full = os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))
        if not any(p is not None and inside(full, p) for p in places):
            raise Deny(f"{agent} may commit only {readable(rules['linus_paths'])}, not {path}.")


def same_prefix(words, entry):
    want = [os.path.expanduser(w) for w in entry.split()]
    have = [os.path.expanduser(w) for w in words[:len(want)]]
    return have == want


def auto_allowed(words, targets):
    name = os.path.basename(words[0])
    if name not in AUTO_ALLOW or targets:
        return False
    sub = words[1] if len(words) > 1 else ""
    if name == "toolchain" and sub == "check" and "--fix" in words:
        return False
    return AUTO_ALLOW[name] is None or sub in AUTO_ALLOW[name]


def check_bash(agent, rules, command, cwd, root):
    """Raises Deny, or returns whether every command may run without a prompt."""
    quiet = True
    for words, targets in simple_commands(strip_heredocs(command)):
        words = strip_prefixes(words)
        if not words:
            continue
        name = os.path.basename(words[0])
        tools = rules["tools"]
        if not any(same_prefix(words, entry) for entry in tools if " " in entry):
            if name not in tools:
                plain = sorted(t for t in tools if " " not in t)
                hint = "read with the Read tool, search with rg" if "rg" in tools else "read with the Read tool"
                raise Deny(f"{agent} runs only its tools in the shell: {', '.join(plain)} "
                           f"({hint}); `{name}` is not one of them.")
            sub = words[1] if len(words) > 1 else ""
            if name == "rg" and any(w.startswith(RG_REFUSED) for w in words[1:]):
                raise Deny("rg may not run other programs: no --pre, --search-zip.")
            if name == "linus":
                if sub not in LINUS_READS and sub not in rules["linus"]:
                    allowed = ", ".join(sorted(rules["linus"])) or "none"
                    raise Deny(f"{agent} may not run linus {sub}: its linus writes are {allowed}.")
                if sub not in LINUS_READS and "linus_paths" in rules:
                    check_linus_paths(agent, rules, words[2:], cwd, root)
            elif tools[name] is not None and sub not in tools[name] and sub not in ("-h", "--help"):
                raise Deny(f"{agent} may run {name} only as: {', '.join(sorted(tools[name]))}.")
        for path in targets:
            check_write(agent, rules, path, cwd, root)
        quiet = quiet and auto_allowed(words, [t for t in targets if t != "/dev/null"])
    return quiet


def log_denial(payload, agent, reason):
    entry = {
        "time": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agent": agent,
        "agent_id": payload.get("agent_id"),
        "tool": payload.get("tool_name"),
        "input": payload.get("tool_input"),
        "reason": reason,
    }
    try:
        with open(GUARD_LOG, "a") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else ""
    rules = AGENTS.get(agent)
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if rules is None:
        return 0
    # The main thread's hooks (claude --agent kent) also see its sub-agents'
    # calls: each sub-agent has its own guard, so leave them to it.
    if payload.get("agent_type") and payload["agent_type"] != agent:
        return 0
    tool, args = payload.get("tool_name"), payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    root = repo_root(cwd)
    try:
        if tool == "Bash":
            try:
                if check_bash(agent, rules, args.get("command", ""), cwd, root):
                    print(json.dumps({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "[guard] a workflow tool that reads or writes only the workflow's files",
                    }}))
            except ValueError:
                raise Deny("the command could not be parsed (unbalanced quotes?): run one tool per command.")
        elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            path = args.get("file_path") or args.get("notebook_path")
            if path:
                check_write(agent, rules, path, cwd, root)
        elif tool in ("Read", "Grep", "Glob") and "read" in rules:
            check_read(agent, rules, args.get("file_path") or args.get("path") or cwd, cwd, root)
    except Deny as denial:
        log_denial(payload, agent, str(denial))
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[guard] {denial}",
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
