#!/usr/bin/env python3
"""permissionRequest hook for bash, edit and create.

Rule: an operation is approved when every effect it has falls inside a folder
versioned with git (a work tree path that is not git-ignored), because git can
always bring it back. /tmp is the only other approved place (logs, commit
message files). Anything else, or anything the hook cannot reason about, falls
through to the normal permission prompt. `git push` is always denied, and git
commands that throw away uncommitted work always ask.

Output: {"behavior": "allow"}, {"behavior": "deny", ...} or {} (fall through).
"""
import json
import os
import re
import shlex
import subprocess
import sys

FALL_THROUGH = {}
ALLOW = {"behavior": "allow"}
DENY_PUSH = {"behavior": "deny", "message": "git push is reserved to the user: commit locally and stop."}

READ_ONLY = {
    "cat", "ls", "head", "tail", "wc", "grep", "rg", "awk", "cut", "sort",
    "uniq", "tr", "jq", "echo", "printf", "pwd", "date", "which", "type",
    "true", "false", "test", "[", ":", "sleep", "basename", "dirname",
    "realpath", "readlink", "stat", "file", "diff", "column", "nl", "tac",
    "notify-send", "ps", "whoami", "id", "hostname", "du", "df", "tree",
}

# Commands whose effect is not on files (processes, containers, network,
# packages, privileges): always ask.
SYSTEM = {
    "kill", "pkill", "killall", "systemctl", "service", "shutdown", "reboot",
    "apt", "apt-get", "dpkg", "snap", "pip", "pip3", "pipx", "npm", "yarn",
    "pnpm", "gem", "curl", "wget", "ssh", "scp", "rsync", "crontab", "sudo",
    "su", "doas", "eval", "exec", "source", ".", "xargs", "nohup", "setsid",
    "dd", "mkfs", "mount", "umount", "chown", "gh",
}

DOCKER_READ_ONLY = {"ps", "top", "logs", "inspect", "images", "stats"}
EDGAR_READ_ONLY = {"ps", "status", "logs", "ls", "list", "help", "--help"}
INLINE_CODE_FLAGS = {"-c", "-e", "--eval", "-E", "-r"}
INTERPRETERS = {"sh", "bash", "zsh", "dash", "python", "python3", "node", "ruby", "perl", "elixir", "iex", "erl"}
PATH_ARGS = {"rm", "rmdir", "mkdir", "touch", "truncate", "cp", "mv", "ln", "chmod", "tee", "patch", "install"}
SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")"}


def resolve(path, cwd):
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(path)))


def existing_dir(path):
    while path and not os.path.isdir(path):
        path = os.path.dirname(path)
    return path or "/"


def git(cwd, *args):
    try:
        return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None


def work_tree(path):
    result = git(existing_dir(path), "rev-parse", "--show-toplevel")
    return result.stdout.strip() if result and result.returncode == 0 else None


def scratch(path):
    return path == "/dev/null" or path == "/tmp" or path.startswith("/tmp/")


def versioned(path):
    """Inside a git work tree, not in .git, not git-ignored."""
    root = work_tree(path)
    if not root or path == os.path.join(root, ".git") or path.startswith(os.path.join(root, ".git") + os.sep):
        return False
    if path == root:
        return True
    ignored = git(root, "check-ignore", "-q", "--no-index", path)
    return ignored is not None and ignored.returncode == 1


def tracked(path):
    root = work_tree(path)
    result = git(root, "ls-files", "--error-unmatch", path) if root else None
    return result is not None and result.returncode == 0


def writable(path, cwd):
    path = resolve(path, cwd)
    return scratch(path) or versioned(path)


def strip_heredocs(command):
    """Drops heredoc bodies and their `<<MARKER`; the redirect receiving the
    heredoc (e.g. `cat > /tmp/msg <<EOF`) is still checked."""
    out, terminator = [], None
    for line in command.split("\n"):
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        match = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if match:
            terminator = match.group(1)
            line = line[: match.start()] + line[match.end():]
        out.append(line)
    return None if terminator is not None else "\n".join(out)


def tokenize(command):
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def segments(tokens):
    """Yields (words, output redirect targets) for each simple command."""
    words, targets, i = [], [], 0
    while i < len(tokens):
        token = tokens[i]
        if token in SEPARATORS:
            if words or targets:
                yield words, targets
            words, targets = [], []
        elif re.fullmatch(r"[<>&|]+", token):
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            i += 1
            if ">" in token and not (token.endswith("&") or re.fullmatch(r"\d+-?|-", target)):
                targets.append(target)
            if words and re.fullmatch(r"\d", words[-1]):
                words.pop()
        else:
            words.append(token)
        i += 1
    if words or targets:
        yield words, targets


def git_allowed(args, cwd):
    while args and args[0] in ("--no-pager", "-C", "-c", "-P"):
        if args[0] == "-C" and len(args) > 1:
            cwd = resolve(args[1], cwd)
        args = args[2:] if args[0] in ("-C", "-c") else args[1:]
    if not args:
        return True
    sub, rest = args[0], args[1:]
    losing_work = (
        (sub == "reset" and "--hard" in rest)
        or sub in ("clean", "filter-branch", "filter-repo", "gc", "prune")
        or (sub == "checkout" and ("--" in rest or "." in rest or "-f" in rest or "--force" in rest))
        or (sub == "restore" and "--staged" not in rest)
        or (sub == "stash" and rest[:1] in (["drop"], ["clear"]))
        or (sub == "branch" and ("-D" in rest or ({"-d", "--delete"} & set(rest) and {"-f", "--force"} & set(rest))))
        or (sub == "worktree" and rest[:1] == ["remove"])
    )
    return not losing_work and work_tree(cwd) is not None


def segment_allowed(words, cwd):
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
        words = words[1:]
    if not words:
        return True
    cmd, args = os.path.basename(words[0]), words[1:]

    if cmd in SYSTEM:
        return False
    if cmd == "set":
        return True
    if cmd in ("timeout", "nice", "time", "stdbuf"):
        while args and (args[0].startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", args[0])):
            args = args[1:]
        return segment_allowed(args, cwd)
    if cmd in INTERPRETERS and any(a in INLINE_CODE_FLAGS for a in args):
        return False
    if cmd in READ_ONLY:
        return True
    if cmd == "git":
        return git_allowed(args, cwd)
    if cmd == "docker":
        return bool(args) and args[0] in DOCKER_READ_ONLY
    if cmd == "edgar":
        if args[:1] == ["exec"] and len(args) >= 3:
            return segment_allowed(args[2:], cwd)
        return bool(args) and args[0] in EDGAR_READ_ONLY
    if cmd == "find" and any(a in ("-exec", "-execdir", "-ok", "-okdir") for a in args):
        return False
    paths = [a for a in args if not a.startswith("-")]
    if cmd == "rm":
        return bool(paths) and all(scratch(resolve(p, cwd)) or tracked(resolve(p, cwd)) for p in paths)
    if cmd in ("cp", "install", "ln"):
        return bool(paths) and writable(paths[-1], cwd)
    if cmd in PATH_ARGS:
        return bool(paths) and all(writable(p, cwd) for p in paths if not re.fullmatch(r"[0-7]{3,4}|[ugoa]*[-+=][rwxXst]*", p))
    # Any other command acts on its working directory: approve it inside a
    # versioned folder, provided no path argument points outside one.
    if not versioned(cwd):
        return False
    path_like = [a for a in args if a.startswith(("/", "~", "..")) and not a.startswith("//")]
    return all(writable(p, cwd) for p in path_like)


def decide_shell(command, cwd):
    if re.search(r"\bgit\b[^;&|\n]*\bpush\b", command):
        return DENY_PUSH
    if any(s in command for s in ("`", "$(", "<(", ">(")):
        return FALL_THROUGH
    stripped = strip_heredocs(command)
    if stripped is None:
        return FALL_THROUGH
    try:
        tokens = tokenize(stripped)
    except ValueError:
        return FALL_THROUGH
    found = False
    for words, targets in segments(tokens):
        found = True
        if not all(writable(t, cwd) for t in targets):
            return FALL_THROUGH
        if words[:1] in (["cd"], ["pushd"]):
            cwd = resolve(words[1], cwd) if len(words) > 1 else os.path.expanduser("~")
            continue
        if not segment_allowed(words, cwd):
            return FALL_THROUGH
    return ALLOW if found else FALL_THROUGH


def tool_input(payload):
    args = payload.get("toolInput", payload.get("toolArgs", payload.get("tool_input", payload.get("permissionRequest"))))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return None
    return args if isinstance(args, dict) else None


def decide(payload):
    tool = payload.get("toolName") or payload.get("tool_name") or (payload.get("permissionRequest") or {}).get("kind")
    args = tool_input(payload)
    cwd = payload.get("cwd") or os.getcwd()
    if args is None or args.get("requestSandboxBypass"):
        return FALL_THROUGH
    command = args.get("command") or args.get("fullCommandText")
    if tool in ("bash", "Bash", "shell") and isinstance(command, str):
        return decide_shell(command, cwd)
    if tool in ("edit", "create", "Edit", "Write") and isinstance(args.get("path"), str):
        return ALLOW if writable(args["path"], cwd) else FALL_THROUGH
    return FALL_THROUGH


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        print("{}")
        return
    if os.environ.get("COPILOT_HOOK_DEBUG"):
        with open("/tmp/copilot-hook-permission.jsonl", "a") as log:
            log.write(json.dumps(payload) + "\n")
    print(json.dumps(decide(payload)))


if __name__ == "__main__":
    main()
