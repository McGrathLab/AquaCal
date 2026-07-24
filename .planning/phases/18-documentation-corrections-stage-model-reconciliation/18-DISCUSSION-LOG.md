# Phase 18: Documentation Corrections & Stage-Model Reconciliation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-24
**Phase:** 18-documentation-corrections-stage-model-reconciliation
**Mode:** `--auto` — no questions were put to the user. Every area below was resolved to
the recommended option and logged for audit.
**Areas discussed:** Stage-rename depth, Ex-Stage-4 vocabulary, Pose-graph figure
strategy, Config-reference home, Sweep blast radius, Drift-proofing the DOCS-01 numbers

---

## Stage-rename depth (DOCS-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Full reconciliation now | Prose, console, docstrings, timing keys, `internals/` filenames and JSON stage tags all move to three-stage vocabulary while Phases 16–17 sit unreleased | ✓ |
| Human-facing only | Fix prose and console output; leave `timings["stage4_*"]` and stage-tagged artifacts as-is | |
| Rename with compat aliases | New keys plus old-key aliases retained for a release | |

`[auto]` Stage-rename depth — Q: "How deep does the three-stage rename cut?" → Selected:
"Full reconciliation now" (recommended default)

**Notes:** DOCS-06's requirement text explicitly names timing keys and `benchmark.json`
keys, so the machine-surface rename is the requirement, not an interpretation of it.
REQUIREMENTS.md constraint 1 exists precisely because settling the schema *after* the WP5
experiment grid runs would force a re-run. Nothing outside the repo consumes these keys
yet (unreleased on local `main`), so compat aliases would create a second vocabulary to
maintain for no external benefit. Extending the rename to `internals/` filenames goes one
step past the literal requirement list and is flagged as such in CONTEXT.md D-02.

---

## Ex-Stage-4 vocabulary (DOCS-06)

| Option | Description | Selected |
|--------|-------------|----------|
| "Stage 3's optional intrinsic pass" / key `stage3_intrinsic_pass` | The worklist's own wording (`aquacal-post-review-milestone.md:52`) | ✓ |
| "Stage 3b" / key `stage3b` | Compact, preserves ordinal feel | |
| "Stage 3 (intrinsics mode)" / key `stage3_intrinsics_mode` | Emphasises "mode of Stage 3" phrasing from the worklist | |

`[auto]` Ex-Stage-4 vocabulary — Q: "What replaces 'Stage 4' in prose and keys?" →
Selected: "Stage 3's optional intrinsic pass / `stage3_intrinsic_pass`" (recommended
default)

**Notes:** Chosen because it is already the language the paper-side worklist uses, which
minimises the chance of introducing a *new* docs/paper divergence while closing the old
one. "Stage 3b" was rejected as reintroducing an ordinal that implies a separate stage.
⚠ Flagged in CONTEXT.md D-07: the manuscript is not in this repo and its stage labels were
not quoted verbatim in the worklist, so the naming needs confirming against the paper
before the rename lands.

---

## Pose-graph figure strategy (DOCS-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Port the supplement's generator | Bring the paper supplement's multi-panel generator into `docs/_static/scripts/`, regenerate, rename output to `pose_graph.png` | ✓ |
| Write a fresh in-repo generator | New script replaying `estimate_extrinsics`'s heap directly | |
| Minimal patch of the existing figure | Recolour the redundant edge grey, flip three arrows, retitle | |

`[auto]` Pose-graph figure strategy — Q: "How is `bfs_pose_graph.png` replaced?" →
Selected: "Port the supplement's generator" (recommended default)

**Notes:** Both REQUIREMENTS.md (DOCS-03) and the fixes doc §2.6 call out that the
supplement's generator *replays the library's own heap logic*, so the figure cannot drift
from the code — that non-drift property, not the artwork, is why reuse beats redrawing.
Minimal patching was rejected: it leaves a hand-maintained PNG that can silently go stale
again. Option 2 is recorded as the explicit fallback if the supplement generator is not
available from the user, held to the same non-drift standard.

---

## Config-reference home (DOCS-04)

| Option | Description | Selected |
|--------|-------------|----------|
| New `docs/guide/configuration.md` | Dedicated reference page, linked from the guide index; troubleshooting cross-links into it | ✓ |
| Extend `docs/guide/cli.md` | Grow the existing config section of the CLI page | |
| Rely on autodoc | Improve `CalibrationConfig` docstrings and let `docs/api/config.rst` carry it | |

`[auto]` Config-reference home — Q: "Where do the v1.7–v1.8 config features get
documented?" → Selected: "New `docs/guide/configuration.md`" (recommended default)

**Notes:** There is no configuration reference today — material is split between `cli.md`
and autodoc'd `config.rst`, neither of which a user browses for "what keys exist".
Phase 21's DOCS-05 adds four more documented surfaces on top of these, so a page that can
absorb them is worth creating now rather than growing `cli.md` a second time. Autodoc
alone was rejected: it lists fields but cannot carry the "when would I use this" framing
DOCS-04 is asking for.

---

## Sweep blast radius

| Option | Description | Selected |
|--------|-------------|----------|
| `src/` + `docs/` + `README.md`; `.planning/` and `CHANGELOG.md` untouched | Grep-and-verify over shipped surfaces; historical records preserved as written | ✓ |
| Enumerated line numbers only | Edit exactly the sites listed in the fixes doc | |
| Everything including `.planning/` and `CHANGELOG.md` | Total consistency across the repo | |

`[auto]` Sweep blast radius — Q: "Which trees do the terminology sweeps cover?" →
Selected: "`src/` + `docs/` + `README.md`, historical records untouched" (recommended
default)

**Notes:** The fixes doc's line numbers are a floor, not a ceiling — they were captured
before Phases 16–17 landed and have moved. Rewriting `.planning/` and `CHANGELOG.md`
would contradict the convention already set during the McGrathLab org move, where in-repo
URLs were updated but those two were deliberately left as historical records. Separately
noted in CONTEXT.md D-19: `CLAUDE.md` carries the four-stage description and should be
corrected, but it is gitignored (`.gitignore:216`) so the edit is local-only and
uncommittable.

---

## Drift-proofing the DOCS-01 numbers

| Option | Description | Selected |
|--------|-------------|----------|
| Test-asserted | A test derives group count and P live from the shipped grouping path and asserts the documented values | ✓ |
| Hand-written with a source comment | Write the corrected numbers and cite how they were derived | |
| Hand-written only | Just correct the prose | |

`[auto]` Drift-proofing the DOCS-01 numbers — Q: "How are the corrected numbers kept from
rotting?" → Selected: "Test-asserted" (recommended default)

**Notes:** The wrong "~12×" claim survived because nothing tied the prose to the code —
and the fixes doc traces its lineage back to the dissertation's `appendix-a.tex`, so it
has already propagated once. A test closes that loop. ⚠ Flagged in CONTEXT.md D-21: the
fixes doc's measurements used `scipy.optimize._numdiff.group_columns`, which quick task 3
(`3c8685c`) replaced with `build_structural_column_groups`; Phase 17's notes indicate the
counts still land at 13 / 17-with-intrinsics, but the planner must verify against the
shipped path rather than inherit the figures.

---

## Claude's Discretion

- Exact prose wording of every replacement string (the fixes doc's suggestions are a
  strong starting point, not a mandate).
- Internal organisation of the new `docs/guide/configuration.md`, and how much it
  duplicates vs. cross-links `docs/api/config.rst`.
- Plan decomposition — one plan or several across the rename, the terminology sweep, and
  the new config page.
- Where the DOCS-01 assertion test lives.
- Whether the corrected pose-graph figure keeps the multi-panel layout.

## Deferred Ideas

- `extrinsics.py:602` `sorted()` consistency nit (fixes doc §1.4) — declined; cosmetic,
  no behavioral effect, and this phase is documentation-only.
- Documenting what this milestone adds (`calc-index`, `benchmark.json` schema,
  trace/conditioning flags, full `shared_interface` write-up) → Phase 21, DOCS-05.
- Notebook re-execution and the stale "Stage 4 RMS" narration → Phase 21, DATA-03.
- The dissertation's `appendix-a.tex` carrying the same wrong grouping claim — outside
  this repo, flagged for the user.

## Todo Cross-Reference — auto-fold overridden

`--auto` folds todos scoring ≥ 0.4. Both matches were **reviewed and declined** instead,
because folding either would violate a locked sequencing decision:

| Todo | Score | Disposition |
|---|---|---|
| Upload new Zenodo dataset with image-based inputs | 0.90 | Declined — STATE.md: "Now Phase 21 (DATA-01/02/03) — do not action standalone" |
| Reduce memory and CPU load during calibration | 0.40 | Declined — PROJECT.md: v1.9 measures but deliberately does not reduce the peak; PERF-01 in REQUIREMENTS.md Future |

Both matched on generic keywords (`docs`/`config`/`json`, `refinement`/`stage`) rather
than on phase content.
