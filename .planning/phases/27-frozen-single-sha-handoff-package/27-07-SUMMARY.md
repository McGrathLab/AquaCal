---
phase: 27-frozen-single-sha-handoff-package
plan: 07
subsystem: experiments-provenance
tags: [provenance, ledger, frozen-rows, phase-30-handoff, D-19]
requires:
  - "numbers-ledger.tsv (author's manuscript tree, read-only)"
  - "experiments/archive/ pre-fix trees"
  - "experiments/pre_rerun_baseline/results_linux32gb/"
  - "experiments/suite_expectations.json (stage -> out_dir map)"
provides:
  - "experiments/FROZEN-ROWS.md: 23 ledger rows classified with sha, machine class and cause"
  - "Phase 30 / POST-03's dangling-reference list"
affects:
  - "experiments/EMITTER-COVERAGE.md (27-06): the two reports partition the ledger by ledger id"
tech-stack:
  added: []
  patterns:
    - "EXPECTATIONS.md's written-before-the-fact voice, dense per-row-verdict tables, and bold anti-misreading callouts"
    - "Provenance read from the artifact's own environment.git_sha, never from the archiving commit's HEAD"
key-files:
  created:
    - experiments/FROZEN-ROWS.md
  modified: []
decisions:
  - "Machines are referred to by class (W16 / L32), never by hostname or user path -- T-27-07-03"
  - "Per-artifact sha beats a tree-level summary sha: e2_cv413 is attributed to 1af0650, not linux32gb_scope.json's top-level d27bda7"
  - "The frozen-row note lives in experiments/ alongside EXPECTATIONS.md, not .planning/ (author's discretion per CONTEXT)"
  - "RL-guard-frac added to section 4 on the author's ruling after 27-06's coverage walk; total 22 -> 23"
  - "RL-guard-frac carries the only `not recorded` cells in the document -- no artifact, no provenance block, and campaign context is not written in as though it were a record"
metrics:
  duration: ~50 min
  completed: 2026-08-19
---

# Phase 27 Plan 07: Frozen Ledger Rows Summary

D-19's in-repo note now classifies all 23 `numbers-ledger.tsv` rows the Phase 28 run will not
re-source, each with the sha and machine class it was actually measured at, so Phase 30 can purge
the archive trees against a stated list instead of re-deriving one.

## What was built

`experiments/FROZEN-ROWS.md` (331 lines), in six sections:

- **§0 how to read it** — column semantics, and the two machine classes: **W16** (Windows 11, 20
  logical cores, 16,857,190,400 B) and **L32** (Linux 6.8.0-136-generic, i9-13900KF, 32 cores,
  33,351,241,728 B).
- **§1 pre-fix archive trees** — 5 rows, not 3 as the plan estimated (see Deviations).
- **§2 the earlier Linux campaign** — 9 rows, not 6 (the `linux32gb_scope.json` group is 3).
- **§3 frozen behind the OpenCV 4.13 pin** — the 7 `KEEP-FROZEN-5f` rows.
- **§4 unregenerable by construction** — **2 rows**: `RL-determinism`, naming P26-D-42, and
  `RL-guard-frac`, added on the author's ruling (see below).
- **§5 what Phase 30 inherits** + **§6 what this note does NOT do**, plus a subsection stating how
  the note joins `EMITTER-COVERAGE.md` by ledger `id`.

22 of the 23 shas were recovered from an artifact's own provenance block. **`RL-guard-frac` is the
single row that needs the `not recorded` marker**, in both its sha and its machine cell — see the
addition section below for why nothing was inferred to fill them.

## Findings recorded in the note

Four are load-bearing beyond this plan; a fifth arrived with the `RL-guard-frac` addition and is
recorded in that section below:

1. **L32 is, to every recorded detail, the Phase 28 target** — same kernel build (6.8.0-136), core
   count (32) and RAM as D-25's target facts. So §2's rows differ from the coming run by
   *software and output directory*, not hardware. A Phase 30 reader who assumes a hardware
   difference would re-point those citations for the wrong reason.
2. **`linux32gb_scope.json`'s tree-level `git_sha` is wrong for one of its five subtrees.**
   `e2_cv413/benchmark.json` records `1af06508db120daacce8618b8387c7a7213b1fbe`; the scope file's
   top level says `d27bda76...`. The two cv413-sourced ledger rows (`S-repro-cv413`,
   `M-perf-cv413`) are therefore attributed per-artifact. This is the F-001 shape in miniature.
3. **`M-L302-signed`'s artifact attribution is one level off.** `real_rig_metrics.json` has no
   signed-mean field — `e2_real_rig.py:252-254` computes `mean(abs(...))` and RMS, averaging the
   sign away before the file is written. The +0.043 mm figure is derivable from
   `reconstruction_errors.csv`'s `signed_error_m` column, which is gitignored under DATA-01b
   (`.gitignore:239`) and ships only in the Zenodo archive. Sha and machine are still correct — same
   run, same solve — but the bytes are not in this repo.
4. **The §3 rows' file IS rewritten by the run; the numbers are not re-sourced from it.**
   `e2_production` writes `experiments/results/real_rig_metrics.json`, so a naive reading of the
   stage list would conclude those seven rows refresh. They do not: they are DOI-frozen and the
   fresh file's role is `check_e2_band`'s 1e-6 control (`check_rerun_gates.py:1378`). This
   distinction is stated explicitly because it is the one a reader gets wrong.

Also recorded: the sha-recovery **method**. Neither archive directory carries a sidecar of its own,
so the producing sha comes from the contemporaneous sidecar at the archiving commit's parent
(`git show 8a90ea3^:...e6_provenance.json` -> `74e75a7b`; `git show 117bad7^:...benchmark.json` ->
`77a1026a`), with the copies confirmed byte-identical by `md5sum` after `tr -d '\r'`. Reading the
sha out of `experiments/results/` at the commit the archive README *names* gives a different, older
generation of the E6 CSV — the results tree lagged the sidecar.

## Values reconciled against artifacts

Every quoted number in the note was checked against the file it cites, not copied from the ledger:

| Quantity | Ledger text | Artifact value |
|---|---|---|
| E4 grid peak memory | 0.87 to 11.32 GiB | 0.87 / 11.32 GiB from the nine cells' `peak_bytes_stage3_*` |
| E2 peak working set | 10.35 GiB / ~11 GB | `whole_run_peak_bytes` 11108622336 B = 10.346 GiB |
| E2 runtime | "tens of minutes" (~19 min) | 725.68 + 394.96 = 1120.6 s = 18.7 min |
| Submitted optimality | 2.08e4 | `stage3_intrinsic_pass.optimality` 20813.59 |
| Submitted pooled RMS | 1.019 px | `mean_reprojection_px` 1.019136 |
| All 7 §5f values | 0.82 px, 0.55–2.08, 0.258, 0.628, 0.43%, 14.9 px, +0.043 mm | six match `pre_rerun_baseline/results/real_rig_metrics.json` exactly; the seventh is finding 3 |
| Both determinism arms | same git_sha | `2a623f9d09bc...` in both `results/` and `results_e6_repeat2/` `e6_provenance.json` |

## Deviations from Plan

### Scope corrections (Rule 1 - the plan's row counts were low)

**1. [Rule 1 - Bug] The archive group is 5 rows, not 3**
- **Found during:** Task 1, filtering the ledger
- **Issue:** D-19 and the plan objective both say "three rows cite `archive/...`". The actual
  filter returns five: `RL-prefix-affected`, `RL-prefix-healthy`, `RL-prefix-best` (E6) **plus**
  `RL-opt-submitted` and `RL-rms-submitted` (E2). The "three" appears to have counted the E6 tree
  only.
- **Fix:** Classified all five. No ledger edit — the count was wrong in the plan, not the ledger.

**2. [Rule 1 - Bug] The earlier-machine group is 9 rows, not 6**
- **Found during:** Task 1
- **Issue:** The plan counts six `results_linux32gb/...` rows "and the `linux32gb_scope.json`
  group" without folding the latter into the total. That group is three rows (`S-repro-cv413`,
  `M-perf-cv413`, `RL-repro-grid`).
- **Fix:** Classified all nine. Subtotal 21 rows at first commit, against the plan's stated 17
  minimum; 23 after the author ruling below.

### Presentational adjustment

**3. [Rule 2 - Clarity] Made the `not recorded` count mechanically unambiguous**
- The `machine` column legend originally read "deliberately not recorded" about hostnames, which
  collided with the acceptance criterion's `grep -c 'not recorded'`. Reworded to "deliberately
  omitted" and added an explicit statement about which data cells carry the marker.

No architectural decisions were required; no Rule 4 checkpoint was hit.

## Post-acceptance addition: `RL-guard-frac` (commit `4c9a37f`)

**Source: an author ruling**, made after reviewing plan 27-06's coverage report, and relayed by the
orchestrator. 27-06's walk surfaced `RL-guard-frac` as a ledger row D-19 did not name. The rest of
the note was accepted as written, including the corrected 22-row population.

**THE TOTAL MOVED: 22 -> 23.** Flagged explicitly here because a silently-moving total is exactly
what this note exists to prevent. The group counts are now 5 pre-fix archive / 9 earlier campaign /
7 OpenCV-pinned / **2** by construction, and every count in the document was updated in lockstep:
§0's marker claim, §4's heading and table, §5's inheritance-table row and its "for each of the 23
rows" lead-in, the `EMITTER-COVERAGE.md` join subsection's arithmetic, and the closing tally line.

### The ledger row was verified directly, and the paraphrase did not survive

The orchestrator's message described `RL-guard-frac` as "a guard-rejection fraction". The ledger's
own `quantity` cell reads **"corner fraction at or above the interface, pre-fix baseline scenario"**,
with `locator` "a small fraction of target corners" and `current_text` **0.69%**. It is a
*scenario-geometry* fraction — how much of the synthetic board protruded through the modelled water
surface — **not** a solver-guard rejection rate. The note records the ledger's wording, and says
plainly why the distinction matters: a Phase 30 reader who files it as a guard statistic will look
for it in the wrong emitter and wrongly conclude the row is merely uncited.

**The category the ruling assigned is nonetheless correct**, by a different route than stated:
Phase 19.3's depth-clearance fix removed the state being measured. Post-fix, zero corners sit at or
above the interface in any scenario (MF-08), so the frozen post-fix sha returns 0.00% by
construction — not a reproduction of 0.69% and not a refutation of it. §4 now opens by naming the
two routes: `RL-determinism` is unregenerable because the **schedule** cannot produce it,
`RL-guard-frac` because the **code** cannot.

### Why its sha and machine are `not recorded`

The row has no artifact and no provenance block: the ledger's `artifact` and `derivation` cells are
both empty, and its note reads "no committed artifact -- pre-fix state". The 0.69% came from an
ad-hoc probe during Phase 19.2 plan 28 / the 19.3 seed work, which wrote no artifact and therefore
no `environment` block. The closest contemporaneous anchor is the §1 archive tree at `74e75a7b` on
W16, measured on the same baseline scenario (12 cameras, 100 frames, seed 42) — **that is recorded
in the prose as campaign context and deliberately not written into the table cells**, because an
inferred sha in a provenance column is indistinguishable from a recorded one. §0's claim was
rewritten from "no data cell carries the marker" to name this row as the single exception.

### A fifth finding, from verifying the ledger note's cross-references

The row's note says the figure is "recorded identically in 19.3-SEED.md, REQUIREMENTS.md and
MF-07/MF-08". Two of the three hold: `19.3-SEED.md:53` (61 / 8800 = 0.69%, worst protrusion
66.1 mm, with the full clearance derivation) and `.planning/MANUSCRIPT-FINDINGS.md:640` (MF-07) /
`:686` (MF-08). `.planning/REQUIREMENTS.md` exists at this sha and contains **neither the figure nor
the protrusion language** (checked for `0.69`, `8800`, `protrud`, `above the interface`). Recorded
in §5 as a third item needing a Phase 30 decision, with the reassurance attached: **the figure is
not at risk, the pointer is.**

### Consistency with 27-06, which reads the same tree

The author accepted 27-06's grade of `linux32gb_scope.json` as EMITTER-BACKED / NOT REGENERATED.
The join subsection previously implied §2 had no emitter; it now states 27-06's grading explicitly
and does not dispute it — an emitter for the class of artifact still puts nothing back into
`results_linux32gb/`, which is the path those rows cite. Per-artifact sha attribution is noted as
the agreed treatment in both documents, so the `1af0650` finding is relayed rather than contradicted.
`experiments/EMITTER-COVERAGE.md` was not touched.

## Constraints honoured

- **`numbers-ledger.tsv` was opened read-only** and never written. Rows are cited by `id`
  throughout (T-27-07-01).
- **No hostnames or user paths.** `results_linux32gb/e2_timing/run.log` contains an absolute
  `/home/<user>/...` path; it is not reproduced. Machines are referred to as W16 / L32 only
  (T-27-07-03).
- **No archive or `results_linux32gb` tree was deleted or moved.** The purge is Phase 30 / POST-03.
- **`experiments/EXPECTATIONS.md` untouched** (27-03 owns it this wave).
- **`experiments/EMITTER-COVERAGE.md` untouched** (27-06 owns it this wave).
- **`STATE.md` and `ROADMAP.md` untouched** — orchestrator-owned.
- **No test suite run.** This plan adds one Markdown file and changes no code; the plan's own
  verification section specifies no targeted test command.

## Acceptance criteria

| Criterion | Result |
|---|---|
| `test -f experiments/FROZEN-ROWS.md` | PASS |
| >= 17 rows keyed by ledger `id` | PASS — 23 unique ids, no duplicates |
| `grep -c 'e6_repeat2'` >= 1 | PASS — 6 |
| `grep -q results_linux32gb` | PASS |
| No blank cell, no invented sha | PASS — 22 shas from an artifact's own provenance block; `RL-guard-frac` marked `not recorded` in both cells, which the criterion permits for a row whose provenance genuinely cannot be recovered |
| "What Phase 30 inherits" section | PASS — §5, with a four-group purge table |
| "What this note does NOT do" section | PASS — §6, five bold callouts |
| `key_links` pattern `NOT REGENERATED` | PASS — in the `EMITTER-COVERAGE.md` join subsection |

**Internal count consistency**, re-verified after the addition: §1 (5) + §2 (9) + §3 (7) + §4 (2)
= 23, matching §0's "other 22" plus one marked row, §5's "each of the 23 rows", the join
subsection's 7 + 9 + 7, and the closing tally. `grep -oE '^\| `(M-|S-|RL-)[A-Za-z0-9-]+`' | sort -u
| wc -l` returns 23 with no duplicates.

## Self-Check: PASSED

- `experiments/FROZEN-ROWS.md` — FOUND (331 lines)
- Commit `c5646da` — FOUND (`docs(27-07): classify every ledger row this run will not regenerate`)
- Commit `4c9a37f` — FOUND (`docs(27-07): add RL-guard-frac to the by-construction group`)
- `numbers-ledger.tsv` — unmodified (opened read-only; outside this repo, never staged)
- `experiments/EMITTER-COVERAGE.md`, `STATE.md`, `ROADMAP.md` — never opened for writing
- `git diff --diff-filter=D` across both commits — no deletions
