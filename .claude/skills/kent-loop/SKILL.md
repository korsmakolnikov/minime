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
`$KENT_LOOP` (default `/tmp/kent-loop`): `project/` is the test project,
`state/` the workflow's logs (`MINIME_STATE_DIR`), so a test never writes
into the real logs.

| Command | What it does |
|---|---|
| `start "<message>"` | kent in `project/`, headless, in background; the message is the user's first |
| `say "<text>"` | the user's next message |
| `read` | kent's messages, its tool calls and errors, and the end of each turn with its cost, since the last read |
| `wait` | blocks until kent ends a turn asking the user something, or stops; run it in background and read after |
| `denials` | every call the guard refused, all agents |
| `snapshot [label]` | a snapshot of the session now |
| `snapshots` | the fixture's snapshots, numbered |
| `restore <NN>` | replace `project/` and `state/` with snapshot NN (kent stopped) |
| `status`, `stop` | the process |

kent runs with `--permission-mode acceptEdits` and an allowlist of the
workflow's tools only (no `bypassPermissions`): what the guard does not
refuse and the list does not hold is refused by the headless prompt. The
session stays alive between messages (`tail -f` on the inbox), so joshua
and simon keep running in background. There is no AskUserQuestion in
headless mode: kent asks in text.

## Snapshots: time travel between agent turns

While kent runs, a watcher snapshots the session every time an agent ends a
turn with a signal matching `KENT_LOOP_SNAPSHOT_SIGNALS` (default `*_DONE`
and `FORD_AS_IS`: a finished piece of work, not each question). A snapshot is
a folder `<NN>-<agent>-<signal>` in `$KENT_LOOP_FIXTURE` (default
`fixtures/<name of $KENT_LOOP>` in minime, versioned): the project with its
`.git` (ignored files left out: rebuild them with `toolchain build`), the
workflow's logs and state (`MINIME_STATE_DIR`, kent's progress file
included), kent's stream and the sub-agent transcripts the events name.

To iterate on one agent, restore the snapshot taken just before it and
start kent again with "riprendi": kent resumes from its progress file, the
logs say what happened before, and the agents up to that point do not run
again. `meta.json` names the minime commit the snapshot was taken with.

kent's stream and the sub-agent transcripts hold the whole API requests,
the user's private instructions included: `fixtures/.gitignore` keeps them
local (`kent.tar.gz`, `transcripts.tar.gz`), and git gets only the project
and the workflow's logs. Before committing new snapshots, check their size,
and that nothing in them names a real system (the test projects are
fictitious).

## A session

1. **Prepare the project** in `$KENT_LOOP/project`: an empty folder for a
   greenfield test, or a repository with a first commit (a README, some
   docs) to test a project in a folder or a brownfield one; or `restore` a
   snapshot of an earlier session. Remove the folder and `state/` to start
   again from scratch.
2. **Start** with what a user would say, in Italian: the goal, the scope
   and the decisions already taken, so that kent does not ask again what
   an earlier session settled.
3. **Loop**: `wait` (in background), then `read` and `denials`. Answer with
   `say`. A delegation in words ("for the remaining steps I accept the
   options you recommend") speeds up hughes and ford; say so to the user.
4. **Look at the evidence**, not only kent's words: `git -C
   $KENT_LOOP/project log`, the files written, `state/kent-events.jsonl`
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
