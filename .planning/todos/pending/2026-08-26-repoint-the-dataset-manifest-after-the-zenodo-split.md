---
created: 2026-08-26T00:00:00.000Z
title: Repoint the dataset manifest after the Zenodo split — `zenodo_record_id: 21889922` describes one record, and there are now two with different lifecycles
area: data
resolves_phase: 30
files:
  - src/aquacal/datasets/data/manifest.json
  - src/aquacal/datasets/download.py
  - src/aquacal/datasets/loader.py
  - tests/unit/test_datasets.py
  - tests/unit/test_stale_provenance_strings.py
---

## Requirement

**POST-01** (Phase 30) — *"§3, the Zenodo archive's `reference_outputs/`, and the tutorial's
expected-value table are re-cut as a matched set against the new E2 numbers."* The manifest pin is
the library-side half of that reconciliation.

## Problem

`src/aquacal/datasets/data/manifest.json` pins a **single** record:

```json
"real-rig": {
  "zenodo_record_id": 21889922,
  "zenodo_filename": "real-rig-calib.zip",
  "checksum": "md5:dff1012fb772d627e0f3f106d5c6de84",
  "size_bytes": 4350418046
}
```

`download.py:151-162` reads exactly `zenodo_record_id`, `zenodo_filename` and `checksum` and builds
**one** URL: `f"https://zenodo.org/records/{record_id}/files/{filename}"`.

RUN-05 split that archive into **two records with different lifecycles**:

| | Record A — inputs | Record B — results |
|---|---|---|
| Deposition | **22116461** (PUBLISHED) | **22117061** (staged, unpublished as of 2026-08-26) |
| Version DOI | `10.5281/zenodo.22116461` | not yet minted |
| Concept DOI | `10.5281/zenodo.22116460` | not yet minted |
| File | `real-rig-inputs.zip` | `real-rig-results-2.1.0.zip` |
| Size | `4341018405` | `9503394` |
| md5 | `d95a1abc3f7089443ea2bc7ea12fb599` | `f033538e1c9da165aa6267f4ae5d4f78` |
| Archive root | **FLAT** — `extrinsic/`, `intrinsic/`, `README.md` at the root | **FLAT** |
| Re-versioned | only if the capture changes | whenever results change |

`21889922` wraps everything in a top-level `real-rig/` directory, which is why extracting it into
`aquacal_data/real-rig/` yields the doubled `aquacal_data/real-rig/real-rig/`. **Neither new
archive has that wrapper**, so the extraction logic strips a different prefix — or none.

## `zenodo_record_id`'s blast radius — the ten sites, verbatim from `29-RESEARCH.md`

Filed rather than done precisely so that a later session does not have to re-grep.

| Site | What breaks |
|---|---|
| `src/aquacal/datasets/data/manifest.json` | describes **one** file; a split needs two entries and a compose step, or an explicit decision to leave the pin |
| `src/aquacal/datasets/download.py:126-180` | downloads and extracts **one** zip into `aquacal_data/<name>/` |
| `src/aquacal/datasets/loader.py:49-58, 90` | docstring asserting `reference_outputs/` ships in the `'real-rig'` archive; also resolves `reference_calibration.json` and looks for `config.yaml` rather than `config_paper.yaml` — a latent mismatch worth noting |
| `experiments/reconstruction_bootstrap.py:57, 181, 226, 365` | hard-codes `"reference_outputs/reconstruction_errors.csv"` — **inside the frozen tree** |
| `experiments/e2_real_rig.py:635, 1231, 1233` | help text and the no-`--config` reader's-default path naming the bundled record — **inside the frozen tree** |
| `experiments/suite_expectations.json:1641` | verification prose naming the record — **inside the frozen tree** |
| `experiments/FROZEN-ROWS.md:145, 263` | names the record as the source of `reconstruction_errors.csv` — **inside the frozen tree** |
| `tests/unit/test_datasets.py:577` | hard-coded equality on the record id |
| `tests/unit/test_stale_provenance_strings.py:120, 176` | asserts the literal record-id token is present |
| `.gitignore:226, 454` | comment prose naming the record |

**Four of the ten sites are inside the frozen `experiments/` tree.** Repointing them changes source
files at the tag the run was made from, which is a materially different act from committing that
run's output. **Nothing in Phase 29 needed the pin to move** — record `21889922` remains published,
valid and citable throughout, and Record B had no DOI at all until the author published it.

**The two `tests/` assertions are the cheap half and are the first things to change.**

## The shape the fix should take — promote, do not add alongside

This is Phase 29 plan 29-08's recorded `<assumption_delta_decision>` verdict, transferred here.

The genuine delta is a **pluralization**. A *dataset* is no longer one Zenodo record; it is an
**input record plus a results record**, and the results record is independently re-versioned. The
`zenodo_record_id` / `zenodo_filename` / `checksum` triple describes **one variant**, not the
identity.

**Promote** the dataset identity to a *set of records*, demoting `zenodo_record_id` to one variant's
detail. **Do not add a second id alongside a still-required first.** Adding alongside silently keeps
the singular assumption: a future third record — a second results version, say — could be stored but
never resolved as the default, and nothing would go red.

## Two `loader.py` findings that travel with this

1. **`loader.py:79-86`** resolves `reference_calibration.json` from the **same extracted directory
   as the frames**. After the split, `load_example('real-rig')` needs **both records fetched and
   merged** into one cache layout.
2. **`loader.py:90`** looks for a **`config.yaml`** that exists in **neither** archive — both ship
   `config_paper.yaml`. A **pre-existing silent no-op**, untouched by the split and no worse
   because of it.

## Suggested invariant test (not built in Phase 29)

Every dataset the manifest declares round-trips through `download_and_extract` into the cache layout
`loader.py` expects, **for every declared record** — a test that goes red the instant a second
record is bolted on without the loader learning to compose them.

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Open items handed
  forward*, item 5
- `.planning/phases/29-gate-verification-results-commit/29-RESEARCH.md` § *`_manifest.py` Blast
  Radius — scope, do not decide*
- `.planning/phases/29-gate-verification-results-commit/29-zenodo-record-a.txt` and
  `29-zenodo-record-b.txt` — both records' sizes, digests and archive roots
- `.planning/phases/29-gate-verification-results-commit/29-RECORD-COMPOSITION.md` — the payload
  ruling, whose carried-forward item 1 already records the fetch-and-merge consequence
