#!/usr/bin/env python3
"""Print the namespace dependency graph of a Python package.

Usage: deps_graph.py <source_root> <package> [--depth N]

Modules are grouped by their first N dotted segments (default 2, e.g.
``sysops.ticketing``). The output lists every group with its module count,
then every edge between groups with the number of import statements behind
it. Read-only: files are parsed with ast, nothing is imported.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from pathlib import Path


def module_name(root: Path, path: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports(name: str, path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    package = name.split(".") if path.name == "__init__.py" else name.split(".")[:-1]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)] if node.level > 1 else package
                found.append(".".join([*base, node.module] if node.module else base))
            elif node.module:
                found.append(node.module)
    return found


def group(name: str, depth: int) -> str:
    return ".".join(name.split(".")[:depth])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("package")
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()

    root = args.source_root.resolve()
    package_dir = root / args.package.replace(".", "/")
    sizes: Counter[str] = Counter()
    edges: defaultdict[tuple[str, str], int] = defaultdict(int)

    for path in sorted(package_dir.rglob("*.py")):
        name = module_name(root, path)
        source = group(name, args.depth)
        sizes[source] += 1
        for target_module in imports(name, path):
            if not (target_module == args.package or target_module.startswith(args.package + ".")):
                continue
            target = group(target_module, args.depth)
            if target != source:
                edges[(source, target)] += 1

    print("# groups (modules)")
    for name, count in sorted(sizes.items()):
        print(f"{name}\t{count}")
    print("# edges (import statements)")
    for (source, target), count in sorted(edges.items()):
        print(f"{source} -> {target}\t{count}")


if __name__ == "__main__":
    main()
