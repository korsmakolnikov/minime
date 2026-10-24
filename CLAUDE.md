# minime

My agents, skills and tools for two CLIs, which share one architecture-first
workflow: `claude/` for Claude Code, `copilot/` for the GitHub Copilot CLI,
`common/` for what both use (the tools in `common/bin`, their library in
`common/lib/minime`, the signal schemas, the shared skills). The README's
"Architecture" section maps all of it.

## The workflow's structural files: versioned on Claude, never on Copilot

`.sources/` (shopping lists, domain spec, ADL, components map),
`.documentation/` and `toolchain.yaml` are the workflow's control files in
the projects it works on. Whether they go into git depends on the side:

* **Copilot side** (`copilot/`): the Copilot agents **never** version these
  files: never stage, commit or mention them in a project's `AGENTS.md`.
  Copilot runs on company code shared with colleagues who do not know about
  the experiment. `linus` refuses them when it runs there, and `make update`
  lists them in that machine's global git ignore (`minime-migrate
  --ignore-workflow-files`).
* **Claude side** (`claude/`): the Claude agents **do** version them. kent
  commits them (`docs(workflow): …`) only between units, so they never fall
  inside a unit martin squashes; marvin may point to them in `AGENTS.md`.
  Claude Code works only on personal, mostly open-source projects.
* **Shared code** (`common/`): it must serve both rules. Branch on the CLI
  (`linus` reads `CLAUDECODE` or `LINUS_COAUTHOR`), never hard-code one rule.
* **The LangGraph version** will decide at runtime, through a flag.

When you work on one side, keep the other side's rule intact.

## Working on this repository

* **Both sides are maintained here.** The Copilot agents also run on Opus,
  so their content stays valid for both; when a change is decided for one
  side, write what the other side needs in its `NEXT_ITERATION.md`
  (`claude/NEXT_ITERATION.md`, `copilot/NEXT_ITERATION.md`) unless asked to
  change both.
* **Agent and skill files** are in C2-level English; talk to the user in
  Italian.
* **Structural changes** (an agent, skill, tool, hook or install target
  added, removed or renamed) update in the same change: the two diagrams
  in the README's "Architecture" section and `INSTALLED` in the Makefile
  (`make clean-check` verifies it).
* **Tests**: `make test` (the guard and the tools, `tests/`). Run it after
  touching `common/bin`, `common/lib` or `claude/hooks`; set
  `MINIME_STATE_DIR` so a manual try does not write into the real logs
  under `/tmp`.
* **Installing**: `make install` (Claude), `make copilot-install`
  (Copilot), `make clean` to remove everything either installed.
* **Commits**: Conventional Commits, on a feature branch; never push
  without being asked.
