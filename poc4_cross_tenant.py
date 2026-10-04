#!/usr/bin/env python3
"""PoC 4: authenticated Bob reads Alice's task through a second server instance.

Two loopback instances share one SQLite store. Requests go directly to each
port; this does not demonstrate a load balancer or durable worker failover.
Run automatically: python3 demo.py 4
"""
from common import check_server, client_for, demo_args, expect, line, run_demo, task_from


def main():
    args = demo_args(__doc__)
    expect(args.port != args.peer_port, "PoC 4 requires two distinct server ports")
    check_server(args)
    check_server(args, port=args.peer_port)
    alice = client_for(args)
    bob = client_for(args, args.peer_port)
    # Show both token-derived identities before attempting the boundary crossing.
    own = task_from(bob("tools/call", {
        "name": "make_invoice", "arguments": {"note": "Bob's own task"},
    }, token="tok-bob"))["taskId"]
    identity = task_from(bob("tasks/get", {"taskId": own}, token="tok-bob"))
    expect(identity.get("owner") == "bob" and identity.get("tenant") == "globex",
           "The second instance did not authenticate Bob/globex")
    handle = task_from(alice("tools/call", {
        "name": "run_billing", "arguments": {"amount": 9000, "note": "acme simulated billing"},
    }, token="tok-alice"))["taskId"]
    print(f"Alice/acme creates {handle} on port {args.port}.")
    print(f"Authenticated Bob/globex uses port {args.peer_port} and an assumed leaked handle.")
    peek = task_from(bob("tasks/get", {"taskId": handle}, token="tok-bob"))
    expect(peek.get("owner") == "alice" and peek.get("tenant") == "acme",
           "Bob did not read Alice's task across instances")
    print(f"  Bob's read: owner={peek['owner']} tenant={peek['tenant']} status={peek['status']}")
    line()
    print("Observed: authenticated access crossed the tenant boundary through the shared store.")
    print("FIX: scope authorization to trusted issuer, subject, tenant, object, and operation.")


if __name__ == "__main__":
    run_demo(main)
