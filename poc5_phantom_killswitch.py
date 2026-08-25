#!/usr/bin/env python3
"""
PoC 5 - The Phantom Kill Switch   (headliner)

tasks/cancel is cooperative and ack-only. The client asks to cancel, gets an
acknowledgement, the UI flips to "cancelled" - and the work keeps running and
completes its side effect anyway. Compliance hears "stop = stopped." The spec
says "stop = please."

Setup:
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh
Run:
    python3 poc5_phantom_killswitch.py
"""
import time
from common import call, line, charges

PORT = 9001

print("Start a task that ends in a real side effect (a $500 charge).")
r = call(PORT, "tools/call", {"name": "place_order", "arguments": {"amount": 500, "note": "the thing we want to stop"}},
         token="tok-alice")
h = r["task"]["taskId"]
print(f"   handle: {h}")
line()

time.sleep(1)
print("Change of heart - hit the kill switch:")
ack = call(PORT, "tasks/cancel", {"taskId": h})
print(f"   tasks/cancel -> {ack}")
st = call(PORT, "tasks/get", {"taskId": h})
print(f"   UI now shows status = {st['task']['status']}   ('cancelled' - phew, right?)")
line()

print("Wait for the work that 'stopped' to finish...")
time.sleep(4)
final = call(PORT, "tasks/get", {"taskId": h})
ch = [c for c in charges() if c["task_id"] == h]
print(f"   task status: {final['task']['status']}")
print(f"   charges recorded for this task: {ch}")
line()
if ch:
    print(f"The badge says 'cancelled' and the ${ch[0]['amount']:.0f} charge went through anyway.")
print("A kill switch that only ack's is not a kill switch.")
print("\nFIX: make cancel authorized, honored by the worker, and transactional")
print("     with side effects - and make 'stopped' auditable, not aspirational.")
