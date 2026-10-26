"""Tests of claude/hooks/signal_stop.py: run with `make test`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "claude", "hooks", "signal_stop.py")
BIN = os.path.join(ROOT, "common", "bin")

VALID = 'Una domanda.\n\nASK_USER\n{"question": "Quale database?", "why": "Decide il driver."}\nEND_ASK_USER\n'
INVALID = 'Una domanda.\n\nASK_USER\n{"question": "Quale database?"}\nEND_ASK_USER\n'


def assistant(*blocks, request=None, tokens=0):
    message = {"role": "assistant", "content": list(blocks)}
    if request:
        message.update(id=request, model="claude-opus-5-5",
                       usage={"input_tokens": tokens, "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 10 * tokens, "output_tokens": tokens})
    return {"type": "assistant", "message": message}


def text(value):
    return {"type": "text", "text": value}


def handback(message):
    return {"type": "tool_use", "id": "toolu_1", "name": "SubagentHandback", "input": {"message": message}}


class SignalStopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        self.env = dict(os.environ, MINIME_STATE_DIR=self.tmp.name,
                        SIGNAL_SCHEMAS=os.path.join(ROOT, "common", "signals"),
                        PATH=BIN + os.pathsep + os.environ["PATH"])
        self.transcript = os.path.join(self.tmp.name, "agent.jsonl")
        self.write_transcript()

    def tearDown(self):
        self.tmp.cleanup()

    def write_transcript(self, *entries):
        with open(self.transcript, "w") as log:
            log.write(json.dumps({"type": "user", "message": {"role": "user", "content": "Lancia."}}) + "\n")
            for entry in entries:
                log.write(json.dumps(entry) + "\n")

    def stop(self, last_message="", event="SubagentStop"):
        """The hook's decision (None when it lets the agent stop)."""
        payload = {"hook_event_name": event, "agent_type": "ford", "agent_id": "a1",
                   "agent_transcript_path": self.transcript, "last_assistant_message": last_message}
        run = subprocess.run([sys.executable, HOOK, "--expect", "ASK_USER,FORD_DONE"],
                             input=json.dumps(payload), capture_output=True, text=True, env=self.env)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout) if run.stdout.strip() else None

    def events(self):
        path = os.path.join(self.tmp.name, "kent-events.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as log:
            return [json.loads(line) for line in log]

    def test_last_assistant_message(self):
        self.write_transcript(assistant(text(VALID)))
        self.assertIsNone(self.stop(VALID))
        [event] = self.events()
        self.assertEqual((event["agent"], event["agent_id"], event["signal"], event["ok"]),
                         ("ford", "a1", "ASK_USER", True))
        self.assertEqual(event["transcript"], self.transcript)

    def test_handback_message(self):
        self.write_transcript(assistant(text("Ecco il rapporto."), handback(VALID)))
        self.assertIsNone(self.stop(""))
        [event] = self.events()
        self.assertEqual((event["signal"], event["ok"]), ("ASK_USER", True))

    def test_handback_wins_over_last_message(self):
        self.write_transcript(assistant(handback(INVALID)))
        decision = self.stop(VALID)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("SubagentHandback", decision["reason"])

    def test_invalid_block_is_sent_back(self):
        self.write_transcript(assistant(text(INVALID)))
        decision = self.stop(INVALID)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("why", decision["reason"])
        [event] = self.events()
        self.assertEqual((event["signal"], event["ok"]), (None, False))
        self.assertIn("why", event["problems"])

    def test_no_block(self):
        self.assertEqual(self.stop("Fatto.")["decision"], "block")

    def test_retry_after_a_handback_reads_the_new_message(self):
        """A blocked handback, then a plain final message: the stale handback is not read
        again, and the turn leaves two events with the same id, a failure then a pass."""
        self.write_transcript(assistant(handback(INVALID)))
        self.assertEqual(self.stop("")["decision"], "block")
        self.write_transcript(assistant(handback(INVALID)),
                              {"type": "user", "message": {"role": "user", "content": "Fix the block."}},
                              assistant(text(VALID)))
        self.assertIsNone(self.stop(VALID))
        self.assertEqual([(e["agent_id"], e["ok"]) for e in self.events()], [("a1", False), ("a1", True)])

    def test_usage_and_replay(self):
        """Each turn counts its own requests once, whatever the blocks per request."""
        first = [assistant(text("Leggo."), request="m1", tokens=5),
                 assistant(text(VALID), request="m2", tokens=7), assistant(text(VALID), request="m2", tokens=7)]
        self.write_transcript(*first)
        self.stop(VALID)
        self.write_transcript(*first, {"type": "user", "message": {"role": "user", "content": "Ancora."}},
                              assistant(text(VALID), request="m3", tokens=3))
        self.stop(VALID)
        one, two = self.events()
        self.assertEqual((one["usage"]["calls"], one["usage"]["output"], one["usage"]["cache_read"]), (2, 12, 120))
        self.assertEqual((two["usage"]["calls"], two["usage"]["calls_total"], two["usage"]["output"]), (1, 3, 3))
        self.assertEqual(one["launch"], "Lancia.")
        self.assertNotIn("launch", two)
        self.assertEqual(one["usage"]["model"], "claude-opus-5-5")

    def test_failed_signal_is_an_error(self):
        self.write_transcript(assistant(text(INVALID)))
        self.stop(INVALID)
        with open(os.path.join(self.tmp.name, "kent-errors.jsonl")) as log:
            [error] = [json.loads(line) for line in log]
        self.assertEqual((error["kind"], error["agent"]), ("signal", "ford"))

    def test_main_thread_is_not_checked(self):
        self.assertIsNone(self.stop("Ciao.", event="Stop"))
        self.assertEqual(self.events(), [])

    def test_unreadable_payload(self):
        run = subprocess.run([sys.executable, HOOK, "--expect", "ASK_USER"], input="not json",
                             capture_output=True, text=True, env=self.env)
        self.assertEqual((run.returncode, run.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
