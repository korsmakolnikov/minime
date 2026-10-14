---
name: adl-interview
description: Protocol for interviewing the user to build ADL definitions and component interfaces one question at a time, including the ASK_USER relay format used by sub-agents that cannot talk to the user directly. Use when composing or revising .adl files or designing component interfaces with the user.
---

# Interviewing the user

Load `adl-spec` first.

## Talking to the user

Use the `ask_user` tool if you have it. As a sub-agent without it, end your
turn with **exactly one** relay block and nothing after it:

```
ASK_USER
question: <one focused question, self-contained>
choices: <option 1> | <option 2> | <option 3>     (optional)
default: <recommended option>                     (optional)
why: <one line on what the answer changes>
END_ASK_USER
```

Write the question in the user's language (the orchestrator tells you which)
and code snippets exactly as they will be written, comments and docs in
English. The orchestrator forwards it verbatim and replies with the user's
answer as your next turn. Never guess an answer to a question you asked.

## Principles

* **One question per turn**, preferably a concrete proposal the user can
  accept, amend or reject ("I propose these three domains: …").
* Ask about the **domain**; decide implementation details yourself.
* Challenge the design: cycles, a component every other one depends on,
  names hiding two responsibilities, assertions that cannot be checked
  statically.
* Never add an artifact or an assertion the user has not confirmed; show the
  complete ADL text and get an explicit yes before writing a file.

## Order of the interview

1. **Scope.** A whole system, a domain, a subdomain or a component;
   greenfield or a change to an existing architecture. First read the
   shopping list (`.sources/shopping_lists/<branch>.md`), the domain spec
   (`.sources/spec.yaml`) and `.sources/as-is/` if they exist, and do not ask what
   they answer.
2. **Artifacts, top-down.** System, then domains, then each domain's
   subdomains and components, then libraries and services if relevant,
   confirming the logical and physical name of each.
3. **Assertions.** Containment first (`CLASSES are only CONTAINED within …`),
   then dependency rules between siblings, then cross-domain rules; `FOREACH`
   when a rule applies to every artifact of a collection. Say whether each
   can become a static fitness function (see `adl-fitness`); if not, ask
   whether to keep it as documentation and record the tooling it needs in
   `REQUIRES`.
4. **Review.** Show each complete file and wait for approval, then write it.
5. **Component interfaces** (not ADL: they go straight into code), one
   component at a time: its responsibility in one sentence; its public
   operations (name, inputs, output, failure modes); the data types crossing
   the boundary; facade (plain public functions) or port (behaviour/Protocol
   with pluggable implementations). Get the signatures, in the target
   language, approved before writing them with the `adl-scaffold` skill.
