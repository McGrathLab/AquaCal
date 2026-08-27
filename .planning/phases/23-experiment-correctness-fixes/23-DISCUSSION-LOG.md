# Phase 23: Experiment Correctness Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 23-Experiment Correctness Fixes
**Areas discussed:** Pin mechanics + the unmeasured combo, `--check` verification contract,
In-phase verification budget, Plan decomposition + commit granularity

---

## Pin mechanics + the unmeasured combo

### How should `water_z` be held in E1's non-refractive arm?

| Option | Description | Selected |
|--------|-------------|----------|
| Bounds freeze in the experiment | Tight bound (lb = ub ± 1e-12) on the `water_z` slot, passed from `e1_refractive_comparison.py`. Zero library change, arm-local, constrains the solve rather than the report. | ✓ |
| Library flag mirroring `normal_fixed` | `water_z_fixed` threaded through pack/unpack/sparsity/pipelines/schema/CLI. Most principled — drops the parameter, honest DOF count — but ~100 references across 9 files, six days before a freeze. | |
| Solve free, re-evaluate the guard at GT | Recompute the counter with `water_z` at ground truth. Cheapest; defensible only because the direction is provably flat, but reports a counter for a configuration never solved. | |

**User's choice:** Bounds freeze in the experiment
**Notes:** Investigation during the discussion found `build_bounds` (`_optim_common.py:522`)
already emits a dedicated `[0.01, 2.0]` bound for the `water_z` slot and `optimize_interface`
already passes `bounds=` to `least_squares`, so the chosen route tightens an existing slot rather
than adding a mechanism. The rejected flag route was costed at 101 `normal_fixed` references
across 9 files.

### If the pinned + normal-free combination comes back badly conditioned, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Measure it first, before writing plans | Probe the combination now, ~3 min on the existing harness. Makes the fallback question moot in most outcomes. | ✓ |
| FIX-01 wins — drop the free normal for that arm | Keeps the pin and the zero guard count (retires audit F-003 defect 1); the two E1 arms then differ in DOF as well as index. | |
| FIX-02 wins — drop the pin, explain the count | Keeps DOF parity with production and discloses the count as benign unit-index bookkeeping. Loses the "zero out-of-domain observations" claim. | |

**User's choice:** Measure it first, before writing plans
**Notes:** The combination is what the re-run actually executes and no probe has reached it,
because pinning did not exist.

### Both degenerate arms landed exactly on a `water_z` bound. How should that be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Record it as evidence, and detect it generally | Log in MANUSCRIPT-FINDINGS.md as corroboration of the null direction, plus a check flagging any solve terminating on the `water_z` bound. | ✓ |
| Record it as evidence only | Note the finding, add no detection; keep Phase 23 to the six FIX requirements. | |
| Neither — the pin makes it moot for E1 | Treat as an artifact of the pre-fix state. | |

**User's choice:** Record it as evidence, and detect it generally
**Notes:** Placement was then split — the evidence stays in Phase 23, the general detector was
handed to **DEGEN-02 in Phase 24**, where "parameter resting on its bound" is naturally a failure
*kind* and `_optim_common.py` is already being touched. This avoids widening Phase 23's pre-freeze
diff.

### What should the non-refractive arm's benchmark record say about the pin?

| Option | Description | Selected |
|--------|-------------|----------|
| Value, mechanism, and reason | Held value (1.031 m), how (bounds-frozen), why (exact null direction at unit index) with a pointer to the measurement. | ✓ |
| Value and mechanism | What and how; rationale lives only in MANUSCRIPT-FINDINGS.md. | |
| A boolean flag | `water_z_pinned: true`. Minimal schema risk, leaves the reason to be reconstructed. | |

**User's choice:** Value, mechanism, and reason

### The hardcoded `[0.01, 2.0]` `water_z` bound — user-raised

**User's question (free text):** *"quick question on the pinned bounds -- are those hardcoded deep
in the library to 0.1-2.0? If so, that makes the library a bit less general than we are claiming,
doesnt it?"*

Confirmed: `_optim_common.py:571-575` sets both as bare literals, `build_bounds` takes no bound
argument, and `docs/guide/troubleshooting.md:99` instructs users with a >2 m standoff to *"modify
the bounds in the source code."* Intrinsics bounds in the same function are data-relative
(`0.5 * fx`–`2.0 * fx`).

| Option | Description | Selected |
|--------|-------------|----------|
| Parameterize in Phase 23, pin rides on it | Add `water_z_bounds` defaulting to today's values (bit-unchanged); FIX-01's pin becomes a call with a degenerate interval. One change serves both. | |
| Parameterize AND derive the default from data | Same threading, default computed from camera positions and the initial estimate. Better for users, but moves the feasible region on every solve. | |
| File it, fix it post-submission | Record as a finding; thread FIX-01's pin as its own narrow change. Minimal pre-freeze diff. | ✓ |
| You decide | | |

**User's choice:** File it, fix it post-submission
**Notes:** Filed as
`.planning/todos/pending/2026-08-17-POST-SUBMISSION-water-z-bounds-are-hardcoded-and-force-a-source-fork.md`.
Judgment call recorded in the todo: under the milestone's scope test it fails on the suite (no
published number moves) but arguably passes on the library, in the milestone whose output is a
paper describing that library. Also settled: `troubleshooting.md:99` is **not** corrected now —
it accurately describes a real limitation and changes when the limitation does.

---

## `--check` verification contract

### How should the contract handle columns that are artifacts of the checking path?

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude them, by an explicit named list | Skip `exit_code` and `status_reason`, printing what was skipped each run. Named beats heuristic — the next such column needs a deliberate decision. | ✓ |
| Make `--check` populate them honestly | Emit `exit_code: 0` for a cell whose committed record says it succeeded. No exemption list, but fabricates a field in a provenance artifact. | |
| Drop `--check` as FIX-05's verification | Smoke cells only; leave the contract entirely to DRIVER-03. Smallest diff, but leaves a red gate through the freeze for the Linux operator to interpret. | |

**User's choice:** Exclude them, by an explicit named list
**Notes:** Phase 23 implements; Phase 26 (DRIVER-03) documents. The two must not diverge.

### Does the 9-of-10 red matter beyond fixing it?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — record it as a process finding | A gate that cannot pass is worse than no gate; it trains everyone to ignore it. Same class as the decision-coverage gate that passed while parsing nothing. | ✓ |
| No — just fix it | The 33 metric columns did reproduce, so nothing was missed. | |
| Yes, and audit the other gates now | Check `check_rerun_gates.py` and others for always-red/always-green before the freeze, since Phase 29 depends on them. | |

**User's choice:** Yes — record it as a process finding
**Notes:** The broader gate audit was not taken; carried to Deferred Ideas against the Phase 27
freeze gate.

---

## In-phase verification budget

### How much gets run inside Phase 23?

| Option | Description | Selected |
|--------|-------------|----------|
| Cheap tier only: E1 both arms + E4 smoke cells | ~6 min; covers the three fixes whose outcome cannot be predicted by reading (FIX-01, FIX-02, FIX-05's aggregation path). | ✓ |
| Cheap tier plus E1's 10-seed band | Adds ~1 h; turns FIX-01's effect into a band, relevant because four band seeds carry their own degenerate counts (14907, 2128, 1134). Re-run in Phase 28 regardless. | |
| Nothing — tests and inspection only | Every number traceable to the frozen sha, but the first sight of whether pin + free-normal converges would be on the Linux machine. | |

**User's choice:** Cheap tier only
**Notes:** Runtimes were measured from the committed queue logs rather than estimated — E4's
nine-cell grid ran 3.5–4 h across `rerun_19_3.log` and `rerun_19_4.log`, which put it firmly in
Phase 28.

### How do we stop in-phase outputs being mistaken for run artifacts?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated `--out` under a git-ignored verification directory | e.g. `experiments/verify_23/`, never committed. Side effect: exercises FIX-05's `--out` path. | ✓ |
| Dedicated directory, committed as phase evidence | Auditable pre-freeze record, at the cost of repo numbers not from the frozen sha. | |
| Default output tree, cleaned up after | Simplest; relies on cleanup discipline during the milestone's most safety-critical window. | |

**User's choice:** Dedicated `--out`, git-ignored
**Notes:** Consequence carried into CONTEXT.md — evidence must be transcribed into
MANUSCRIPT-FINDINGS.md rather than referenced as an artifact path.

---

## Plan decomposition + commit granularity

### How should the six fixes be split into plans?

| Option | Description | Selected |
|--------|-------------|----------|
| Four plans, grouped by coupling | (1) FIX-01+02, (2) FIX-05, (3) FIX-03+04, (4) FIX-06. Matches the real dependency structure; isolates the string-only change. | ✓ |
| Six plans, one per requirement | Cleanest traceability and matches the roadmap's wording, but forces FIX-01/02's ordering between plans rather than inside one. | |
| Two plans: solver-affecting and reporting-only | Sharpest statement of what can move a number, but puts four unrelated fixes across three files in one plan. | |

**User's choice:** Four plans, grouped by coupling

### Commit granularity within a plan?

| Option | Description | Selected |
|--------|-------------|----------|
| One commit per requirement, even inside a shared plan | FIX-01 and FIX-02 as two ordered commits in one plan, bisectable apart. Applies the v2.0.0 one-commit-per-breaking-change lesson. | ✓ |
| One commit per plan | Simpler history, but welds FIX-01 and FIX-02 together permanently. | |
| One commit per file touched | Overkill; would split FIX-06's single logical correction across two trees. | |

**User's choice:** One commit per requirement

---

## Claude's Discretion

- The exact mechanism for reaching `build_bounds` from `e1_refractive_comparison.py` — least
  invasive route that still constrains the solve.
- The FIX-01 fallback if the pinned + normal-free probe degrades.
- Whether the `--check` exclusion list is E4-local or shared across experiments.

## Deferred Ideas

- Parameterize the `water_z` bound, then derive it from data — filed as a POST-SUBMISSION todo.
- The `±0.2` rad tilt bound has the same hardcoded-absolute question — folded into that todo.
- General bound-hit detection — handed to DEGEN-02 in Phase 24 as a degeneracy *kind*.
- Audit the other gates for always-red / always-green behaviour — reconsider at the Phase 27
  freeze gate, since Phase 29 depends on `check_rerun_gates.py` being able to fail.
- Source-level `normal_fixed` reconciliation — already deferred by the milestone; unchanged.
