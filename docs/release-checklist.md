# Draft audience release checklist

Tracks [release preparation (#7)](https://github.com/infamousjoeg/mcp-stateless-threats/issues/7)
for Joe Garcia's Job 3 lab, *Stateless MCP, Stateful Trust*, MCP Dev Summit,
Toronto, October 6, 2026. This is a preparation checklist, not a published
release announcement. No release tag or successful validation run is asserted.

## Validate the integrated revision

Python 3.11+ is the runtime target; the CI target matrix is **Ubuntu and macOS,
each on Python 3.11 and 3.14**. Record exact versions and results after execution.
Syntax parsing alone is not a runtime compatibility test.

- [ ] Finish and review the scoped issues: [docs #1](https://github.com/infamousjoeg/mcp-stateless-threats/issues/1), [runner #2](https://github.com/infamousjoeg/mcp-stateless-threats/issues/2), [evidence #3](https://github.com/infamousjoeg/mcp-stateless-threats/issues/3), [scenarios #4](https://github.com/infamousjoeg/mcp-stateless-threats/issues/4), [tests #5](https://github.com/infamousjoeg/mcp-stateless-threats/issues/5), and [MIT license #6](https://github.com/infamousjoeg/mcp-stateless-threats/issues/6).
- [ ] Compare every README command and evidence-field description with the final CLI and emitted JSON. Preserve all five intentional vulnerabilities.
- [ ] Run the tests and all demos on the exact candidate commit:

  ```bash
  # Terminal A, in the candidate checkout
  python3 --version
  python3 -m unittest discover -s tests -v
  python3 demo.py all
  python3 demo.py 1
  python3 demo.py 5 --evidence-json evidence.json
  ```

- [ ] Check repeated managed runs, custom manual ports/store, PoC 2's wrong-mode error, occupied-port startup, same-task evidence correlation and timeout, and cleanup of owned processes/stores. Follow the README's terminal instructions and choose a new store filename for each fresh manual run.
- [ ] Confirm `--fresh` refuses an existing store even through another port, and that runner `--evidence-json` works only with selector `5`. Match all ten evidence keys to the captured JSON.
- [ ] Confirm each CI matrix result on that commit. Record the OS, exact Python version, command, exit status, commit SHA, and real CI run URL or local transcript. Keep absent results explicitly pending.

| Validation evidence | Status |
| --- | --- |
| Ubuntu / Python 3.11 | Pending |
| Ubuntu / Python 3.14 | Pending |
| macOS / Python 3.11 | Pending |
| macOS / Python 3.14 | Pending |
| Rehearsal machine / exact Python version | Pending |
| Candidate commit SHA and retained transcript | Pending |

## Align the audience material

- [ ] Capture a verified transcript or short recording of PoCs 1 and 5, plus the full emitted PoC 5 JSON. Label it with the tested commit and environment.
- [ ] Align the deck's claims with the run: `tools/call`, cancellation acknowledgement versus reported status versus observed outcome, local simulated payments, and deterministic injection simulation.
- [ ] Label a two-instance diagram as PoC 4 or a composite; PoC 1 uses one instance. Reconcile depicted amounts with the actual examples.
- [ ] Label slide evidence illustrative until it matches captured output. Do not describe the local ledger check as a payment-provider reconciliation job.
- [ ] Verify title, speaker, event/date, and MIT copyright (`2026 Joe Garcia`). Add session/slides links only when their real URLs are available.
- [ ] Keep the simulator scope and pinned official specification links prominent. Keep [secure comparison #8](https://github.com/infamousjoeg/mcp-stateless-threats/issues/8) and [conformance #9](https://github.com/infamousjoeg/mcp-stateless-threats/issues/9) as explicit follow-ups.

## Publish after review

- [ ] Review and integrate the candidate branch; update issue #7 with remaining release work.
- [ ] Choose a release tag for the rehearsed, verified commit. Record the actual tag and commit only once created; no tag is designated by this draft.
- [ ] Publish the verified transcript/evidence with the release. Confirm README commands work from that tagged checkout.
- [ ] Point the audience URL/QR code to the actual stable release and verify it from a clean browser.
- [ ] Set appropriate repository topics and a homepage only if a real destination is available; verify public README, license, and release links.
