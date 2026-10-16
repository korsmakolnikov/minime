#!/usr/bin/env python3
"""PreToolUse hook of the workflow agents: the rules code can check.

Usage, in an agent's frontmatter: guard.py <agent>

For every Bash, Edit, Write and NotebookEdit call of the agent it denies:

* `git push`, network clients and cluster commands, for every agent;
* any git write: the `linus` command is the only write path to git;
* the `linus` subcommands the agent may not run (martin only squashes,
  unclebob and ford commit their own work, the others only read);
* file writes outside the agent's own places, through Edit/Write or through
  the shell (redirects, tee, sed -i, cp, mv, rm, mkdir, touch).

It is a backstop, not a sandbox: it denies only what it recognises, and a
command it cannot parse goes on to the normal permission check; joshua
audits the rest. Every denial is appended to /tmp/kent-guard.jsonl.

Output: a PreToolUse deny decision with the reason, or nothing (allow the
normal flow to continue).
"""
import datetime
import json
import os
import re
import shlex
import subprocess
import sys

GUARD_LOG = "/tmp/kent-guard.jsonl"
NETWORK = {"curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "netcat", "telnet", "ftp", "socat"}
CLUSTER = {"kubectl", "helm", "k9s", "kubectx", "kubens", "minikube", "kind"}
GIT_READS = {
    "log", "show", "diff", "status", "blame", "rev-parse", "merge-base", "ls-files",
    "ls-tree", "cat-file", "rev-list", "describe", "shortlog", "grep", "name-rev",
    "symbolic-ref", "for-each-ref", "show-ref", "reflog", "help", "version", "--version",
}
# git subcommands that only read with some options; any other use writes.
GIT_READ_WITH = {
    "branch": {"--show-current", "--list", "-l", "-a", "-r", "--contains", "--merged", "--no-merged", "-v", "-vv"},
    "config": {"--get", "--get-all", "--get-regexp", "--list", "-l"},
    "stash": {"list", "show"},
    "remote": {"-v", "show", "get-url"},
    "worktree": {"list"},
}
LINUS_READS = {"base", "range", "next", "check-message", "--help", "-h", "help"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&"}
WRITE_ALL_ARGS = {"rm", "rmdir", "mkdir", "touch", "truncate", "mv", "chmod"}
WRITE_LAST_ARG = {"cp", "install", "ln"}
INPLACE = {"sed", "perl"}

# Per agent: the linus subcommands it may run besides the read-only ones,
# and where it may write. A place is a path under the repository root
# ("repo:<relative>"), an absolute path, or "repo:" for the whole work tree.
# A trailing "/" makes it a folder; otherwise it is one file. Places in
# "except" are refused even inside an allowed one.
AGENTS = {
    "kent": {
        "linus": set(),
        "edit": ["/tmp/", "repo:.sources/shopping_lists/"],
        # the move of the legacy .adl/ and .shopping_lists/ into .sources/
        "shell": ["/tmp/", "repo:.sources/", "repo:.adl/", "repo:.shopping_lists/"],
    },
    "hughes": {"linus": set(), "edit": ["/tmp/", "repo:.sources/spec.yaml"]},
    "ford": {
        "linus": {"stage", "stage-patch", "unstage", "commit", "fixup"},
        "edit": ["/tmp/", "repo:"],
        "except": ["repo:.sources/spec.yaml", "repo:.sources/shopping_lists/", "repo:.documentation/"],
    },
    "unclebob": {
        "linus": {"stage", "stage-patch", "unstage", "commit", "amend", "fixup"},
        "edit": ["/tmp/", "repo:"],
        "except": ["repo:.sources/", "repo:.documentation/"],
    },
    "martin": {"linus": {"squash"}, "edit": ["/tmp/"]},
    "simon": {"linus": set(), "edit": ["/tmp/", "repo:.documentation/"]},
    "joshua": {"linus": set(), "edit": ["/tmp/"]},
    "linus": {"linus": {"stage", "stage-patch", "unstage", "commit", "amend", "fixup", "squash"}, "edit": ["/tmp/"]},
    "argyris": {
        "linus": {"stage", "stage-patch", "unstage", "commit"},
        "edit": ["/tmp/", "~/.claude/agents/", "~/.claude/skills/", "~/code/minime/"],
    },
}


class Deny(Exception):
    """A call the agent may not make; the message tells it why."""


def repo_root(cwd):
    try:
        run = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def place(spec, root):
    """The absolute path of a place spec, or None when it needs a repository."""
    if spec.startswith("repo:"):
        if root is None:
            return None
        rel = spec[len("repo:"):]
        return os.path.join(root, rel) if rel else root + "/"
    return os.path.expanduser(spec)


def inside(path, spec_path):
    if spec_path.endswith("/"):
        return path == spec_path.rstrip("/") or path.startswith(spec_path)
    return path == spec_path


def check_write(agent, rules, places_key, path, cwd, root):
    path = os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))
    if path == "/dev/null":
        return
    specs = rules.get(places_key) or rules["edit"]
    allowed = any(p is not None and inside(path, p) for p in (place(s, root) for s in specs))
    refused = any(p is not None and inside(path, p) for p in (place(s, root) for s in rules.get("except", [])))
    if not allowed or refused:
        where = ", ".join(s.replace("repo:", "<repo>/") or "<repo>" for s in specs)
        raise Deny(f"{agent} may not write {path}: its files are {where}"
                   + (f", except {', '.join(s.replace('repo:', '<repo>/') for s in rules['except'])}" if rules.get("except") else "")
                   + ".")


def strip_heredocs(command):
    """Drops heredoc bodies (they are data) and joins continued lines."""
    lines, out, marker = command.replace("\\\n", " ").split("\n"), [], None
    for line in lines:
        if marker is not None:
            if line.strip() == marker:
                marker = None
            continue
        match = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if match:
            marker = match.group(1)
            line = line[:match.start()] + line[match.end():]
        out.append(line)
    return out


def simple_commands(command):
    """Yields (words, redirect targets) of each simple command."""
    for line in strip_heredocs(command):
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
    while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in ("command", "time", "nice", "env")):
        words = words[1:]
    return words


def check_git(words):
    args, i = words[1:], 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-C", "-c", "--git-dir", "--work-tree") else 1
    sub = args[i] if i < len(args) else ""
    rest = args[i + 1:]
    if sub == "push":
        raise Deny("No agent ever pushes: the user pushes by hand.")
    if sub in GIT_READS or sub == "":
        return
    if sub in GIT_READ_WITH and (rest and rest[0] in GIT_READ_WITH[sub] or not rest and sub in ("branch", "stash", "remote", "worktree")):
        return
    raise Deny(f"git {sub} writes to the repository: the linus command is the only git write path (linus --help).")


def check_bash(agent, rules, command, cwd, root):
    for words, targets in simple_commands(command):
        words = strip_prefixes(words)
        if not words:
            continue
        name = os.path.basename(words[0])
        if name in NETWORK or name in CLUSTER:
            raise Deny(f"{name} reaches other machines: the user runs it.")
        if name == "git":
            check_git(words)
        if name == "linus":
            sub = words[1] if len(words) > 1 else ""
            if sub not in LINUS_READS and sub not in rules["linus"]:
                allowed = ", ".join(sorted(rules["linus"])) or "none"
                raise Deny(f"{agent} may not run linus {sub}: its linus writes are {allowed}.")
        paths = list(targets)
        args = [w for w in words[1:] if not w.startswith("-")]
        if name == "tee":
            paths += args
        elif name in WRITE_ALL_ARGS:
            paths += args
        elif name in WRITE_LAST_ARG and args:
            paths.append(args[-1])
        elif name in INPLACE and any(w.startswith("-i") or w == "--in-place" for w in words[1:]):
            paths += [a for a in args[1:]]
        for path in paths:
            check_write(agent, rules, "shell", path, cwd, root)


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
    tool, args = payload.get("tool_name"), payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    root = repo_root(cwd)
    try:
        if tool == "Bash":
            try:
                check_bash(agent, rules, args.get("command", ""), cwd, root)
            except ValueError:
                return 0  # unparsable: the normal permission check decides
        elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            path = args.get("file_path") or args.get("notebook_path")
            if path:
                check_write(agent, rules, "edit", path, cwd, root)
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
