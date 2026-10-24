"""Tests of the optional configuration files and of the Copilot hook's aliases:
run with `make test`."""
import importlib.util
import os
import subprocess
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "common", "bin")
HOOK = os.path.join(ROOT, "copilot", "hooks", "scripts", "auto_approve.py")


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        self.config = os.path.join(self.tmp.name, "config")
        self.system = os.path.join(self.tmp.name, "shop")
        os.makedirs(self.config)
        os.makedirs(os.path.join(self.system, "apps"))
        self.env = dict(os.environ, MINIME_CONFIG_DIR=self.config,
                        PATH=BIN + os.pathsep + os.environ["PATH"])
        self.saved = os.environ.get("MINIME_CONFIG_DIR")
        os.environ["MINIME_CONFIG_DIR"] = self.config

    def tearDown(self):
        if self.saved is None:
            os.environ.pop("MINIME_CONFIG_DIR", None)
        else:
            os.environ["MINIME_CONFIG_DIR"] = self.saved
        self.tmp.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.config, name), "w") as out:
            out.write(textwrap.dedent(text))

    def config_tool(self, *args, cwd=None):
        return subprocess.run(["minime-config", *args], cwd=cwd or self.tmp.name, env=self.env,
                              capture_output=True, text=True)

    def test_no_file_means_nothing_configured(self):
        self.assertEqual(self.config_tool("large-systems").stdout, "")
        self.assertEqual(self.config_tool("aliases").stdout, "")
        self.assertEqual(self.config_tool("large-system").returncode, 1)

    def test_an_extension_adds_its_systems(self):
        self.write("large-systems.toml", """\
            [extension]
            files = ["work.toml", "missing.toml"]

            [systems]
            tiny = "/nowhere"
            """)
        self.write("work.toml", f'[systems]\nshop = "{self.system}"\n')
        self.assertEqual(self.config_tool("large-systems").stdout.split("\n")[:2],
                         ["tiny /nowhere", f"shop {os.path.realpath(self.system)}"])
        found = self.config_tool("large-system", cwd=os.path.join(self.system, "apps"))
        self.assertEqual((found.returncode, found.stdout), (0, "shop\n"))

    def test_an_extension_cycle_ends(self):
        self.write("large-systems.toml", '[extension]\nfiles = ["large-systems.toml"]\n[systems]\na = "/a"\n')
        self.assertEqual(self.config_tool("large-systems").stdout, "a /a\n")

    def test_aliases_list(self):
        self.write("aliases.toml", """\
            [alias.docker]
            cmd = "devbox"
            context = "app"
            """)
        self.assertEqual(self.config_tool("aliases").stdout, "docker = devbox context app\n")

    def test_projects_by_language(self):
        self.write("projects.toml", '[projects]\nelixir = ["shop", "store"]\n')
        self.assertEqual(self.config_tool("projects", "elixir").stdout, "shop\nstore\n")
        self.assertEqual(self.config_tool("projects", "python").stdout, "")

    def hook(self):
        spec = importlib.util.spec_from_file_location("auto_approve", HOOK)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        settings = os.path.join(self.tmp.name, "bash_copilot")
        with open(settings, "w") as out:
            out.write('export COPILOT_CONTAINERS="app"\n')
        setattr(module, "AUTONOMY_FILE", settings)
        return module

    def decision(self, hook, command):
        repo = os.path.join(self.tmp.name, "repo")
        if not os.path.isdir(repo):
            subprocess.run(["git", "init", "-q", repo], check=True)
        return hook.decide({"toolName": "bash", "toolInput": {"command": command}, "cwd": repo})

    def test_hook_treats_an_alias_like_docker(self):
        self.write("aliases.toml", """\
            [alias.docker]
            cmd = "devbox"
            read_only = ["ps", "status"]
            """)
        hook = self.hook()
        self.assertEqual(self.decision(hook, "devbox exec -e MIX_ENV=test app mix test"), hook.ALLOW)
        self.assertEqual(self.decision(hook, "devbox status"), hook.ALLOW)
        self.assertEqual(self.decision(hook, "devbox exec other mix test"), hook.FALL_THROUGH)
        self.assertEqual(self.decision(hook, "devbox rm app"), hook.FALL_THROUGH)

    def test_hook_without_aliases_still_judges_docker(self):
        hook = self.hook()
        self.assertEqual(self.decision(hook, "docker exec app mix test"), hook.ALLOW)
        self.assertEqual(self.decision(hook, "docker exec other mix test"), hook.FALL_THROUGH)


if __name__ == "__main__":
    unittest.main()
