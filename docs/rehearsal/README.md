# Captured candidate rehearsal

This is a real run of source commit
[`bbe33a59e443fd966acc058f4d215e0634f3232f`](https://github.com/infamousjoeg/mcp-stateless-threats/commit/bbe33a59e443fd966acc058f4d215e0634f3232f),
captured October 3, 2026, in a fresh local clone with a clean working tree.
Environment: macOS 26.6.2 arm64, Python 3.14.6. It identifies a tested candidate;
it is not a final release tag.

- [Complete transcript](transcript.txt): all 16 regression tests passed; all
  five demos passed twice; the standalone PoCs 1 and 5 also passed.
- [PoC 5 application record](poc5-evidence.json): the same-task simulated $500
  charge was recorded about 4.06 seconds after acknowledgement receipt, while
  the server continued to report `cancelled`.
- [Provenance manifest](manifest.json): source commit/file hashes, interpreter,
  commands, exit statuses, timings, and evidence-file hash.

The temporary runtime root was empty after every command, and the clone
remained clean. Runtime output is retained verbatim; only the published export
destination in command lines is normalized to `poc5-evidence.json`.

The all-demo transcript includes Bob/globex authenticating with the synthetic
Bob token on the second instance and reading Alice/acme's task. PoC 1 uses one
instance and an assumed handle leak. PoC 3 remains a deterministic simulation.

The charge record establishes this local side effect, not whole-task
completion or independent payment-provider verification. Use the actual
record/task ID when showing captured evidence. See the
[evidence interpretation](../cancellation-evidence.md).

The [CI workflow](../../.github/workflows/ci.yml) exercises Ubuntu/macOS with
Python 3.11 and 3.14. Consult the
[actual workflow runs](https://github.com/infamousjoeg/mcp-stateless-threats/actions/workflows/ci.yml)
for the result on the commit being considered for release. This local
transcript does not establish the other platforms' results.
