"""Behavioral checks for the local teaching lab, including intended vulnerabilities."""
import contextlib
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def server(store, weak=False):
    port = free_port()
    args = [sys.executable, str(ROOT / "server.py"), "--port", str(port), "--store", str(store)]
    if weak:
        args.append("--weak-handles")
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise AssertionError(log.read())
                try:
                    common.call(port, "server/discover")
                    break
                except (OSError, ValueError, common.DemoError):
                    time.sleep(0.02)
            else:
                raise AssertionError("Test server did not become ready")
            yield port
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def run_script(name, *args, timeout=20):
    return subprocess.run(
        [sys.executable, str(ROOT / name), *map(str, args)],
        cwd=ROOT, env=ENV, text=True, capture_output=True, timeout=timeout,
    )


class LabTests(unittest.TestCase):
    def test_managed_server_releases_port_on_exception(self):
        from demo import server_instance
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "caller failed"):
                with server_instance(Path(directory) / "tasks.db") as port:
                    raise RuntimeError("caller failed")
            with self.assertRaises(OSError):
                socket.create_connection(("127.0.0.1", port), timeout=0.2)

    def test_interrupt_cleans_up_owned_processes_and_stores(self):
        self.assert_signal_cleanup(signal.SIGINT, 130)

    def test_termination_cleans_up_owned_processes_and_stores(self):
        self.assert_signal_cleanup(signal.SIGTERM, 143)

    def assert_signal_cleanup(self, termination_signal, expected_exit):
        with tempfile.TemporaryDirectory() as directory:
            port = free_port()
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "demo.py"), "5", "--port", str(port)],
                cwd=ROOT, env=dict(ENV, TMPDIR=directory),
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 5
                while True:
                    self.assertIsNone(process.poll(), "Runner stopped before the interrupt")
                    try:
                        common.call(port, "server/discover", timeout=0.1)
                        break
                    except common.DemoError:
                        if time.monotonic() >= deadline:
                            self.fail("Runner server did not start")
                        time.sleep(0.02)
                process.send_signal(termination_signal)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, expected_exit, stdout + stderr)
                with self.assertRaises(OSError):
                    socket.create_connection(("127.0.0.1", port), timeout=0.2)
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                # Also clean this test's isolated group if a regression leaks a child.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                process.communicate()

    def test_foreign_or_old_charge_cannot_satisfy_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "evidence.db"
            with sqlite3.connect(store) as db:
                db.execute("CREATE TABLE charges(id INTEGER, task_id TEXT, ts REAL)")
                db.executemany("INSERT INTO charges VALUES(?,?,?)", [
                    (1, "other-task", 200.0), (2, "target-task", 99.0),
                ])
            with self.assertRaises(common.DemoError):
                common.wait_for_charge(store, "target-task", timeout=0.05, not_before=100.0)

    def test_existing_store_survives_fresh_on_another_port(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "existing.db"
            original = b"Keep existing data even when the requested port is available."
            store.write_bytes(original)
            result = run_script("server.py", "--port", free_port(), "--store", store, "--fresh")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(store.read_bytes(), original)

    def test_poc4_rejects_different_peer_store(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first.db", Path(directory) / "second.db"
            with server(first) as port, server(second) as peer:
                result = run_script(
                    "poc4_cross_tenant.py", "--port", port, "--peer-port", peer, "--store", first,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--store", result.stderr)
                with sqlite3.connect(first) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)

    def test_poc_uses_environment_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "environment.db"
            with server(store) as port:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "poc1_handle_heist.py")], cwd=ROOT,
                    env=dict(ENV, MCP_DEMO_PORT=str(port), MCP_DEMO_STORE=str(store)),
                    text=True, capture_output=True, timeout=5,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runner_all_demos(self):
        result = run_script("demo.py", "all", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for number in range(1, 6):
            self.assertIn(f"PASS PoC {number}", result.stdout)

    def test_runner_occupied_port_leaves_existing_listener(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            result = run_script("demo.py", "1", "--port", port)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cannot bind", result.stderr)
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                pass

    def test_ledger_read_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "missing.db"
            with self.assertRaises((sqlite3.Error, RuntimeError, OSError)):
                common.charges(str(store))
            self.assertFalse(store.exists(), "Reading evidence must not create a database")

    def test_failed_bind_does_not_reset_database(self):
        with tempfile.TemporaryDirectory() as directory, socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            store = Path(directory) / "existing.db"
            original = b"Existing user's data must survive a failed bind."
            store.write_bytes(original)
            result = run_script(
                "server.py", "--port", occupied.getsockname()[1],
                "--store", store, "--fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(store.read_bytes(), original)

    def test_poc5_custom_configuration_produces_correlated_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "custom.db"
            evidence_file = Path(directory) / "evidence.json"
            with server(store) as port:
                result = run_script(
                    "poc5_phantom_killswitch.py", "--port", port, "--store", store,
                    "--evidence-json", evidence_file,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                evidence = json.loads(evidence_file.read_text())
                self.assertEqual(evidence["cancel_ack"], "received")
                self.assertEqual(evidence["reported_task_status"], "cancelled")
                self.assertEqual(evidence["side_effect"], "charge_posted")
                self.assertEqual(evidence["outcome"], "not_stopped")
                self.assertEqual(evidence["outcome_verified_by"], "demo_local_ledger_check")
                self.assertEqual(evidence["amount"], 500.0)
                rows = common.charges(str(store))
                self.assertEqual(rows[0]["task_id"], evidence["task_id"])
                self.assertGreaterEqual(rows[0]["ts"], evidence["cancel_ack_at"])

    def test_evidence_export_cannot_overwrite_its_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "preserved.db"
            with server(store) as port:
                symbolic, hard = Path(directory) / "symbolic.json", Path(directory) / "hard.json"
                symbolic.symlink_to(store)
                os.link(store, hard)
                original = store.read_bytes()
                destinations = [store, symbolic, hard, *(Path(str(store) + suffix)
                                for suffix in ("-wal", "-shm", "-journal"))]
                for destination in destinations:
                    with self.subTest(destination=destination.name):
                        result = run_script(
                            "poc5_phantom_killswitch.py", "--port", port, "--store", store,
                            "--evidence-json", destination,
                        )
                        self.assertNotEqual(result.returncode, 0, "Export must not replace the database")
                        self.assertEqual(store.read_bytes(), original)
                        with sqlite3.connect(store) as db:
                            self.assertEqual(db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
                        self.assertNotIn("Traceback", result.stderr)

    def test_wrong_handle_mode_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "strong.db"
            with server(store) as port:
                result = run_script("poc2_enumerable_handles.py", "--port", port, "--store", store)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--weak-handles", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_weak_enumeration_works_across_clock_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "weak.db"
            with server(store, weak=True) as port:
                old = common.call(
                    port, "tools/call", {"name": "make_invoice", "arguments": {}}, token="tok-alice",
                )["task"]["taskId"]
                time.sleep(1.05)
                result = run_script("poc2_enumerable_handles.py", "--port", port, "--store", store)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(old, result.stdout)

    def test_poc5_timeout_fails_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "timeout.db"
            with server(store) as port:
                result = run_script(
                    "poc5_phantom_killswitch.py", "--port", port, "--store", store, "--timeout", "0.1",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('"outcome": "not_stopped"', result.stdout)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
