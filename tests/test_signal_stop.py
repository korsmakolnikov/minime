"""Tests of claude/hooks/signal_stop.py: run with `make test`."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "claude", "hooks", "signal_stop.py")
VALID = 'Audit done.\nAUDIT_OK\n{"events": []}\nEND_AUDIT_OK\n'
BROKEN = 'Audit done.\nAUDIT_OK\n{"events": 3}\nEND_AUDIT_OK\n'


class SignalStopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        self.env = dict(os.environ, MINIME_STATE_DIR=self.tmp.name,
                        SIGNAL_SCHEMAS=os.path.join(ROOT, "common", "signals"),
                        PATH=os.path.join(ROOT, "common", "bin") + os.pathsep + os.environ["PATH"])

    def tearDown(self):
        self.tmp.cleanup()

    def transcript(self, *entries):
        path = os.path.join(self.tmp.name, "agent.jsonl")
        with open(path, "w") as out:
            for entry in entries:
                out.write(json.dumps(entry) + "\n")
        return path

    def stop(self, last_message="", transcript=None, event="SubagentStop"):
        """The hook's decision ({} when it lets the agent stop)."""
        payload = {"hook_event_name": event, "agent_type": "joshua", "agent_id": "a1",
                   "agent_transcript_path": transcript, "last_assistant_message": last_message}
        run = subprocess.run([sys.executable, HOOK, "--expect", "AUDIT_OK,AUDIT_VIOLATIONS"],
                             input=json.dumps(payload), capture_output=True, text=True, env=self.env)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout) if run.stdout.strip() else {}

    def events(self):
        path = os.path.join(self.tmp.name, "kent-events.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as log:
            return [json.loads(line) for line in log]

    def test_last_assistant_message_without_handback(self):
        path = self.transcript({"type": "assistant", "message": {"content": [{"type": "text", "text": VALID}]}})
        self.assertEqual(self.stop(VALID, path), {})
        self.assertEqual([(e["signal"], e["ok"]) for e in self.events()], [("AUDIT_OK", True)])

    def test_handback_message_wins_over_an_empty_last_message(self):
        path = self.transcript(
            {"type": "user", "message": {"content": "AUDIT"}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "SubagentHandback", "input": {"message": VALID}}]}})
        self.assertEqual(self.stop("", path), {})
        self.assertEqual(self.events()[0]["signal"], "AUDIT_OK")

    def test_broken_handback_blocks(self):
        path = self.transcript({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "SubagentHandback", "input": {"message": BROKEN}}]}})
        decision = self.stop(VALID, path)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("SubagentHandback", decision["reason"])

    def test_a_blocked_stop_and_its_retry_log_two_events_of_one_turn(self):
        self.assertEqual(self.stop(BROKEN)["decision"], "block")
        self.assertEqual(self.stop(VALID), {})
        events = self.events()
        self.assertEqual([(e["agent_id"], e["ok"]) for e in events], [("a1", False), ("a1", True)])
        self.assertIsNone(events[0]["signal"])
        self.assertIn("problems", events[0])

    def test_main_thread_stop_is_not_checked(self):
        self.assertEqual(self.stop("no signal here", event="Stop"), {})
        self.assertEqual(self.events(), [])


if __name__ == "__main__":
    unittest.main()
