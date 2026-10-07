"""Helpers that turn ADL assertions into pytest fitness functions.

Copied into the project by the ``adl-fitness`` skill. Dependencies are read
statically from ``import`` statements with :mod:`ast`, so nothing is imported
or executed. Imports guarded by ``TYPE_CHECKING`` are counted too: an
architectural dependency is a dependency even when it is only for typing.
Dynamic imports (``importlib.import_module``) are not seen; declare a stronger
tool such as ``import-linter`` in the ADL ``REQUIRES`` clause when that matters.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Module:
    name: str
    path: Path


def within(module: str, namespace: str) -> bool:
    return module == namespace or module.startswith(namespace + ".")


def modules(source_root: Path | str, package: str) -> list[Module]:
    """All modules of ``package`` found under ``source_root``."""
    root = Path(source_root)
    package_dir = root / package.replace(".", "/")
    assert package_dir.is_dir(), f"Package {package!r} not found under {root}."
    found = []
    for path in sorted(package_dir.rglob("*.py")):
        parts = list(path.relative_to(root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        found.append(Module(".".join(parts), path))
    return found


def modules_within(source_root: Path | str, package: str, namespace: str) -> list[Module]:
    return _filter_within(modules(source_root, package), namespace)


def _filter_within(found: Iterable[Module], namespace: str) -> list[Module]:
    return [m for m in found if within(m.name, namespace)]


def _resolve_relative(module: Module, level: int, target: str | None) -> str:
    package_parts = module.name.split(".")
    if module.path.name != "__init__.py":
        package_parts = package_parts[:-1]
    base = package_parts[: len(package_parts) - (level - 1)] if level > 1 else package_parts
    return ".".join([*base, target] if target else base)


def dependencies(module: Module) -> set[str]:
    """Distinct absolute module names imported by ``module``."""
    tree = ast.parse(module.path.read_text(), filename=str(module.path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = (
                _resolve_relative(module, node.level, node.module)
                if node.level
                else node.module or ""
            )
            found.add(base)
            found.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
    found.discard(module.name)
    return found


def _wrap(value: str | Iterable[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def assert_defined(source_root: Path | str, package: str, namespaces: str | Iterable[str]) -> None:
    """Guard against vacuous passes: each namespace must contain a module."""
    found = modules(source_root, package)
    for namespace in _wrap(namespaces):
        assert _filter_within(found, namespace), (
            f"ADL artifact {namespace!r} has no modules in {package!r}."
        )


def assert_only_within(
    source_root: Path | str,
    package: str,
    namespaces: str | Iterable[str],
    allow: Iterable[str] = (),
) -> None:
    """ASSERT(CLASSES are only CONTAINED within <namespaces>)."""
    namespaces = _wrap(namespaces)
    allowed = set(allow)
    strays = [
        m.name
        for m in modules(source_root, package)
        if m.name not in allowed and not any(within(m.name, ns) for ns in namespaces)
    ]
    assert not strays, f"Modules outside {namespaces}: {strays}"


def _refute_dependency(found: list[Module], origin: str, targets: list[str]) -> None:
    violations = [
        (module.name, dependency)
        for module in _filter_within(found, origin)
        for dependency in sorted(dependencies(module))
        if any(within(dependency, t) for t in targets)
    ]
    assert not violations, f"{origin} depends on {targets}: {violations}"


def assert_no_dependency(
    source_root: Path | str, package: str, origin: str, targets: str | Iterable[str]
) -> None:
    """ASSERT(<origin> has NO DEPENDENCY on {<targets>})."""
    _refute_dependency(modules(source_root, package), origin, _wrap(targets))


def assert_mutually_independent(
    source_root: Path | str, package: str, namespaces: Iterable[str]
) -> None:
    """ASSERT(<each> has NO DEPENDENCY on other <siblings>), pairwise."""
    namespaces = list(namespaces)
    found = modules(source_root, package)
    for origin in namespaces:
        _refute_dependency(found, origin, [n for n in namespaces if n != origin])
