# Stateless MCP, Stateful Trust — threat lab

The Job 3 lab for Joe Garcia's section of *Stateless MCP, Stateful Trust*,
MCP Dev Summit, Toronto, October 6, 2026.

**Deliberately vulnerable, simplified MCP-shaped simulator.** The five scenarios
use synthetic Alice/acme and Bob/globex identities, fixed demo tokens, and local
SQLite charges. There is no payment provider or LLM integration. The server's
wire format is not a full MCP implementation; see [specification scope](docs/spec-scope.md).
Run locally on loopback with synthetic data only.

Stateless transport still needs persistent ownership, tenant policy, and
execution state. The [pinned stable Tasks specification](https://github.com/modelcontextprotocol/ext-tasks/blob/5246bc3d0253c1c4b09e682f690b7e8b97362500/specification/2026-07-28/tasks.md#L900)
requires authentication and authorization checks on **every task-related
request**, as well as sufficient task-ID entropy. This server deliberately
omits those access checks. Removing sessions did not remove that obligation.

## Run the lab

Python **3.11+**, standard library only; no dependencies to install. Commands
below use a macOS/Linux shell. Check the actual interpreter with `python3 --version`.

```bash
# Terminal A
git clone https://github.com/infamousjoeg/mcp-stateless-threats.git
cd mcp-stateless-threats
python3 demo.py
```

`python3 demo.py` and `python3 demo.py all` run all five scenarios.
`python3 demo.py N` selects any scenario from `1` through `5`.
Start with the two headline examples:

```bash
# Terminal A, in the checkout
python3 demo.py 1
python3 demo.py 5
```

The runner selects the correct server mode, checks readiness and outcomes, and
stops only its own subprocesses. **Each scenario always uses a fresh temporary
store**, removed after its servers stop. The runner does not accept `--store`
or reuse your manual database. Use it for repeat runs and fresh starts.

To keep PoC 5's application evidence:

```bash
# Terminal A, in the checkout
python3 demo.py 5 --evidence-json evidence.json
```

The runner accepts `--evidence-json PATH` **only with selector `5`**, not `all`
or another selector. The saved JSON remains after the temporary store is removed.
Choose an unused output filename for each saved run; existing files are preserved.

Ports default to `0` (the OS assigns available ports). Optional overrides:

```bash
# Terminal A, in the checkout
python3 demo.py 4 --port 9101 --peer-port 9102 --timeout 15
```

`--timeout` defaults to 15 seconds and bounds startup and evidence waits.
A setup error or missing expected outcome returns a nonzero exit status.
These are intentionally vulnerable scenarios: successfully reproducing a flaw
is the expected lab outcome.

## The five scenarios

| PoC | Manual server mode | Expected observation and boundary |
| --- | --- | --- |
| **1 — Handle Heist** | One server, normal handles | An anonymous caller reads Alice's task metadata and gets an unauthorized cancellation acknowledgement. The leaked handle is supplied directly; stopping the worker is not demonstrated. |
| **2 — Enumerable Handles** | One server, `--weak-handles` | A deterministic counter lets Bob's own handle seed enumeration. Alice's records are counted separately from Bob's. Entropy and authorization are separate requirements. |
| **3 — Confused Deputy** | One server, normal handles | A regex extracts a handle from a crafted document; a request using Bob's token changes Alice's reported status to `cancelled`. This simulates an already-influenced agent, not an LLM prompt-injection test or proof that work stopped. |
| **4 — Cross-Tenant Bleed** | Two servers, normal handles, shared store | Bob/globex uses Bob's token on instance B to read Alice/acme's task created on instance A. Both instances deliberately omit task ownership/tenant checks. |
| **5 — Phantom Kill Switch** | One server, normal handles | Cancellation is acknowledged and status reports `cancelled`, but a same-task $500 simulated charge is subsequently found in the local ledger. See [cancellation evidence](docs/cancellation-evidence.md). |

## Manual terminals

Use these commands to inspect the servers directly. Open each terminal in the
same checkout. Each scenario uses a new absolute store filename under
`/tmp/job3-audience-lab`. **All servers and the PoC within that scenario must
share the exact same absolute path**, including PoC 5's ledger reader.

Before **each** scenario, stop **all** servers from the previous scenario with
**Ctrl-C in their own terminals**, and wait for those commands to exit.
Then choose an unused store filename. The examples use `poc1-run1.db` through
`poc5-run1.db`; for a repeat, change `run1` to an unused name in **every**
participating command. `--fresh` atomically creates a new file and refuses an
existing store, even when starting on a different port. It never deletes data.
For PoC 4, only instance A gets `--fresh`; B opens A's existing shared store.
Wait for each server's startup message before starting its client.

```bash
# Terminal A, once before the first manual scenario
mkdir -p /tmp/job3-audience-lab
```

**PoC 1 — one server, normal handles**

```bash
# Terminal A: start server; leave running
python3 server.py --port 9001 --store /tmp/job3-audience-lab/poc1-run1.db --fresh
```

```bash
# Terminal B: run the client
python3 poc1_handle_heist.py --port 9001 --peer-port 9002 --store /tmp/job3-audience-lab/poc1-run1.db --timeout 15
```

**PoC 2 — one server, weak handles; stop all previous servers first**

```bash
# Terminal A: start server; leave running
python3 server.py --port 9001 --store /tmp/job3-audience-lab/poc2-run1.db --fresh --weak-handles
```

```bash
# Terminal B: run the client
python3 poc2_enumerable_handles.py --port 9001 --peer-port 9002 --store /tmp/job3-audience-lab/poc2-run1.db --timeout 15
```

**PoC 3 — one server, normal handles; stop all previous servers first**

```bash
# Terminal A: start server; leave running
python3 server.py --port 9001 --store /tmp/job3-audience-lab/poc3-run1.db --fresh
```

```bash
# Terminal B: run the client
python3 poc3_confused_deputy.py --port 9001 --peer-port 9002 --store /tmp/job3-audience-lab/poc3-run1.db --timeout 15
```

**PoC 4 — two servers, normal handles; stop all previous servers first**

```bash
# Terminal A: start instance A; leave running
python3 server.py --port 9001 --store /tmp/job3-audience-lab/poc4-run1.db --fresh
```

```bash
# Terminal B: after A is ready, start instance B; leave running
python3 server.py --port 9002 --store /tmp/job3-audience-lab/poc4-run1.db
```

```bash
# Terminal C: after both servers are ready, run the client
python3 poc4_cross_tenant.py --port 9001 --peer-port 9002 --store /tmp/job3-audience-lab/poc4-run1.db --timeout 15
```

**PoC 5 — one server, normal handles; stop both PoC 4 servers first**

```bash
# Terminal A: start server; leave running
python3 server.py --port 9001 --store /tmp/job3-audience-lab/poc5-run1.db --fresh
```

```bash
# Terminal B: run the client; saving the evidence file is optional
python3 poc5_phantom_killswitch.py --port 9001 --peer-port 9002 --store /tmp/job3-audience-lab/poc5-run1.db --timeout 15 --evidence-json /tmp/job3-audience-lab/cancellation-evidence.json
```

Afterward, stop all manual servers with Ctrl-C in their terminals. Manual
stores remain available for inspection. Prefer the runner for a fresh repeat.

Manual defaults are port `9001`, peer port `9002`, store `/tmp/mcp_tasks.db`,
and timeout `15` seconds. `--peer-port` is used by PoC 4; all PoCs accept it.
`MCP_DEMO_PORT`, `MCP_DEMO_PEER_PORT`, and `MCP_DEMO_STORE` provide shared
manual configuration; explicit CLI flags take precedence. Set environment
variables in **every** participating terminal. The examples use explicit flags
to make that agreement visible.

If a port is occupied, choose another and update the matching client flag
(and `--peer-port` for instance B). If `--fresh` finds an existing store, stop
all servers and choose a new filename across that scenario's commands.
If PoC 2 reports the wrong mode, stop all servers and restart its weak-mode
command with a new store filename. For PoC 5, check the shared absolute store
and timeout; absence of evidence does not establish a stopped task.

## Validation and follow-ups

Python 3.11+ is the runtime target. The [captured candidate rehearsal](docs/rehearsal/README.md)
records successful all-five runs and the headline examples on macOS 26.6.2 /
Python 3.14.6, including the full PoC 5 JSON. The expanded suite of 17 tests
passes on Ubuntu/macOS with Python 3.11 and 3.14; see the
[recorded matrix results](docs/release-checklist.md) and check the
[workflow results](https://github.com/infamousjoeg/mcp-stateless-threats/actions/workflows/ci.yml)
for the commit being released. The [release checklist](docs/release-checklist.md)
tracks final integration, deck alignment, and publication.

The five vulnerabilities are intentional. A secure comparison
([#8](https://github.com/infamousjoeg/mcp-stateless-threats/issues/8)) and full
protocol conformance ([#9](https://github.com/infamousjoeg/mcp-stateless-threats/issues/9))
remain follow-ups. [Scope and production adaptations](docs/spec-scope.md)
explain the controls beyond this lab.

Licensed under [MIT](LICENSE). Copyright 2026 Joe Garcia.
