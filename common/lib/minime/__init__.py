"""Shared helpers of the minime workflow tools (common/bin).

The tools are the only commands the agents run: each does one job the same
way every time, so the agents stay agnostic of how it is done.
"""
import datetime
import os
import subprocess
import sys

# Where the workflow keeps its logs and state; tests point it elsewhere.
STATE_DIR = os.environ.get("MINIME_STATE_DIR", "/tmp")
FLOW_LOG = os.path.join(STATE_DIR, "kent-flow.log")


def state_path(name):
    return os.path.join(STATE_DIR, name)


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
