# Audience release checklist

Tracks [release preparation (#7)](https://github.com/infamousjoeg/mcp-stateless-threats/issues/7)
for Joe Garcia's Job 3 lab, *Stateless MCP, Stateful Trust*, MCP Dev Summit,
Toronto, October 6, 2026. The [candidate rehearsal](rehearsal/README.md)
records the local checks. The final tag, release assets, and publication
status are recorded in [issue #7](https://github.com/infamousjoeg/mcp-stateless-threats/issues/7)
and [GitHub Releases](https://github.com/infamousjoeg/mcp-stateless-threats/releases).

## Validate the integrated revision

Python 3.11+ is the runtime target; the CI target matrix is **Ubuntu and macOS,
each on Python 3.11 and 3.14**. Record exact versions and results after execution.
Syntax parsing alone is not a runtime compatibility test.

- [x] Implement and independently review the scoped issues: [docs #1](https://github.com/infamousjoeg/mcp-stateless-threats/issues/1), [runner #2](https://github.com/infamousjoeg/mcp-stateless-threats/issues/2), [evidence #3](https://github.com/infamousjoeg/mcp-stateless-threats/issues/3), [scenarios #4](https://github.com/infamousjoeg/mcp-stateless-threats/issues/4), [tests #5](https://github.com/infamousjoeg/mcp-stateless-threats/issues/5), and [MIT license #6](https://github.com/infamousjoeg/mcp-stateless-threats/issues/6). Integration remains a separate step below.
- [x] Compare README commands and evidence-field descriptions with the final CLI and emitted JSON. All five intentional vulnerabilities remain.
- [x] Run the tests and all demos on the recorded source commit:

  ```bash
  # Terminal A, in the candidate checkout
  python3 --version
  python3 -m unittest discover -s tests -v
  python3 demo.py all
  python3 demo.py 1
  python3 demo.py 5 --evidence-json evidence.json
  ```

- [x] Check repeated managed runs, custom manual ports/store, PoC 2's wrong-mode error, occupied-port startup, same-task evidence correlation and timeout, and cleanup of owned processes/stores, including SIGINT and SIGTERM. See the regression results and rehearsal transcript.
- [x] Confirm `--fresh` refuses an existing store even through another port. Match all ten evidence keys to the captured JSON; reject export destinations that overwrite existing files or the ledger.
- [x] Confirm each CI matrix result on source commit `01366c6124af4c6798d4475d64e7b59c06dbf71c`: 17 tests passed with exit status 0 in all four jobs, running `python -m unittest discover -s tests -v`.

| Validation evidence | Status |
| --- | --- |
| Ubuntu 24.04.5 / Python 3.11.16 | [17 tests passed](https://github.com/infamousjoeg/mcp-stateless-threats/actions/runs/37207737358/job/111452361571) |
| Ubuntu 24.04.5 / Python 3.14.7 | [17 tests passed](https://github.com/infamousjoeg/mcp-stateless-threats/actions/runs/37207737358/job/111452361511) |
| macOS 26.6.2 / Python 3.11.9 | [17 tests passed](https://github.com/infamousjoeg/mcp-stateless-threats/actions/runs/37207737358/job/111452361415) |
| macOS 26.6.2 / Python 3.14.7 | [17 tests passed](https://github.com/infamousjoeg/mcp-stateless-threats/actions/runs/37207737358/job/111452361473) |
| Rehearsal machine / exact Python version | macOS 26.6.2 arm64 / Python 3.14.6: 16 tests pass; all five demos pass twice |
| Candidate commit SHA and retained transcript | `bbe33a59e443fd966acc058f4d215e0634f3232f`; [transcript and manifest](rehearsal/README.md) |

The CI source revision adds a regression and removes reverse DNS from
loopback startup, which resolved the initial macOS runner stall. The original
local rehearsal remains valid evidence for its recorded revision. Recheck CI
on the final merge and rehearse the public checkout before publication.

## Presenter handoff

The deck is maintained separately. These presentation tasks do not prevent
publishing the verified repository:

- [x] Capture a verified transcript of PoCs 1 and 5, plus the full emitted PoC 5 JSON. The [rehearsal](rehearsal/README.md) identifies the tested source commit and environment.
- [ ] Align the deck's claims with the run: `tools/call`, cancellation acknowledgement versus reported status versus observed outcome, local simulated payments, and deterministic injection simulation.
- [ ] Label a two-instance diagram as PoC 4 or a composite; PoC 1 uses one instance. Reconcile depicted amounts with the actual examples.
- [ ] Label slide evidence illustrative until it matches captured output. Do not describe the local ledger check as a payment-provider reconciliation job.
- [x] Verify repository title, speaker, event/date, and MIT copyright (`2026 Joe Garcia`). Session/slides links remain omitted until real URLs are available.
- [x] Keep the simulator scope and pinned official specification links prominent. Keep [secure comparison #8](https://github.com/infamousjoeg/mcp-stateless-threats/issues/8) and [conformance #9](https://github.com/infamousjoeg/mcp-stateless-threats/issues/9) as explicit follow-ups.

## Publication procedure

1. Integrate the reviewed candidate, confirm final CI, and rehearse the public checkout.
2. Tag that verified commit and publish the transcript, evidence, and provenance.
3. Verify the actual release URL and its QR code.
4. Set the repository homepage to the release; verify the public README and MIT license.
5. Record the final commit, tag, CI run, and release URL in issue #7.
