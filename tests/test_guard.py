"""Tests of claude/hooks/guard.py: run with `make test`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "claude", "hooks", "guard.py")


class GuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        cls.repo = os.path.join(cls.tmp.name, "repo")
        os.makedirs(cls.repo)
        subprocess.run(["git", "init", "-q", cls.repo], check=True)
        cls.env = dict(os.environ, MINIME_STATE_DIR=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_guard(self, agent, tool, **tool_input):
        payload = {"tool_name": tool, "tool_input": tool_input, "cwd": self.repo}
        run = subprocess.run([sys.executable, GUARD, agent], input=json.dumps(payload),
                             capture_output=True, text=True, env=self.env)
        self.assertEqual(run.returncode, 0, run.stderr)
        if not run.stdout.strip():
            return None
        return json.loads(run.stdout)["hookSpecificOutput"]["permissionDecisionReason"]

    def allowed(self, agent, command):
        self.assertIsNone(self.run_guard(agent, "Bash", command=command), command)

    def denied(self, agent, command, reason=""):
        result = self.run_guard(agent, "Bash", command=command)
        self.assertIsNotNone(result, command)
        self.assertIn(reason, result)

    def test_tools_only(self):
        self.allowed("unclebob", "toolchain test --agent unclebob --commit")
        self.allowed("unclebob", "git-read log --oneline -5")
        self.denied("unclebob", "git log", "runs only its tools")
        self.denied("unclebob", "cat lib/foo.ex", "`cat` is not one of them")
        self.denied("unclebob", "toolchain test x && rm -rf lib", "`rm`")
        self.denied("hughes", "git-read log", "`git-read`")

    def test_subcommands(self):
        self.allowed("kent", "shopping-list write <<'EOF'\n# list\nEOF")
        self.denied("ford", "shopping-list write <<'EOF'\nx\nEOF", "only as: path, show")
        self.denied("kent", "toolchain test --branch", "only as: related, show")
        self.allowed("joshua", "audit-log append <<'AUDIT'\n## V-1\nAUDIT")
        self.denied("joshua", "audit-log archive", "only as")
        self.allowed("argyris", "audit-log archive")

    def test_linus(self):
        self.allowed("unclebob", "linus commit --phase red --model m \\\n  test/a_test.exs \\\n  <<'MSG'\ntest(x): y\nMSG")
        self.allowed("unclebob", "linus hunks lib/a.ex")
        self.allowed("unclebob", "linus stage-hunks lib/a.ex 1 3")
        self.denied("unclebob", "linus squash --scope x --from abc", "may not run linus squash")
        self.allowed("martin", "linus squash --scope x --from abc <<'MSG'\nfeat(x): y\nMSG")
        self.denied("martin", "linus commit --phase red", "may not run linus commit")
        self.allowed("joshua", "linus range")

    def test_shell_tricks(self):
        self.denied("unclebob", "flow-log unclebob \"$(rm -rf /)\"", "command substitution")
        self.denied("unclebob", "flow-log unclebob `id`", "command substitution")
        self.denied("unclebob", "linus commit --phase red <<MSG\n$(id)\nMSG", "quote the heredoc")
        self.denied("unclebob", "toolchain show > /etc/x", "may not write /etc/x")
        self.allowed("unclebob", "toolchain show > /tmp/out.txt")
        self.allowed("unclebob", "toolchain show 2>&1")
        self.denied("unclebob", "toolchain show 'unbalanced", "could not be parsed")
        self.allowed("unclebob", "MIX_ENV=test toolchain build")

    def test_prefix_entries(self):
        self.allowed("argyris", "make -C ~/code/minime install")
        self.denied("argyris", "make -C ~/code/minime uninstall", "`make`")
        self.denied("argyris", "make install", "`make`")

    def test_edit_places(self):
        def edit(agent, path):
            return self.run_guard(agent, "Edit", file_path=os.path.join(self.repo, path))
        self.assertIsNone(edit("unclebob", "lib/a.ex"))
        self.assertIsNotNone(edit("unclebob", ".sources/spec.yaml"))
        self.assertIsNotNone(edit("unclebob", "AGENTS.md"))
        self.assertIsNotNone(edit("unclebob", "toolchain.yaml"))
        self.assertIsNone(edit("hughes", ".sources/spec.yaml"))
        self.assertIsNotNone(edit("hughes", ".sources/components.yaml"))
        self.assertIsNone(edit("ford", ".sources/components.yaml"))
        self.assertIsNotNone(edit("ford", ".sources/spec.yaml"))
        self.assertIsNone(edit("marvin", "apps/web/AGENTS.md"))
        self.assertIsNotNone(edit("marvin", "lib/a.ex"))
        self.assertIsNone(edit("kent", "toolchain.yaml"))
        self.assertIsNotNone(edit("kent", "lib/a.ex"))
        self.assertIsNone(edit("simon", ".documentation/b/workspace.dsl"))
        self.assertIsNotNone(edit("martin", "lib/a.ex"))

    def test_denials_are_logged(self):
        self.denied("joshua", "rm -rf /")
        with open(os.path.join(self.tmp.name, "kent-guard.jsonl")) as log:
            last = json.loads(log.readlines()[-1])
        self.assertEqual(last["agent"], "joshua")

    def test_unknown_agent_passes(self):
        self.assertIsNone(self.run_guard("nobody", "Bash", command="rm -rf /"))


if __name__ == "__main__":
    unittest.main()
