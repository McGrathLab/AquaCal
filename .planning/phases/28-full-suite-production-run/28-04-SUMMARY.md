---
phase: 28-full-suite-production-run
plan: 04
subsystem: infra
tags: [preservation, archive, checksums, provenance, evidence, data-integrity]

# Dependency graph
requires:
  - phase: 28-full-suite-production-run
    plan: 03
    provides: "the completed production run at 7005a27 -- six output trees and three driver state artifacts in the clone, untouched"
  - phase: 28-full-suite-production-run
    plan: 01
    provides: "the dry-run rehearsal whose gitignored residue sits beside the production output and is excluded from the archive by construction"
provides:
  - "/home/tlancaster/rerun-freeze-02-output.tar.gz -- 461 files, 31,838,334 B, read-only, completeness proven by count"
  - "/home/tlancaster/suite_run_freeze02.log.preserved -- 430,438 B, read-only"
  - "/home/tlancaster/rerun-freeze-02-output.sha256 -- two recorded hashes, attempt 1's two-line form"
  - "/home/tlancaster/freeze02-tree-state-at-handoff.txt -- the nine untracked output paths, byte-parallel with attempt 1's record"
  - "/home/tlancaster/freeze02-archive-manifest.txt -- per-path counts, the completeness assertion, and the 507-vs-461 reconciliation"
  - "Proof by hash that attempt 1's preserved bulk is unmodified"
affects: [28-05-run-record, 29-gate-verification-results-commit]

actuals:
  tokens: 3100
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Archive completeness proven by comparing a tar listing count against a live find count over the same path list, rather than assumed from the tar command succeeding"
    - "The preserve list authored from the driver's own variables (run_experiment_suite.sh:264-272, :304, :309) rather than copied from prose documentation"
    - "Prior evidence asserted unmodified by re-hashing against a recorded value, not by testing for presence"
    - "Order is preserve, then chmod, then checksum -- so the hash is taken over an artifact that can no longer change"

key-files:
  created:
    - /home/tlancaster/rerun-freeze-02-output.tar.gz
    - /home/tlancaster/suite_run_freeze02.log.preserved
    - /home/tlancaster/rerun-freeze-02-output.sha256
    - /home/tlancaster/freeze02-tree-state-at-handoff.txt
    - /home/tlancaster/freeze02-archive-manifest.txt
  modified: []

key-decisions:
  - "freeze02-tree-state-at-handoff.txt was kept as bare `git status --porcelain` output, byte-parallel with attempt 1's nine-line record, and the dry-run-residue explanation was written into the archive manifest instead. Annotating the tree-state file itself would have destroyed the direct comparability that is its only purpose."
  - "The 46-file gap between attempt 1's 507 and this archive's 461 was reconciled item by item rather than noted as a discrepancy. It is entirely rehearsal residue attempt 1 swept in; the corrected nine-path list excludes it by construction, and this archive holds production output only."
  - "Attempt 1's artifacts were asserted unmodified by re-hashing both against the values in rerun-freeze-01-output.sha256, not by ls. Both match."

patterns-established:
  - "A count assertion is what turns 'the tar command ran' into 'the archive is complete' -- it is the check whose absence let attempt 1's documented preserve list stay wrong through a whole production run"

requirements-completed: [RUN-02]

coverage:
  - id: D1
    description: "All nine paths the driver writes are inside a single archive outside the clone, with completeness proven by count"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "find <nine paths> -type f | wc -l == tar tzf … | grep -v '/$' | wc -l  =>  461 == 461; distinct top-level entries == 9"
        status: pass
  - id: D2
    description: "The run log is preserved separately and both artifacts are locked read-only with recorded checksums"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "stat -c %a on both => 444; rerun-freeze-02-output.sha256 holds 2 lines matching fresh sha256sum"
        status: pass
  - id: D3
    description: "Attempt 1's preserved bulk is proven unmodified by hash"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "sha256sum rerun-freeze-01-output.tar.gz => 6ed041e8…1965d; suite_run_freeze01.log.preserved => ebdb7271…4885; both match the recorded values"
        status: pass
---

# Phase 28 Plan 04: Preserve the Output Summary

**All nine paths the driver writes are archived outside the clone at `/home/tlancaster/rerun-freeze-02-output.tar.gz` — 461 files, 31,838,334 bytes — with completeness proven by count rather than assumed. Both preserved artifacts are read-only with recorded checksums, and attempt 1's bulk is proven unmodified by hash. Nothing was deleted from the clone.**

## Performance

- **Duration:** 3 min
- **Tasks:** 2
- **Files created:** 5 (all off-repo by plan design; plan 05 routes the `freeze02-*` records into the phase directory)

## The tree was still pristine when this ran

    git -C $CLONE rev-parse HEAD  ->  7005a2771aa115e4f4c1284cec7e145739586a4a

The frozen sha, unmoved. `git status --porcelain` reports exactly **nine** entries, all untracked, all of them the run's own output:

    ?? experiments/results/
    ?? experiments/results_e2_band/
    ?? experiments/results_e2_invocations/
    ?? experiments/results_e2_memory/
    ?? experiments/results_e2_timing/
    ?? experiments/results_e4_repeat/
    ?? experiments/run_experiment_suite_state.7005a27.failures.txt
    ?? experiments/run_experiment_suite_state.7005a27.stagelogs/
    ?? experiments/run_experiment_suite_state.7005a27.tsv

### A note the plan asked for, with the opposite finding

The plan expected this record to carry **more** than nine entries — the nine output paths *plus* this attempt's dry-run residue — and asked that the difference from attempt 1's nine-line record be noted rather than explained away.

It carries nine. The residue is real and present:

    experiments/run_experiment_suite_state.7005a27.dryrun.tsv
    experiments/run_experiment_suite_state.7005a27.dryrun.failures.txt
    experiments/run_experiment_suite_state.7005a27.dryrun.stagelogs/     (39 entries)

but it is **gitignored** (`.gitignore:266-272`), and the default `git status --porcelain` form does not list ignored paths. Enumerating with `--untracked-files=all --ignored` finds 652 entries, 425 of them `!!`, 39 matching `dryrun`.

So the two attempts' tree-state records are byte-parallel at nine lines each, **but for different reasons** — attempt 1 had no dry-run residue at all, attempt 2 has residue that is ignored. Recorded because a future reader comparing the two files would otherwise conclude the trees were in the same state, and they were not.

The file was left as bare porcelain output rather than annotated in place: direct comparability with attempt 1's counterpart is its only purpose, and a header would have destroyed it. The explanation lives in `freeze02-archive-manifest.txt`.

## All nine paths present, none missing

Every path passed `test -e` individually **before** the archive was created. No finding to report.

| Path | Files |
|---|---:|
| `experiments/results` | 152 |
| `experiments/results_e2_band` | 136 |
| `experiments/results_e2_invocations` | **119** |
| `experiments/results_e2_timing` | **6** |
| `experiments/results_e2_memory` | **6** |
| `experiments/results_e4_repeat` | 4 |
| `experiments/run_experiment_suite_state.7005a27.tsv` | 1 |
| `experiments/run_experiment_suite_state.7005a27.failures.txt` | 1 |
| `experiments/run_experiment_suite_state.7005a27.stagelogs` | 36 |
| **Total** | **461** |

The three bolded rows are the trees attempt 1's *documented* `tar` line omitted — 131 files that would have been silently lost had this plan copied the prose instead of authoring the list from `run_experiment_suite.sh:264-272`.

## Completeness, proven rather than assumed

    tar tzf rerun-freeze-02-output.tar.gz | grep -v '/$' | wc -l   =  461
    find <the nine paths> -type f | wc -l                          =  461
    distinct top-level experiments/<name> entries                  =    9   (expected 9)

**The counts agree.** This assertion is the whole point of the step — it is the check whose absence let attempt 1's preserve list stay wrong through an entire production run.

## 507 versus 461, reconciled exactly

Attempt 1's archive holds 507 files; this one holds 461. The 46-file difference is **entirely rehearsal residue** that attempt 1 swept in and the corrected nine-path list excludes by construction:

| Entry in attempt 1's archive | Files |
|---|---:|
| `experiments/results_smoke_e2_band` | 4 |
| `experiments/results_smoke_e2_invocations` | 4 |
| `…state.3ab9c13.dryrun.tsv` | 1 |
| `…state.3ab9c13.dryrun.failures.txt` | 1 |
| `…state.3ab9c13.dryrun.stagelogs` | 36 |
| **Total** | **46** |

507 − 46 = 461. **The arithmetic closes exactly**, and every one of the six output trees and three state artifacts has an *identical file count* in both attempts, path for path. That is a structural agreement between the two runs worth noting on its own: the same stages produced the same number of artifacts in the same places.

This archive contains production output only.

## Preserved, locked, checksummed

| Artifact | Bytes | Mode | Attempt 1's counterpart |
|---|---:|---|---:|
| `rerun-freeze-02-output.tar.gz` | 31,838,334 | `r--r--r--` | 31,845,719 |
| `suite_run_freeze02.log.preserved` | 430,438 | `r--r--r--` | 425,119 |

Both within a few KB of attempt 1 — recorded not as a target but because a wildly different size would be worth noticing before the artifacts leave this phase, and neither is.

`/home/tlancaster/rerun-freeze-02-output.sha256`, in attempt 1's two-line form:

    3b21b88323bd7c04e9712ae2742cc09d423f925620e729ea7bbe2d391c9f030e  …/rerun-freeze-02-output.tar.gz
    5bdc6090df5741c86c225a1a14a4eee05f344a71f5d39ade7e50bd9dcf46915e  …/suite_run_freeze02.log.preserved

The order was preserve → `chmod a-w` → `sha256sum`, so each hash is taken over an artifact that can no longer change.

## Attempt 1's evidence is unmodified — by hash, not by presence

Both artifacts re-hashed and compared against `rerun-freeze-01-output.sha256`:

| Artifact | Recorded | Computed now | |
|---|---|---|---|
| `rerun-freeze-01-output.tar.gz` | `6ed041e8…1965d` | `6ed041e8…1965d` | **match** |
| `suite_run_freeze01.log.preserved` | `ebdb7271…4885` | `ebdb7271…4885` | **match** |

Attempt 1's name was neither reused nor overwritten; its tarball is still `-r--r--r--`, still 31,845,719 B, mtime still 2026-08-20 09:28.

## The boundary this plan does not cross (A1)

This plan preserves, captures and records checksums. It does **not**:

- create the `results/rerun-freeze-02` branch,
- commit any output tree,
- push anything from the production clone.

RUN-03, RUN-04 and RUN-05 all map to **Phase 29** in `REQUIREMENTS.md`, and `28-CONTEXT.md`'s in-scope list stops at *returning the artifacts with provenance intact*. The evidence capture, by contrast, could not be deferred — it had to be read while the tree was still pristine, which is why it is here and not there.

The production clone is still on a **detached HEAD** (`git branch --show-current` prints nothing) and nothing in it was created, modified, moved or deleted by this plan.

## Task Commits

1. **Task 1: capture tree state, archive all nine paths, prove completeness by count** — verify returns `OK live=461 arch=461`
2. **Task 2: preserve the log, lock read-only, record checksums** — verify returns `OK`
