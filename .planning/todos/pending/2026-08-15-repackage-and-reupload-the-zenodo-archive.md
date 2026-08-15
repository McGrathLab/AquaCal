---
created: 2026-08-15T00:00:00.000Z
title: Split the Zenodo record into immutable inputs and a versioned results package — the current single-zip bundle makes every output revision cost a 4.35 GB re-upload
area: data
resolves_phase: 29
files:
  - experiments/e2_real_rig.py
  - experiments/reconstruction_bootstrap.py
---

## Problem

`main.tex` §3's numbers trace to the published archive's `reference_outputs/`. A fresh E2 run
produces new ones, so after the re-run the archive either gets re-published or it contradicts the
paper it exists to support.

**The bundling is what makes this expensive.** Record `21889922` is a single ~4.35 GB zip holding
inputs (13 × 262 extrinsic frames, `config_paper.yaml`) *and* outputs (`calibration.json`,
`diagnostics.json`, `reconstruction_errors.csv`, `reprojection_residuals.csv`,
`exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`). Zenodo's new-version flow
carries *files* forward without re-upload — but with one file in the record there is nothing to
carry. **Every future revision of a few megabytes of results costs a full 4.35 GB upload**, and
this will not be the last re-run.

Inputs and outputs have completely different lifecycles. Bundling them is the defect.

## Decision (author, 2026-08-15) — split into two records

**Record A — inputs.** The extrinsic frames. Immutable; versioned only if the capture changes.
One zip is fine: no consumer wants a subset, since multi-camera calibration needs every camera.
Zenodo publishes an MD5 per file, so "these are the frames the run consumed" stays verifiable.

**Record B — results package.** `config_paper.yaml`, the reference outputs, and the run manifest.
A few MB; re-versioned whenever results change.

**`config_paper.yaml` goes with the results, not the inputs.** It describes *how* the results were
produced and it can plausibly change in this milestone (schema changes, the memory flag). In the
input record a config change would invalidate a 4.35 GB upload already made; in the results record
the input record becomes genuinely immutable, and Record B becomes self-contained — config, outputs
and manifest are what a reviewer wants to inspect together anyway.

## Sequencing — the run is not blocked by any of this

The inputs are already on disk, so the re-run proceeds regardless. **Only the DOI citation depends
on an upload**, and that is a later gate.

- **Do the repackage and Record A's upload *while the run is in flight*, from the Windows box —
  not before the run** (author decision, 2026-08-15). Planning happens on Windows, the suite runs
  on the Linux machine, and the Windows box is idle and better-connected for the whole window.

  The reason is not only bandwidth: **the pre-run window is the highest-stakes moment of the
  milestone.** A mis-launched queue costs the entire run, so the checklist immediately before the
  push should be as short as possible. An unrelated multi-gigabyte upload does not belong in it.
  Once the queue is confirmed running on Linux, the upload uses dead time on an otherwise idle
  machine.
- **Use the Zenodo API, not a browser.** Multipart upload is resumable; an hours-long browser tab
  failing partway is the bad outcome.
- **Safe to do concurrently with the run, with one constraint.** D-19.3-18's "commit nothing while
  a run is in flight" was written when planning and running shared a machine, where per-stage
  `git rev-parse HEAD` could capture two shas. With the run isolated on Linux the rule narrows to:
  **do not pull, check out, or otherwise mutate the Linux checkout while the queue is running.**
  Committing and pushing from the Windows box is harmless. This is what makes the repackage work
  safe to do in parallel.
- **Record B uploads after the run is verified** — minutes, not hours.
- Zenodo can **reserve a DOI on an unpublished draft**, so the manuscript can cite the identifier
  while an upload is still in flight, if it comes to the wire.
- Verify the round trip before publishing Record B: a fresh run off Record B's `config_paper.yaml`
  against Record A's frames must reproduce the new §3 numbers — the same check that confirmed 262
  usable frames → 210/52 split → 200 calibration frames → `num_comparisons = 7762` on 2026-08-12.

## Fallback, if the input upload cannot complete in time

Leave `21889922` untouched as the historical submitted package and publish **only** Record B. The
paper then cites raw data at `21889922` and results at the new DOI. Zero large upload.

**The wart must be handled deliberately, not left implicit:** `21889922` still contains the *old*
`reference_outputs/`, so a reviewer who unzips 4.35 GB meets numbers that disagree with the paper.
That needs an explicit supersession statement both in Record B's description and in the paper's
data-availability section. For a submission whose reviewers pressed on reproducibility, prefer
spending the overnight over explaining the discrepancy.

## Pre-run check — confirm there is no real circularity

Before the run, audit which scripts read the archive's `reference_outputs/`. They are meant to be
comparison targets, never inputs. Two specific paths to confirm:

- `reconstruction_bootstrap.py --reconstruction-errors` takes a path. **If it is pointed at the
  archive's `reconstruction_errors.csv` rather than at the fresh E2 output, the new results are
  partly derived from the old ones.** Point it at the run's own output.
- Anything `--check` compares against, and E2's no-`--config` "reader's default" path, which
  resolves against the published archive.

## Code consequence

`e2_real_rig`'s archive-resolution logic (the no-`--config` reader path) points at one bundled
record today. After the split it needs frames from Record A and config from Record B. That change
lands in the same file as the stale `--config` help text already being fixed in
`2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md` — do them together.

## Do not

- Do not re-bundle inputs and outputs into one file again. That is the defect being fixed.
- Do not chunk the input zip per camera. Considered and rejected 2026-08-15: no consumer wants one
  camera without the others, and upload reliability belongs to the client's multipart support, not
  to the published artifact's shape.
- Do not silently reuse the existing version DOI. Citing a version DOI is a promise that it pins
  bytes; repointing it breaks that for anyone who already has it.
- Do not delete the old version. Zenodo versions accumulate; the submitted package's history stays
  legible and the audit's provenance trail keeps resolving.
- Do not upload Record B before the hand-verification passes. A published archive from an
  unverified run is harder to retract than to delay.
- **Do not edit the paper's DOI citation from this repo.** Report the new DOIs to the manuscript
  session.

## Related

- `REVISION-ROADMAP.md` §10 item 1 (version vs concept DOI) — this makes that decision live again,
  now across two records.
- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` — Record B must be built
  from the fresh tree, so sequence the purge after the upload.
- `2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — the manifest ships inside
  Record B, and should record Record A's DOI as the input it consumed.

## Scope boundary — artifacts, not prose

Library and data work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only from
this repo; the DOI citation and data-availability wording are the manuscript session's edits.
