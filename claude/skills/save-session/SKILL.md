---
name: save-session
description: Save kent's session to its progress file before the user interrupts it, so that a later `claude --agent kent` in the same repository resumes from there. Use when the user types /save-session, or asks to save, park or pause the workflow session.
---

# save-session

The user is about to interrupt the workflow. Everything kent knows that the
repository and the logs do not hold must go into the progress file now:
`session-state write` replaces it whole, in the workflow's state folder
(`~/.local/state/minime/<repository>/kent-partial-session-progress.md`),
which outlives a reboot and is kept 30 days. kent reads it with
`session-state show` at step 0 of the next session.

## Steps

1. Read what is on disk: `git-read branch --show-current`, `git-read log
   --oneline -15`, `git-read status --porcelain`, and the current file
   (`session-state show`), to keep what it holds and is still true.
2. Write the file with `session-state write` and a quoted heredoc, every
   section below, in the user's language; quote questions and answers
   verbatim:

   ```markdown
   # Session: <repository> @ <branch> (base <base branch>), saved <date and time>

   ## Where we are
   Step <n> (<name>). Next action: <exactly what kent does first on resume>.

   ## Components
   | Order | Component | Scope | State (todo, unclebob, martin, squashed <hash> under the user's review, reviewed) |

   ## Open question to the user
   <the question, verbatim, and which agent asked it; "none">

   ## Agents
   <each agent launched in this session: name, agent id, what it was doing,
   whether its turn ended; a running agent's work is lost with the session:
   say what the resumed session must relaunch>

   ## Decisions and answers that still matter
   <one line each>

   ## Paths
   Shopping list, spec, ADL, components map, documentation.

   ## Harness and commands that worked
   <the harness discovered, the toolchain commands>

   ## Agent instructions collected for marvin
   <one line each>
   ```

3. Tell the user, in their language: the file's path, what the resumed
   session will do first, and that it starts with `claude --agent kent`
   from the repository's root. Uncommitted work stays in the working tree;
   kent commits nothing for the save.
