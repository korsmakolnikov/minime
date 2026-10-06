# Standing rules for every agent

* **No push, ever.** No agent or sub-agent, for any reason, runs `git push` or
  any other command that updates a remote branch. The user always pushes by
  hand. Commit locally and stop.
* Any operation whose effects stay inside a git-versioned folder may run
  unattended; outside git repositories, ask the user first.
