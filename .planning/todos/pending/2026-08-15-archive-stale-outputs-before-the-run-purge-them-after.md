---
created: 2026-08-15T00:00:00.000Z
title: Move every pre-re-run output tree aside before the run, and purge it at release — the shipped library should carry only the data the paper cites
area: experiments
resolves_phase: 26
files:
  - experiments/results/
  - experiments/results_linux32gb/
  - experiments/results_e2_band/
  - experiments/e4_benchmark_grid.py
---

## Decision (author, 2026-08-15)

After the re-run, remove the stale output from the library. Git preserves the history; the final
release should carry only the real data the paper actually cites.

**Split into two phases, because the early half does work for the run itself.**

## Phase 1 — before the run: move aside, do not delete

Relocate every existing output tree — `experiments/results/`, `experiments/results_linux32gb/`,
`experiments/results_e2_band/` — into a single clearly-named archive directory
(`experiments/results_prerun_archive/` or similar), in one commit, immediately after tagging the
pre-run sha.

**This is not tidiness; it removes three live failure modes.**

- **It defuses the E4 aggregator defect at the source.** `e4_benchmark_grid.py:226` resolves the
  real-rig row from a `__file__`-anchored `E2_BENCHMARK_PATH` that does not follow `--out`. The
  dangerous case that todo identifies is an `--out` run silently *pairing* one machine's synthetic
  cells with another machine's real-rig row — which can only happen while a stale
  `experiments/results/benchmark.json` exists at the default path. Move it and the worst case
  becomes a missing row that announces itself.
- **It makes the hand-verification unambiguous.** With `--check` suspended for reshaped artifacts,
  the verifier's strongest invariant is "everything under `experiments/results/` was produced by
  this run". That is only true if the directory starts empty.
- **It kills resume-skip ambiguity.** Experiments that skip completed work on resume cannot
  half-populate a fresh tree from a previous run's leftovers.

**Keep the archive reachable for the duration of the run.** The E2 control described in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` compares the fresh real-rig run
against the committed baseline and expects agreement at ~1e-8; that comparison needs the old tree
present. Archived, not deleted, until the run is verified.

## Phase 2 — after the run is verified: purge

Delete the archive directory in one commit whose message names the tag it is recoverable from.

- Purge only after the hand-verification has passed and the post-run `--check` re-baselining has
  landed. Deleting the comparison basis before the comparison is made is the one way this goes
  wrong.
- Audit for path references before deleting: `linux32gb_scope.json`, `experiments/README.md` §2,
  `check_rerun_gates.py`, and any test fixture pointing at `results_linux32gb/` or
  `results_e2_band/`. A purge that leaves dangling references trades stale data for broken tooling.
- The Zenodo re-package (`2026-08-15-repackage-and-reupload-the-zenodo-archive.md`) must carry the
  **new** reference outputs. Sequence the purge so the archive upload is built from the fresh tree,
  not from whatever survives.

## Do not

- Do not delete anything in Phase 1. "Git preserves it" is true and is still not a reason to make
  the run's own control unreachable mid-flight.
- Do not purge before the post-run re-baselining lands. Until then the suite has no regression
  protection and the old tree is the only reference for what changed.
- Do not leave the archive directory in the release. A `results_prerun_archive/` shipped to PyPI or
  Zenodo is worse than the problem it solved — it reintroduces exactly the two-sources-of-truth
  confusion this exists to end.
- Do not rely on `.gitignore` instead of moving the trees. The artifacts are committed; ignoring
  them changes nothing about what is on disk during the run.

## Related

- `2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — tag the pre-run sha before
  Phase 1; that tag is what makes the purge safe.
- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — Phase 1 defuses its worst case, but
  does **not** replace the fix.
- `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — owns the verification the
  purge waits on.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo.
