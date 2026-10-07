---
name: minime-sync
description: Mirrors the live Copilot setup in ~/.copilot (agents, skills, hooks, settings, global instructions), the autonomy settings in ~/.bash_copilot and the gutexberg, mortimer and spec-check commands into ~/code/minime/copilot/, then records the change as a new commit through gutexberg. Use before a /restart and whenever an agent, skill, hook or setting has changed.
---

# minime-sync

`~/.copilot` is the live setup; `~/code/minime/copilot/` is its versioned
mirror on the `copilot` branch, installed elsewhere with
`make copilot-install`. This skill copies live → mirror and commits.

Start every shell description with the calling agent's `[name]`. Run every
command from `~/code/minime` (`cd ~/code/minime && …`): the destinations are
versioned, so the permission hook lets them through. **Never push.**

## 1. Preconditions

```sh
cd ~/code/minime && git branch --show-current && git status --short
```

Stop and tell the user if the branch is not `copilot`, or if the tree is not
clean (show `git status`: uncommitted work in the mirror is not yours).

## 2. Copy

Copy only what the mirror tracks (never `permissions-config.json`,
`config.json`, `session-state/` or logs: they are machine state).

```sh
cd ~/code/minime \
  && cp ~/.copilot/agents/*.agent.md copilot/agents/ \
  && for s in ~/.copilot/skills/*/; do cp -r "$s" copilot/skills/; done \
  && cp -r ~/.copilot/hooks/. copilot/hooks/ \
  && cp ~/.copilot/settings.json ~/.copilot/copilot-instructions.md copilot/ \
  && cp ~/.bash_copilot copilot/bash_copilot \
  && cp ~/.local/bin/gutexberg ~/.local/bin/mortimer ~/.local/bin/spec-check copilot/bin/
```

Then look for files the live setup no longer has (renamed or deleted):

```sh
cd ~/code/minime && for d in agents skills hooks; do diff -rq ~/.copilot/$d copilot/$d; done
```

An `Only in copilot/…` line is a file removed or renamed live: if renamed,
`git mv old new` before copying (history follows the file), otherwise
`git rm` it; ask the user when you cannot tell. No `Only in ~/.copilot/…`
line may remain after the copy.

## 3. Check

```sh
cd ~/code/minime && git add -N . && git status --short && git diff --stat
```

* Nothing changed: say the mirror is already in sync and stop.
* A new agent or skill, or a renamed one: update the tables in `README.md`;
  a new top-level file in `copilot/`: add its install line to the
  `copilot-install` target of the `Makefile` and mention it in the README.
* Show the user the `git diff --stat` (and the diff of `README.md`/`Makefile`
  if you edited them).

## 4. Commit through gutexberg

Every change is a new commit: never a fixup, never an amend. Write a
Conventional Commits message with the `copilot` scope: a one-sentence subject
(`feat(copilot): …`, `fix(copilot): …`, `docs(copilot): …`), a blank line and
one or two C2-level English sentences saying what changed and why. Validate it
first:

```sh
cd ~/code/minime && gutexberg check-message <<'MSG'
<subject>

<body>
MSG
```

Then commit with one readable command, since the user reads the message in
the permission prompt: the changed paths one per line, the message as a
quoted heredoc (gutexberg appends the Copilot trailer), and `--model <id>`
only if your model differs from the one in `~/.copilot/settings.json`.

```sh
cd ~/code/minime && gutexberg commit --phase other \
  copilot/agents/foo.agent.md \
  README.md \
  <<'MSG'
<subject>

<body>
MSG
```

Report the new commit hash and confirm the tree is clean.
