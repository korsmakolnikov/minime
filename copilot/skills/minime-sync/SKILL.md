---
name: minime-sync
description: Mirrors the live Copilot setup in ~/.copilot (agents, skills, hooks, settings, global instructions) and the gutexberg and soong-poll commands into ~/code/minime/copilot/, then records the change as a fixup of the "feat: copilot workflow" commit through gutexberg. Use before a /restart and whenever an agent, skill, hook or setting has changed.
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

* The branch must be `copilot`; otherwise stop and tell the user.
* The tree must be clean; otherwise stop and show `git status`: uncommitted
  work in the mirror is not yours to commit.

## 2. Copy

Copy only what the mirror tracks (never `permissions-config.json`,
`config.json`, `session-state/` or logs: they are machine state).

```sh
cd ~/code/minime \
  && cp ~/.copilot/agents/*.agent.md copilot/agents/ \
  && for s in ~/.copilot/skills/*/; do cp -r "$s" copilot/skills/; done \
  && cp -r ~/.copilot/hooks/. copilot/hooks/ \
  && cp ~/.copilot/settings.json ~/.copilot/copilot-instructions.md copilot/ \
  && cp ~/.local/bin/gutexberg ~/.local/bin/soong-poll copilot/bin/
```

Then look for files the live setup no longer has (renamed or deleted):

```sh
cd ~/code/minime && for d in agents skills hooks; do diff -rq ~/.copilot/$d copilot/$d; done
```

Every `Only in copilot/…` line is a file removed or renamed live. If it was
renamed, use `git mv old new` before copying (history follows the file);
otherwise `git rm` it. Ask the user when you cannot tell which.
`Only in ~/.copilot/…` lines must not remain after the copy.

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

The target is the root commit of the branch:

```sh
cd ~/code/minime && git log --format=%h --grep='^feat: copilot workflow$' master..copilot
```

Write only the **body** to a temporary file (gutexberg writes the
`fixup! …` subject and the Copilot trailer itself): one or two C2-level English
sentences saying what changed.

```sh
cd ~/code/minime && printf '%s\n' '<body>' > /tmp/minime-sync-msg \
  && gutexberg stage <changed paths> \
  && gutexberg fixup <target> --model <your model id> -F /tmp/minime-sync-msg; \
  rm -f /tmp/minime-sync-msg; git status --short; git log --oneline -1
```

Never squash or autosquash the fixup: the user does it by hand. Report the new
commit hash and confirm the tree is clean.
