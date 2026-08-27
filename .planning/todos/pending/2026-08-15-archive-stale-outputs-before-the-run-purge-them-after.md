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

---

## Phase 1 LANDED — 2026-08-24, Phase 29.1 plan 06

**This todo stays PENDING. Phase 2 — the purge — has not happened and must not happen yet.**

Phase 1 was written for the run that became `rerun-freeze-01`, and by the time it was executed
that run had already happened. So it landed against the *output of* that run rather than against
the trees it was originally drafted for, which is the same work for the same three reasons.

**What moved.** Every output tree the 2026-08-20 production run wrote, plus the driver's own
state, into `experiments/freeze01_run_output/` — one commit, `git mv` so history follows the
files, each tree keeping its name one level down so the layout mirrors `pre_rerun_baseline/`:

| Subtree | Tracked | Ignored |
|---|---:|---:|
| `results/` | 147 | 5 |
| `results_e2_band/` | 7 | 129 |
| `results_e2_invocations/` | 25 | 94 |
| `results_e2_memory/` | 3 | 3 |
| `results_e2_timing/` | 3 | 3 |
| `results_e4_repeat/` | 4 | 0 |
| `driver_state/` (real + dry-run state, failures, 18 stage logs) | 38 | 38 |
| **total** | **227** | **272** |

499 files left; 499 files arrived. **Nothing was deleted** — the do-not list above was followed
literally, and the run's own control stayed reachable throughout.

**Why it is named for a tag rather than "prerun_archive".** With two archives now present, a
reader has to be able to tell which run each holds without opening either.
`pre_rerun_baseline/` is the pre-re-run tree; `freeze01_run_output/` is `rerun-freeze-01`'s run.

**The audit clause of this todo was executed as part of the move, not deferred to the purge.**
It is written for the eventual delete and applies verbatim to a move; 324 tracked files name a
moved path, each ruled on in `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-06-SUMMARY.md`.
Two rulings are worth repeating here because a later sweep will be tempted to undo them:

- **`suite_expectations.json`'s two conditional artifact entries were deliberately NOT moved with
  the tree.** They name `experiments/results_e2_invocations/e2_classification`, which is where the
  *next* run's E2 classification invocation writes — not where this run's copies now sit.
  Re-pointing them at the archive would make the manifest describe the past instead of the
  expectation, which is the exact defect plan 29.1-09 had just closed.
- **`tests/unit/_baseline_paths.py`'s `ARCHIVE` still points at `pre_rerun_baseline/`.** It is a
  statement about six specific Phase-19.1 seedless records that live there. No code changed:
  `resolve_results_dir` prefers the live tree only while it holds a file, so emptying
  `experiments/results/` repointed the committed-baseline rails by itself.

**Two ignore-rule mirrors were required, and one was load-bearing.** Every literal-prefix rule
naming a moved tree was mirrored under the new prefix in the same commit, before anything moved;
`results_e2_invocations/*/all_observation_depths.csv` is 10.9 MB and `experiments/` had no rule
for that filename outside the invocation-tree prefix (D-19), so without its mirror the next
commit would have tripped `check-added-large-files --maxkb=1000`. The second mirror was not
anticipated by the plan: `.pre-commit-config.yaml`'s detect-secrets `exclude` also names the
moved trees, and the staged rename reported Hex High Entropy String findings across the
`e6_configs` records until its optional archive segment was widened. The hook's own comment had
predicted this for the Phase 26 move.

### Phase 2 — still pending, and what it waits on

Unchanged from the top of this file, with the blockers restated as of 2026-08-24:

1. **The re-run must happen and be verified.** It has not. The re-run is licensed by the
   `rerun-freeze-02` tag that Phase 29.1 plan 08 cuts, and is a re-execution of Phase 28.
2. **The post-run `--check` re-baselining must land.** Until it does, the suite has no regression
   protection and the archived tree is the only reference for what changed.
3. **Phase 29's E7 before/after comparison is still open** and reads from
   `experiments/pre_rerun_baseline/`, so that archive in particular cannot go yet.
4. **The Zenodo re-package must be built from the fresh tree**, so sequence the purge after it.

When Phase 2 runs, it purges **both** archives' blocks together with the trees: the
`.gitignore` mirror block headed *"Phase 29.1 / plan 29.1-06"*, the matching
`pre_rerun_baseline` block above it, and `.pre-commit-config.yaml`'s archive segment. Each block
says so at its own head.
