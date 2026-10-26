"""Shared helpers of the minime workflow tools (common/bin).

The tools are the only commands the agents run: each does one job the same
way every time, so the agents stay agnostic of how it is done.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

# How long a repository's logs are kept, and the cap on all of them.
KEEP_DAYS = 30
KEEP_BYTES = 100 * 1024 * 1024


def state_root():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "minime")


def prune(root, current):
    """Drops the repositories' log folders untouched for KEEP_DAYS, then the
    oldest ones while all of them weigh more than KEEP_BYTES; at most once a
    day, and never the current one."""
    marker = os.path.join(root, ".pruned")
    try:
        if time.time() - os.path.getmtime(marker) < 86400:
            return
    except OSError:
        pass
    try:
        os.makedirs(root, exist_ok=True)
        open(marker, "w").close()
        folders = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path) and path != current:
                files = [os.path.join(d, f) for d, _, fs in os.walk(path) for f in fs]
                newest = max([os.path.getmtime(path)] + [os.path.getmtime(f) for f in files])
                folders.append((newest, sum(os.path.getsize(f) for f in files), path))
        folders.sort()
        total = sum(size for _, size, _ in folders)
        for newest, size, path in folders:
            if time.time() - newest > KEEP_DAYS * 86400 or total > KEEP_BYTES:
                shutil.rmtree(path, ignore_errors=True)
                total -= size
    except OSError:
        pass


def state_dir():
    """Where the workflow keeps its logs and state: $MINIME_STATE_DIR (tests,
    kent-loop), else on Claude Code one folder per repository under
    ~/.local/state/minime, kept KEEP_DAYS like Claude Code's transcripts,
    which the events point to; else (Copilot) /tmp."""
    if os.environ.get("MINIME_STATE_DIR"):
        return os.environ["MINIME_STATE_DIR"]
    if os.environ.get("CLAUDECODE") != "1":
        return "/tmp"
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    name = os.path.basename(top.stdout.strip()) if top.returncode == 0 else "no-repository"
    root = state_root()
    path = os.path.join(root, name)
    prune(root, path)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return "/tmp"
    return path


def repo_state(spec):
    """The state folder of another repository: its name under state_root(),
    or a path (kent-loop's state folder, for instance)."""
    path = os.path.expanduser(spec) if os.sep in spec else os.path.join(state_root(), spec)
    if not os.path.isdir(path):
        raise ToolError(f"no logs for {spec}: {path} does not exist")
    return path


def take_repo(args):
    """Removes `--repo <name | path>` from args: (the other args, its state
    folder, or None when the option is absent)."""
    if "--repo" not in args:
        return args, None
    at = args.index("--repo")
    if at + 1 >= len(args):
        raise ToolError("--repo needs a repository name (or a state folder's path)")
    return args[:at] + args[at + 2:], repo_state(args[at + 1])


def repos():
    """The repositories with logs, as (name, state folder), by name."""
    root = state_root()
    if not os.path.isdir(root):
        return []
    return sorted((n, os.path.join(root, n)) for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)))


STATE_DIR = state_dir()
FLOW_LOG = os.path.join(STATE_DIR, "kent-flow.log")
# Every agent turn (kent-events.jsonl) and every error: the violations the
# agents log, the signals that failed, the guard's refusals (kent-errors.jsonl).
EVENTS_LOG = os.path.join(STATE_DIR, "kent-events.jsonl")
ERRORS_LOG = os.path.join(STATE_DIR, "kent-errors.jsonl")


def state_path(name):
    return os.path.join(STATE_DIR, name)


def append_jsonl(path, row):
    try:
        with open(path, "a") as log:
            log.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


class ToolError(Exception):
    """A failure the tool reports in one line and exits 1 on."""


def die(message, status=1):
    print(f"{os.path.basename(sys.argv[0])}: {message}", file=sys.stderr)
    sys.exit(status)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def git(*args, cwd=None, check=True):
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and run.returncode != 0:
        raise ToolError(f"git {' '.join(args)}: {run.stderr.strip() or run.stdout.strip()}")
    return run.stdout


def repo_root(cwd=None):
    try:
        return git("rev-parse", "--show-toplevel", cwd=cwd).strip()
    except ToolError:
        raise ToolError("not inside a git repository")


def current_branch(root):
    branch = git("branch", "--show-current", cwd=root).strip()
    if not branch:
        raise ToolError("HEAD is detached: check out a branch first")
    return branch


def flow_log(agent, lines):
    """Appends lines to the activity log, each tagged with the agent."""
    stamp = now()
    try:
        with open(FLOW_LOG, "a") as log:
            for line in lines:
                log.write(f"{stamp} [{agent}] {line.rstrip()}\n")
    except OSError:
        pass


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w") as out:
        out.write(text)
    os.replace(tmp, path)


def read_stdin(what):
    if sys.stdin.isatty():
        raise ToolError(f"{what} comes from stdin (a quoted heredoc)")
    text = sys.stdin.read()
    if not text.strip():
        raise ToolError(f"{what} is empty")
    return text if text.endswith("\n") else text + "\n"


def main_guard(main):
    """Runs main, turning a ToolError into one line on stderr and exit 1."""
    try:
        sys.exit(main() or 0)
    except ToolError as error:
        die(str(error))
    except KeyboardInterrupt:
        die("interrupted", 130)
