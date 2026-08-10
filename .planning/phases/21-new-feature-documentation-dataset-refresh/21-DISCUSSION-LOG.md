# Phase 21: New-Feature Documentation & Dataset Refresh - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 21-new-feature-documentation-dataset-refresh
**Areas discussed:** Documentation scope (DOCS-05), Archive build + §3 reproduction gate, Zenodo
publish mechanics, Notebook refresh scope, Contradiction resolution

---

## Todo cross-reference

| Option | Description | Selected |
|--------|-------------|----------|
| Zenodo re-upload todo (0.9) | 2026-02-24 — `initial_distances` -> `initial_water_z: 1.0`; literally DATA-01/02 | ✓ |
| Pin opencv below 5.0 (0.6) | Unbounded `opencv-python>=4.6` can resolve to 5.0 and break a fresh install | ✓ |
| Non-refractive baseline (0.7) | Verify `n_water=1.0` supports the paper's refractive-vs-non-refractive claims | ✓ |
| None — keep all six as todos | Keep the phase boundary tight against 2026-08-21 | |

**User's choice:** All three folded.
**Notes:** Three remaining matches (memory/CPU load, band sidecar, E5 band tests) not folded —
already tracked in HANDOFF.json's post-Zenodo batch.

---

## Documentation scope (DOCS-05)

### `calc-index` vs deferred Phase 20

| Option | Description | Selected |
|--------|-------------|----------|
| Amend DOCS-05, drop calc-index | Rewrite to cover only what shipped; calc-index rides with Phase 20 | ✓ |
| Pull Phase 20 forward into 21 | Implement INDEX-01..03 here, then document it | |
| Leave DOCS-05 partially open | Document the shipped items, carry the requirement into Phase 22 | |

**User's choice:** Amend DOCS-05, drop calc-index.
**Notes:** Scouting confirmed `calc-index` does not exist anywhere in `src/`. Phase 20 is small and
standalone, but was deferred on measured evidence (MF-13), not cost.

### Where the benchmark.json schema is documented

| Option | Description | Selected |
|--------|-------------|----------|
| New guide/benchmarking.md page | benchmark.json + trace CSV + conditioning npz in one place | ✓ |
| Extend configuration.md | Add a schema table to the existing 316-line config reference | |
| Autodoc from the writer module | Docstrings on the writer, pulled into docs/api | |

**User's choice:** New `docs/guide/benchmarking.md`.
**Notes:** `benchmark.json` had zero documentation anywhere — the actual DOCS-05 gap.
`shared_interface` and the trace/conditioning flags were already present in some form.

### Trace and conditioning documentation depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full: columns + interpretation | What each column/key means and how to read it | ✓ |
| Structural only | File names, columns, types; no interpretation | |
| Keep the one-line config rows | Declare configuration.md:244-245 sufficient | |

**User's choice:** Full, including interpretation.

---

## Archive build + §3 reproduction gate

### Frame encoding

| Option | Description | Selected |
|--------|-------------|----------|
| Pilot test decides quality | Corner-displacement pilot across JPEG q92/q95/q100 vs decoded video | |
| Match today's quality (~580 MB) | Reproduce the shipped archive's JPEG quality | |
| JPEG q100 (~1.5 GB) | Maximum-fidelity JPEG | |
| *(user-proposed)* Lossless PNG (~4.4 GB) | Bit-exact to the decoded video frame | ✓ |

**User's choice:** Lossless — *"why cant we just do lossless? Its a zenodo upload, so file size
isnt that important. It means the tutorial takes longer to download, but that seems like an
acceptable cost."*
**Notes:** Checked before accepting: Zenodo's default per-record quota is 50 GB; no CI job
downloads the archive; `load_example` caches. Measured encodings on a real frame — PNG 1,205 KB,
q100 451 KB, q95 296 KB, current archive ~170 KB. Lossless makes the planned JPEG pilot
unnecessary. The download cost the user accepted here evaporated later when the notebooks stopped
using the archive at all.

### Miss policy

| Option | Description | Selected |
|--------|-------------|----------|
| HALT and escalate to you | Stop, report deltas, user decides | ✓ |
| Fall back to option (b) | Move §3 to the numbers the archive produces | |
| Accept within a stated tolerance | Pre-commit a tolerance and accept inside it | |

**User's choice:** HALT and escalate.

### One archive or two

| Option | Description | Selected |
|--------|-------------|----------|
| Two files, one record | ~4.4 GB paper archive + ~600 MB tutorial archive | |
| One archive, ~4.4 GB | Single file, both configs inside | ✓ |
| One archive, tutorial subsets included | Single file, fast config for tutorial runtime only | |

**User's choice:** One archive.
**Notes:** The two-file option's motivation (keep tutorial 01's download small) was eliminated
later by the notebook pivot, which strengthened this choice retroactively.

### Intrinsic frames

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — PNG both | Re-extract intrinsic/ as PNG alongside extrinsic/ | ✓ |
| No — keep intrinsic as shipped | Reuse the existing 49 MB JPEG intrinsic dirs | |

**User's choice:** PNG both.
**Notes:** The gate response's "intrinsic/ unchanged" was about frame count, not encoding.

### Extraction tooling

| Option | Description | Selected |
|--------|-------------|----------|
| Committed script under scripts/ | Standalone, reproducible, not public API | ✓ |
| Under experiments/ | Inherits the suite's provenance conventions | |
| New `aquacal extract-frames` CLI | Real public subcommand | |

**User's choice:** Committed script under `scripts/`.

---

## Zenodo publish mechanics

### Record strategy

| Option | Description | Selected |
|--------|-------------|----------|
| New version of 18645385 | Concept DOI stable, old archive stays resolvable | ✓ |
| Fresh record | No lineage to the 2026-02 archive | |

**User's choice:** New version of 18645385.

### Upload mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Committed script, you run it | Script reads a token from env; user runs it; resumable | |
| You do it manually in the browser | Web UI upload and publish; no token anywhere | ✓ |
| Decide at execution time | Stage the archive, leave the mechanism open | |

**User's choice:** Manual browser upload.
**Notes:** Fragility of a 4.4 GB browser upload was flagged in the option text and in the response;
the user chose it anyway. Recorded, not re-litigated. The plan compensates by pre-computing the
manifest values so the manual step is transcription.

### Pre-publish gates (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Full §3 run from the staged zip | ~50 min run of config_paper.yaml against the exact upload bytes | ✓ |
| Checksum + size + extraction path | The three manifest fields plus loader.py:60 layout | ✓ |
| Tutorial 01 runs against the staged dir | Execute notebook 01 against the extracted staging dir | ✓ *(later superseded)* |
| Both configs load and validate | `load_config()` under v2.0.0 semantics | ✓ |

**User's choice:** All four.
**Notes:** The third gate went vacuous when the notebook pivot removed 01's zenodo branch; it was
flagged in the contradiction pass and replaced (see below).

---

## Notebook refresh scope

### Narration scope (first attempt)

| Option | Description | Selected |
|--------|-------------|----------|
| Contradicted lines only | Fix only what fresh outputs falsify | |
| Full editorial pass | Re-read both notebooks end to end against v2.0.0 | |
| Contradicted lines + stale-claim sweep | Bounded grep-driven sweep on top | |

**User's choice:** *(not answered — redirected)* — *"hmmmm ok, seems like maybe I misunderstood the
tutorial notebook purpose. I thought it used the full zenodo dataset, but sounds like it's a very
different script focused on lightweight work. Maybe the tutorial just goes away?"*
**Notes:** The user's original understanding was in fact correct — `DATA_SOURCE = "zenodo"` is the
committed default in cell 3. Re-asked after the pivot; see Contradiction resolution.

### Tutorial 01's 4.4 GB download

| Option | Description | Selected |
|--------|-------------|----------|
| Keep zenodo opt-in, warn loudly | synthetic-small recommended, explicit 4.4 GB note | |
| Split into a separate reproduction notebook | 01 purely synthetic, new notebook for real-rig | ✓ *(direction)* |
| Keep as-is, no extra warning | Size already in docs and manifest | |

**User's choice:** *"If we're keeping the notebook, I think we move it to be purely synthetic. The
zenodo upload becomes source material for the full experiment suite, and the concerns about
downloads for the fast tutorial goes away."*

### What happens to tutorial 01

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic + prose repro page | 01 synthetic; short non-executed page covers the real-rig path | |
| Purely synthetic, nothing else | Delete the zenodo branch; archive's only consumer is the experiment suite | |
| Keep both paths, flip the default | Default synthetic-small, zenodo branch retained | |
| Delete 01 entirely | 02 becomes the only tutorial | |
| *(user-proposed)* Synthetic notebooks + written CLI tutorial | Real data reserved for the experiment suite; a written CLI walkthrough in the docs | ✓ |

**User's choice:** *"what do you think? I lean towards condensing the notebooks to be fast-running,
synthetic-only notebooks, with the real-world data reserved entirely for the experiment suite. We
could however include a written tutorial in the docs where the user downloads the full zenodo set
and runs calibration via the CLI -- the CLI is the preferred entrypoint, so this is valuable in and
of itself."*
**Notes:** Agreed and endorsed — the docs' only end-to-end worked example currently uses the Python
API, while `docs/guide/cli.md` is a 197-line reference rather than a walkthrough, so the docs teach
the non-preferred entrypoint. Cost identified and accepted: the synthetic paths only run Stages
2-3, so Stage 1 and `run_calibration_from_config` lose their notebook home and gain a better one.

### Numbers in the written CLI tutorial

| Option | Description | Selected |
|--------|-------------|----------|
| Cite the archive's own outputs | Quote from the reference outputs DATA-01b ships, file named inline | ✓ |
| Show no numbers at all | Commands and config only | |
| Numbers plus a regeneration command | Real numbers plus a committed regeneration command | |

**User's choice:** Cite the archive's own outputs.
**Notes:** Raised as a caveat first — a prose tutorial with pasted console numbers is exactly the
hand-carried-number failure mode this milestone exists to prevent.

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| docs/tutorials/ as a .md page | Beside the notebooks under the Tutorials nav | ✓ |
| docs/guide/ as a walkthrough | With cli.md and configuration.md | |

**User's choice:** `docs/tutorials/` as a `.md` page.

### Re-execution repeatability

| Option | Description | Selected |
|--------|-------------|----------|
| Committed command, run manually | Makefile target or script | |
| Manual, documented in the phase summary | Execute by hand, record steps in SUMMARY | ✓ |
| CI staleness check | Fail if stored outputs are older than the code | |

**User's choice:** Manual, documented in the SUMMARY.

---

## Contradiction resolution

The user asked, before closing: *"anything contradictory that we need to resolve from the
discussion first? I know we changed direction a bit on the notebooks halfway through."* Three real
contradictions were found and resolved, plus one correction to the summary.

### Replacement for the vacuous pre-publish gate

| Option | Description | Selected |
|--------|-------------|----------|
| CLI tutorial commands, verbatim | Run the written tutorial's commands against the staged dir | ✓ |
| e2_real_rig.py against staging | Run the experiment-suite consumer instead | |
| Drop it — three gates suffice | Keep the critical path shorter | |

**User's choice:** CLI tutorial commands, verbatim.
**Notes:** "Tutorial 01 runs against the staged dir" tested nothing once 01's zenodo branch was
deleted. The CLI tutorial is now the only doc touching the archive.

### The second (tutorial) config

| Option | Description | Selected |
|--------|-------------|----------|
| Repurpose for the CLI tutorial | Rename to reflect a fast first-contact run | ✓ |
| Drop it — config_paper.yaml only | One config, maximum provenance clarity | |
| Keep both, document the fast one as optional | Ship unchanged, mention as a shortcut | |

**User's choice:** Repurpose for the CLI tutorial.
**Notes:** Its stated purpose ("keep tutorial 01 at ~8 min") died with the pivot.

### Narration scope (re-asked)

| Option | Description | Selected |
|--------|-------------|----------|
| Contradicted lines + stale-claim sweep | Bounded grep-driven sweep | |
| Contradicted lines only | Tightest scope | |
| Full editorial pass | End-to-end re-read against v2.0.0 | ✓ |

**User's choice:** Full editorial pass.
**Notes:** Cheaper after the pivot, since both notebooks became much smaller.

### Correction issued

The summary claimed the "Stages 1-4" leftovers die with the zenodo branch. Only cell 6 does; `01`
cell 0 ("Run all four calibration stages") and cell 26 are notebook-level narration that survive
the deletion and still need editing. Recorded in CONTEXT.md D-20.

### Non-contradiction recorded

"One archive" became *more* correct after the pivot, not less: its competing option existed to keep
the tutorial download small, a cost no longer paid by anyone. The decision stands; only its
rationale changed.

---

## Claude's Discretion

- Page structure and section ordering within `docs/guide/benchmarking.md` and the CLI tutorial.
- The new name for the repurposed fast config, subject to clearly signalling "does not reproduce §3".
- Sequencing of the full editorial pass against notebook re-execution.
- Whether DATA-01b's repo surgery lands before or after the Zenodo publish (the pre-commit
  `exclude` removal must land with it).

## Deferred Ideas

- Phase 20 / INDEX-01..03 and its `calc-index` documentation — deferred on MF-13.
- HANDOFF.json's post-Zenodo repair batch (8 items) — explicitly out of scope.
- MF-12's `layout/line` conditioning test — cheap, not started, suggested for after Zenodo.
- `aquacal extract-frames` as a public CLI subcommand — declined for this phase.
- Automated notebook-staleness detection (CI job or committed re-execution command) — declined;
  the underlying drift problem remains unaddressed.
- CLEAN-01 (`initial_distances` shim retirement) — unblocked by DATA-02 but not this phase.
- Three reviewed-but-unfolded todos: memory/CPU load, band sidecar contention, E5 band test
  fixture sharing.
