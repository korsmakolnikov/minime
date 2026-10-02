---
name: adl-interview
description: Protocol for interviewing the user to build ADL definitions and component interfaces one question at a time, including the ASK_USER relay format used by sub-agents that cannot talk to the user directly. Use when composing or revising .adl files or designing component interfaces with the user.
---

# Interviewing the user

Load `adl-spec` first.

## Talking to the user

If you have the `ask_user` tool, use it. If you do not (you are running as a
sub-agent), end your turn with **exactly one** relay block and nothing after it:

```
ASK_USER
question: <one focused question, self-contained>
choices: <option 1> | <option 2> | <option 3>     (optional)
default: <recommended option>                     (optional)
why: <one line on what the answer changes>
END_ASK_USER
```

Write the question in the user's language (the orchestrator tells you which
one). The orchestrator forwards the question verbatim and replies with the user's
answer as your next turn. Never guess an answer to a question you asked.

## Principles

* **One question per turn.** Prefer a concrete proposal the user can accept,
  amend or reject over an open question ("I propose these three domains: …").
* Ask about the **domain**, not about implementation details you can decide
  yourself.
* Challenge the design: point out cycles, a component that every other one
  depends on, names that hide two responsibilities, assertions that cannot be
  checked statically.
* Never add an artifact or an assertion the user has not confirmed.
* Before writing a file, show the complete ADL text and get an explicit yes.

## Order of the interview

1. **Scope.** What is being defined: a whole system, a domain, a subdomain or a
   component. Greenfield or change to an existing architecture. Read
   `.adl/shopping-list.md` and `.adl/as-is/` first if they exist, and do not
   ask what they already answer.
2. **Artifacts, top-down.** System name and physical name, then domains, then
   for each domain its subdomains and components, then libraries and services
   if relevant. Confirm the logical and physical names of each.
3. **Assertions.** Containment first (`CLASSES are only CONTAINED within …`),
   then dependency rules between siblings, then cross-domain rules. Use
   `FOREACH` when the same rule applies to every artifact of a collection.
   For each assertion say whether it can become a static fitness function
   (see `adl-fitness`). If it cannot, ask whether to keep it as documentation
   and record the tooling it needs in `REQUIRES`.
4. **Review.** Show each complete file and wait for approval. Then write it.
5. **Component interfaces** (not ADL: they go straight into code). For each
   component, one at a time:
   * Its responsibility in one sentence.
   * Its public operations: name, inputs, output, failure modes.
   * The data types crossing the boundary.
   * Facade (plain public functions) or port (behaviour/Protocol with
     pluggable implementations).
   Propose the signatures in the target language and get them approved before
   writing them with the `adl-scaffold` skill.
