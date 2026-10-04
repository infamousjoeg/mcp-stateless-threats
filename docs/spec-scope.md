# Specification scope

This lab is a deliberately vulnerable wire simulation for Job 3 of
*Stateless MCP, Stateful Trust*. Its custom client and server agree with each
other; that does not establish MCP conformance or SDK interoperability.

The comparison target is **MCP 2026-07-28**:

- [Core protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic) and [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).
- [Official stable Tasks specification](https://github.com/modelcontextprotocol/ext-tasks/blob/5246bc3d0253c1c4b09e682f690b7e8b97362500/specification/2026-07-28/tasks.md) and [schema](https://github.com/modelcontextprotocol/ext-tasks/blob/5246bc3d0253c1c4b09e682f690b7e8b97362500/schema/2026-07-28/schema.json), pinned to commit `5246bc3d0253c1c4b09e682f690b7e8b97362500`. Use these released shapes rather than treating the original SEP-2663 proposal as the wire contract.

## Security lesson

The Tasks security section permits task IDs to be used as bearer tokens, but
also requires sufficient entropy and authentication/authorization checks on
every task-related request. Stateless transport does not prevent applications
from binding tasks to authenticated principals and tenants.

Here, the server deliberately treats handle possession as sufficient access,
accepts self-reported client metadata as an identity fallback, offers predictable
handles in weak mode, and misreports cancellation while its worker continues.
The five PoCs illustrate failures in those implementation choices. Random
handles alone do not repair missing object-level authorization.

Task creation uses `tools/call`; there is no `tasks/create` method in this
extension. A cancellation acknowledgement confirms the request, not a stopped
worker. The lab's premature terminal `cancelled` status is an additional
implementation flaw; see [cancellation evidence](cancellation-evidence.md).

## Known wire differences

| Area | This simulator | Pinned specification |
| --- | --- | --- |
| Request metadata | Omits protocol version and client capability declarations | Requires per-request version and capability metadata |
| HTTP headers | Uses `Content-Type` and optional `Authorization` | Defines protocol version/method headers and name headers where required |
| Discovery | `protocolVersions`; extension names in an array | `supportedVersions`; extensions keyed in an object |
| Task creation | `{resultType: "task", task: {...}}` | Task fields directly in the result |
| Task metadata | Omits required lifecycle fields | Includes `createdAt`, `lastUpdatedAt`, and `ttlMs` |
| Task polling | Nested task with `resultType: "task"` | Task fields directly in a `resultType: "complete"` result |
| Cancel/update | Custom cancel acknowledgement; update acts like get | `resultType: "complete"` acknowledgements; update handles input responses |
| RPC errors | Error object nested inside a successful `result` | JSON-RPC error envelope |

The server binds to loopback and stores tasks in SQLite. Fixed `tok-alice`
and `tok-bob` tokens are synthetic identity selectors, not production token
validation. PoC 3 uses a regex and a direct RPC call, not a real model or MCP
host. Charges are local rows, not external payments. Daemon worker threads are
not durable jobs across server restarts.

## Adapting the lesson to production

- Derive principal and tenant from validated authentication. Self-reported
  `clientInfo` is descriptive data, not an authority source. Check the actor,
  tenant, operation, and task on every request, consistently across instances.
- Use opaque, high-entropy handles and keep them out of ordinary logs/errors.
  Correlate events using non-secret identifiers; a trace ID does not prove
  identity, authorization, or completion.
- Treat document content and tool arguments as untrusted. Ownership checks
  stop the cross-user action shown here, but not every unwanted action that an
  otherwise authorized agent could perform.
- Have workers honor cancellation and report actual execution state. For a
  local SQLite effect, coordinate the cancellation check and insertion in one
  transaction. External payments cannot generally join that transaction:
  they require suitable idempotency, execution coordination, and reconciliation.
  A check immediately before a remote call does not eliminate races.
- Persist durable execution and outcome evidence. A read-only query of this
  local mutable ledger is neither external verification nor tamper-proof proof.

The [secure comparison (#8)](https://github.com/infamousjoeg/mcp-stateless-threats/issues/8)
and [conformance work (#9)](https://github.com/infamousjoeg/mcp-stateless-threats/issues/9)
are follow-ups, not implemented guarantees of this intentionally vulnerable lab.
