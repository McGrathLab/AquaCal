# Phase 21: New-Feature Documentation & Dataset Refresh - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Everything this milestone built becomes discoverable in the docs, and the published real-rig
dataset stops being a 2026-02 artifact that produces different numbers than the paper it
accompanies.

Requirements: **DOCS-05, DATA-01, DATA-01a, DATA-01b, DATA-02, DATA-03**.

This phase is the milestone's **critical path**. The Zenodo archive is upstream of the notebook
refresh, the Phase 22 release cut, and the manuscript's DOI citation. SoftwareX deadline is
**2026-08-21**.

**Phase 20 (Refractive Index Helper) is DEFERRED** by user decision 2026-08-07 on measured
evidence (MF-13). Phase 21's ROADMAP entry lists Phase 20 as a dependency, but that dependency is
documentation-shaped and does not block — see D-01.

</domain>

<decisions>
## Implementation Decisions

### Documentation scope (DOCS-05)

- **D-01: Amend DOCS-05 to drop `calc-index`.** The requirement's text names `aquacal calc-index`,
  which does not exist in `src/` — it is Phase 20's INDEX-02 deliverable and Phase 20 is deferred.
  DOCS-05 is rewritten to cover only what this milestone actually shipped, plus the new
  deliverables below. `calc-index` documentation rides with Phase 20 whenever it lands.
  Rejected: pulling Phase 20 forward (widens the critical path 11 days out for a capability
  measured ~5x below seed noise); leaving DOCS-05 open into Phase 22 (unticked box at release cut).

- **D-02: New `docs/guide/benchmarking.md` page.** `benchmark.json` has **zero documentation
  anywhere today** — this is the real DOCS-05 gap. The page documents `benchmark.json`
  field-by-field, the trace CSV columns, and the conditioning `.npz` contents together, since all
  three are the same provenance surface. Rejected: extending `configuration.md` (already 316
  lines, and this is output schema not config); autodoc from the writer module (reads as API
  reference, undiscoverable for a reader holding a `benchmark.json`).

- **D-03: Trace/conditioning docs go deep — columns AND interpretation.** Document what each trace
  column means (cost, step norm, optimality) and what the conditioning `.npz` holds (singular-value
  spectrum, correlation matrix), plus how to read them — including the camera-height /
  interface-distance correlation block that MF-12's `layout/line` hypothesis would be tested
  against. Rejected: structural-only; leaving the two existing one-line rows at
  `docs/guide/configuration.md:244-245` (a flag whose output is undocumented is close to an
  undocumented feature).

- **D-04: Already satisfied, do not redo.** `shared_interface` IS already documented as an
  ablation option at `docs/guide/configuration.md:97,109` and
  `docs/guide/refractive_geometry.md:117`. Verify wording only.

- **D-05: New written CLI tutorial as a `.md` page under `docs/tutorials/`.** The docs' only
  end-to-end worked example currently uses the Python API (notebook 01); `docs/guide/cli.md` is a
  197-line reference, not a walkthrough. Since the CLI is the preferred entrypoint, the docs today
  teach the non-preferred path. This page is the new home for the real dataset, Stage 1 (in-air
  intrinsics), and `run_calibration_from_config`. Placement under `docs/tutorials/` (not
  `docs/guide/`) so a reader browsing Tutorials finds all three. `.md` alongside `.ipynb` in one
  nav section; nbsphinx handles this.

- **D-06: Every number in the CLI tutorial is quoted from the archive's own reference outputs**
  (the `calibration.json` / diagnostics that DATA-01b places inside the archive), with the source
  file named inline so a reader can diff their run against it. **A prose tutorial with pasted
  console numbers is exactly the hand-carried-number failure mode this milestone exists to
  prevent — the paper has been bitten twice this way.** Rejected: showing no numbers (a walkthrough
  with no expected output is hard to self-check); numbers plus a regeneration command (adds another
  thing someone must remember to run — the exact mechanism that made the notebooks stale).

### Archive build (DATA-01, DATA-01a, DATA-01b)

- **D-07: LOSSLESS PNG, both `extrinsic/` and `intrinsic/`. ~4.4 GB.**
  **This overrides the JPEG-sized budget implied by `19.1-E2-GATE-RESPONSE.md`'s "~685 MB"**, on
  the user's explicit reasoning: *"why cant we just do lossless? Its a zenodo upload, so file size
  isnt that important."* Verified affordable before locking — Zenodo's default per-record quota is
  50 GB; **no CI job downloads the archive** (nothing in `.github/workflows/` references
  `load_example` or `real-rig`); `load_example` caches so a reader pays once.

  The decisive benefit: **PNG of the decoded frame is bit-exact to what the video decoder handed
  the §3 run**, so the re-encode disappears as a variable and DATA-01a's acceptance becomes a clean
  test of the library rather than a test of whether JPEG preserves ChArUco corners. **This makes
  the JPEG corner-displacement pilot unnecessary — do not plan it.**

  Measured on a real frame (1200x1600 colour, `e3v829d` extrinsic video):

  | Encoding | Per frame | Extrinsic total (262 x 13) |
  |---|---|---|
  | PNG lossless | 1,205 KB | ~4.0 GB |
  | JPEG q100 | 451 KB | ~1.5 GB |
  | JPEG q95 | 296 KB | ~1.0 GB |
  | Current archive quality | ~170 KB | ~580 MB |

  Total with `intrinsic/` (~350 MB PNG) and DATA-01b reference outputs (~4 MB): **~4.4 GB**. Zip
  adds nothing over PNG.

- **D-08: `intrinsic/` is re-extracted as PNG too.** The gate response's "`intrinsic/` unchanged"
  is about **frame count** (the 60 -> 262 expansion applies only to `extrinsic/`), not encoding.
  Leaving `intrinsic/` as today's JPEG would reintroduce exactly the re-encode variable D-07 was
  chosen to remove, and intrinsics feed every downstream stage.

- **D-09: The extraction is deterministic — every 30th frame, no selection logic.** Measured: the
  extrinsic video holds **7,860 frames**; 7860 / 30 = **exactly 262**. So the release run's "262
  usable frames" is every 30th frame at a 100% detection rate. There is nothing to
  reverse-engineer. `frame_step: 30` with `max_calibration_frames: 200` and
  `holdout_fraction: 0.2` gives 262 usable -> 210 calibration / 52 validation -> 7,762 comparisons.

- **D-10: ONE archive, ~4.4 GB, containing BOTH configs.** One file, one DOI, one frameset, no
  chance of a reader using the wrong one. Rejected: two files in one record (a small tutorial
  archive plus the full paper archive) — **its entire motivation was keeping tutorial 01's download
  small, and after D-14 no notebook downloads the archive at all, so that cost is not paid by
  anyone.** The one-archive decision got *more* right after the notebook pivot, not less.

- **D-11: The extraction tool is a committed script under a new `scripts/` directory.**
  `scripts/` does not exist yet; this creates it. Not public API, so no DOCS-05 obligation, no
  tests-and-docs burden, and no v2.0.0 API-surface commitment 11 days from the deadline. Rejected:
  under `experiments/` (it is data prep, not an experiment); a new `aquacal extract-frames` CLI
  subcommand (adds public capability to a phase whose scope we just narrowed by dropping
  `calc-index`).

- **D-12: The second (tutorial) config is REPURPOSED, not dropped.** The gate decision put a
  `frame_step: 4`-`5` config in the archive "to keep tutorial 01 at today's ~8 min" — a purpose
  that died with D-14. It is retained and **renamed to reflect its new job**: a fast first-contact
  run for the CLI tutorial, so a reader is not forced into a ~50 minute solve on first contact.
  The CLI tutorial walks the reader through it, then points at `config_paper.yaml` for the full
  reproduction. **Whatever it is renamed to must make clear its numbers do NOT reproduce §3.**

### Zenodo publication (DATA-02)

- **D-13: New VERSION of existing record `18645385`, not a fresh record.** The concept DOI stays
  stable, the version gets its own DOI, and the 2026-02 archive stays resolvable for anyone citing
  it. Preserves citation lineage.

- **D-14 (upload): The user uploads and publishes MANUALLY through the Zenodo web UI.** No token
  enters the session or the repo, and no upload script is written. **The plan must produce an
  exact, mechanical step-by-step with the manifest values (`zenodo_record_id`, `checksum`,
  `size_bytes`) pre-computed**, so the manual step is transcription, not judgement.
  *Concern raised and overridden by the user, recorded not re-litigated:* 4.4 GB through a browser
  is fragile and not reproducible for the next release.

- **D-15: FOUR gates must be green BEFORE the DOI is minted.** A Zenodo draft is not publicly
  downloadable, so `load_example`'s end-to-end verification can only run after minting — and a
  minted DOI cannot be withdrawn. Everything checkable pre-publish is therefore checked
  pre-publish, and the post-publish step is a confirmation, not a discovery.

  1. **Full §3 run from the staged zip** — extract the built zip to a scratch dir and run
     `config_paper.yaml` end to end (~50 min), confirming `num_comparisons = 7762` and the other
     eight §3 quantities. This is DATA-01a's actual acceptance test, run against the exact bytes
     that will be uploaded.
  2. **Checksum + size + extraction path** — md5 and byte size from the final zip, and confirm it
     extracts to the nested layout `src/aquacal/datasets/loader.py:60` expects
     (`<cache>/real-rig/...`). These are the three manifest fields; a layout error found
     post-publish costs a second DOI.
  3. **The CLI tutorial's commands, run verbatim against the staged dir** — exactly as a reader
     would. *(This REPLACES "tutorial 01 runs against the staged dir", which the user originally
     selected and which went vacuous when D-14 removed 01's zenodo branch. The CLI tutorial is now
     the only doc that touches the archive, so this is the closest analogue to what was chosen.)*
  4. **Both configs load and validate** under current v2.0.0 semantics via `load_config()` — this
     is where the folded 2026-02-24 todo's `initial_distances` -> `initial_water_z: 1.0` fix
     actually lands.

- **D-16: If the staged archive does NOT reproduce §3 — HALT and escalate to the user.**
  Do **not** fall back to option (b) (moving §3 to the numbers the archive produces), and do
  **not** accept a miss under a self-chosen tolerance. Consistent with 19.2's D-34 halt conditions.
  A minted DOI cannot be withdrawn, and the ENLARGE decision was chosen specifically because the
  full frameset reproduces §3 exactly and therefore requires **no manuscript prose edits** against
  a ~3,916-of-4,000 word budget.

### Notebook refresh (DATA-03) — DIRECTION CHANGED MID-DISCUSSION

- **D-17: Both notebooks become fast, synthetic-only. Real data moves entirely to the experiment
  suite and the CLI tutorial.** User's words: *"I lean towards condensing the notebooks to be
  fast-running, synthetic-only notebooks, with the real-world data reserved entirely for the
  experiment suite. We could however include a written tutorial in the docs where the user
  downloads the full zenodo set and runs calibration via the CLI -- the CLI is the preferred
  entrypoint, so this is valuable in and of itself."*

  **This supersedes the four options originally offered** (keep both paths / flip the default /
  delete 01 / synthetic + prose pointer). The written CLI tutorial (D-05) is the replacement home
  for the real-data path, and it closes a genuine gap rather than relocating content.

- **D-18: Notebook 01's `zenodo` branch is DELETED.** Note `DATA_SOURCE = "zenodo"` is the
  **committed default today** (cell 3) — 01 currently *is* the full-dataset tutorial, which is why
  its stored outputs are real-rig outputs. Removing the branch also removes the stale "~164 MB"
  claim (cell 2) and the "Stages 1-4, ~15-20 min" line (cell 6). It also makes the notebook's Colab
  badge honest — a 4.4 GB download on Colab is not viable at any narration quality.

- **D-19: Notebook 02 demotes `RIG_SIZE` from `"large"` to `"small"`.** This is X4, tracked in
  REQUIREMENTS.md as Phase 21 work under DATA-03. `"large"` is 12 cameras / 30 frames / ~60 min;
  `"small"` is 4 cameras / 20 frames / ~2 min. `RIG_SIZE` appears in two places in the notebook.

- **D-20: FULL editorial pass over both notebooks**, not just contradicted lines. Cheaper than it
  would have been before the pivot, since the notebooks just got much smaller. Both are two feature
  releases behind and nothing has re-read them since 2026-02.
  **Known specific items (not exhaustive — the pass must find the rest):**
  - `01` cell 0: "Run all four calibration stages" — DOCS-06's three-stage framing. **Survives the
    branch deletion** (notebook-level narration, not inside the zenodo branch).
  - `01` cell 26: "Stages 1-4 for real data" in the Summary — same, survives.
  - `02` cell 2: the `"large"` = "~60 min total" comment.
  - `01` cell 2 / cell 6: die with D-18.

- **D-21: Re-execution is MANUAL, with the exact steps recorded in the phase SUMMARY.** No Makefile
  target, no CI staleness check. `nbsphinx_execute` stays `"never"`. Rejected: a committed
  re-execution command; a CI staleness job (adds a workflow plus a heuristic that can produce false
  failures). *Accepted cost, stated plainly:* this leaves the "nothing re-executes these
  automatically" condition that made them six months stale exactly as it is — mitigated only by the
  notebooks now being cheap to run.

### Requirement text that must be reworded by this phase

- **DOCS-05** — drop `calc-index` (D-01); add `docs/guide/benchmarking.md` (D-02) and the written
  CLI tutorial (D-05) as deliverables.
- **DATA-02** — its acceptance says `load_example` is verified "at the path **the notebook**
  resolves". After D-18, no notebook resolves it. Reword to the CLI tutorial and
  `experiments/e2_real_rig.py`.
- **DATA-03** — says "Both tutorial notebooks are re-executed with fresh committed outputs". Still
  satisfiable and now cheaper, but the real-data narration it anticipated moves to the CLI tutorial.
- **DATA-01a** — its `load_example("real-rig")` acceptance survives unchanged; `load_example` is
  still the download mechanism.

### Claude's Discretion

- Exact page structure and section ordering within `docs/guide/benchmarking.md` and the CLI
  tutorial.
- The new name for the repurposed fast config (D-12), subject to it clearly signalling
  "does not reproduce §3".
- How the full editorial pass (D-20) is sequenced against notebook re-execution.
- Whether DATA-01b's repo surgery (removing `calibration.json`, `reprojection_residuals.csv`,
  `reconstruction_errors.csv`, `exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`
  from `experiments/results/`) lands before or after the Zenodo publish — but the
  `exclude: ^experiments/results/` removal from `.pre-commit-config.yaml` must land with it, and
  the 1000 KB guard must pass repo-wide afterward.

### Folded Todos

Three todos fold into this phase's scope:

1. **`2026-02-24-upload-new-zenodo-dataset-with-image-based-inputs.md`** (match 0.9) — wants the
   archive's `config.yaml` re-uploaded with deprecated `initial_distances` replaced by
   `initial_water_z: 1.0` (scalar), matching current `load_config()`. This is literally
   DATA-01/DATA-02; it closes under gate 4 of D-15. Also settles DATA-01's open question of whether
   the shipped `initial_distances` was a scalar or carried pre-v1.4 physical-gap semantics.
2. **`2026-08-05-pin-opencv-below-5-0.md`** (match 0.6) — `opencv-python>=4.6` is unbounded above
   in both `pyproject.toml:33` and `requirements.txt:10`, so a fresh install can resolve to OpenCV
   5.0 and break out of the box. Folded because a broken install breaks the tutorials this phase
   re-executes and the CLI walkthrough it writes.
3. **`2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md`** (match 0.7) — verify
   the `n_water=1.0` baseline can carry the paper's refractive-vs-non-refractive claims. Folded by
   user choice despite being manuscript-shaped and listed in HANDOFF.json's post-Zenodo batch.
   **Planner note:** this is the loosest fit of the three and the most separable if the phase needs
   to shed scope against 2026-08-21.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The archive decision (read these two first — they are binding)
- `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-GATE-RESPONSE.md` §"Item 3 — the
  archive fork" — the **ENLARGE** decision (option a, not b), the two-config structure, and the
  DATA-01b split-by-function rationale. **Its ~685 MB size figure is superseded by D-07;
  everything else stands.**
- `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md` — why the
  published archive does not reproduce §3, the nine §3 quantities and their exact
  `diagnostics.json` values, the release config's settings, and the sequencing diagram showing the
  archive is upstream of DATA-03 and Phase 22.

### Requirements and position
- `.planning/REQUIREMENTS.md` — DOCS-05 (line 77), DATA-01/01a/01b/02/03 (lines 87-91), and the
  traceability table (lines 435-440). Note DATA-01b maps to Phase 21 in the table even though the
  ROADMAP's Phase 21 entry omits it.
- `.planning/HANDOFF.json` — current position, the Phase 20 deferral rationale, the post-Zenodo
  repair batch this phase must NOT absorb, and the binding lessons.
- `.planning/ROADMAP.md` §"Phase 21" — success criteria, including 2a as a stated PUBLICATION
  BLOCKER.

### Manuscript
- `.planning/MANUSCRIPT-FINDINGS.md` — MF-09 is the edit map; read it before touching the paper.
  MF-12 is the `layout/line` conditioning hypothesis referenced by D-03.
- The live paper is in OneDrive: `OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/
  papers/aquacal/main.tex`. **`Desktop\main.pdf` is a stale export that contradicts it.**

### Code and data surfaces this phase touches
- `src/aquacal/datasets/loader.py` — `load_example(name)`; line 60 is the nested-layout resolution
  that gate 2 of D-15 checks.
- `src/aquacal/datasets/_manifest.py`, `src/aquacal/datasets/download.py` — manifest lookup and
  checksum-validated download; `download.py:151-171` reads `zenodo_record_id`, `zenodo_filename`,
  `checksum`.
- `src/aquacal/datasets/data/manifest.json` — currently record `18645385`, md5
  `c66380aaa8cbca6bc04a3157baacbee8`, 164,023,590 bytes. All three change under DATA-02.
- `docs/guide/configuration.md:97,109` and `docs/guide/refractive_geometry.md:117` —
  `shared_interface` already documented (D-04).
- `docs/guide/configuration.md:244-245` — the two one-line rows for `save_optimization_trace` /
  `save_conditioning` that D-03 expands.
- `experiments/results/benchmark.json` — the live schema instance to document under D-02
  (`schema_version`, `environment`, `solver_config`, `problem_shape`, `stages.*`, `memory`,
  `accuracy`).
- `experiments/e2_real_rig.py` — the archive's remaining consumer; defaults to
  `load_example("real-rig")`, gained a `--config` override in 19.2.
- `.pre-commit-config.yaml` — the `exclude: ^experiments/results/` on `check-added-large-files`
  that DATA-01b removes.

### On-disk assets (outside the repo)
- `C:\Users\tucke\Desktop\Aqua\AquaCal\raw_videos\{intrinsics,extrinsics}\*.avi` — 13 + 13 files,
  12 GB total (9.9 GB extrinsics, 1.7 GB intrinsics). The extraction source.
- `C:\Users\tucke\Desktop\Aqua\AquaCal\release_calibration\config.yaml` — the config that produced
  §3. Settings to match exactly: `refine_intrinsics: true`, `refine_auxiliary_intrinsics: true`,
  `frame_step: 30`, `max_calibration_frames: 200`, `holdout_fraction: 0.2`, `n_water: 1.333`,
  `initial_water_z: 1.0` for all 13 cameras, `robust_loss: huber`, `loss_scale: 1.0`.
- `C:\Users\tucke\Desktop\Aqua\AquaCal\release_calibration\diagnostics.json` — **the exact source
  of every §3 real-rig number.** The comparison target for D-15 gate 1.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`load_example(name)` is fully generic** (`loader.py:33-63`) — manifest lookup by name with a
  per-dataset `zenodo_filename`. Adding datasets is a manifest edit, not a code change. (This is
  what made the two-file option feasible; D-10 declined it anyway.)
- **`download_with_progress`** already validates `algorithm:hash` checksums and retries
  (`download.py:38-98`), so DATA-02's checksum requirement needs no new code — only correct values.
- **`experiments/e2_real_rig.py`'s `--config` override** (added 19.2) means both paths already
  exist: default `load_example` for a reader with no local videos, `--config` for the local run.
- **`ImageSet.iterate_frames` honours `step`** and files are `natsort`ed, so `frame_step` applies
  identically to image directories and to video — confirmed in the gate response. This is what
  makes `config_paper.yaml` at `frame_step: 1` over a pre-subsampled 262-frame dir equivalent to
  `frame_step: 30` over the video.

### Established patterns
- **`scripts/` does not exist.** D-11 creates it. Frame-reading code lives in `src/aquacal/io/`
  (`video.py`, `images.py`, `frameset.py`) and can be reused by the extractor.
- **Docs are Sphinx + nbsphinx** with `nbsphinx_execute = "never"`. `docs/guide/` holds 8 pages
  (1,795 lines total); `docs/tutorials/` holds 2 notebooks plus `index.md`. Both new pages need nav
  entries.
- **Package `__init__.py` rules** (`.claude/rules/source-code.md`) apply to any new public symbol —
  D-11 avoids this by keeping the extractor out of the package.

### Integration points
- `manifest.json` is the single seam between the published archive and every consumer. All three
  fields change together (DATA-02).
- The archive layout must satisfy `loader.py:60`'s nested-directory resolution
  (`<cache>/real-rig/...`), which today's `docs/tutorials/aquacal_data/real-rig/real-rig/` staging
  mirrors.
- Current staged archive for reference: `docs/tutorials/aquacal_data/real-rig/real-rig/` — 13
  camera dirs x 60 JPEG frames in `extrinsic/` (146 MB), 13 in `intrinsic/` (49 MB), `output/`
  (2.1 MB).

### Environment traps (verified this session)
- **Git Bash `python` is Anaconda base and cannot decode these AVIs** — `VideoCapture.read()`
  returned `None`. The **AquaCal conda env** reads them correctly. Any extraction or verification
  work must run in the AquaCal env (consistent with the existing pytest-env trap).
- Video probe results: extrinsic AVI `e3v829d` is 762 MB, **7,860 frames**, 1200x1600 colour.

</code_context>

<specifics>
## Specific Ideas

- **"Its a zenodo upload, so file size isnt that important"** — the user's reasoning for lossless
  (D-07). The tutorial download cost that this trades away subsequently evaporated entirely when
  D-17/D-18 removed the notebooks' dependence on the archive, so the trade turned out to be free.
- **"The CLI is the preferred entrypoint, so this is valuable in and of itself"** — the user's
  framing of the written CLI tutorial (D-05) as a net gain rather than a consolation for deleting
  the notebook's real-data path. The plan should treat it that way: it is a deliverable, not a
  migration.
- **The direction change is deliberate and should not be "corrected" back.** Halfway through, the
  user reconsidered the notebooks' purpose after learning `DATA_SOURCE = "zenodo"` was the
  committed default. Everything downstream (D-10's rationale, D-12's repurposing, D-15 gate 3's
  replacement) was re-audited against the pivot and is internally consistent as recorded.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 20 (Refractive Index Helper, INDEX-01..03)** — deferred 2026-08-07 on MF-13: across the
  full +/-0.010 assumed-index sweep, reconstruction MAE moves 0.0040 mm against a seed sd of
  0.0205 mm, ~5x below seed noise. `calc-index` documentation rides with it (D-01). Deferred, not
  dropped.
- **HANDOFF.json's post-Zenodo repair batch (8 items)** — the six seedless-legacy provenance FAILs,
  E1's water_z-pinned non-refractive baseline, widening `gate3_git_sha_consistency`, E4's empty
  guard count, E4's overwritten per-cell `benchmark.json`, MF-12's proposed signed/per-camera
  metrics, and E6's missing `gauge_correct_z`. **Explicitly out of scope here** — they were
  deferred so the whole suite can re-run on one sha after the Zenodo work.
- **MF-12's `layout/line` conditioning test** — run Phase 16's HOOK-03 diagnostic on a line-layout
  and a grid solve at the same seed and compare the camera-height / interface-distance correlation
  block. One calibration each, no new code. Not started; suggested for after Zenodo.
- **`aquacal extract-frames` as a public CLI subcommand** — considered and declined for this phase
  (D-11). Genuinely useful long-term; belongs in a phase that can afford the API-surface
  commitment, tests, and docs.
- **Automated notebook-staleness detection** (CI job or committed re-execution command) — declined
  in D-21. The underlying problem is real and unaddressed: nothing re-executes the notebooks, which
  is why they went six months stale.
- **CLEAN-01: retire the `initial_distances` compatibility shim in `pipeline.py`** — REQUIREMENTS
  line 356 notes it is unblocked by DATA-02 but is a breaking change for pre-v1.4 configs. Not this
  phase.

### Reviewed Todos (not folded)
- `2026-07-23-reduce-memory-and-cpu-load-during-calibration.md` (match 0.6) — performance work,
  unrelated to docs or the dataset.
- `2026-08-05-band-sidecar-competes-with-production-benchmark-record.md` (match 0.6) — experiments
  infrastructure; already tracked in HANDOFF.json's post-Zenodo batch.
- `2026-08-06-e5-band-tests-rerun-the-band-per-test.md` (match 0.6) — test-suite performance;
  already tracked in HANDOFF.json's post-Zenodo batch.

</deferred>

---

*Phase: 21-new-feature-documentation-dataset-refresh*
*Context gathered: 2026-08-10*
