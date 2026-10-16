"""Tests of the workflow tools in common/bin: run with `make test`."""
import os
import subprocess
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "common", "bin")


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        self.state = os.path.join(self.tmp.name, "state")
        self.home = os.path.join(self.tmp.name, "home")
        self.repo = os.path.join(self.tmp.name, "repo")
        for folder in (self.state, self.home, self.repo):
            os.makedirs(folder)
        self.env = dict(os.environ, MINIME_STATE_DIR=self.state, HOME=self.home,
                        XDG_CONFIG_HOME=os.path.join(self.home, ".config"),
                        PATH=BIN + os.pathsep + os.environ["PATH"],
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t")
        self.sh("git", "init", "-q", "-b", "master")
        self.sh("git", "commit", "-q", "--allow-empty", "-m", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def sh(self, *command, stdin=None, ok=True):
        run = subprocess.run(command, cwd=self.repo, env=self.env, input=stdin, capture_output=True, text=True)
        if ok:
            self.assertEqual(run.returncode, 0, f"{command}: {run.stdout}{run.stderr}")
        return run

    def write(self, path, text):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as out:
            out.write(textwrap.dedent(text))

    def test_flow_log(self):
        self.sh("flow-log", "tester", "one line")
        with open(os.path.join(self.state, "kent-flow.log")) as log:
            self.assertIn("[tester] one line", log.read())

    def test_shopping_list(self):
        self.sh("git", "switch", "-qc", "feat/x")
        self.assertNotEqual(self.sh("shopping-list", "show", ok=False).returncode, 0)
        self.sh("shopping-list", "write", stdin="# list\n")
        self.assertEqual(self.sh("shopping-list", "show").stdout, "# list\n")
        self.assertTrue(self.sh("shopping-list", "path").stdout.strip().endswith(".sources/shopping_lists/feat/x.md"))

    def test_session_state(self):
        self.sh("session-state", "write", stdin="step 3\n")
        self.assertEqual(self.sh("session-state", "show").stdout, "step 3\n")
        self.sh("session-state", "clear")
        self.assertNotEqual(self.sh("session-state", "show", ok=False).returncode, 0)

    def test_audit_log(self):
        entry = "## V-20261016-120000-1 — major — unclebob (a1)\n\n- x\n"
        self.sh("audit-log", "append", stdin=entry)
        self.assertNotEqual(self.sh("audit-log", "append", stdin=entry, ok=False).returncode, 0)
        self.assertNotEqual(self.sh("audit-log", "append", stdin="## bad\n", ok=False).returncode, 0)
        self.assertIn("V-20261016-120000-1", self.sh("audit-log", "pending").stdout)
        self.assertNotEqual(self.sh("audit-log", "archive", ok=False).returncode, 0)
        self.assertNotEqual(self.sh("audit-log", "handled", "V-20261016-120000-1", ok=False).returncode, 0)
        self.sh("audit-log", "handled", "V-20261016-120000-1", "--reason", "no change: clear rule")
        self.assertIn("nothing pending", self.sh("audit-log", "pending").stdout)
        self.sh("audit-log", "archive")
        self.assertTrue(os.path.exists(os.path.join(self.state, "joshua.log.prev")))

    def test_minime_migrate(self):
        self.write(".adl/a.adl", "a")
        self.write(".adl/same", "s")
        self.write(".sources/same", "s")
        self.write(".adl/clash", "1")
        self.write(".sources/clash", "2")
        self.write(".shopping_lists/m.md", "m")
        run = self.sh("minime-migrate", "--ignore-workflow-files", ok=False)
        self.assertEqual(run.returncode, 1)
        self.assertIn("CONFLICT", run.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".sources/a.adl")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".sources/shopping_lists/m.md")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".shopping_lists")))
        self.assertEqual(sorted(os.listdir(os.path.join(self.repo, ".adl"))), ["clash"])
        self.write(".adl/again", "a")
        self.sh("minime-migrate", ok=False)
        with open(os.path.join(self.home, ".config", "git", "ignore")) as ignore:
            self.assertEqual(ignore.read().split(), [".sources/", ".documentation/", "toolchain.yaml"])

    def test_minime_migrate_leaves_the_global_ignore_alone_by_default(self):
        self.write(".adl/a.adl", "a")
        self.sh("minime-migrate")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".config", "git", "ignore")))

    def test_linus_workflow_files(self):
        self.sh("git", "switch", "-qc", "feat/w")
        self.write(".sources/spec.yaml", "spec: 2\n")
        claude = dict(self.env, LINUS_COAUTHOR="claude", LINUS_MODEL="m")
        copilot = dict(self.env, LINUS_COAUTHOR="copilot", LINUS_MODEL="m")
        msg = "docs(workflow): add the domain spec\n\nThe first pass of the domain.\n"
        args = ["linus", "commit", "--phase", "other", ".sources/spec.yaml"]
        refused = subprocess.run(args, cwd=self.repo, env=copilot, input=msg, capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("never committed on Copilot", refused.stdout + refused.stderr)
        self.sh("git", "reset", "-q")
        done = subprocess.run(args, cwd=self.repo, env=claude, input=msg, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("spec.yaml", self.sh("git", "show", "--stat", "HEAD").stdout)

    def test_git_read(self):
        self.assertIn("base", self.sh("git-read", "log", "--oneline").stdout)
        self.assertNotEqual(self.sh("git-read", "commit", "-m", "x", ok=False).returncode, 0)
        self.assertNotEqual(self.sh("git-read", "diff", "--output=/tmp/x", ok=False).returncode, 0)
        self.assertNotEqual(self.sh("git-read", "branch", "new", ok=False).returncode, 0)

    def test_linus_hunks(self):
        self.write("f.txt", "\n".join(str(i) for i in range(1, 31)) + "\n")
        self.sh("git", "add", "f.txt")
        self.sh("git", "commit", "-qm", "f")
        lines = [str(i) for i in range(1, 31)]
        lines[2], lines[14], lines[27] = "three", "fifteen", "twentyeight"
        self.write("f.txt", "\n".join(lines) + "\n")
        self.assertIn("hunk 3:", self.sh("linus", "hunks", "f.txt").stdout)
        self.sh("linus", "stage-hunks", "f.txt", "1", "3")
        staged = self.sh("git", "diff", "--cached", "-U0").stdout
        self.assertIn("+three", staged)
        self.assertIn("+twentyeight", staged)
        self.assertNotIn("+fifteen", staged)

    def python_project(self):
        self.write("pyproject.toml", '[project]\nname = "shop"\n[tool.ruff]\n')
        self.write("src/shop/__init__.py", "")
        self.write("src/shop/cart/pricing.py", "def total(): return 0\n")
        self.write("tests/cart/test_pricing.py", "from shop.cart.pricing import total\n")
        self.write("tests/test_checkout.py", "from shop.cart import pricing\n")
        self.write("tests/test_unrelated.py", "import os\n")
        self.write("tests/architecture/test_layers.py", "x = 1\n")
        self.sh("git", "add", "-A")
        self.sh("git", "commit", "-qm", "project")
        self.sh("git", "switch", "-qc", "feat/p")
        self.write("src/shop/cart/pricing.py", "def total(): return 1\n")
        self.sh("git", "commit", "-qam", "change")

    def test_toolchain_python(self):
        self.python_project()
        self.assertEqual(self.sh("toolchain", "related", "--commit").stdout.split(),
                         ["tests/cart/test_pricing.py", "tests/test_checkout.py"])
        self.assertIn("tests/architecture/test_layers.py", self.sh("toolchain", "related", "--branch").stdout)
        self.assertNotEqual(self.sh("toolchain", "test", ok=False).returncode, 0)
        self.write("toolchain.yaml", """\
            language: python
            exec: [echo, IN]
            commands:
              test: [runtests, "{paths}", -v]
            """)
        out = self.sh("toolchain", "test", "--agent", "unclebob", "--commit").stdout
        self.assertIn("IN runtests tests/cart/test_pricing.py tests/test_checkout.py -v", out)
        self.assertNotIn("toolchain.yaml", self.sh("toolchain", "check", "--only", "format").stdout.splitlines()[0])

    def test_toolchain_elixir(self):
        self.write("mix.exs", 'defp deps, do: [{:credo, "~> 1.7"}]\n')
        self.write("lib/shop/cart.ex", "defmodule Shop.Cart do\nend\n")
        self.write("test/shop/cart_test.exs", "Shop.Cart.new()\n")
        self.write("test/shop/other_test.exs", "alias Shop.Cart\n")
        self.write("test/shop/unrelated_test.exs", "x\n")
        self.sh("git", "add", "-A")
        self.sh("git", "commit", "-qm", "project")
        self.write("lib/shop/cart.ex", "defmodule Shop.Cart do\n  #\nend\n")
        self.sh("git", "commit", "-qam", "change")
        self.assertEqual(self.sh("toolchain", "related", "--commit").stdout.split(),
                         ["test/shop/cart_test.exs", "test/shop/other_test.exs"])
        self.write("toolchain.yaml", "language: elixir\nexec: [echo, edgar, exec, crash]\n")
        self.assertIn("edgar exec crash env MIX_ENV=test mix compile --warnings-as-errors",
                      self.sh("toolchain", "build").stdout)

    def test_spec_check_v2(self):
        self.write(".sources/spec.yaml", """\
            spec: 2
            system: shop
            entities:
              - name: Cart
                kind: entity
                description: The items a customer intends to buy.
                fields: [{name: id, type: integer}]
            operations:
              - id: add-item
                description: A customer adds an item to a cart.
                post: [The cart holds the item.]
            properties:
              - id: adding-twice-adds-two
                operation: add-item
                kind: invariant
                forall: [{name: item, generator: any item}]
                holds: Adding an item twice leaves two of it in the cart.
            """)
        self.write(".sources/shop.adl", "DEFINE SYSTEM Shop AS shop\n  DEFINE COMPONENT Cart AS cart\n")
        self.write(".sources/components.yaml", """\
            version: 1
            components:
              - {path: shop.cart, module: Shop.Cart, boundary: interface, realizes: [add-item]}
            """)
        self.write("test/cart_test.exs", "# spec: add-item\n")
        self.assertEqual(self.sh("spec-check", "--stage", "domain").stdout.strip(), "ok")
        realization = self.sh("spec-check", "--stage", "realization", ok=False)
        self.assertIn("'adding-twice-adds-two' is realized by no component", realization.stdout)
        coverage = self.sh("spec-check", "--stage", "coverage", ok=False)
        self.assertIn("'adding-twice-adds-two' is cited by no test", coverage.stdout)
        self.assertNotIn("'add-item' is cited by no test", coverage.stdout)

    def test_scaffold_python(self):
        project = os.path.join(self.tmp.name, "agent-bench")
        os.makedirs(project)
        run = subprocess.run(["scaffold", "python", "PROJECT_NAME=agent-bench"], cwd=project,
                             env=self.env, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        for path in ("pyproject.toml", "Makefile", "src/agent_bench/__init__.py", "tests/test_import.py",
                     ".github/workflows/ci.yml", "toolchain.yaml"):
            self.assertTrue(os.path.exists(os.path.join(project, path)), path)
        again = subprocess.run(["scaffold", "python", "PROJECT_NAME=agent-bench"], cwd=project,
                               env=self.env, capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)


if __name__ == "__main__":
    unittest.main()
