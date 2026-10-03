# Cancellation: acknowledgement, status, outcome

PoC 5 compares three different observations: the server acknowledges a
cancellation request, it reports `cancelled`, and a same-task simulated $500
charge appears afterward in SQLite. The worker intentionally ignores the
cancellation request.

The [pinned stable Tasks cancellation contract](https://github.com/modelcontextprotocol/ext-tasks/blob/5246bc3d0253c1c4b09e682f690b7e8b97362500/specification/2026-07-28/tasks.md#L383)
is cooperative: acknowledgement does not guarantee work will stop or that the
task will transition to `cancelled`. Its `resultType: "complete"` acknowledges
the cancellation RPC, not completion of the underlying task. This simulator
uses a custom acknowledgement and additionally writes a misleading terminal
status; that status is a deliberate implementation defect.

## Reproduce it

```bash
# Terminal A, in the checkout: managed run with an isolated temporary store
python3 demo.py 5 --evidence-json evidence.json
```

The JSON file is retained after the runner removes its temporary store.
`--evidence-json PATH` is optional and accepted by the runner **only with
selector `5`**. Omit it to run without saving a file.

Choose an unused output filename each time. The client refuses existing files,
aliases to the database, and SQLite companion-file paths before starting work,
and exclusively creates the JSON file so a concurrent file is not overwritten.

It is also available on `poc5_phantom_killswitch.py` in the
[manual PoC 5 terminals](../README.md#manual-terminals). The manual PoC's
`--store` must be the same absolute path as the server's.

## Read the record

The following is an **illustrative application record**, not a captured run or
an MCP wire response. It uses the implemented field names with example values;
the task ID, row ID, and timestamps come from each execution.

```json
{
  "cancel_ack": "received",
  "reported_task_status": "cancelled",
  "side_effect": "charge_posted",
  "outcome": "not_stopped",
  "outcome_verified_by": "demo_local_ledger_check",
  "task_id": "<this run's task ID>",
  "amount": 500,
  "cancel_ack_at": 1791028800.0,
  "charge_row_id": 1,
  "charge_posted_at": 1791028804.0
}
```

| Field | Meaning |
| --- | --- |
| `cancel_ack` | A cancellation acknowledgement was received; no stop guarantee |
| `reported_task_status` | What the server says about the task, not independent execution evidence |
| `side_effect` | The local charge table contains a matching simulated charge |
| `outcome` | This task's side effect happened despite the cancellation request |
| `outcome_verified_by` | Names the local demo ledger check; it is not a payment reconciliation service |
| `task_id`, `amount` | Correlate the requested task and the expected $500 charge |
| `cancel_ack_at` | Local Unix timestamp in seconds when the client received the acknowledgement |
| `charge_row_id` | ID of the matching row in this store's `charges` table |
| `charge_posted_at` | Local Unix timestamp in seconds recorded for that charge |

The verifier reads SQLite with a **read-only URI**, filters for this task, and
requires `charge_posted_at >= cancel_ack_at`. A bounded
`--timeout` limits polling. Unrelated or older charges and empty evidence do
not establish this outcome; missing evidence is a failed demonstration, not
proof of a successful stop.

## What the evidence can establish

This is a separate observation path from the task-status RPC, but the database
and clock are local and mutable. Read-only access prevents this reader from
creating or changing the ledger; it does **not** make that ledger external,
independent, or tamper-proof. No real payment was made.

A production stop guarantee needs authorized cancellation, coordinated worker
execution, and evidence of the actual outcome. Local cancellation checks and
SQLite inserts can share a transaction. External payments need idempotency,
execution coordination, and reconciliation with the provider; a local status
update or a single pre-call check is insufficient.
