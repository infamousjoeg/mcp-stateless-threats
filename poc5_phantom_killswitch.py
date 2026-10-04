#!/usr/bin/env python3
"""PoC 5: cancellation acknowledgement, reported status, and observed effect differ.

The protocol permits cooperative cancellation. This simulator additionally
misreports cancellation while its worker ignores it. The payment is a local
SQLite record, not a real charge or external reconciliation service.
Run automatically: python3 demo.py 5
"""
import json
from pathlib import Path
import time
from common import (check_server, client_for, demo_args, expect, line, run_demo,
                    task_from, wait_for_charge)


def main():
    args = demo_args(__doc__, evidence=True)
    if args.evidence_json:
        expect(not args.evidence_json.exists() and not args.evidence_json.is_symlink(),
               "Refusing to overwrite an existing evidence destination. Choose a new --evidence-json path.")
        protected = {Path(str(Path(args.store).resolve()) + suffix)
                     for suffix in ("", "-wal", "-shm", "-journal")}
        expect(args.evidence_json.resolve() not in protected,
               "The evidence destination cannot be the database or a SQLite companion file.")
    check_server(args)
    call = client_for(args)
    print("Alice starts a task that records a simulated $500 charge in SQLite.")
    handle = task_from(call("tools/call", {
        "name": "place_order", "arguments": {"amount": 500, "note": "simulated order to stop"},
    }, token="tok-alice"))["taskId"]
    ack = call("tasks/cancel", {"taskId": handle}, token="tok-alice")
    acknowledged_at = time.time()
    expect(ack.get("ack") is True, "Cancellation was not acknowledged")
    reported = task_from(call("tasks/get", {"taskId": handle}, token="tok-alice"))
    expect(reported.get("status") == "cancelled", "Expected the simulator's false cancelled status")
    print("  cancellation request acknowledged; server reports task status: cancelled")
    print("Polling the local ledger for this task's post-ack side effect...")
    charge = wait_for_charge(args.store, handle, args.timeout, acknowledged_at)
    expect(charge["tenant"] == "acme" and charge["amount"] == 500,
           "The observed charge does not match Alice's simulated order")
    final = task_from(call("tasks/get", {"taskId": handle}, token="tok-alice"))
    expect(final.get("status") == "cancelled", "The final reported status changed unexpectedly")
    evidence = {
        "cancel_ack": "received",
        "reported_task_status": final["status"],
        "side_effect": "charge_posted",
        "outcome": "not_stopped",
        "outcome_verified_by": "demo_local_ledger_check",
        "task_id": handle,
        "amount": charge["amount"],
        "cancel_ack_at": acknowledged_at,
        "charge_row_id": charge["id"],
        "charge_posted_at": charge["ts"],
    }
    if args.evidence_json:
        # Exclusive creation also refuses a file or alias created since preflight.
        with args.evidence_json.open("x") as output:
            output.write(json.dumps(evidence, indent=2) + "\n")
    line()
    print("Observed: acknowledgement received, cancelled status reported, charge still recorded.")
    print("Application evidence record (synthetic local data, not an MCP response):")
    print(json.dumps(evidence, indent=2))
    print("FIX: authorize cancellation, enforce it in the worker, and verify the consequence.")


if __name__ == "__main__":
    run_demo(main)
