# stateless MCP, stateful trust — threat PoCs

Little demos I built for my MCP Dev Summit panel (Toronto) on what the
2026-07-28 spec quietly did to identity, audit, and kill switches.

The July revision made the transport stateless: the `initialize` handshake and
the `Mcp-Session-Id` header are gone, any instance can serve any request, and
cross-call state now lives in server-minted **handles** you pass back as tool
arguments (plus the Tasks extension, SEP-2663). Good for scaling. It also
removed the crutch a bunch of trust/audit assumptions were leaning on.

Each script is a self-contained PoC against one deliberately-vulnerable server.
The server (`server.py`) is insecure on purpose — every weakness has a
`# VULN:` comment with the fix. Nothing here is a zero-day; it's the plumbing
biting when you build the "obvious" way.

## the five

1. **`poc1_handle_heist.py`** — task IDs are bearer tokens. A leaked handle lets an unauthenticated attacker read a victim's task and hit cancel. No session to stop them.
2. **`poc2_enumerable_handles.py`** — "sufficient entropy" is left to you. Guessable handles (a counter, a timestamp) = walk the range, harvest everyone's tasks.
3. **`poc3_confused_deputy.py`** — handles ride as tool arguments, and arguments are what prompt injection controls. Poisoned doc smuggles the victim's handle into a privileged call.
4. **`poc4_cross_tenant.py`** — "any instance serves any request." Two instances, one store, no tenant scoping → one tenant drives another's task by handle alone.
5. **`poc5_phantom_killswitch.py`** — `tasks/cancel` is cooperative + ack-only. Badge says "cancelled," the charge goes through anyway.

## run it

Python 3.11+, stdlib only, no install.

```bash
# most PoCs: one server
python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh
python3 poc1_handle_heist.py

# poc2 wants guessable handles
python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh --weak-handles
python3 poc2_enumerable_handles.py

# poc4 wants two instances sharing one store
python3 server.py --port 9001 --store /tmp/mcp_tasks.db --fresh
python3 server.py --port 9002 --store /tmp/mcp_tasks.db
python3 poc4_cross_tenant.py
```

## the point

Authority didn't disappear in July — it moved into the payload, one request at
a time. If you don't authorize every request as if it showed up cold, you've
built stateless transport on a stateful trust assumption.

spec: https://modelcontextprotocol.io/specification/2026-07-28/changelog
