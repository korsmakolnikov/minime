# Task runner. Every target runs inside the project's uv environment.
.PHONY: deps install build test lint format typecheck check clean

# System packages: Python and uv, on Arch Linux and Ubuntu.
deps:
	@. /etc/os-release; case "$$ID $$ID_LIKE" in \
		*arch*) sudo pacman -S --needed --noconfirm python uv git make ;; \
		*ubuntu*|*debian*) sudo apt-get update && sudo apt-get install -y python3 python3-venv git make curl \
			&& (command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh) ;; \
		*) echo "Unsupported distribution: install Python {{PYTHON}}+, uv, git and make by hand." >&2; exit 1 ;; \
	esac

install:
	uv sync

build:
	uv run python -m compileall -q src tests

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy

clean:
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache dist build
