#!/usr/bin/env python3
"""Run selected threat demonstrations with owned servers and temporary databases."""
import argparse
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from common import DemoError, call, expect, port_number, positive_timeout, run_demo

ROOT = Path(__file__).resolve().parent
DEMOS = {
    "1": "poc1_handle_heist.py",
    "2": "poc2_enumerable_handles.py",
    "3": "poc3_confused_deputy.py",
    "4": "poc4_cross_tenant.py",
    "5": "poc5_phantom_killswitch.py",
}


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@contextmanager
def server_instance(store, port=0, weak=False, timeout=15):
    """Own one process; release it on success, error, or Ctrl-C."""
    with tempfile.TemporaryDirectory(prefix="mcp-demo-server-") as directory:
        ready = Path(directory) / "ready.json"
        log_path = Path(directory) / "server.log"
        with log_path.open("w") as log:
            command = [
                sys.executable, str(ROOT / "server.py"), "--port", str(port),
                "--store", str(store), "--ready-file", str(ready),
            ]
            if weak:
                command.append("--weak-handles")
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + timeout
                while True:
                    if process.poll() is not None:
                        detail = log_path.read_text().strip()
                        raise DemoError(f"Server startup failed: {detail}")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise DemoError(f"Server readiness timed out after {timeout:g}s")
                    if ready.exists():
                        try:
                            state = json.loads(ready.read_text())
                        except json.JSONDecodeError:
                            state = None
                        if state:
                            expect(state["store"] == str(Path(store).resolve()),
                                   "The started server reported a different store")
                            expect(state["weak_handles"] is weak, "The server reported the wrong handle mode")
                            info = call(state["port"], "server/discover", timeout=min(remaining, 1))
                            expect(info.get("demo") == {"store": state["store"], "weak_handles": weak},
                                   "The responding server does not match the requested configuration")
                            yield state["port"]
                            return
                    time.sleep(min(0.02, remaining))
            finally:
                stop_process(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", nargs="?", choices=["all", *DEMOS], default="all")
    parser.add_argument("--port", type=port_number, default=0, help="first server port; 0 selects a free port")
    parser.add_argument("--peer-port", type=port_number, default=0, help="second port for PoC 4; 0 selects a free port")
    parser.add_argument("--timeout", type=positive_timeout, default=15.0)
    parser.add_argument("--evidence-json", type=Path, help="save PoC 5's record outside its temporary store")
    args = parser.parse_args()
    if args.evidence_json and args.demo != "5":
        parser.error("--evidence-json requires selecting demo 5")
    selected = list(DEMOS) if args.demo == "all" else [args.demo]
    for number in selected:
        print(f"\nPoC {number}: {DEMOS[number]}", flush=True)
        with tempfile.TemporaryDirectory(prefix=f"mcp-poc{number}-") as directory, ExitStack() as stack:
            store = Path(directory) / "tasks.db"
            port = stack.enter_context(server_instance(store, args.port, weak=number == "2", timeout=args.timeout))
            peer = port
            if number == "4":
                peer = stack.enter_context(server_instance(store, args.peer_port, timeout=args.timeout))
            command = [
                sys.executable, str(ROOT / DEMOS[number]), "--port", str(port),
                "--peer-port", str(peer), "--store", str(store), "--timeout", str(args.timeout),
            ]
            if args.evidence_json:
                command += ["--evidence-json", str(args.evidence_json.resolve())]
            try:
                result = subprocess.run(
                    command, cwd=ROOT, env=dict(os.environ, PYTHONUNBUFFERED="1"),
                    timeout=args.timeout + 5,
                )
            except subprocess.TimeoutExpired as error:
                raise DemoError(f"PoC {number} exceeded its execution deadline") from error
            expect(result.returncode == 0, f"PoC {number} failed with exit status {result.returncode}")
        print(f"PASS PoC {number}", flush=True)
    print("\nAll selected demos produced their expected observations.")


if __name__ == "__main__":
    def terminate(signum, _frame):
        # Unwind the process/store contexts even when a supervisor sends SIGTERM.
        signal.signal(signum, signal.SIG_IGN)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    run_demo(main)
