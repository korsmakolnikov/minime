# Standing rules for every agent

* **No push, ever.** No agent or sub-agent, for any reason, runs `git push` or
  any other command that updates a remote branch. The user always pushes by
  hand. Commit locally and stop.
* Any operation whose effects stay inside a git-versioned folder may run
  unattended; outside git repositories, ask the user first.
* **Never `cd` in the shell.** The shell persists across commands and its
  directory can become the session's: a session stuck in a subfolder raises a
  path-access prompt for everything above it. Run commands from the project
  root with paths (`git -C <dir>`, `mix test test/foo_test.exs`), or in a
  subshell, `(cd <dir> && <command>)`, which leaves the shell where it was.
* **Reply in the user's language.** When the user writes in Italian, reason
  and reply in Italian.
