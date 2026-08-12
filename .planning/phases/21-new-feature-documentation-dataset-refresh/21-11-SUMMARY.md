---
phase: 21-new-feature-documentation-dataset-refresh
plan: 11
status: complete
completed: 2026-08-11
requirements: [DATA-01b]
---

# 21-11: The three large E2 artifacts leave git — DATA-01b closed

Commit `e0ef765`. `calibration.json`, `reprojection_residuals.csv` and
`reconstruction_errors.csv` are out of version control, and the repo-wide
`check-added-large-files` guard is back with **no exclusion at all**.

Sequencing was the whole point of `depends_on: ["21-09"]`: the repository copies were the
only copies until record 21889922 went public. The `## Published` pre-condition was checked
before any `git rm` — `21-ARCHIVE-MANIFEST.md` carries a concrete `zenodo_record_id: 21889922`
and its **PUBLISHED 2026-08-11** block.

## Task 1 — repair the one live consumer, before removing its input

`experiments/reconstruction_bootstrap.py` read a hardcoded
`Path("experiments/results/reconstruction_errors.csv")`. It now calls
`resolve_reconstruction_errors_path(explicit: Path | None = None)` at call time
(`reconstruction_bootstrap.py:162`), with three-step precedence:

1. the new `--reconstruction-errors` flag — the escape hatch for a local run;
2. `experiments/results/reconstruction_errors.csv` if present, so a developer who has just
   re-run E2 uses the fresh file;
3. the published archive, `load_example("real-rig")/reference_outputs/reconstruction_errors.csv`.

If none resolves, `FileNotFoundError` names all three locations and states that the file now
ships inside the Zenodo archive under `reference_outputs/`.

**`load_example` is imported inside the resolver** (`reconstruction_bootstrap.py:197`), never
at module scope, so importing the module cannot trigger a multi-gigabyte download — T-21-11-03.
Every new resolver test monkeypatches it; no test touches the network.

Verified against the real downloaded archive: the fallback reads **7,762 rows across 52
frames**, matching the holdout shape that gate 1 established in 21-08.

## Task 2 — out of git, guard restored

| File | Fate |
|---|---|
| `experiments/results/calibration.json` | `git rm`, gitignored |
| `experiments/results/reprojection_residuals.csv` | `git rm`, gitignored |
| `experiments/results/reconstruction_errors.csv` | `git rm`, gitignored |
| `exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz` | untouched — already gitignored |

`.pre-commit-config.yaml` loses `exclude: ^experiments/results/` **and** the seven-line comment
above it justifying the bypass, which the removal made false. `args: ['--maxkb=1000']` is
unchanged, and the `detect-secrets` hook's unrelated `exclude` was not touched. No replacement
exclusion was added anywhere.

**Tracked content under `experiments/results/`: 4.45 MB -> 0.51 MB.** Re-measured now,
`git ls-files experiments/results | xargs stat -c%s` totals **534,011 B (0.51 MiB)** across
151 files. For the before figure, the equivalent git blob total at `e0ef765^` is
**4,511,773 B (4.30 MiB)**; the recorded 4.45 MB was the working-directory measurement, which
runs ~154 KB higher because CRLF checkout adds one byte per line to the removed
116,002-/23,029-/7,763-line files. Same removal, two measurement bases — the working-directory
figure is the one the commit message quotes.

## Task 3 — provenance repointed

`experiments/README.md` names the archive location for each relocated artifact and keeps
EXP-11's universal provenance claim true, with no DOI or record id duplicated outside
`manifest.json`:

| Artifact | README says |
|---|---|
| `reconstruction_errors.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `reprojection_residuals.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `calibration.json` | Archive `reference_outputs/` — **equivalent, not identical** |

It also shows the retrieval snippet (`load_example("real-rig").cache_path / "reference_outputs"`)
and the local regeneration command.

## Three things the plan did not anticipate

### 1. `calibration.json` is NOT byte-identical in the archive

The archive ships the **2026-08-10 image-source** run; the file removed from the repo was the
**2026-07-31 video-source** run. Both are library 1.8.0 and agree to **~1.5e-8 on `water_z`** —
that is precisely the video-vs-image equivalence MF-19's control established in 21-08, so the
divergence is the source medium, not a defect. The exact removed bytes remain retrievable from
git history at `25655f7`. `experiments/README.md` states the split explicitly under its
`calibration.json` caveat, so a reader who diffs the two files is not surprised.

The **two CSVs ARE byte-identical** to their archive copies, verified by md5 against the
downloaded archive *before* anything was deleted.

### 2. Two provenance registries had to move with the files

Neither is in the plan's `files_modified`. Both live in
`tests/unit/test_experiments_provenance.py`:

- `SELF_DESCRIBING_JSON` listed `calibration.json`;
- `CSV_TO_RECORD` mapped `reconstruction_errors.csv` and `reprojection_residuals.csv` to
  `experiments/results/benchmark.json`.

Both registries are computed **from the working directory**, not from git. A developer who ran
the suite locally still had the files on disk (they are gitignored, not deleted), so both
would have passed locally and failed only on a fresh clone or on CI. That is exactly the
failure mode that reaches other people first, and it was caught here rather than there. The
`SELF_DESCRIBING_JSON` entry was replaced with a `NOTE:` comment recording why
`calibration.json` left and where it went, so the omission reads as deliberate.

### 3. A test broken by 21-10 was fixed here

`tests/unit/test_datasets.py::test_manifest_loading` hardcoded
`zenodo_record_id == 18645385`. The full suite had completed before `25655f7` landed, so no
gate ever covered it. It now pins **record id, checksum and size together**
(`21889922` / `md5:dff1012fb772d627e0f3f106d5c6de84` / `4350418046`), with a comment saying to
bump all three deliberately on any new Zenodo version — silent drift there means
`load_example` fetches the wrong archive.

## Post-merge gate

The orchestrator's full unfiltered `pytest tests/` returned **1,817 passed, 25 skipped, 0
failed**. That figure is the orchestrator's, reported here as received; this summary did not
re-run the suite (1–2 hours) and cannot independently confirm it, and no log of the run was
found on disk.

Two later GitHub `Tests` runs did fail, both on Linux/CI-only preconditions unrelated to this
plan and both already fixed: float64 anchors compared with exact equality failing by 1–2 ULP
on the Linux runner (`eea0a83`), and a `psutil` peak-WSET assertion that assumed an optional
`[bench]` dependency CI does not install (`d27bda7`).

## Self-Check: PASSED

- `git ls-files` returns nothing for any of the three removed paths; all three are in
  `.gitignore` (lines 237–239) under a comment naming `reference_outputs`
- `grep 'exclude: \^experiments/results/' .pre-commit-config.yaml` returns nothing;
  `args: ['--maxkb=1000']` intact at line 17
- Tracked `experiments/results/` total is 534,011 B, under the 1,200,000 B bar
- `resolve_reconstruction_errors_path` exists at `reconstruction_bootstrap.py:162`;
  `load_example` is imported at line 197, inside the resolver
- The archive's `reference_outputs/reconstruction_errors.csv` reads 7,762 rows / 52 `frame_idx`
  values
- `experiments/README.md` contains `reference_outputs` and `load_example` and no `10.5281`
  or `zenodo.org/record` literal
