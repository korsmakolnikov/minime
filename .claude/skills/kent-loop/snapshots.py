#!/usr/bin/env python3
"""Snapshots of a kent-loop session, for time travel between agent turns.

Usage (the kent-loop driver calls it; BASE is $KENT_LOOP):
  snapshots.py take <base> <fixture dir> <label>   one snapshot now
  snapshots.py watch <base> <fixture dir>          one snapshot per agent turn
                                                   that ends with a matching
                                                   signal, while kent runs
  snapshots.py list <fixture dir>
  snapshots.py restore <base> <snapshot dir>       replace project/ and state/

A snapshot is a folder <NN>-<label> in the fixture folder:
  meta.json            time, label, the event that triggered it, minime's HEAD
  project.tar.gz       the test project, its .git included, ignored files left out
  state.tar.gz         the workflow's logs and state (MINIME_STATE_DIR)
  kent.tar.gz          kent's stream (out.jsonl)                     } local only:
  transcripts.tar.gz   the sub-agent transcripts the events log names } see below

kent's stream and the transcripts hold the whole API requests, the user's
private instructions and context included: fixtures/.gitignore keeps them out
of git, so a snapshot restored on another machine has neither.
"""
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time

SIGNALS = re.compile(os.environ.get("KENT_LOOP_SNAPSHOT_SIGNALS", r"_DONE$|^FORD_AS_IS$"))
MINIME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))


def project_files(project):
    """The project's files relative to it: .git and what git does not ignore."""
    files = []
    for top, _, names in os.walk(project):
        if os.path.relpath(top, project).split(os.sep)[0] == ".git":
            files += [os.path.relpath(os.path.join(top, n), project) for n in names]
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=project,
                            capture_output=True, text=True)
    if listed.returncode == 0:
        files += [f for f in listed.stdout.split("\0") if f]
    else:
        for top, dirs, names in os.walk(project):
            dirs[:] = [d for d in dirs if d not in (".venv", "_build", "deps", "node_modules", "__pycache__")]
            files += [os.path.relpath(os.path.join(top, n), project) for n in names]
    return sorted(set(f for f in files if os.path.isfile(os.path.join(project, f))))


def pack(path, root, names):
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            tar.add(os.path.join(root, name), arcname=name, recursive=False)


def events(base):
    path = os.path.join(base, "state", "kent-events.jsonl")
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path):
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def take(base, fixture, label, event=None):
    os.makedirs(fixture, exist_ok=True)
    number = 1 + max([int(d.split("-")[0]) for d in os.listdir(fixture) if d[:2].isdigit()] or [0])
    target = os.path.join(fixture, f"{number:02d}-{re.sub(r'[^A-Za-z0-9_.-]+', '-', label)}")
    os.makedirs(target)
    project = os.path.join(base, "project")
    pack(os.path.join(target, "project.tar.gz"), project, project_files(project))
    state = [os.path.join("state", f) for f in sorted(os.listdir(os.path.join(base, "state")))] \
        if os.path.isdir(os.path.join(base, "state")) else []
    pack(os.path.join(target, "state.tar.gz"), base, state)
    pack(os.path.join(target, "kent.tar.gz"), base, [f for f in ("out.jsonl",) if os.path.exists(os.path.join(base, f))])
    transcripts = sorted({e["transcript"] for e in events(base) if e.get("transcript") and os.path.exists(e["transcript"])})
    with tarfile.open(os.path.join(target, "transcripts.tar.gz"), "w:gz") as tar:
        for path in transcripts:
            tar.add(path, arcname=path.lstrip("/"))
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=MINIME, capture_output=True, text=True)
    meta = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "label": label, "event": event,
            "minime": head.stdout.strip(), "base": base}
    with open(os.path.join(target, "meta.json"), "w") as out:
        json.dump(meta, out, indent=2)
        out.write("\n")
    print(f"snapshot {target}")


def watch(base, fixture):
    pidfile = os.path.join(base, "kent.pid")
    seen = len(events(base))
    while os.path.exists(pidfile):
        rows = events(base)
        for row in rows[seen:]:
            if row.get("ok") and SIGNALS.search(row.get("signal") or ""):
                take(base, fixture, f"{row.get('agent')}-{row['signal']}", row)
                sys.stdout.flush()
        seen = len(rows)
        time.sleep(2)


def restore(base, snapshot):
    project = os.path.join(base, "project")
    for folder in (project, os.path.join(base, "state")):
        subprocess.run(["rm", "-rf", folder], check=True)
    os.makedirs(project)
    with tarfile.open(os.path.join(snapshot, "project.tar.gz")) as tar:
        tar.extractall(project, filter="tar")
    with tarfile.open(os.path.join(snapshot, "state.tar.gz")) as tar:
        tar.extractall(base, filter="tar")
    if os.path.exists(os.path.join(snapshot, "kent.tar.gz")):
        with tarfile.open(os.path.join(snapshot, "kent.tar.gz")) as tar:
            tar.extractall(base, filter="tar")
    transcripts = os.path.join(snapshot, "transcripts.tar.gz")
    with tarfile.open(transcripts) if os.path.exists(transcripts) else tarfile.open(fileobj=io.BytesIO(), mode="w") as tar:
        for member in tar.getmembers():
            path = "/" + member.name
            if member.isfile() and not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as out:
                    out.write((tar.extractfile(member) or io.BytesIO()).read())
    with open(os.path.join(base, "read.cursor"), "w") as cursor:
        cursor.write(str(sum(1 for _ in open(os.path.join(base, "out.jsonl")))) if os.path.exists(
            os.path.join(base, "out.jsonl")) else "0")
    print(f"restored {snapshot} into {base}: start kent again to resume from it")


def main():
    args = sys.argv[1:]
    if args[:1] == ["take"] and len(args) == 4:
        take(*args[1:])
    elif args[:1] == ["watch"] and len(args) == 3:
        watch(*args[1:])
    elif args[:1] == ["list"] and len(args) == 2:
        for name in sorted(os.listdir(args[1])) if os.path.isdir(args[1]) else []:
            meta = os.path.join(args[1], name, "meta.json")
            if os.path.exists(meta):
                m = json.load(open(meta))
                print(f"{name}  {m['time']}  minime {m['minime']}")
    elif args[:1] == ["restore"] and len(args) == 3:
        restore(*args[1:])
    else:
        print(__doc__.strip())
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
