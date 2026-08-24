---
created: 2026-08-17T00:00:00.000Z
title: Audit the suite for static strings that annotate a recomputed value — the FIX-06 defect class, not just its four instances
area: experiments
resolves_phase: 27
files:
  - experiments/e2_real_rig.py
  - src/aquacal/datasets/synthetic.py
  - experiments/e1_refractive_comparison.py
  - experiments/e4_benchmark_grid.py
  - experiments/e6_generalization_sweep.py
  - experiments/e7_focal_standoff_analysis.py
---

## Problem

FIX-06 (Phase 23) corrected four stale provenance strings. Planning recon on 2026-08-17 found that
one of them — `e2_real_rig.py`'s `mean_per_camera_reprojection_px` provenance parenthetical — was
not merely stale but **structurally self-invalidating**: a *static* string annotating a *computed*
field. It quoted `0.8786`; `experiments/results/real_rig_metrics.json` now holds
`0.8240385366779744`. The string did not rot through neglect. It rotted because the value it names
is recomputed on every run while the string is not.

Phase 23's plan 04 fixed that instance correctly — it names the derivation and quotes no live value,
with a test asserting `"0.8240" not in source`, so swapping one frozen number for another (which
would have reproduced the defect one run later) is blocked.

**What was not addressed is the class.** No one has enumerated the other places in the suite where a
static string annotates a value that gets recomputed. Phase 23 deliberately did not widen to cover
it: D-13 isolates plan 04 specifically so it can never be blamed for a number moving, and bolting an
open-ended audit onto it would have destroyed that property.

## Why this is not a grep

A naive sweep flags correct code. `e2_real_rig.py:255-262` legitimately cites `0.8786` and `1.0191`
because it names the release run **explicitly and by name** — and it is the note that stops the
pooled RMS being compared against the per-camera mean. It must stay.

The distinction is attribution, and it is judgment rather than pattern matching:

- **Legitimate** — the string names a specific historical run, release, or archived record, so the
  number is a citation and is *supposed* to be frozen.
- **Defective** — the string annotates a field the code recomputes, with no attribution, so the
  number silently becomes a claim about the current run that nobody re-derives.

Phase 23's plan 04 also documented a related trap: every gate written for this class necessarily
contains the stale strings itself (in the plan, the test, the supersession header), so assertions
must be scoped to named files and phrased on **claim sentences**, never bare number tokens.

## Why Phase 27

Phase 27 is the freeze. After it, a wrong number is a wrong number in the archive the paper cites,
and there is no cheap correction. This is the same reasoning that parks the always-red/always-green
gate audit at the Phase 27 gate (`23-CONTEXT.md` § Deferred Ideas), and it belongs in the same slot
for the same reason: it is the last cheap moment to check.

Scope it as a **classification pass, not a rewrite** — enumerate the candidate sites, sort each into
legitimate-historical or unattributed-annotation, and fix only the second category. If the pass finds
nothing in category two, that is a valid and valuable outcome to record.

## Known non-issues (checked 2026-08-17 — do not re-litigate)

`src/aquacal/datasets/synthetic.py`'s four "real-rig standoff" mentions (`:1016`, `:1062`, `:1100`,
`:1142`) are **accurate and current**. They describe the D-19.3-09 change — that these presets now
inherit the module-level `WATER_Z` (~1.031 m) instead of the old 0.15 m shallow-tank value. They
mention the real rig because the presets genuinely use its standoff. Two of them (`:1100`, `:1142`)
are additionally *data*: they sit inside scenario `description=` values that reach committed tutorial
output and `tests/unit/test_datasets.py:502`, so editing them would move artifact content.

## Acceptance

- Every candidate site in `experiments/` and `src/aquacal/` is listed with a classification and a
  one-line reason.
- Sites in the defective category either name their derivation (quoting no live value) or carry
  explicit run attribution.
- Any gate added is scoped to named files and asserts on claim sentences, not bare numbers.
- The pass runs **before** the Phase 27 freeze, or is explicitly and knowingly declined.

---

## Partially discharged in Phase 29.1 — 2026-08-24 (plan 03)

**Stays pending.** Only a bounded portion of this todo's Acceptance is discharged. What follows
states the bound precisely so a later pass starts from it rather than re-deriving it.

**The bound and why it exists (D-09).** The pass covered only the strings, in the modules that
WROTE the 2026-08-20 production run's artifacts, that annotate a value **that run recomputed**.
That is this todo's literal ask — "static strings that annotate a recomputed value" — and it is the
only boundary in which every finding carries evidence: each verdict is checkable against a
committed artifact. The alternative, sweeping all of `experiments/`, was ruled out because ~500 KB
of it annotates values no recent run touched, so findings there would be assertions rather than
measurements.

**Files in the bound (11):** the ten stage-invocation modules named in
`experiments/suite_expectations.json` — `e1_refractive_comparison.py`, `e2_real_rig.py`,
`e3_derived_quantities.py`, `e4_benchmark_grid.py`, `e5_index_sensitivity.py`,
`e6_generalization_sweep.py`, `e7_interface_ablation.py`, `e7_focal_standoff_analysis.py`,
`fd_jacobian_accuracy.py`, `reconstruction_bootstrap.py` — plus the driver
`run_experiment_suite.sh`.

**What the pass found and fixed.** 196 candidate lines from a single recorded command, 158 dropped
in Pass A as design inputs, 38 classified individually. **27 legitimate citations** (including this
todo's own named non-issue, `e2_real_rig.py`'s `0.8786` / `1.0191` release citations, confirmed
legitimate and left alone) and **11 defective rows across 9 blocks** in `e1_refractive_comparison.py`,
`e4_benchmark_grid.py`, `e6_generalization_sweep.py` and `run_experiment_suite.sh`. All eleven were
corrected: each now either names its derivation and quotes no live value, or carries explicit run
attribution. Two twin sites outside the bound (`_expectations.py:23`,
`check_rerun_gates.py:621`/`:673`) were corrected with them, because leaving a twin standing is the
partial-fix shape this class of gate exists to catch.

**Full record — read this before any later pass:**
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-STALE-STRING-AUDIT.md`. It carries the
boundary with a reason for every exclusion, the enumeration command verbatim, the Pass A drop
counts, and the per-site classification table with the remedy applied to each defective row.

**This todo's Acceptance, item by item:**

- *"Every candidate site in `experiments/` and `src/aquacal/` is listed with a classification and a
  one-line reason."* — **Partially met.** Met inside the bound. **Not** met for the rest of
  `experiments/` (`e4_check_detail.py`, `seed_sweep_19_3.sh`, `render_expectation_sheet.py`, the
  archived trees, and four of the five shared helpers), and **not attempted** for `src/aquacal/`,
  which this phase may not modify by hard constraint. Note that the shared-helper exclusion was
  premised on those modules carrying "mechanism, not measured values", and `_expectations.py`
  falsified that premise — so a later pass should treat the helpers as candidates, not as excluded
  by kind.
- *"Sites in the defective category either name their derivation or carry explicit run
  attribution."* — **Met inside the bound**, for all 11.
- *"Any gate added is scoped to named files and asserts on claim sentences, not bare numbers."* —
  **Met.** `tests/unit/test_stale_provenance_strings.py::TestBoundedStaleStringSweep`: 16
  claim-sentence assertions across six named file constants, no tree walk, repo root anchored to
  the test file's own location. All 16 clauses were verified present before the fix, so the gate is
  not vacuous.
- *"The pass runs before the Phase 27 freeze, or is explicitly and knowingly declined."* — **Timing
  changed, knowingly.** Phase 27 cut `rerun-freeze-01`; this pass ran in Phase 29.1, before
  `rerun-freeze-02`, which is the tag the re-run and the Zenodo archive will be built from. The
  reasoning is unchanged — this is the last cheap moment before a wrong number becomes a wrong
  number in the cited archive.

**What remains out of scope, explicitly:**

1. The rest of `experiments/` beyond the eleven boundary files.
2. All of `src/aquacal/` — out by this phase's hard constraint 1, independent of merit. This todo's
   own § *Known non-issues* already clears `synthetic.py`'s four real-rig-standoff mentions; that
   ruling stands and was not re-litigated.
3. `.planning/` prose. Two stale figures found there incidentally (MF-12's decomposition digits and
   MF-16's regenerability claim) are recorded in
   `.planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md` and were deliberately not
   edited — a manuscript finding is supposed to record what was measured when it was written.
