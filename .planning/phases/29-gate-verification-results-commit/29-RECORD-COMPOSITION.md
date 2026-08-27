# Record A / Record B payload composition — the ruling

**Ruled:** 2026-08-26
**Ruled by:** author (tlancaster), via plan 29-01 Task 1 (`checkpoint:decision`, gate `blocking`)
**Option chosen:** `research-default`
**Requirement:** RUN-05
**Reversibility:** one-way — Record A is immutable once published, a permanent DOI over a fixed
byte set. A missing input is fixable only by cutting a new version, which breaks the "these are
the frames the run consumed" citation the record exists to make.

**Rationale (author):** Record A must be a complete, self-contained input set — that is what
"these are the frames the run consumed" has to mean to a reviewer — so the intrinsic calibration
frames ship alongside the extrinsic ones despite the ~14% added transfer on D-29-04's critical
path; the archived calibration comparison target is a *result*, not an input, so it travels with
the results package it belongs to.

This file is the authorised payload list. Plan 29-04 reads it before building Record A's zip;
plan 29-07 reads it before building Record B. Nothing else authorises a byte into either record.

---

## Record A (immutable inputs)

Paths are relative to `aquacal_data/real-rig/real-rig/` (the extracted cache of the published
archive `21889922`, present on this machine; `aquacal_data/.gitignore` contains `*`, so none of
it is tracked).

| Path | Size (measured 2026-08-26, `du -sh`) |
|---|---:|
| `extrinsic/` | 3.6 GB |
| `intrinsic/` | 518 MB |
| `README.md` | 3.5 KB |

**Total: ~4.1 GB.** Assigned by the folded todo: the extrinsic frames only. The other two are this
ruling's additions.

Record A is inputs *only*. It carries no calibration result, no configuration and no run output.
Its zip must be **built** from the paths above — the published `real-rig-calib.zip` bundles inputs
and outputs together, and that bundling is precisely the defect this split exists to fix.

## Record B (versioned results package)

Paths marked *(archive)* are relative to `aquacal_data/real-rig/real-rig/`. Paths marked *(run)*
are relative to the repository root and come from **this run's own output**, not from the archive.

| Path | Origin | Size |
|---|---|---:|
| `config_paper.yaml` | *(archive)* | 2.5 KB |
| `config_quickstart_not_paper.yaml` | *(archive)* | 2.3 KB |
| `reference_calibration.json` | *(archive)* | 2.2 MB |
| `reference_outputs/` | *(run)* — **this run's fresh copies, replacing the archive's** | 19 MB |
| `run_manifest.json` | *(run)* | — |

**Total: ~21 MB.** Assigned by the folded todo: the paper config, the reference outputs and the
run manifest. The other two are this ruling's additions.

**The reference outputs directory is replaced, never copied forward.** The archive's
copies are the *old* numbers, which is exactly the discrepancy the supersession statement in Record B's description
must warn a reviewer about. The six filenames Record B ships under it all exist in this run's
output, five of them gitignored under `experiments/results/` — Record B is exactly the payload
D-29-17's ignore rules exclude from git, which is the design working as intended.

---

## Carried forward to plan 29-08 — surfaced, not decided

Two findings from reading `src/aquacal/datasets/loader.py` during this ruling. Both are recorded
here and **left untouched by Phase 29**; the `manifest.json` / `_manifest.py` repointing is an
explicitly deferred item (CONTEXT § Deferred Ideas, RESEARCH § *`_manifest.py` Blast Radius*) and
stays deferred.

1. **Two records, one cache layout.** `loader.py:79-86` resolves the archived calibration
   comparison target from the *same extracted directory* as the frames, and
   `download.py:145-180` builds exactly one record URL from `manifest.json`. Splitting the record
   means `load_example('real-rig')` must fetch two records and merge them into one cache layout,
   or the pin stays on `21889922` by explicit decision. This consequence exists under any split;
   it is not an argument against the option chosen here.

2. **Latent pre-existing mismatch.** `loader.py:90` looks for a file named `config.yaml`, a name
   that exists neither in the current archive nor in either record above. That config read is
   already a silent no-op today. Pre-existing, out of scope here, not introduced by this split.

---

## Sources

- `.planning/todos/pending/2026-08-15-repackage-and-reupload-the-zenodo-archive.md` — § Decision
  (author, 2026-08-15), the two-record design and the config-goes-with-results ruling
- `.planning/phases/29-gate-verification-results-commit/29-RESEARCH.md` — § *The A/B Split
  Payloads* (measured composition), Assumptions Log row A4 (this question, rated LOW confidence)
- `.planning/phases/29-gate-verification-results-commit/29-CONTEXT.md` — D-29-04 (Record A first,
  critical path), D-29-17 (what git holds vs. what the archive holds)
- Sizes re-measured independently on this machine 2026-08-26 and agree with RESEARCH exactly.
