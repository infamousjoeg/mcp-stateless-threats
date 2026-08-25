#!/usr/bin/env python3
"""
PoC 4 - Cross-Tenant Bleed on the Round-Robin

"Any server instance can handle any request." Great for scaling - and it
removed the implicit isolation a lot of deployments leaned on. The spec even
deleted tasks/list because task->caller binding "cannot be defined" in this
model, punting multi-tenant isolation entirely to you. If your task store is
keyed only by handle, a tenant that lands on a *different* instance drives
another tenant's task by handle alone.

Setup - TWO instances, ONE shared store (that's the whole point):
    python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh
    python3 server.py --port 9002 --store /tmp/mcp_tasks.db
Run:
    python3 poc4_cross_tenant.py
"""
from common import call, line

ACME = 9001     # tenant 'acme' talks to instance A
GLOBEX = 9002   # tenant 'globex' talks to instance B - different box, same store

print("acme (on srv:9001) starts a task:")
r = call(ACME, "tools/call", {"name": "run_billing", "arguments": {"amount": 9000, "note": "acme confidential"}},
         token="tok-alice")
h = r["task"]["taskId"]
print(f"   handle {h} lives in the shared store")
line()

print("globex (on srv:9002 - a DIFFERENT instance) was handed/guessed that handle.")
peek = call(GLOBEX, "tasks/get", {"taskId": h})
print(f"   globex reads it off srv:9002 -> owner={peek['task']['owner']} tenant={peek['task']['tenant']} status={peek['task']['status']}")
line()
print("Two companies, two instances, zero session affinity - and one tenant read")
print("the other's task just by hitting a different node with the handle.")
print("\nFIX: namespace state by (issuer, subject, tenant); the protocol won't")
print("     keep tenants apart for you now that any instance serves any request.")
