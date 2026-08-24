---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-08-24T14:57:19.319Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 29.1 | deviation | experiments/_expectations.py | 23 | Twin of e1_refractive_comparison.py:213 corrected outside D-09's declared boundary (Rule 2 deviation); the shared-helper exclusion premise is falsified and a later stale-string pass must treat the helpers as candidates | open |  | 2026-08-24T14:57:19.319Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "29.1",
    "file": "experiments/_expectations.py",
    "line": 23,
    "description": "Twin of e1_refractive_comparison.py:213 corrected outside D-09's declared boundary (Rule 2 deviation); the shared-helper exclusion premise is falsified and a later stale-string pass must treat the helpers as candidates",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T14:57:19.319Z",
    "resolved_at": null
  }
]
````
