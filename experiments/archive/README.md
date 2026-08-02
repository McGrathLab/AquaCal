# `experiments/archive/` — pre-fix artifact archive

This directory preserves committed experiment artifacts as they stood
immediately BEFORE a non-inert library or scenario fix, so that a reader
diffing the manuscript's numbers has a single artifact to diff against
instead of reconstructing the "before" state from git archaeology. It
exists deliberately outside `experiments/results/` — see "The convention"
below.

## When to add a new archive generation

Add one when a change to library code or scenario construction is expected
to move already-committed, manuscript-facing experiment numbers, and the
change is not simply reverted if wrong (i.e. it is landing regardless).
Five or more experiments moving in one commit is exactly the case where
this matters most — git history alone forces a reader to reconstruct one
commit's worth of `experiments/results/` state per experiment, per number,
by hand.

## Index

| Directory | Experiments covered | Archived | Precedes | Producing commit(s) |
|---|---|---|---|---|
| `e2-2026-07-30-pre-pnp-guard/` | E2 | 2026-07-30 | The degenerate-PnP guard in `refractive_solve_pnp` (unvalidated `cv2.solvePnP` returning `success=True` for near-minimal oblique views, `\|t\|` up to 3.09e12 m) | `35d76a6828550a5a81d47e7eb820f9e34cdb2fe3` |
| `e1-2026-08-02-pre-depth-fix/` | E1 | 2026-08-02 | Phase 19.3's synthetic scenario depth-clearance fix (board corners protruding through the water surface; D-19.3-01/19) | `3d23ddd757d474e974d10d96bccd506d7b564f78` |
| `e4-2026-08-02-pre-depth-fix/` | E4 | 2026-08-02 | Same depth-clearance fix, plus E4's benchmark grid inheriting `GRID_DEPTH_RANGE` | `c511429e3fcd6b4e052a1362f44965d1c12f7f33` |
| `e5-2026-08-02-pre-depth-fix/` | E5 | 2026-08-02 | Same depth-clearance fix; `e5_index_sensitivity.py`'s hardcoded shallow `depth_range` | `aa4c92e4f063c75493c1d4c64cfde555636270be` |
| `e6-2026-08-02-pre-depth-fix/` | E6 | 2026-08-02 | Same depth-clearance fix, plus the scale-axis redefinition (D-19.3-07) and the paired determinism sweep's pre-fix baseline (63/308 cells, D-19.3-14) | `74e75a7b33d4d9be1467f5806e76d1e77604e047` |
| `e7-2026-08-02-pre-depth-fix/` | E7 | 2026-08-02 | Same depth-clearance fix (E7's `"realistic"` scenario call is affected via the shared depth-range enforcement even though its standoff itself is untouched) | `f9843972a879d95b87cbff66f06cc37c54e522c3` |

## The convention

Each archive directory is named `<experiment>-<date>-<what-it-precedes>/`
and contains its own `README.md` covering five things:

1. **Why it exists** — the defect being fixed and what it invalidated,
   stated precisely (and, where the fix does not change accuracy, saying so
   explicitly rather than implying the old numbers were wrong).
2. **Provenance** — the exact commit that PRODUCED the archived artifacts
   (read from that experiment's own provenance sidecar's
   `environment.git_sha` field — `benchmark.json`, `e5_provenance.json`,
   `e6_provenance.json`, etc. — never from the archiving commit's HEAD), and
   the run that produced them.
3. **What is copied vs what is retrievable** — small, manuscript-facing
   files (CSVs, `.tex` tables, sidecars with no `git_sha` field) are copied
   byte-for-byte. Files that would trip `check-added-large-files`
   (`--maxkb=1000`) or `detect-secrets` (any `assemble_benchmark_record`-
   shaped JSON carries `environment.git_sha`, a 40-hex string the secrets
   scanner reads as high-entropy) are instead pointed at with
   `git show <sha>:<path>`. Bypassing those hooks to store a redundant copy
   is explicitly rejected — see `e2-2026-07-30-pre-pnp-guard/README.md`'s
   own reasoning, which this repeats rather than re-litigates.
4. **Why it is NOT under `experiments/results/`** —
   `tests/unit/test_experiments_provenance.py` globs that directory at
   collection time and would sweep an archived copy into the live-
   provenance gate as if it were a current result.
5. **How to use it** — diff a freshly regenerated artifact against the
   archived copy; only the deltas attributable to the named fix (and, where
   a seed band exists, falling inside it) are legitimate.

## Do not delete an archive generation

until the manuscript's numbers have been reconciled against the
corresponding re-run (for the `pre-depth-fix` generation, that is MF-08 in
`.planning/MANUSCRIPT-FINDINGS.md`).
