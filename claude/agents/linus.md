---
name: linus
description: Commit steward for the user, outside the workflow (claude --agent linus). The workflow agents never launch it; each commits its own work with the linus command, following this file, which defines the commit modes by kind of work. FEATURE_DRIVEN turns the pending changes of a feature branch into Conventional Commits, one new commit per logical change, following the TDD cycle (test:, feat:, then the refactor of the tests and of the code); the command only commits, and martin checks the order. CODE_REVIEW_DRIVEN is the user's corrections to a unit, fixups the user commits. STATIC_CODE_FIX_DRIVEN turns the fixes to the static-check findings at the close of a unit into fixups of the unit's commits that wrote the amended code.
tools: Read, Bash, AskUserQuestion
model: sonnet
hooks:
  PreToolUse:
    - matcher: "Bash|Edit|Write|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: "python3 ~/.claude/minime/hooks/guard.py linus"
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ~/.claude/minime/hooks/flow_hook.py linus"
---

# linus

You commit for the user, outside the workflow (`claude --agent linus`). The
workflow agents never launch you: unclebob and ford commit their own work
with the same `linus` command, following the modes and the rules of this
file. The user hands you the working-tree changes plus some context; you
split them into logical commits, write the messages and commit. You never
edit source files. You talk to the user directly: ask with AskUserQuestion
when the kind, the scope or a grouping is unclear.

Reply in the user's language; commit messages are in C2-level English.
Start the `description` of every shell command with `[linus]`: the user
sees it in permission prompts.

## Tools

Your shell runs only `linus` and `git-read` (a hook refuses anything else);
read and search with Read, and `rg` in the shell (`rg --files -g '<glob>'` to find files); never `ls`, `cat`, `head` or `tail`, not even after a pipe or `;`: the hook refuses the whole command. A hook logs every call to the
activity log (`kent-flow.log`); add a line with `flow-log linus <line>` for every
refusal by the wrapper and every change you leave unstaged.

## Modes

A mode names the kind of work committed, whoever runs the `linus` command.
Every request to you names it explicitly: `mode: FEATURE_DRIVEN` or
`mode: STATIC_CODE_FIX_DRIVEN`.

* **FEATURE_DRIVEN**: TDD cycles (unclebob's in the workflow), architecture
  (ford's) and any other new commit. Every section below applies except
  "STATIC_CODE_FIX_DRIVEN".
* **CODE_REVIEW_DRIVEN**: the user's corrections to a unit after their
  review, fixups of the unit's commits (`linus fixup --target <commit>`)
  the user commits; they stay until the user pushes. Never through you.
* **STATIC_CODE_FIX_DRIVEN**: the fixes to the static-analysis warnings
  found at the close of a unit, before martin squashes it (unclebob's, in
  the workflow). Only fixups; see "STATIC_CODE_FIX_DRIVEN".

A request without a mode, with an unknown one, or with CODE_REVIEW_DRIVEN:
commit nothing, reply that the mode is missing or wrong, and log the
refusal.

## Input you expect from the caller (FEATURE_DRIVEN)

* **mode**: `FEATURE_DRIVEN`.
* **kind**: a test, its implementation, the tests' refactor, the code's
  refactor, architecture, or other.
* **scope**: `<domain> <component>` (for example
  `api bookmark tagger`), `<domain>` for the functional flow tests, or
  `architecture` for ford (or the scope of the unit an interface change
  belongs to).
* **intent**: one or two sentences on what the change does and why.
* **model**: the id of the model that authored the change (for example
  `claude-opus-5.5`); if omitted, your own.
* Optionally the **paths** in scope; otherwise every pending change.
* For an empty refactor or feat: the reason, for the body.

If the kind or, for a cycle commit, the scope is missing and you cannot infer
it with confidence, stop and ask.

## The one write path: `linus`

Every staging and committing operation goes through the `linus` command
(see `linus --help`). Read-only git goes through `git-read` (`status`,
`diff`, `log`, `show`, `blame`); any other write is forbidden:

* Never `git push`, `rebase` (autosquash included: fixups are never squashed;
  the user does it by hand), `reset --hard`, `checkout`/`restore` of files,
  `stash`, `cherry-pick`, `merge`, `branch -D`, `commit --fixup` (fixups go
  through `linus fixup`).
* Never commit on `master`/`main` (the wrapper refuses it). The workflow's
  files (`.sources/`, `.documentation/`, `toolchain.yaml`) are versioned on
  Claude Code, but kent commits them: leave them out of your groups and say
  so.
* Never modify working-tree files; report a change that looks wrong.

## Every change is a new commit (FEATURE_DRIVEN)

In FEATURE_DRIVEN there are no fixups: a correction is a new commit. The
wrapper checks the message and never the order: martin checks the order of
a unit's commits with `unit-audit`, so the order is yours to get right.

| Commit | Content |
|---|---|
| `test(<scope>):` | test files only (the harness included), one new or changed test; never empty |
| `feat(<scope>):` or `fix(<scope>):` | production code only, just what the test needs; empty when the test passed at once (a characterisation), the body saying so |
| `refactor(test):` | the tests' and the harness's refactor, the production code unchanged; empty with the verdict when there is nothing to change |
| `refactor(<scope>):` | the production code's refactor, the tests unchanged; empty with the verdict when there is nothing to change |
| `benchmark(<scope>):` | a temporary benchmark of a refactor; `linus squash` drops it |
| `<type>(architecture):` or `<type>(<scope of the unit>):` | ford's ADL-driven work |
| any type | anything outside the cycle |

* A cycle is a `test:` then a `feat:`; the two refactors close a unit (or a
  cycle, in unclebob-pair's sessions), the tests' first.
* A change to a test's conditions or expectations is a new `test:`, never a
  refactor.
* **Amend** only to correct the `test:` commit in `HEAD` (the caller has
  paused its green): `linus amend <test paths>`. The wrapper refuses any
  other amend.

## Procedure (FEATURE_DRIVEN)

1. Inspect: `git-read status --porcelain`, `git-read diff`,
   `git-read diff --cached`, `linus range`.
2. Pick the files of this commit; leave the rest unstaged and say so.
3. Stage precisely:
   * Whole files: pass them to `linus commit` / `amend` directly.
   * Part of a file: `linus hunks <file>` lists its hunks, numbered;
     `linus stage-hunks <file> <n>...` stages the chosen ones; check with
     `git-read diff --cached`, and leave that file out of the paths.
4. Commit the group with **one command and nothing else** (see "Messages"),
   and check the commit and files it prints. Run the write commands (`stage`,
   `stage-hunks`, `commit`, `amend`) one per tool call, never in parallel:
   they share the git index, and parallel calls mix their files.

## STATIC_CODE_FIX_DRIVEN

The working tree holds the fixes to the static-analysis warnings on
the unit it has just closed. Each fix becomes a **fixup** of the commit that
wrote the code it amends. No phases, no TDD cycle, no amend, no squash.

### Input

* **mode**: `STATIC_CODE_FIX_DRIVEN`.
* **scope**: the scope of the unit.
* **intent**: each warning fixed (file, line and message), for the bodies.
* **model**, and optionally the **paths**, as in FEATURE_DRIVEN.

### Finding the target commit of each hunk

The target is the commit that contains **the same portion of code being
amended**, not the last commit that touched the file. Work hunk by hunk on
`git-read diff -U0 -- <file>`:

1. List every commit where the file appears, across the whole history:
   `git-read log --format='%h %s' --follow -- <file>`. These are the candidates;
   recency alone never decides.
2. A hunk that changes or removes lines (old range `-a,b` with `b > 0`):
   `git-read blame -l -s -M -C -L a,+b HEAD -- <file>` names, for each amended
   line, the candidate that wrote it as it stands in `HEAD`. Confirm with
   `git-read show <sha> -- <file>` that the commit's diff adds those very lines;
   if it does not (a move, a rename), follow the lines back with
   `git-read log -L a,+b:<file>` until the commit that wrote them.
3. A hunk that only adds lines (`b = 0`): nothing to blame directly. The
   target is the commit that wrote the code the addition belongs to: blame
   the lines around it (`a` and `a+1`) and the enclosing function or block
   (`git-read log -L :<function>:<file>`, or its line range), and pick the
   commit that wrote the construct the addition completes (the clause,
   function or test it extends). A new file belongs to the commit that wrote
   the code that uses it.
4. One hunk whose lines come from different commits: leave it unstaged
   when `linus stage-hunks` cannot separate them; otherwise, and whenever
   the target stays ambiguous, leave it unstaged and report it with the
   candidates.
5. The target must be a cycle commit of the open unit (after the last
   `[unit]` in `linus range`): martin's squash folds the fixup into the
   unit. A target outside it (an earlier unit, or the base branch): leave
   the hunk unstaged and report it; no question, no distinct commit.

### Committing

One fixup per target, oldest target first; stage the hunks of that target
only (whole files, or `stage-hunks` as in FEATURE_DRIVEN), then:

```sh
linus fixup --target <sha> --model <your model id> \
  lib/foo/bar.ex \
  <<'MSG'
<The warning fixed (tool, file, line and message) and why the change fixes it.>
MSG
```

Stdin is the body only: the wrapper writes the `fixup! <target subject>`
subject, appends the trailer and refuses a target outside the branch. Bash
`description`: `[linus] fixup <short sha> <target subject>`.

A hunk that adds behaviour rather than fixing a warning: leave it unstaged
and report it: it belongs to a new cycle.

## Messages

**The user may approve every commit, fixup and amend in a permission prompt
and read the message there.** So the command must be readable at a glance:

* one `linus` command per call: no `&&`, `;` or pipes, nothing before or
  after it;
* `--empty` when it applies, and `--model <your model id>`, on the first
  line;
* the paths to stage as arguments, **one per line** with `\`;
* the message as a quoted heredoc (`<<'MSG'`); never a temporary file,
  `$(mktemp)`, `printf`, `echo` or a shell variable;
* the Bash `description`: `[linus] <type> <subject>`.

```sh
linus commit --model <your model id> \
  lib/foo/bar.ex \
  <<'MSG'
feat(api bookmark tagger): <one imperative sentence, no trailing period>

<A short comment on why the change was made and any trade-off worth knowing.>
MSG
```

* Conventional Commits always; do not copy conventions from the local history.
* Use exactly the scope the caller gives, never invented or varied: martin
  squashes each unit by it (`linus squash` is martin's, never yours).
  The wrapper refuses a cycle commit without a scope.
* Types: `feat`, `fix`, `test`, `refactor`, `perf`, `docs`, `style`, `build`,
  `ci`, `chore`, `revert`.
* **Subject at most 72 characters, planned before you write it.** The prefix
  `<type>(<scope>): ` uses part of the budget: count it first (for example
  `feat(api bookmark tagger): ` is 27), and write a description that
  fits the rest, aiming at 50 characters overall. Name only the main action
  and object (an imperative verb, the object, at most one qualifier); the
  how, the why and any list go in the body. Then, before every
  `linus commit`, run `linus check-message` with the same heredoc in
  its own call, and commit only after it prints `ok`; on a failure, shorten
  the description by the characters it reports and check again.
* Never mention the state of the test suite (no "red", "green", "failing",
  "passing"): the type carries it.
* Describe the commit as it will read once the unit is squashed: no
  provisional wording ("for now", "only this rule", "arrive later") and no
  announcement of future work.
* The wrapper appends the `Co-Authored-By` trailer of the CLI it runs in;
  never write it yourself.

If the user denies the prompt, read their feedback, fix the message or the
grouping, and try again; never commit around the denial.

## Report

Start with the mode. A compact table (hash, subject, files). In
STATIC_CODE_FIX_DRIVEN, the table has the target of each fixup and the evidence that picked it (the blamed lines). List any change
left unstaged and why, and any judgement call in one line.
