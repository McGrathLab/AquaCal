---
created: 2026-08-20T00:00:00.000Z
title: suite_expectations.json, EXPECTATIONS.md and README.md all expect e1_seed_band_degeneracy_breakdown.json, which by design is not written
area: experiments
resolves_phase: 28
files:
  - experiments/suite_expectations.json
  - experiments/EXPECTATIONS.md
  - experiments/README.md
  - experiments/e1_refractive_comparison.py
---

Found by the 2026-08-20 production run at `rerun-freeze-01`. The second of the **two real
FAILs** in the end-of-run roll-up.

## The finding

    [FAIL] e1_band completeness:e1_seed_band_degeneracy_breakdown.json
           NOT FOUND at experiments/results/e1_seed_band_degeneracy_breakdown.json.
           Stage 'e1_band' is expected to produce it under the 'full' profile.

The stage exited 0 and wrote everything else it owes (`exp1_band.csv` 256 rows,
`exp1_parameter_band.csv` 384 rows, `e1_seed_band_provenance.json`), all of which PASS.

## This is a manifest defect, not a missing writer

The instinctive read — "E5 and E7 write a seed-band breakdown, E1 forgot to" — is wrong. The
authoritative writer table lives in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` § *The new sidecar*, and
**E1's band is deliberately not in it**:

| writer | filename |
|---|---|
| `e1_refractive_comparison.py` (`_run_full`, `_run_smoke`) | `e1_degeneracy_breakdown.json` |
| `e5_index_sensitivity.py` (`--seeds`) | `e5_seed_band_degeneracy_breakdown.json` |
| `e7_interface_ablation.py` (`--seeds`) | `e7_seed_band_degeneracy_breakdown.json` |

E5 and E7 have `--seeds` rows. E1 has only `_run_full` / `_run_smoke`. The code matches that
table exactly: `_run_band` (`e1_refractive_comparison.py:1050`) enumerates its outputs in its
docstring and never claims the sidecar, and the single `write_degeneracy_breakdown` call at
`:882` is on the `_run_full` path.

So three documents name an artifact the design never specified:

    suite_expectations.json:448, :717
    EXPECTATIONS.md:186
    README.md:132   (stage 16's expected-artifacts column)

## The fix is a decision

- **Drop it from the three manifests** if the design table is right that E1's band has no
  per-seed discard story worth keeping. Cheapest, and makes the roll-up green.
- **Add the writer** if it does — E1's band is 4 seeds x 4 noise levels x 2 models, so a
  per-seed breakdown is not obviously meaningless, and its absence is the only gap in the
  E1/E5/E7 symmetry.

Whichever way it goes, all four documents (three manifests plus the design table) should end up
agreeing, because right now no two of them do.

---

## Resolved 2026-08-24 — UNCLAIMED: the expectation is removed, no writer was added (D-04, D-05)

Phase 29.1, plan `29.1-02`, task 1. Of the two available resolutions — add a
`write_degeneracy_breakdown` call site to `_run_band`, or drop the expectation — the phase took
the second, and the reason is the design table, not convenience.

**The authority.** `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`
§ *The new sidecar* is the writer table for the whole `e{N}_degeneracy_breakdown.json` family.
It carries `--seeds` rows for **E5** and **E7** and deliberately **none for E1**. `_run_band`'s
code and docstring already matched that table; the three manifests were the outlier. Adding a
writer would have amended the design from the manifest side, silently.

**What moved (D-04).**

- `experiments/suite_expectations.json` — dropped from the `e1_band` stage's `produces` list
  **and** the artifact entry. `_expectations._validate_manifest` enforces bidirectional
  agreement between the two, so `load_expectations()` succeeding is the proof both moved
  together.
- `experiments/EXPECTATIONS.md` — **regenerated**, never hand-edited: section 7 is a generated
  region owned by `experiments/render_expectation_sheet.py`, and
  `tests/unit/test_expectations.py` fails when the sheet and the manifest drift. Declared
  artifact count 63 → 62. `--check` exits 0.
- `experiments/README.md` — removed from stage 16's expected-artifacts column, leaving the three
  artifacts the band does write.

**D-05's evidence is recorded in the manifest itself**, on the `e1_band` stage's `description`,
where a future reader meets the question rather than only here: E1's synthetic scenario produces
**zero** degenerate observations, so the sidecar would carry per-seed denominators
(`observations_evaluated__*`) and PnP attempt counts and nothing else — **but** E7's band sidecar
is equally all-zero on real degeneracy counters and is written anyway, so "it would be empty" is
not disqualifying by precedent alone. The design table is the reason. Re-adding the expectation
means amending that table first.

**Outcome.** This was the second of the two real FAILs in the 2026-08-20 roll-up and the only one
surviving plan `29.1-01`. The full-profile roll-up over `experiments/results` now reads
`TOTAL: 176 PASS, 7 N/A, 0 FAIL`, reached without weakening any gate. E5's and E7's band
degeneracy sidecars are still claimed — the unclaiming is scoped to one artifact, and task 1's
verification asserts that.

**What pins it.** `tests/unit/test_expectations.py` (88 passing) plus
`render_expectation_sheet --check`. A future re-add of the artifact entry without the `produces`
line, or vice versa, fails `load_expectations()` loudly.
