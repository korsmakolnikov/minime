---
name: container-scaffold
description: The project's runtime infrastructure, laid by ford after the architecture scaffold - a Dockerfile for the application, compose.yaml with the services the ADL names (a database, a broker), .dockerignore, the Makefile targets to run them, and the CI's path filter for a project in a folder. Load it in ford's target mode when the ADL has an external system that runs as a service, or the shopping list asks for containers.
---

# container-scaffold

The services a project runs on are part of its architecture: the ADL names
the external systems (a database, a broker, a cache) and the components
that talk to them. Once the architecture scaffold is committed, lay down
what runs them locally, so that the integration session finds them ready.
No business logic: the application's entrypoint is the module the ADL
names, which may still be an interface.

## When

* The ADL has an external system that runs as a service, or the shopping
  list asks for a Dockerfile or compose.
* After the architecture scaffold (`adl-scaffold`) and before the
  interfaces: the interfaces of the components that talk to a service read
  its settings as compose passes them.

Ask the user only what the shopping list leaves open: the service images
and versions (propose the current stable major), the port the application
listens on, how it is started.

## What to write

In the project's directory (the folder, for a project in a folder of a
repository):

* **`Dockerfile`**: the application only, built from the lock file, no
  development dependencies, running as a non-root user. Python with uv:

  ```dockerfile
  FROM python:<version>-slim
  COPY --from=ghcr.io/astral-sh/uv:<uv version> /uv /usr/local/bin/uv
  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-dev --no-install-project
  COPY src ./src
  RUN uv sync --frozen --no-dev
  RUN useradd --create-home app
  USER app
  ENV PATH="/app/.venv/bin:$PATH"
  CMD [<the command that starts the application>]
  ```

* **`.dockerignore`**: `.git`, `.venv`, the caches, `tests/`, `.sources/`,
  `.documentation/`.
* **`compose.yaml`**: one service for the application (`build: .`) and one
  per service in the ADL. Each service with a `healthcheck` (Postgres:
  `pg_isready`); the application `depends_on` them with `condition:
  service_healthy`; data in a named volume. The application reads every
  setting from the environment (a `DATABASE_URL`, not host, port and name
  apart); compose sets development values, never real secrets.
* **Makefile targets**: `up` (`docker compose up --build -d`), `down`
  (`docker compose down`), `logs`. Leave the existing targets as they are.
* **CI of a project in a folder**: its workflow at the repository's root
  (`.github/workflows/<folder>.yml`) runs only on changes to the folder and
  to itself: `paths: ["<folder>/**", ".github/workflows/<folder>.yml"]`
  under both `push` and `pull_request`. The scaffold writes it so; add it
  when an older workflow lacks it.

The tests do not use compose: integration tests start their own services
(testcontainers, or what the handbook says), so they run the same in CI.
That harness is not part of this scaffold: unclebob writes it test-first,
in the first unit whose red needs the service, and refactors it as it grows.

## Check and commit

* `toolchain build` still passes, and the architecture tests too.
* Commit with `linus commit --phase architecture` as `build(<scope>): …`,
  the Dockerfile, `.dockerignore`, compose and Makefile in one commit, the
  CI filter in its own `ci(<scope>): …`.
* Report the files in `FORD_DONE` (the services, their images, the settings
  the application reads), so that kent passes them to unclebob for the
  integration session.
