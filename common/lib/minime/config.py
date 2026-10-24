"""The optional configuration files of the workflow, in TOML.

They live in $MINIME_CONFIG_DIR (default $XDG_CONFIG_HOME/minime, that is
~/.config/minime) and none is required: a missing file is an empty one. Each
file may name others to merge into it, from the same folder, with the same
structure (a missing one is skipped):

    [extension]
    files = ["work.toml"]

large-systems.toml: the systems too large for the full test suite, by name,
with their location.

    [systems]
    shop = "~/code/shop"

projects.toml: the projects a language handbook covers besides those its
frontmatter lists, by language, as folder names.

    [projects]
    elixir = ["shop"]

aliases.toml: commands that stand for docker or docker compose, such as a
wrapper that runs them in a remote environment. `context` is the container
the wrapper usually runs in; `read_only` its subcommands that change
nothing, besides `exec`.

    [alias.docker]
    cmd = "devbox"
    context = "app"
    read_only = ["ps", "logs", "status"]
"""
import os
import tomllib

from . import ToolError

FILES = ("large-systems", "projects", "aliases")


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.environ.get("MINIME_CONFIG_DIR") or os.path.join(base, "minime")


def merge(into, other):
    for key, value in other.items():
        if isinstance(value, dict) and isinstance(into.get(key), dict):
            merge(into[key], value)
        else:
            into[key] = value


def load(name, folder=None, seen=None):
    """The file <name>.toml merged with its extensions; {} when missing."""
    folder = folder or config_dir()
    seen = set() if seen is None else seen
    path = os.path.join(folder, name if name.endswith(".toml") else f"{name}.toml")
    if path in seen or not os.path.isfile(path):
        return {}
    seen.add(path)
    try:
        with open(path, "rb") as source:
            data = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ToolError(f"{path}: {error}")
    for extension in (data.pop("extension", {}) or {}).get("files", []):
        merge(data, load(extension, folder, seen))
    return data


def large_systems():
    """{name: absolute path} of the large systems."""
    systems = load("large-systems").get("systems", {})
    return {name: os.path.realpath(os.path.expanduser(path)) for name, path in systems.items()}


def projects(language):
    """The folder names projects.toml adds to the language's handbook."""
    return list(load("projects").get("projects", {}).get(language, []))


def aliases():
    """{docker command: {cmd, context, read_only}}, as aliases.toml gives them."""
    return {name: entry for name, entry in load("aliases").get("alias", {}).items()
            if isinstance(entry, dict) and entry.get("cmd")}
