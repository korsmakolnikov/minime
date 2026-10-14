#!/usr/bin/env python3
"""permissionRequest hook for bash, edit, create and the read tools.

Rule: an operation is approved when every effect it has falls inside a folder
versioned with git (a work tree path that is not git-ignored), because git can
always bring it back. /tmp is the other approved place: agents may run and
write anything there, and so is the `.documentation/` folder at the root of a
work tree, where simon writes the architecture documentation that git
ignores. Command substitutions are approved when their own
command is. Anything else, or anything the hook cannot reason about, falls
through to the normal permission prompt. `git push`, network clients and
cluster commands are always denied, and git commands that throw away
uncommitted work always ask. Commands run in a container (`docker exec`,
`docker compose exec`, `edgar exec`) are judged like host commands, and only
in the containers listed in COPILOT_CONTAINERS in ~/.bash_copilot. Reads
(view, grep, glob) of the agent and skill definitions under ~/.copilot, and
reads, edits and file creations under /tmp, are approved too; other edits ask
unless the editing agent is autonomous (AUTONOMY_<AGENT> in ~/.bash_copilot).

Every request left to the user is logged, with the reason, to
/tmp/copilot-hook-asks.jsonl.

Output: {"behavior": "allow"}, {"behavior": "deny", ...} or {} (fall through).
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time

AUTONOMY_FILE = os.path.expanduser("~/.bash_copilot")
SESSIONS = os.path.expanduser("~/.copilot/session-state")
MINIME = os.path.realpath(os.path.expanduser(os.environ.get("COPILOT_MINIME", "~/code/minime")))
AGENT_LOOKUP_WAIT = 2.0
ASKS_LOG = "/tmp/copilot-hook-asks.jsonl"

FALL_THROUGH = {}
ALLOW = {"behavior": "allow"}
DENY_PUSH = {"behavior": "deny", "message": "git push is reserved to the user: commit locally and stop."}

READ_ONLY = {
    "cat", "ls", "head", "tail", "wc", "grep", "rg", "awk", "cut", "sort",
    "uniq", "tr", "jq", "echo", "printf", "pwd", "date", "which", "type",
    "true", "false", "test", "[", ":", "sleep", "basename", "dirname",
    "realpath", "readlink", "stat", "file", "diff", "column", "nl", "tac",
    "notify-send", "ps", "whoami", "id", "hostname", "du", "df", "tree",
    "spec-check",
}

# Commands whose effect is not on files (processes, packages, privileges):
# always ask.
SYSTEM = {
    "kill", "pkill", "killall", "systemctl", "service", "shutdown", "reboot",
    "apt", "apt-get", "dpkg", "snap", "pip", "pip3", "pipx", "npm", "yarn",
    "pnpm", "gem", "crontab", "sudo", "su", "doas", "eval", "exec", "source",
    ".", "xargs", "nohup", "setsid", "dd", "mkfs", "mount", "umount", "chown",
    "gh",
}

# Commands reaching other machines: always denied, the user runs them.
NETWORK = {
    "curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "netcat",
    "telnet", "ftp", "socat",
}
CLUSTER = {"kubectl", "helm", "k9s", "kubectx", "kubens", "minikube", "kind"}

DOCKER_READ_ONLY = {"ps", "top", "logs", "inspect", "images", "stats"}
EDGAR_READ_ONLY = {"ps", "status", "logs", "ls", "list", "help", "--help"}
# Options of `docker exec`, `docker compose exec` and `edgar exec` that take a
# value, so that the container is the first word after them.
EXEC_VALUE_FLAGS = {"-e", "--env", "--env-file", "-w", "--workdir", "-u", "--user", "--index"}
INLINE_CODE_FLAGS = {"-c", "-e", "--eval", "-E", "-r"}
INTERPRETERS = {"sh", "bash", "zsh", "dash", "python", "python3", "node", "ruby", "perl", "elixir", "iex", "erl"}
PATH_ARGS = {"rm", "rmdir", "mkdir", "touch", "truncate", "cp", "mv", "ln", "chmod", "tee", "patch", "install"}
SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")"}
# Shell grammar words: the prefixes lead the command that follows them; the
# closers and a `for`/`select` header run nothing themselves (their list
# substitutions are checked on their own).
SHELL_PREFIXES = {"if", "then", "else", "elif", "while", "until", "do", "!", "{"}
SHELL_CLOSERS = {"fi", "done", "}", "break", "continue"}
READ_TOOLS = {"view", "grep", "glob", "read"}
EDIT_TOOLS = {"edit", "create", "Edit", "Write"}
READABLE_ROOTS = tuple(
    os.path.realpath(os.path.expanduser(p)) for p in ("~/.copilot/agents", "~/.copilot/skills")
)


class Denied(Exception):
    """A command no agent may run; the message tells the agent why."""


ASK_REASONS = []


def ask(reason):
    """Records why a request is left to the user and refuses it."""
    ASK_REASONS.append(reason)
    return False


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


def documentation(path):
    """Inside the `.documentation/` folder at the root of a work tree."""
    root = work_tree(path)
    folder = os.path.join(root, ".documentation") if root else None
    return bool(folder) and (path == folder or path.startswith(folder + os.sep))


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
    if SUBST in path:
        return False
    path = resolve(path, cwd)
    return scratch(path) or versioned(path) or documentation(path)


def strip_heredocs(command):
    """Drops heredoc bodies and their `<<MARKER`; the redirect receiving the
    heredoc (e.g. `cat > /tmp/msg <<EOF`) is still checked. Returns the
    command and the bodies of unquoted heredocs, where the shell still runs
    command substitutions."""
    out, expanded, terminator, quoted = [], [], None, False
    for line in command.split("\n"):
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            elif not quoted:
                expanded.append(line)
            continue
        match = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if match:
            quoted, terminator = bool(match.group(1)), match.group(2)
            line = line[: match.start()] + line[match.end():]
        out.append(line)
    if terminator is not None:
        return None, None
    return "\n".join(out), "\n".join(expanded)


# Stands for the output of a substitution: harmless as an argument, never
# accepted as a path to write or remove.
SUBST = "\x00subst"
BACKTICK = re.compile(r"`([^`]*)`")


def innermost_substitution(command):
    """(start, end, inner) of the first `$(…)`, `<(…)` or `>(…)` to close,
    which holds no other one. Quote-aware, so parentheses inside quotes (as in
    `jq 'select(…)'`) do not end it. None when there is none."""
    opened, quotes, i = [], [None], 0
    while i < len(command):
        char, quote = command[i], quotes[-1]
        if quote == "'":
            if char == "'":
                quotes[-1] = None
        elif char == "\\":
            i += 1
        elif command.startswith("(", i + 1) and (char == "$" or (char in "<>" and quote is None)):
            opened.append([i, i + 2, 0])
            quotes.append(None)
            i += 1
        elif char == "'" and quote is None:
            quotes[-1] = "'"
        elif char == '"':
            quotes[-1] = None if quote == '"' else '"'
        elif quote is None and opened and char == "(":
            opened[-1][2] += 1
        elif quote is None and opened and char == ")":
            if opened[-1][2]:
                opened[-1][2] -= 1
            else:
                start, inner, _ = opened.pop()
                return start, i + 1, command[inner:i]
        i += 1
    return None


def without_substitutions(command, cwd):
    """Replaces each command substitution, innermost first, with SUBST after
    checking its command; returns None when one is not allowed."""
    command = re.sub(r"\$\(\([^()]*\)\)", SUBST, command)
    while True:
        found = innermost_substitution(command)
        if found is None:
            match = BACKTICK.search(command)
            found = match and (match.start(), match.end(), match.group(1))
        if not found:
            return None if any(s in command for s in ("`", "$(", "<(", ">(")) else command
        start, end, inner = found
        if decide_shell(inner, cwd) != ALLOW:
            return None
        command = command[:start] + SUBST + command[end:]


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


def sed_read_only(args):
    """sed that only prints: no in-place edit, no script file, and no script
    able to write or run (`w`, `W`, `e`, or the `w`/`e` flags of `s`)."""
    scripts, i = [], 0
    while i < len(args):
        arg = args[i]
        if arg.startswith(("-i", "--in-place", "-f", "--file")) or (re.fullmatch(r"-[a-zA-Z]+", arg) and set(arg[1:]) & {"i", "f"}):
            return False
        if arg in ("-e", "--expression") and i + 1 < len(args):
            scripts.append(args[i + 1])
            i += 1
        elif arg.startswith("--expression="):
            scripts.append(arg.split("=", 1)[1])
        i += 1
    if not scripts:
        positional = [a for a in args if not a.startswith("-")]
        scripts = positional[:1]
    if not scripts:
        return False
    for script in scripts:
        bare = re.sub(r"\\.", "", script)
        bare = re.sub(r"s(.)(?:(?!\1).)*\1(?:(?!\1).)*\1([gpiImM0-9]*)", lambda m: "s" + m.group(2), bare)
        bare = re.sub(r"/[^/]*/", " ", bare)
        if re.search(r"[wWe]", bare):
            return False
    return True


def segment_allowed(words, cwd):
    while words and words[0] in SHELL_PREFIXES:
        words = words[1:]
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]):
        words = words[1:]
    if not words or words[0] in SHELL_CLOSERS:
        return True
    if words[0] in ("for", "select"):
        return True
    cmd, args = os.path.basename(words[0]), words[1:]

    if cmd in NETWORK:
        raise Denied(f"{cmd} reaches the network, which is reserved to the user: ask them to run it.")
    if cmd in CLUSTER:
        raise Denied(f"{cmd} acts on a cluster, which is reserved to the user: ask them to run it.")
    if cmd in SYSTEM:
        return ask(f"{cmd} acts on the system")
    if cmd == "set":
        return True
    if cmd in ("timeout", "nice", "time", "stdbuf"):
        while args and (args[0].startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", args[0])):
            args = args[1:]
        return segment_allowed(args, cwd)
    if cmd in INTERPRETERS and any(a in INLINE_CODE_FLAGS for a in args):
        return ask(f"{cmd} runs inline code the hook cannot read")
    if cmd in READ_ONLY:
        return True
    if cmd == "git":
        return git_allowed(args, cwd)
    if cmd == "linus":
        if args[:1] in (["commit"], ["amend"], ["squash"], ["fixup"]):
            # Commits ask (the user reads the message in the prompt) unless the
            # committer is autonomous: argyris for the minime mirror, else linus.
            real = os.path.realpath(cwd)
            in_minime = real == MINIME or real.startswith(MINIME + os.sep)
            return versioned(cwd) and autonomy("argyris" if in_minime else "linus")
        return versioned(cwd)
    if cmd == "docker":
        if args[:1] == ["exec"]:
            return container_command_allowed(args[1:], cwd)
        if args[:2] == ["compose", "exec"]:
            return container_command_allowed(args[2:], cwd)
        return bool(args) and args[0] in DOCKER_READ_ONLY or ask(f"docker {' '.join(args[:1])} is not read-only")
    if cmd == "edgar":
        if args[:1] == ["exec"]:
            return container_command_allowed(args[1:], cwd)
        return bool(args) and args[0] in EDGAR_READ_ONLY or ask(f"edgar {' '.join(args[:1])} is not read-only")
    if cmd == "find" and any(a in ("-exec", "-execdir", "-ok", "-okdir") for a in args):
        return ask("find runs a command on what it finds")
    if cmd == "sed":
        return sed_read_only(args) or ask("sed may write files")
    paths = [a for a in args if not a.startswith("-")]
    if cmd == "rm":
        return bool(paths) and all(SUBST not in p and (scratch(resolve(p, cwd)) or tracked(resolve(p, cwd))) for p in paths) \
            or ask("rm of untracked files outside /tmp")
    if cmd in ("cp", "install", "ln"):
        return bool(paths) and writable(paths[-1], cwd) or ask(f"{cmd} writes outside versioned folders and /tmp")
    if cmd in PATH_ARGS:
        return bool(paths) and all(writable(p, cwd) for p in paths if not re.fullmatch(r"[0-7]{3,4}|[ugoa]*[-+=][rwxXst]*", p)) \
            or ask(f"{cmd} writes outside versioned folders and /tmp")
    # Any other command acts on its working directory: approve it inside a
    # versioned folder or /tmp, provided no path argument points outside them.
    if not (scratch(cwd) or versioned(cwd)):
        return ask(f"{cmd} runs in {cwd}, outside versioned folders and /tmp")
    path_like = [a for a in args if a.startswith(("/", "~", "..")) and not a.startswith("//")]
    return all(writable(p, cwd) for p in path_like) or ask(f"{cmd} has a path argument outside versioned folders and /tmp")


def container_command_allowed(args, cwd):
    """`<container> <command…>` after `exec` and its options: the container
    must be listed in COPILOT_CONTAINERS, and the command is judged as if it
    ran on the host, in the same working directory."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in EXEC_VALUE_FLAGS else 1
    if i + 1 >= len(args):
        return ask("container command without a container or a command")
    container = args[i]
    if container not in setting("COPILOT_CONTAINERS").split():
        return ask(f"container {container} is not in COPILOT_CONTAINERS")
    return segment_allowed(args[i + 1:], cwd)


def decide_shell(command, cwd):
    stripped, expanded = strip_heredocs(command)
    if re.search(r"\bgit\b[^;&|\n]*\bpush\b", command if stripped is None else stripped + "\n" + expanded):
        return DENY_PUSH
    if stripped is None:
        ask("unterminated heredoc")
        return FALL_THROUGH
    if expanded and without_substitutions(expanded, cwd) is None:
        ask("substitution in a heredoc body not approved")
        return FALL_THROUGH
    stripped = without_substitutions(stripped, cwd)
    if stripped is None:
        ask("command substitution not approved")
        return FALL_THROUGH
    try:
        tokens = tokenize(stripped)
    except ValueError:
        ask("command the hook cannot tokenize")
        return FALL_THROUGH
    found = False
    for words, targets in segments(tokens):
        found = True
        if not all(writable(t, cwd) for t in targets):
            ask(f"redirect outside versioned folders and /tmp: {' '.join(targets)}")
            return FALL_THROUGH
        if words[:1] in (["cd"], ["pushd"]):
            cwd = resolve(words[1], cwd) if len(words) > 1 else os.path.expanduser("~")
            continue
        if not segment_allowed(words, cwd):
            ask(f"not approved: {' '.join(words)}")
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
        ask("no tool arguments, or a sandbox bypass")
        return FALL_THROUGH
    command = args.get("command") or args.get("fullCommandText")
    if tool in ("bash", "Bash", "shell") and isinstance(command, str):
        try:
            return decide_shell(command, cwd)
        except Denied as denied:
            return {"behavior": "deny", "message": str(denied)}
    edited = args.get("path") or args.get("file_path")
    if tool in EDIT_TOOLS and isinstance(edited, str):
        return decide_edit(payload, edited, cwd)
    if tool in READ_TOOLS:
        paths = read_paths(args)
        if paths and all(readable(p, cwd) for p in paths):
            return ALLOW
        ask(f"read outside /tmp and the agent and skill folders: {' '.join(paths)}")
        return FALL_THROUGH
    ask(f"tool {tool} not handled")
    return FALL_THROUGH


def setting(name):
    """The value of `export NAME=…` in ~/.bash_copilot, read live; empty when
    missing."""
    pattern = re.compile(r"^\s*(?:export\s+)?%s=(['\"]?)(.*)\1\s*$" % name)
    try:
        with open(AUTONOMY_FILE) as config:
            for line in config:
                match = pattern.match(line)
                if match:
                    return match.group(2)
    except OSError:
        pass
    return ""


def autonomy(agent):
    """AUTONOMY_<AGENT> from ~/.bash_copilot: True only for 1."""
    return setting("AUTONOMY_" + agent.upper()) == "1"


def session_events(session_id, offset=0):
    """The events of a session's events.jsonl from offset, and the new offset."""
    path = os.path.join(SESSIONS, session_id or "-", "events.jsonl")
    try:
        with open(path, "rb") as log:
            log.seek(offset)
            chunk = log.read()
    except OSError:
        return [], offset
    end = chunk.rfind(b"\n") + 1
    events = []
    for line in chunk[:end].splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events, offset + end


def requesting_agent(payload, path, cwd, wait=AGENT_LOOKUP_WAIT):
    """The agent behind an edit/create request. The payload does not name it, so
    find the pending tool call on the same file in the session's events.jsonl
    (it may be logged a little after the hook starts) and follow its parent
    task call to the agent launched by it; a call without a parent belongs to
    the session's main agent. None when it cannot be told."""
    session_id = payload.get("sessionId") or payload.get("session_id")
    names, pending, main_agent, offset = {}, {}, None, 0
    deadline = time.monotonic() + wait
    while True:
        events, offset = session_events(session_id, offset)
        for event in events:
            etype, data = event.get("type"), event.get("data") or {}
            if etype == "subagent.selected" and main_agent is None:
                main_agent = data.get("agentName")
            elif etype == "subagent.started":
                names[data.get("toolCallId")] = data.get("agentName")
            elif etype == "tool.execution_start" and data.get("toolName") in ("edit", "create"):
                target = (data.get("arguments") or {}).get("path")
                if isinstance(target, str) and resolve(target, cwd) == path:
                    pending[data.get("toolCallId")] = data.get("parentToolCallId")
            elif etype == "tool.execution_complete":
                pending.pop(data.get("toolCallId"), None)
        if pending:
            parent = list(pending.values())[-1]
            return names.get(parent) if parent else main_agent
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def decide_edit(payload, file_path, cwd):
    path = resolve(file_path, cwd)
    if scratch(path) or documentation(path):
        return ALLOW
    real = os.path.realpath(path)
    if any(real.startswith(root + os.sep) for root in READABLE_ROOTS) and autonomy("argyris") \
            and requesting_agent(payload, path, cwd) == "argyris":
        return ALLOW
    if writable(path, cwd) and autonomy("unclebob") and requesting_agent(payload, path, cwd) == "unclebob":
        return ALLOW
    # Everything else, code edits first of all, asks the user.
    ask(f"edit of {path} by an agent without autonomy")
    return FALL_THROUGH


def read_paths(args):
    paths = args.get("path") or args.get("paths")
    if isinstance(paths, str):
        return [paths]
    if isinstance(paths, list) and all(isinstance(p, str) for p in paths):
        return paths
    return []


def readable(path, cwd):
    """Agent and skill definitions, which agents read for the agents they
    launch and the skills they use, and the scratch files under /tmp."""
    target = os.path.realpath(resolve(path, cwd))
    return scratch(target) or any(target == root or target.startswith(root + os.sep) for root in READABLE_ROOTS)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        print("{}")
        return
    if os.environ.get("COPILOT_HOOK_DEBUG"):
        with open("/tmp/copilot-hook-permission.jsonl", "a") as log:
            log.write(json.dumps(payload) + "\n")
    decision = decide(payload)
    if decision == FALL_THROUGH:
        log_ask(payload)
    print(json.dumps(decision))


def log_ask(payload):
    """One line per request left to the user, with the reasons, so that the
    prompts that interrupt the flow can be studied and removed."""
    args = tool_input(payload) or {}
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session": payload.get("sessionId") or payload.get("session_id"),
        "tool": payload.get("toolName") or payload.get("tool_name") or (payload.get("permissionRequest") or {}).get("kind"),
        "cwd": payload.get("cwd"),
        "request": args.get("command") or args.get("fullCommandText") or args.get("path") or args.get("file_path") or args,
        "reasons": ASK_REASONS,
    }
    try:
        with open(ASKS_LOG, "a") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    main()
