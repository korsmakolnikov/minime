"""How to build, test and check a project: toolchain.yaml and the language drivers.

toolchain.yaml sits at the project root and is never versioned (the global
git ignore lists it). Every key is optional but `language`:

    toolchain: 1
    language: elixir            # elixir | python: picks the driver
    exec: [edgar, exec, crash]  # prefix of every command (a container wrapper)
    exec_stdin: [docker, exec, -i, crash]  # the same, keeping stdin open (adl-graph)
    env: {MIX_ENV: test}        # extra environment of every command
    commands:                   # replace a driver command; {paths} expands to
      test: [make, test, "ARGS={paths}"]   # the paths, space separated
    architecture_tests: [test/architecture]

Without the file, the language is detected (mix.exs, pyproject.toml) and the
driver's defaults run on the host.
"""
import os
import re
import shlex
import subprocess

from minime import ToolError, git

CONFIG = "toolchain.yaml"


def load(root):
    path = os.path.join(root, CONFIG)
    if not os.path.exists(path):
        language = detect(root)
        if language is None:
            raise ToolError(f"no {CONFIG} and no known project file (mix.exs, pyproject.toml) in {root}")
        return {"language": language, "detected": True}
    try:
        import yaml
    except ImportError:
        raise ToolError("reading toolchain.yaml needs PyYAML (python3 -m pip install pyyaml)")
    config = yaml.safe_load(open(path)) or {}
    if not isinstance(config, dict) or config.get("language") not in DRIVERS:
        raise ToolError(f"{path}: `language` must be one of {', '.join(DRIVERS)}")
    for key, kind in (("exec", list), ("exec_stdin", list), ("env", dict), ("commands", dict), ("architecture_tests", list)):
        if key in config and not isinstance(config[key], kind):
            raise ToolError(f"{path}: `{key}` must be a {kind.__name__}")
    return config


def detect(root):
    if os.path.exists(os.path.join(root, "mix.exs")):
        return "elixir"
    if any(os.path.exists(os.path.join(root, f)) for f in ("pyproject.toml", "setup.py", "setup.cfg")):
        return "python"
    return None


def workflow_file(path):
    """The workflow's own files, never versioned: not project changes."""
    return path == CONFIG or path.startswith((".sources/", ".documentation/"))


class Project:
    def __init__(self, root):
        self.root = root
        self.config = load(root)
        self.driver = DRIVERS[self.config["language"]](root)

    # -- commands ---------------------------------------------------------
    def argv(self, name, paths=(), default=None):
        """The command `name` with its paths, wrapped in exec and env."""
        custom = (self.config.get("commands") or {}).get(name)
        if custom is not None:
            joined = " ".join(shlex.quote(p) for p in paths)
            command = []
            for part in custom:
                if part == "{paths}":
                    command += list(paths)
                else:
                    command.append(part.replace("{paths}", joined))
            if "{paths}" not in " ".join(custom):
                command += list(paths)
        else:
            command = list(default) + list(paths)
        env = dict(self.driver.env.get(name, {}), **(self.config.get("env") or {}))
        prefix = [str(p) for p in self.config.get("exec") or []]
        if prefix:
            pairs = [f"{k}={v}" for k, v in env.items()]
            return prefix + (["env", *pairs] if pairs else []) + command, {}
        return command, env

    def run(self, name, paths=(), default=None, tee=None):
        command, env = self.argv(name, paths, default)
        print("$ " + " ".join(shlex.quote(c) for c in command), flush=True)
        process = subprocess.Popen(command, cwd=self.root, env=dict(os.environ, **env),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="", flush=True)
            if tee:
                tee(line)
        return process.wait()

    # -- files ------------------------------------------------------------
    def existing(self, files):
        return [f for f in files if os.path.isfile(os.path.join(self.root, f))]

    def commit_files(self, rev="HEAD"):
        out = git("show", "--name-only", "--diff-filter=d", "--format=", rev, cwd=self.root)
        return self.existing(sorted(set(out.split())))

    def branch_files(self):
        base = subprocess.run(["linus", "base"], cwd=self.root, capture_output=True, text=True)
        if base.returncode != 0:
            raise ToolError(f"linus base: {base.stderr.strip()}")
        committed = git("diff", "--name-only", "--diff-filter=d", f"{base.stdout.strip()}...HEAD", cwd=self.root)
        status = git("status", "--porcelain", "--untracked-files=all", cwd=self.root)
        dirty = [line[3:].split(" -> ")[-1] for line in status.splitlines()]
        changed = set(committed.split()) | set(dirty)
        return self.existing(sorted(f for f in changed if not workflow_file(f)))

    def related(self, files, architecture=False):
        tests = set()
        for path in files:
            tests |= set(self.driver.related(path))
        if architecture:
            for folder in self.config.get("architecture_tests") or self.driver.architecture_tests:
                full = os.path.join(self.root, folder)
                if os.path.isdir(full):
                    tests |= {os.path.relpath(os.path.join(d, f), self.root)
                              for d, _, fs in os.walk(full) for f in fs if self.driver.is_test(f)}
        return sorted(self.existing(tests))


class Elixir:
    name = "elixir"
    architecture_tests = ["test/architecture"]
    env = {"build": {"MIX_ENV": "test"}}

    def __init__(self, root):
        self.root = root
        mix = os.path.join(root, "mix.exs")
        text = open(mix).read() if os.path.exists(mix) else ""
        lock = os.path.join(root, "mix.lock")
        self.deps = text + (open(lock).read() if os.path.exists(lock) else "")

    def is_test(self, name):
        return name.endswith("_test.exs")

    def source(self, path):
        return path.endswith(".ex") or (path.endswith(".exs") and not self.is_test(path))

    def test(self):
        return ["mix", "test"]

    def build(self):
        return ["mix", "compile", "--warnings-as-errors"]

    def related(self, path):
        if self.is_test(os.path.basename(path)):
            return [path]
        if not path.endswith(".ex"):
            return []
        found = []
        mirrored = re.sub(r"(^|/)lib/", r"\1test/", path, count=1)[:-3] + "_test.exs"
        found.append(mirrored)
        try:
            text = open(os.path.join(self.root, path)).read()
        except OSError:
            return found
        for module in re.findall(r"^\s*defmodule\s+([\w.]+)", text, flags=re.M):
            out = git("grep", "-lwF", "-e", module, "--", "*_test.exs", cwd=self.root, check=False)
            found += out.split()
        return found

    def checks(self, files):
        """(name, default command, paths, configured) of each static check."""
        sources = [f for f in files if f.endswith((".ex", ".exs"))]
        return [
            ("format", ["mix", "format", "--check-formatted"], sources, True),
            ("lint", ["mix", "credo", "--strict"], sources, ":credo" in self.deps or '"credo"' in self.deps),
            ("types", ["mix", "dialyzer"], [], ":dialyxir" in self.deps or '"dialyxir"' in self.deps),
        ]

    def fix_format(self):
        return ["mix", "format"]


class Python:
    name = "python"
    architecture_tests = ["tests/architecture"]
    env = {}

    def __init__(self, root):
        self.root = root
        self.uv = os.path.exists(os.path.join(root, "uv.lock")) or "[tool.uv]" in self.pyproject()

    def pyproject(self):
        path = os.path.join(self.root, "pyproject.toml")
        return open(path).read() if os.path.exists(path) else ""

    def run(self, *command):
        return (["uv", "run"] if self.uv else []) + list(command)

    def is_test(self, name):
        base = os.path.basename(name)
        return base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))

    def test(self):
        return self.run("pytest")

    def build(self):
        folders = [f for f in ("src", "tests") if os.path.isdir(os.path.join(self.root, f))] or ["."]
        return self.run("python", "-m", "compileall", "-q", *folders)

    def module(self, path):
        parts = path[:-3].split("/")
        if parts[0] == "src":
            parts = parts[1:]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def related(self, path):
        if self.is_test(path):
            return [path]
        if not path.endswith(".py"):
            return []
        module = self.module(path)
        if not module:
            return []
        inner = module.split(".")[1:]
        found = []
        if inner:
            found += [os.path.join("tests", *inner[:-1], f"test_{inner[-1]}.py"),
                      os.path.join("tests", f"test_{inner[-1]}.py")]
        parent, _, leaf = module.rpartition(".")
        patterns = [rf"^\s*(from|import)\s+{re.escape(module)}\b"]
        if parent:
            patterns.append(rf"^\s*from\s+{re.escape(parent)}\s+import\s+.*\b{re.escape(leaf)}\b")
        for pattern in patterns:
            out = git("grep", "-lE", "-e", pattern, "--", "test_*.py", "*_test.py", "**/test_*.py",
                      cwd=self.root, check=False)
            found += out.split()
        return found

    def configured(self, tool):
        text = self.pyproject()
        if f"[tool.{tool}" in text or re.search(rf'["\']{tool}\b', text):
            return True
        files = {"ruff": ("ruff.toml", ".ruff.toml"), "mypy": ("mypy.ini", ".mypy.ini")}[tool]
        return any(os.path.exists(os.path.join(self.root, f)) for f in files)

    def checks(self, files):
        sources = [f for f in files if f.endswith(".py")]
        ruff = self.configured("ruff")
        return [
            ("format", self.run("ruff", "format", "--check"), sources, ruff),
            ("lint", self.run("ruff", "check"), sources, ruff),
            ("types", self.run("mypy"), sources, self.configured("mypy")),
        ]

    def fix_format(self):
        return self.run("ruff", "format")


DRIVERS = {"elixir": Elixir, "python": Python}
