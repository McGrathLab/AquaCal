---
schema_version: 1
open_count: 4
waived_count: 0
fixed_count: 0
total_count: 4
last_updated: 2026-08-24T18:49:04.593Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 29.1 | deviation | experiments/_expectations.py | 23 | Twin of e1_refractive_comparison.py:213 corrected outside D-09's declared boundary (Rule 2 deviation); the shared-helper exclusion premise is falsified and a later stale-string pass must treat the helpers as candidates | open |  | 2026-08-24T14:57:19.319Z |  |
| 2 | 29.1 | unmet-truth | tests/unit/test_discard_accounting.py |  | D4: three exact-equality anchor tests fail on Linux (1 ULP to rel 1.4e-9); rerun-freeze-02 cut with a recorded ruling, not a fix -- see 29.1-PREPUSH-AUDIT.md section 1 | open |  | 2026-08-24T18:49:04.473Z |  |
| 3 | 29.1 | unmet-truth | tests/unit/test_optim_common.py |  | D4: TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector fails by 1 ULP on Linux; ruled on, not fixed | open |  | 2026-08-24T18:49:04.530Z |  |
| 4 | 29.1 | unmet-truth | tests/unit/test_pipeline.py |  | D4: TestSolverConfigSeedIsInert::test_matches_pre_change_anchor fails by 2.4e-16 on Linux; ruled on, not fixed | open |  | 2026-08-24T18:49:04.593Z |  |

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
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "29.1",
    "file": "tests/unit/test_discard_accounting.py",
    "line": null,
    "description": "D4: three exact-equality anchor tests fail on Linux (1 ULP to rel 1.4e-9); rerun-freeze-02 cut with a recorded ruling, not a fix -- see 29.1-PREPUSH-AUDIT.md section 1",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T18:49:04.473Z",
    "resolved_at": null
  },
  {
    "id": 3,
    "kind": "unmet-truth",
    "phase": "29.1",
    "file": "tests/unit/test_optim_common.py",
    "line": null,
    "description": "D4: TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector fails by 1 ULP on Linux; ruled on, not fixed",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T18:49:04.530Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "unmet-truth",
    "phase": "29.1",
    "file": "tests/unit/test_pipeline.py",
    "line": null,
    "description": "D4: TestSolverConfigSeedIsInert::test_matches_pre_change_anchor fails by 2.4e-16 on Linux; ruled on, not fixed",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T18:49:04.593Z",
    "resolved_at": null
  }
]
````
