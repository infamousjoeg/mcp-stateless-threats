# Draft audience release checklist

Tracks [release preparation (#7)](https://github.com/infamousjoeg/mcp-stateless-threats/issues/7)
for Joe Garcia's Job 3 lab, *Stateless MCP, Stateful Trust*, MCP Dev Summit,
Toronto, October 6, 2026. This is a preparation checklist, not a published
release announcement. No release tag is designated. The
[candidate rehearsal](rehearsal/README.md) records the completed local checks;
final integration and publication remain below.

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
- [ ] Confirm each CI matrix result on that commit. Record the OS, exact Python version, command, exit status, commit SHA, and real CI run URL or local transcript. Keep absent results explicitly pending.

| Validation evidence | Status |
| --- | --- |
| Ubuntu / Python 3.11 | Pending |
| Ubuntu / Python 3.14 | Pending |
| macOS / Python 3.11 | Pending |
| macOS / Python 3.14 | Pending |
| Rehearsal machine / exact Python version | macOS 26.6.2 arm64 / Python 3.14.6: 16 tests pass; all five demos pass twice |
| Candidate commit SHA and retained transcript | `bbe33a59e443fd966acc058f4d215e0634f3232f`; [transcript and manifest](rehearsal/README.md) |

The four matrix rows refer to remote CI and must be checked for the final
candidate. They are separate from the local macOS result above.

## Align the audience material

- [x] Capture a verified transcript of PoCs 1 and 5, plus the full emitted PoC 5 JSON. The [rehearsal](rehearsal/README.md) identifies the tested source commit and environment.
- [ ] Align the deck's claims with the run: `tools/call`, cancellation acknowledgement versus reported status versus observed outcome, local simulated payments, and deterministic injection simulation.
- [ ] Label a two-instance diagram as PoC 4 or a composite; PoC 1 uses one instance. Reconcile depicted amounts with the actual examples.
- [ ] Label slide evidence illustrative until it matches captured output. Do not describe the local ledger check as a payment-provider reconciliation job.
- [x] Verify repository title, speaker, event/date, and MIT copyright (`2026 Joe Garcia`). Session/slides links remain omitted until real URLs are available.
- [x] Keep the simulator scope and pinned official specification links prominent. Keep [secure comparison #8](https://github.com/infamousjoeg/mcp-stateless-threats/issues/8) and [conformance #9](https://github.com/infamousjoeg/mcp-stateless-threats/issues/9) as explicit follow-ups.

## Publish after review

- [ ] Review and integrate the candidate branch; update issue #7 with remaining release work.
- [ ] Choose a release tag for the rehearsed, verified commit. Record the actual tag and commit only once created; no tag is designated by this draft.
- [ ] Publish the verified transcript/evidence with the release. Confirm README commands work from that tagged checkout.
- [ ] Point the audience URL/QR code to the actual stable release and verify it from a clean browser.
- [ ] Set appropriate repository topics and a homepage only if a real destination is available; verify public README, license, and release links.
