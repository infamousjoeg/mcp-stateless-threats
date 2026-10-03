"""Helpers for the deliberately simplified local MCP threat lab."""
import argparse
from contextlib import closing
from functools import partial
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request


class DemoError(RuntimeError):
    """A setup or observed-outcome failure that an attendee can act on."""


def positive_timeout(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and greater than zero")
    return value


def port_number(value):
    value = int(value)
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return value


def demo_args(description, evidence=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--port", type=port_number, default=os.getenv("MCP_DEMO_PORT", "9001"))
    parser.add_argument("--peer-port", type=port_number, default=os.getenv("MCP_DEMO_PEER_PORT", "9002"))
    parser.add_argument("--store", default=os.getenv("MCP_DEMO_STORE", "/tmp/mcp_tasks.db"))
    parser.add_argument("--timeout", type=positive_timeout, default=15.0)
    if evidence:
        parser.add_argument("--evidence-json", type=Path, help="also save the application evidence record")
    return parser.parse_args()


def expect(condition, message):
    if not condition:
        raise DemoError(message)


def call(port, method, params=None, token=None, client=None, timeout=15):
    """One request in this lab's simplified wire format; see docs/spec-scope.md."""
    params = dict(params or {})
    if client:
        params["_meta"] = {"io.modelcontextprotocol/clientInfo": client}
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp", data=body, headers={"Content-Type": "application/json"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (OSError, ValueError) as error:
        raise DemoError(f"Request to port {port} failed: {error}. Check the server and --port.") from error
    expect(isinstance(payload, dict) and isinstance(payload.get("result"), dict),
           f"Port {port} did not return a lab RPC result")
    return payload["result"]


def client_for(args, port=None):
    return partial(call, args.port if port is None else port, timeout=args.timeout)


def check_server(args, port=None, weak=None):
    actual_port = args.port if port is None else port
    info = client_for(args, actual_port)("server/discover")
    demo = info.get("demo", {})
    expect(demo.get("store") == str(Path(args.store).resolve()),
           f"Port {actual_port} uses a different store. Pass the same --store to server and PoC.")
    if weak is not None:
        expect(demo.get("weak_handles") is weak,
               "This demo needs --weak-handles. Stop the old server and restart in the correct mode.")
    return info


def task_from(result):
    task = result.get("task")
    expect(isinstance(task, dict) and task.get("taskId"), f"Expected a task, received {result!r}")
    return task


def charges(store="/tmp/mcp_tasks.db", task_id=None):
    """Read evidence without creating or modifying a missing/mistyped database."""
    uri = Path(store).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=1)) as connection:
        connection.row_factory = sqlite3.Row
        if task_id is None:
            rows = connection.execute("SELECT * FROM charges ORDER BY id")
        else:
            rows = connection.execute("SELECT * FROM charges WHERE task_id=? ORDER BY id", (task_id,))
        return [dict(row) for row in rows]


def wait_for_charge(store, task_id, timeout, not_before):
    deadline = time.monotonic() + timeout
    while True:
        observed = [row for row in charges(store, task_id) if row["ts"] >= not_before]
        if observed:
            return observed[0]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DemoError(f"No post-ack charge observed for this task within {timeout:g}s; outcome unproven.")
        time.sleep(min(0.05, remaining))


def run_demo(main):
    try:
        main()
    except (DemoError, OSError, sqlite3.Error) as error:
        print(f"Demo failed: {error}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("Demo interrupted.", file=sys.stderr)
        raise SystemExit(130)


def line():
    print("-" * 64)
