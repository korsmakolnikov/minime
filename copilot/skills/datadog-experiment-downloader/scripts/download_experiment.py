"""Download a Datadog LLM Observability experiment, including every agent loop."""

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

PAGE_SIZE = 100
LOOP_WINDOW_MARGIN = timedelta(hours=1)
DEFAULT_MAX_CONTENT_LENGTH = 100_000
RETRY_DELAYS_SECONDS = (2, 5, 15)

Runner = Callable[[Sequence[str]], str]


class PupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Options:
    experiment_id: str
    output: Path
    workers: int = 8
    max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH
    skip_loops: bool = False
    overwrite: bool = False


def run_pup(arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ["pup", "--no-agent", *arguments],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise PupError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def call_json(
    runner: Runner,
    arguments: Sequence[str],
    retry_delays: Sequence[float] = RETRY_DELAYS_SECONDS,
) -> Any:
    last_error: Exception | None = None
    for delay in (0, *retry_delays):
        time.sleep(delay)
        try:
            return json.loads(runner(arguments))
        except (PupError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
            last_error = error
    raise PupError(f"pup {' '.join(arguments)} failed: {last_error}")


def loop_window_start(trace_id: str) -> str:
    """
    Return an RFC3339 lower bound for the agent loop query.

    Datadog 128-bit trace IDs start with the trace creation time as 8 hex
    digits of Unix seconds. The default pup window of one hour misses older
    traces, so the window is anchored on that timestamp instead.
    """
    try:
        started_at = datetime.fromtimestamp(int(trace_id[:8], 16), UTC)
    except ValueError:
        return "30d"
    return (started_at - LOOP_WINDOW_MARGIN).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_event_ids(runner: Runner, experiment_id: str) -> list[str]:
    event_ids: list[str] = []
    while True:
        page = call_json(
            runner,
            [
                "llm-obs",
                "experiments",
                "events",
                "list",
                experiment_id,
                "--limit",
                str(PAGE_SIZE),
                "--offset",
                str(len(event_ids)),
            ],
        )
        events = page.get("events", [])
        event_ids.extend(event["id"] for event in events)
        if not events or len(event_ids) >= page.get("total_matching", 0):
            return event_ids


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), "utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _fetch_event(runner: Runner, options: Options, event_id: str) -> dict[str, Any]:
    path = options.output / "events" / f"{event_id}.json"
    if path.exists() and not options.overwrite:
        return _read_json(path)
    event = call_json(
        runner,
        ["llm-obs", "experiments", "events", "get", options.experiment_id, event_id],
    )
    _write_json(path, event)
    return event


def _fetch_loop(runner: Runner, options: Options, trace_id: str) -> str | None:
    path = options.output / "loops" / f"{trace_id}.json"
    if path.exists() and not options.overwrite:
        return None
    try:
        loop = call_json(
            runner,
            [
                "llm-obs",
                "spans",
                "get-agent-loop",
                "--trace-id",
                trace_id,
                "--from",
                loop_window_start(trace_id),
                "--to",
                "now",
                "--max-content-length",
                str(options.max_content_length),
            ],
        )
    except PupError as error:
        return str(error)
    _write_json(path, loop)
    return None


def _manifest_entry(event: dict[str, Any]) -> dict[str, Any]:
    dimensions = event.get("dimensions", {})
    return {
        "event_id": event.get("id"),
        "trace_id": event.get("trace_id"),
        "case_id": dimensions.get("input.case_id"),
        "status": event.get("status"),
        "duration_ms": event.get("duration_ms"),
        "metrics": event.get("metrics", {}),
        "expected_outcome": dimensions.get("expected_output.outcome"),
        "predicted_outcome": dimensions.get("output.prediction"),
        "error": dimensions.get("error"),
    }


def download(options: Options, runner: Runner = run_pup) -> dict[str, Any]:
    (options.output / "events").mkdir(parents=True, exist_ok=True)
    (options.output / "loops").mkdir(parents=True, exist_ok=True)
    summary = call_json(
        runner, ["llm-obs", "experiments", "summary", options.experiment_id]
    )
    _write_json(options.output / "summary.json", summary)
    event_ids = list_event_ids(runner, options.experiment_id)
    with ThreadPoolExecutor(max_workers=options.workers) as pool:
        events = list(
            pool.map(
                lambda event_id: _fetch_event(runner, options, event_id), event_ids
            )
        )
        trace_ids = sorted(
            {event["trace_id"] for event in events if event.get("trace_id")}
        )
        loop_errors = (
            [None] * len(trace_ids)
            if options.skip_loops
            else list(
                pool.map(
                    lambda trace_id: _fetch_loop(runner, options, trace_id), trace_ids
                )
            )
        )
    failed_loops = {
        trace_id: error
        for trace_id, error in zip(trace_ids, loop_errors, strict=True)
        if error is not None
    }
    manifest = {
        "experiment_id": options.experiment_id,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "total_events": summary.get("total_events"),
        "downloaded_events": len(events),
        "downloaded_loops": len(list((options.output / "loops").glob("*.json"))),
        "failed_loops": failed_loops,
        "events": [_manifest_entry(event) for event in events],
    }
    _write_json(options.output / "manifest.json", manifest)
    return manifest


def parse_arguments(argv: Sequence[str]) -> Options:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id")
    parser.add_argument(
        "--output", type=Path, help="Defaults to /tmp/dd-experiment-<id>"
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--max-content-length", type=int, default=DEFAULT_MAX_CONTENT_LENGTH
    )
    parser.add_argument("--skip-loops", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args(argv)
    return Options(
        experiment_id=arguments.experiment_id,
        output=arguments.output
        or Path(f"/tmp/dd-experiment-{arguments.experiment_id}"),
        workers=arguments.workers,
        max_content_length=arguments.max_content_length,
        skip_loops=arguments.skip_loops,
        overwrite=arguments.overwrite,
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if argv is None else argv)
    manifest = download(options)
    report = {
        key: manifest[key]
        for key in (
            "experiment_id",
            "total_events",
            "downloaded_events",
            "downloaded_loops",
        )
    }
    report["failed_loops"] = len(manifest["failed_loops"])
    report["output"] = str(options.output)
    print(json.dumps(report, indent=2))
    return 0 if not manifest["failed_loops"] else 1


if __name__ == "__main__":
    sys.exit(main())
