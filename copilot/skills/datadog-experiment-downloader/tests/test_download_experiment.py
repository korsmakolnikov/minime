import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "download_experiment.py"
spec = importlib.util.spec_from_file_location("experiment_downloader", SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load download_experiment.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

EXPERIMENT_ID = "experiment-1"
TRACE_IDS = ("69566fd0000000001111111111111111", "69567028000000002222222222222222")


class FakePup:
    def __init__(self, *, failing_traces=(), page_size=1):
        self.calls: list[list[str]] = []
        self.failing_traces = set(failing_traces)
        self.page_size = page_size

    def __call__(self, arguments):
        arguments = list(arguments)
        self.calls.append(arguments)
        match arguments[:4]:
            case ["llm-obs", "experiments", "summary", _]:
                return json.dumps({"total_events": len(TRACE_IDS)})
            case ["llm-obs", "experiments", "events", "list"]:
                offset = int(arguments[arguments.index("--offset") + 1])
                events = [{"id": f"event-{index}"} for index in range(len(TRACE_IDS))][
                    offset : offset + self.page_size
                ]
                return json.dumps({"events": events, "total_matching": len(TRACE_IDS)})
            case ["llm-obs", "experiments", "events", "get"]:
                index = int(arguments[5].removeprefix("event-"))
                return json.dumps(
                    {
                        "id": arguments[5],
                        "trace_id": TRACE_IDS[index],
                        "status": "ok",
                        "duration_ms": 1000.0,
                        "metrics": {"outcome": index},
                        "dimensions": {
                            "input.case_id": f"case-{index}",
                            "expected_output.outcome": "opened_standard",
                            "output.prediction": "opened_standard",
                        },
                    }
                )
            case ["llm-obs", "spans", "get-agent-loop", "--trace-id"]:
                if arguments[4] in self.failing_traces:
                    raise module.PupError("no spans found")
                return json.dumps({"trace_id": arguments[4], "iterations": []})
        raise AssertionError(f"Unexpected pup call: {arguments}")


class DownloadExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.output = Path(self.directory.name)
        sleep = patch.object(module.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        self.addCleanup(self.directory.cleanup)

    def _options(self, **overrides):
        return module.Options(EXPERIMENT_ID, self.output, workers=2, **overrides)

    def test_downloads_summary_paginated_events_and_every_agent_loop(self) -> None:
        manifest = module.download(self._options(), FakePup())

        self.assertTrue((self.output / "summary.json").is_file())
        self.assertEqual(
            sorted(path.name for path in (self.output / "events").iterdir()),
            ["event-0.json", "event-1.json"],
        )
        self.assertEqual(
            sorted(path.stem for path in (self.output / "loops").iterdir()),
            sorted(TRACE_IDS),
        )
        self.assertEqual(manifest["downloaded_events"], 2)
        self.assertEqual(manifest["downloaded_loops"], 2)
        self.assertEqual(manifest["failed_loops"], {})
        self.assertEqual(manifest["events"][1]["case_id"], "case-1")
        self.assertEqual(
            json.loads((self.output / "manifest.json").read_text())["experiment_id"],
            EXPERIMENT_ID,
        )

    def test_reports_failed_loops_after_retries(self) -> None:
        pup = FakePup(failing_traces={TRACE_IDS[0]})

        manifest = module.download(self._options(), pup)

        self.assertEqual(list(manifest["failed_loops"]), [TRACE_IDS[0]])
        attempts = [call for call in pup.calls if TRACE_IDS[0] in call]
        self.assertEqual(len(attempts), 1 + len(module.RETRY_DELAYS_SECONDS))

    def test_skips_files_already_downloaded(self) -> None:
        module.download(self._options(), FakePup())
        pup = FakePup()

        module.download(self._options(), pup)

        self.assertFalse(
            [call for call in pup.calls if {"get", "get-agent-loop"} & set(call)]
        )

    def test_skip_loops_downloads_only_events(self) -> None:
        manifest = module.download(self._options(skip_loops=True), FakePup())

        self.assertEqual(manifest["downloaded_loops"], 0)
        self.assertEqual(manifest["failed_loops"], {})

    def test_loop_window_starts_an_hour_before_the_trace(self) -> None:
        self.assertEqual(
            module.loop_window_start("69566fd0000000001111111111111111"),
            "2026-01-01T12:00:00Z",
        )
        self.assertEqual(module.loop_window_start("not-hex"), "30d")


if __name__ == "__main__":
    unittest.main()
