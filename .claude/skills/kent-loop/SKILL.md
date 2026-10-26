---
name: kent-loop
description: Drive a headless kent session on a test project to try the workflow end to end - start kent, read what it and its agents did, answer as the user, read the guard's refusals - and close the loop by fixing minime between turns. Use when asked to test, try or validate kent's workflow (or an agent, skill, tool or hook it uses) on a real project, or to find out what does not work in it.
---

# kent-loop

The loop: kent runs headless on a throwaway project; you play the user and
argyris at once. You answer kent's questions, watch every agent through the
logs, and when something goes wrong you fix minime (agents, skills, tools,
hooks), run `make test` and `make install`, commit, and go on or start
again. The user decides the domain, the architecture and the method; pass
them those questions, decide the rest yourself.

## The driver

`.claude/skills/kent-loop/kent-loop`, run from the repository's root (the
project settings allow it without a prompt). The session lives in
`$KENT_LOOP` (default `~/.cache/kent-loop`, so that a reboot does not lose it): `kent-loop-sandbox/` is the test project (named so that `python-handbook` covers it),
`state/` the workflow's logs (`MINIME_STATE_DIR`), so a test never writes
into the real logs.

| Command | What it does |
|---|---|
| `start "<message>"` | kent in `kent-loop-sandbox/`, headless, in background; the message is the user's first |
| `say "<text>"` | the user's next message |
| `read` | kent's messages, its tool calls and errors, and the end of each turn with its cost, since the last read |
| `wait` | blocks until kent ends a turn asking the user something, or stops; run it in background and read after |
| `denials` | every call the guard refused, all agents |
| `status`, `stop` | the process |

kent runs with `--permission-mode acceptEdits` and an allowlist of the
workflow's tools only (no `bypassPermissions`): what the guard does not
refuse and the list does not hold is refused by the headless prompt. The
session stays alive between messages (`tail -f` on the inbox), so joshua
and simon keep running in background. There is no AskUserQuestion in
headless mode: kent asks in text.

## A session

1. **Prepare the project** in `$KENT_LOOP/kent-loop-sandbox`: an empty folder for a
   greenfield test, or a repository with a first commit (a README, some
   docs) to test a project in a folder or a brownfield one. Remove the
   folder and `state/` to start again from scratch.
2. **Start** with what a user would say, in Italian: the goal, the scope
   and the decisions already taken, so that kent does not ask again what
   an earlier session settled.
3. **Loop**: `wait` (in background), then `read` and `denials`. Answer with
   `say`. A delegation in words ("for the remaining steps I accept the
   options you recommend") speeds up hughes and ford; say so to the user.
4. **Look at the evidence**, not only kent's words: `git -C
   $KENT_LOOP/kent-loop-sandbox log`, the files written, `state/kent-events.jsonl`
   (signals, ok or not), `state/kent-flow.log`, joshua's violations as kent
   prints them.
5. **Fix and resume.** A fix to an agent file reaches only sessions started
   after `make install`; the guard and the tools apply at once. Tell kent
   what changed when it matters to the running session, or start again.
6. **Stop** with `stop` when the test is over; record what it showed in
   `claude/NEXT_ITERATION.md`.

## What to watch

* Questions asked by the wrong agent (scope is kent's, domain hughes's,
  technology ford's), or asked twice.
* A step handed to the user that a tool or an agent could take.
* Guard refusals: one followed by the right tool is noise; repeated ones
  are a missing tool or a rule the agent file does not state.
* Signals that fail at the first try (`ok: false` in the events log).
* Facts claimed and not checked: verify commits and files yourself.
