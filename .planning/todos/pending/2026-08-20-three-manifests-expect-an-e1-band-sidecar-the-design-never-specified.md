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
