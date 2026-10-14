---
name: datadog-experiment-downloader
description: "Download a complete Datadog LLM Observability experiment with pup: summary, every event with its dimensions and metrics, and the agentic loop (reasoning, tool calls, tool results) of every trace. Use before analysing an experiment run offline, comparing runs, or investigating why cases failed."
---

# Datadog Experiment Downloader

## Overview
`scripts/download_experiment.py` mirrors one Datadog LLM Observability experiment to a local folder through the `pup` CLI. It fetches events and agent loops in parallel, retries transient failures, resumes partial downloads, and writes a manifest that maps each case to its event, trace and outcome.

## Prerequisites
- `pup` on `PATH` (usually `~/.local/bin`) and authenticated (`pup auth login`). Expired tokens are refreshed automatically.
- The experiment ID, taken from the experiment URL (`https://app.datadoghq.eu/llm/experiments/<id>`) or from the last line of the experiment runner output.

## Usage

```bash
PATH=$HOME/.local/bin:$PATH uv run --no-project python \
  ~/.copilot/skills/datadog-experiment-downloader/scripts/download_experiment.py \
  <experiment_id> --output /tmp/dd-experiment-<label>
```

Options:
- `--output`: destination folder; defaults to `/tmp/dd-experiment-<id>`. Never write it inside a repository.
- `--workers`: parallel pup calls, default 8.
- `--max-content-length`: characters kept per agent loop step, default 100000. pup truncates heavily without it.
- `--skip-loops`: download only the summary and events.
- `--overwrite`: refetch files that already exist; by default the download resumes.

The command prints a JSON report and exits with status 1 when any agent loop could not be fetched.

## Output layout

```
<output>/
  summary.json            # pup llm-obs experiments summary
  manifest.json           # experiment, counts, failed_loops, one entry per event
  events/<event_id>.json  # pup llm-obs experiments events get (dimensions, metrics, trace_id)
  loops/<trace_id>.json   # pup llm-obs spans get-agent-loop (iterations, timeline)
```

Each manifest entry holds `event_id`, `trace_id`, `case_id`, `status`, `duration_ms`, `metrics`, `expected_outcome`, `predicted_outcome` and `error`. Join a case to its loop through `trace_id`.

## Analysis tips
- Compare `manifest.json` entries with `summary.json` `total_events`: a missing event usually means a case timed out or crashed.
- In loop timelines, `tool_calls` may be a list or its string representation; parse the latter with `ast.literal_eval`.
- Reasoning lives in timeline items with role `reasoning`; final decisions are `final_result_*` tool calls.
- Values such as `[Croatia Health Insurance Number Scanner]` are Datadog Sensitive Data Scanner redactions, not model output.

## Troubleshooting
- `no spans found for trace`: the loop query window was wrong or spans are still being indexed. The script anchors the window one hour before the trace start (decoded from the first 8 hex digits of the trace ID); rerun later to resume only the missing loops.
- Authentication errors: run `pup auth login`, then rerun; completed files are kept.
