# Phase 29: Gate Verification & Results Commit - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 6 new + 1 modified (+1 read-only dependency)
**Analogs found:** 6 / 7 (one partial — no in-repo HTTP-upload analog exists)

---

## File Classification

| New/Modified File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|---------|------|-----------|----------------|---------------|
| `scripts/zenodo_upload.py` | new | utility / operational CLI | streaming file-I/O over request-response HTTP | `src/aquacal/datasets/download.py` (retry/checksum/stream idiom) + `scripts/extract_frames.py` (CLI shell) | role-match (composite; **no upload analog exists**) |
| `scripts/zenodo_metadata_a.json`, `scripts/zenodo_metadata_b.json` (or one `--metadata` file) | new | config | static data | `src/aquacal/datasets/data/manifest.json` | role-match |
| `.planning/phases/29-…/analyze_e2_control.py` | new | analysis script | file-I/O transform → evidence text | `.planning/phases/19.2-…/analyze_e7_spread.py` (shape) + RESEARCH § *The E2 same-seed control* (recipe) | role-match |
| `.planning/phases/29-…/analyze_e7_before_after.py` | new | analysis script | file-I/O transform → evidence text | `.planning/phases/19.2-…/analyze_e7_spread.py` | **exact** (same statistic, same metric, same pairings) |
| `29-gates-full.txt`, `29-e2-control.txt`, `29-e7-before-after.txt`, `29-zenodo-drafts.txt` | new | evidence artifacts | batch capture | `.planning/phases/28-…/freeze02-gates-full.txt` and siblings | **exact** |
| `tests/unit/test_experiments_provenance.py` | **modified** | test | CRUD over module-level constants + discovery helpers | the module's own existing idioms (self-analog) | **exact** |
| `tests/unit/_baseline_paths.py` | read-only | test helper | — | — | **no change expected** (see § *Do Not Touch*) |

> **Scope fence (D-29-08).** Nothing under `experiments/results*/`, `experiments/check_rerun_gates.py`,
> or anywhere else in the frozen `experiments/` tree is created or modified. That tree is
> read-only reference for every file above.

---

## Pattern Assignments

### `scripts/zenodo_upload.py` (utility / operational CLI, streaming HTTP)

**Primary analog:** `src/aquacal/datasets/download.py` — the only Zenodo code path in the repo.
**Secondary analog:** `scripts/extract_frames.py` — the established shape of a one-off
operational script in `scripts/` (unpackaged; `[tool.setuptools.packages.find] where = ["src"]`).

#### Imports pattern — copy from `src/aquacal/datasets/download.py:1-13`

```python
"""Dataset download and caching utilities."""

from __future__ import annotations

import hashlib
import shutil
import time
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm
```

Conventions to carry: module docstring first, `from __future__ import annotations`,
stdlib block → third-party block, `pathlib.Path` not `os.path`. `requests` and `tqdm` are
already runtime deps (`pyproject.toml:44-45`) — add nothing.

#### CLI shell — copy from `scripts/extract_frames.py:1-13, 39-48, 150-163, 245-246`

The module docstring doubles as the `argparse` description and states "not part of the public
API" plus a literal invocation line:

```python
"""Deterministic every-Nth-frame AVI -> lossless PNG frame extractor.

This is a data-prep utility, not part of the `aquacal` public API. …

Not intended to be imported. Run it directly:

    python scripts/extract_frames.py --video-dir raw_videos/extrinsics \\
        --out-dir staged/extrinsic --step 30
"""
```

```python
def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured `argparse.ArgumentParser` for this script.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video-dir", type=Path, required=True,
        help="Directory of *.avi files, one per camera.",
    )
```

```python
def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python scripts/extract_frames.py`.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]` via `argparse`).

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    …

if __name__ == "__main__":
    sys.exit(main())
```

Carry: `build_arg_parser()` split out from `main()`; `main(argv=None) -> int`;
`logging.basicConfig(level=logging.INFO, format="%(message)s")` set inside `main`, with a
module-level `logger = logging.getLogger(__name__)`; `sys.exit(main())` guard; error paths
`logger.error("ERROR: %s", …); return 1` rather than raising to the top; a final
`logger.info("TOTAL: …")` summary line. `download.py` uses bare `print()` — **prefer
`extract_frames.py`'s `logger`** for the new script, since it is a `scripts/` peer.

#### Retry + backoff — copy structurally from `src/aquacal/datasets/download.py:54-120`

```python
    for attempt in range(max_retries):
        try:
            # Download with streaming and progress bar
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            …
            temp_dest.replace(dest)
            return

        except (requests.RequestException, RuntimeError) as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"Download failed after {max_retries} attempts: {e}")
```

Load-bearing properties to preserve in the upload counterpart:
- `for attempt in range(max_retries)` with the whole transfer **inside** the `try`, so the file
  handle is **reopened on every attempt** (a consumed file object PUTs zero bytes — RESEARCH
  § *Failure modes*).
- `except (requests.RequestException, RuntimeError)` — the same two-type tuple, so a
  checksum-mismatch `RuntimeError` raised inside the body is itself retryable.
- `2**attempt` backoff with the attempt counter in the message.
- Terminal `raise RuntimeError(f"… after {max_retries} attempts: {e}")`.
- Invert the timeout: `download.py`'s `timeout=30` is right for a GET; the upload needs
  `timeout=(30, 3600)` and **never** `timeout=None`.

#### Checksum verification — copy from `src/aquacal/datasets/download.py:80-107`

```python
            if expected_checksum:
                # Parse algorithm:hash format
                if ":" not in expected_checksum:
                    raise ValueError(
                        f"Invalid checksum format: {expected_checksum}. "
                        "Expected format: 'algorithm:hash' (e.g., 'md5:abc123...')"
                    )

                algorithm, expected_hash = expected_checksum.split(":", 1)

                if algorithm == "md5":
                    hash_obj = hashlib.md5()
                elif algorithm == "sha256":
                    hash_obj = hashlib.sha256()
                else:
                    raise ValueError(f"Unsupported checksum algorithm: {algorithm}")

                with open(temp_dest, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hash_obj.update(chunk)

                actual_hash = hash_obj.hexdigest()
                if actual_hash != expected_hash:
                    temp_dest.unlink()  # Delete corrupted file
                    raise RuntimeError(
                        f"Checksum mismatch for {dest.name}. "
                        f"Expected: {expected_hash}, Got: {actual_hash}"
                    )
```

**This is the symmetry that makes the upload verification free:** the `"algorithm:hash"` string
this parser already understands is *exactly* the shape Zenodo returns in the bucket response's
`checksum` field (`"md5:2942bfab…"`). Reuse the parse-then-compare structure verbatim; the
chunked `iter(lambda: f.read(8192), b"")` digest loop transfers unchanged (widen the block to
`1 << 20` for a 4.35 GB file). Per RESEARCH § *Security Domain* V5, guard the response shape —
a missing `checksum` key must become a failed attempt, not a `KeyError` traceback.

#### Progress bar — copy from `src/aquacal/datasets/download.py:60-79`

```python
            total_size = int(response.headers.get("content-length", 0))
            temp_dest = dest.with_suffix(dest.suffix + ".tmp")

            with (
                open(temp_dest, "wb") as f,
                tqdm(
                    desc=dest.name,
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as progress_bar,
            ):
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
```

Carry the `tqdm(desc=…, unit="B", unit_scale=True, unit_divisor=1024)` kwargs exactly. For the
upload direction the bar must be driven from a **read-wrapped file object** (`data=fp` must stay
a file object so `requests` sets a real `Content-Length` — do not substitute a generator).

#### Metadata / manifest validation — copy from `src/aquacal/datasets/download.py:145-160`

```python
    record_id = dataset_info.get("zenodo_record_id")
    filename = dataset_info.get("zenodo_filename")
    checksum = dataset_info.get("checksum")

    if not record_id or not filename:
        raise ValueError(
            f"Dataset '{dataset_name}' is missing Zenodo metadata in manifest. "
            "Cannot download."
        )

    url = f"https://zenodo.org/records/{record_id}/files/{filename}"
```

The `.get()` + explicit `raise ValueError` with a named-subject message is the project's
required-field idiom. Apply it to the new script's metadata file (title, creators, license,
`upload_type`, `access_right`) **before** any network call, so a malformed metadata block fails
in the first second rather than after a 4-hour PUT.

#### Deliberate divergences from the analog (state these in the plan)

| Divergence | Reason |
|---|---|
| No `publish()` function at all | D-29-01 / RESEARCH Pitfall 6. Token is `deposit:write` only. |
| Token from `os.environ["ZENODO_TOKEN"]` / `ZENODO_SANDBOX_TOKEN`, never a CLI arg or file | D-29-07; CLI args leak via `ps` and shell history. |
| Required explicit `--sandbox` / `--base-url` with **no production default** | RESEARCH § *Known threat patterns* — "uploading to production while intending sandbox". |
| `logger` instead of `download.py`'s bare `print()` | `scripts/` peer convention (`extract_frames.py`). Scrub `Authorization` before logging any header dict or `requests` exception. |
| No `.tmp` staging path | `download.py`'s `.tmp` protects a local write; there is no local write here. Its role is taken by the md5 round-trip check. |

---

### `scripts/zenodo_metadata_a.json` / `_b.json` (config, static data)

**Analog:** `src/aquacal/datasets/data/manifest.json`

```json
{
  "version": "1.0",
  "datasets": {
    "real-rig": {
      "type": "real",
      "included": false,
      "zenodo_record_id": 21889922,
      "zenodo_filename": "real-rig-calib.zip",
      "checksum": "md5:dff1012fb772d627e0f3f106d5c6de84",
      "size_bytes": 4350418046,
      "description": "13-camera production rig (12 primary + 1 auxiliary fisheye) — download from Zenodo"
    }
  }
}
```

Conventions: flat JSON, snake_case keys, a top-level `"version"` string, checksums as
`"md5:<hex>"`, sizes as integer `size_bytes`, human-readable `description`. Keeping the Zenodo
deposition metadata as a data file (rather than a dict literal in the script) also lets the
author read and correct it before the draft is created — which is the D-29-02 review surface.

**Do not put the token in this file.** `detect-secrets` runs with `.secrets.baseline`.

---

### `analyze_e7_before_after.py` (analysis script, transform → evidence)

**Analog:** `.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py`
— an **exact** recipe match, and a **broken entry point**. Copy the statistic; replace the I/O.

#### Imports + constants — copy from `analyze_e7_spread.py:39-52`

```python
from __future__ import annotations

import sys
from math import comb
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/tucke/Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation")
METRIC = "camera_height_drift_mm"
PAIRS = [("shared_fixed", "percamera_fixed"), ("shared_refined", "percamera_refined")]
```

`METRIC` and `PAIRS` transfer **verbatim** — RESEARCH verified they reproduce the published
10/10, p = 0.00098. **`ROOT` must not transfer**: it is a hard-coded Windows path to a sweep
directory that no longer exists (and `load()` globs `seed_*/interface_ablation.csv`, a layout
that no longer exists either). Replace with the two-tree comparison the phase needs:

```python
BEFORE = Path("experiments/pre_rerun_baseline/results/interface_ablation_band.csv")
AFTER = Path("experiments/results/interface_ablation_band.csv")
```

— `interface_ablation_band.csv` already carries `arm`, `seed` and `camera_height_drift_mm`
directly (480 rows = 4 arms × 10 seeds × 12 cameras), so `load()`'s per-seed concat disappears
into a single `pd.read_csv`.

#### The core statistic — copy VERBATIM from `analyze_e7_spread.py:68-101`

```python
    per = (
        df.assign(a=df[METRIC].abs())
        .groupby(["arm", "seed"])["a"]
        .mean()
        .unstack("seed")
    )
    seeds = sorted(per.columns)
    n = len(seeds)
    …
    for shared, percam in PAIRS:
        if shared not in per.index or percam not in per.index:
            print(f"  {shared} / {percam}: arm missing, skipped")
            continue
        diff = per.loc[percam] - per.loc[shared]  # >0 means shared is better
        n_pos = int((diff > 0).sum())
        crosses = bool(diff.min() < 0 < diff.max())
        p_one = sum(comb(n, k) for k in range(n_pos, n + 1)) / 2**n
        r = per.loc[shared].corr(per.loc[percam])
```

Do not substitute `scipy.stats.binomtest` or a two-sided p — the analog's own docstring records
that one/two-sided was conflated once already, and the one-tailed form is what reproduces the
published number.

#### Reporting shape — copy from `analyze_e7_spread.py:102-116`

```python
        print(f"  {shared} vs {percam}")
        for s in seeds:
            print(
                f"     seed {s}: percamera {per.loc[percam, s]:8.4f}  "
                f"shared {per.loc[shared, s]:8.4f}  diff {diff[s]:+8.4f}"
            )
        print(f"     shared better in {n_pos}/{n} seeds; diff crosses zero: {crosses}")
        print(
            f"     paired diff: mean {diff.mean():+.4f}  "
            f"range [{diff.min():+.4f}, {diff.max():+.4f}]"
        )
        print(f"     exact sign test (one-tailed): p = {p_one:.4f}")
        print(f"     between-arm correlation across seeds: r = {r:+.4f}")
```

Carry: plain `print()` to stdout (the caller redirects into the evidence file), numbered
`=== (n) … ===` section banners, an explicit `=== VERDICT ===` block, and a closing `CAVEAT:`
paragraph. **The analog's `CAVEAT` is hard-wired to `n = 5`** — the new script must derive `n`
from the data (`n = len(per.columns)`, which is 10 here) or drop the sentence. The analog's
`f"seeds present: {seeds}  ({n} of 5)"` line has the same defect.

**Must report both pairings and both trees** (D-29-16, RESEARCH § *The result* table).

#### Entry point — copy from `analyze_e7_spread.py:66, 148-152`

```python
def main() -> int:
    …
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(Note `raise SystemExit(main())` here vs `sys.exit(main())` in `scripts/extract_frames.py` —
both are in-repo; match the analog you are sitting beside.)

---

### `analyze_e2_control.py` (analysis script, transform → evidence)

**Structural analog:** `analyze_e7_spread.py` (same shell: module docstring stating the
criterion and why the obvious test is wrong, module-level path constants, `main() -> int`,
`print()` to stdout, `raise SystemExit(main())`).
**Recipe:** RESEARCH.md § *Code Examples* → *The E2 same-seed control*.
**Path-resolution analog:** `.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py:1-11`

```python
"""Scratch: enumerate exactly which E4 columns mismatch under --check. Read-only."""

from pathlib import Path

import pandas as pd

out_dir = Path("experiments/results")
committed = pd.read_csv(out_dir / "benchmark_grid.csv")
```

The established idiom for a one-off analysis script is **repo-relative path constants at module
level plus a documented cwd**, not `_baseline_paths.resolve_results_dir()`. Use it here
deliberately: `resolve_results_dir()` *switches subject* based on whether the live tree holds a
file, and this script must name its two trees explicitly — RESEARCH's guardrail *"name the
baseline file, not 'the pre-run numbers'"*, since `pre_rigrun_baseline/` and
`freeze01_run_output/` give different (and differently-meaningful) answers.

Recipe to carry (RESEARCH § *Code Examples*):

```python
BEFORE = "experiments/pre_rerun_baseline/results/real_rig_metrics.json"
AFTER  = "experiments/results/real_rig_metrics.json"
SEED   = 42  # printed in the output; the band spans 0.761->0.910 px across seeds

for k in sorted(set(a) | set(b)):
    if k == "provenance":
        continue
    va, vb = a.get(k), b.get(k)
    if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
        rel = abs(vb - va) / abs(va) if va else float("nan")
        print(f"seed {SEED} vs seed {SEED}  {k:36s} {va!r:>24} -> {vb!r:>24}  rel={rel:.3e}")
```

**Non-negotiable output properties** (RESEARCH Pitfall 2 / D-29-10 stop-list item 1): every line
prints `seed 42 vs seed 42`; the seed is read from the sibling `benchmark.json`'s
`solver_config["seed"]` and asserted equal on both sides rather than assumed; both baselines are
reported and labelled (`pre_rerun_baseline` → ~2.5e-08 max, `freeze01_run_output` → exactly 0,
byte-identical); the script exits non-zero if max relative drift ≥ 1e-6.

**Where these two scripts live** — planner's call, two in-repo precedents:
`.planning/phases/29-…/` (matches `analyze_e7_spread.py`, keeps script beside its evidence file,
never ships) or `scripts/` (matches `extract_frames.py`, is `ruff`-covered either way). The phase
directory is the closer analog for a one-off evidence producer.

---

### Evidence artifacts (`29-*.txt`)

**Analog:** `.planning/phases/28-full-suite-production-run/freeze02-gates-full.txt` and its
15 siblings (`freeze02-rollup.txt`, `freeze02-env.txt`, `freeze02-archive-manifest.txt`,
`freeze02-stage-timing.txt`, …), each sitting beside its `freeze01-*` counterpart so the two
attempts compare line for line.

Pattern: a flat, kebab-cased, **per-attempt-prefixed** `.txt` in the phase directory, produced by
redirecting a tool's stdout, never hand-edited. Phase 29's prefix is the phase number
(RESEARCH § *Project Constraints*: `29-*.txt` / `29-*.md`):

```bash
python experiments/check_rerun_gates.py experiments/results --profile full \
  > .planning/phases/29-gate-verification-results-commit/29-gates-full.txt
# expect: TOTAL: 176 PASS, 7 N/A, 0 FAIL   and   0 lines matching '^\[FAIL'
```

Set: `29-gates-full.txt`, `29-e2-control.txt`, `29-e7-before-after.txt`,
`29-zenodo-drafts.txt` (draft `id` + `links.html` + the bucket response JSON — the round-trip
proof and the only repo-side handle on the service-side drafts).

---

### `tests/unit/test_experiments_provenance.py` (test — MODIFIED, 8 assertion repairs)

**Analog: the module itself.** D-29-13 requires repairs that match this file's own conventions.
Four distinct idioms cover all eight failures.

#### Idiom A — a carve-out is a named `frozenset` with a dated, reasoned comment block

Copy the shape of `SELF_DESCRIBING_JSON` (`:78-99`):

```python
SELF_DESCRIBING_JSON = frozenset(
    {
        # real_rig_metrics.json: E2's own schema, carries a `provenance` dict
        # naming exactly how each field was derived from the pipeline run
        # that also wrote the sibling benchmark.json (same directory, same
        # run) -- that sibling file is this one's provenance record.
        "real_rig_metrics.json",
        # interface_ablation_conditioning.json: E7's conditioning report
        # (`per_arm` singular-value/correlation data), covered by the four
        # e7_benchmark_*.json records produced by the same E7 run.
        "interface_ablation_conditioning.json",
        # NOTE: calibration.json was removed from this set by DATA-01b (plan
        # 21-11). …
    }
)
```

Every member carries a per-member comment naming **which record covers it**, and removals are
kept as `# NOTE:` tombstones rather than deleted. `SEEDLESS_LEGACY_RECORDS` (`:101-134`) goes
further, carrying a `# CORRECTED 2026-08-18 (plan 26-13).` block that annotates rather than
rewrites the superseded rationale — the project-wide "annotate, never rewrite" pattern.

**Applies to failures #1, #2** (a `run_manifest.json` carve-out beside `SELF_DESCRIBING_JSON`,
commented with `experiments/_run_manifest.py:82` as its schema owner — it is DRIVER-02's
suite-level manifest, flat, with no `environment` block and no `solver_config`) and **#8a** (the
five new DEGEN-01/DEGEN-02 breakdown JSONs, each with the record that covers it).

#### Idiom B — `CSV_TO_RECORD` entries are parenthesised multi-line strings naming a real file

Copy from `:136-176`:

```python
CSV_TO_RECORD: dict[str, str] = {
    "benchmark_grid.csv": (
        "experiments/results/e4_cells/*/benchmark.json (nine per-cell records) "
        "for the nine synthetic rows, plus experiments/results/benchmark.json "
        "(E2's pipeline record) for the real_rig_13cam_200fr row; also carries "
        "its own seed column"
    ),
    "camera_parameters.csv": "experiments/results/benchmark.json (E2, same run)",
    …
    "exp1_band.csv": (
        "experiments/results/e1_seed_band_provenance.json (the band-owned "
        "sidecar, quick task 260807-dcv), which records solver_config['seeds'] "
        "matching this CSV's own seed column across seeds 42-51; …"
    ),
```

Conventions: value is a full repo-relative path plus prose naming the plan/quick-task that
introduced it; short values stay one-line, long ones use implicit concatenation inside parens
(88-col ruff limit); **a band entry embeds its seed span verbatim as `seeds A-B`**, because
`test_multi_seed_band_declares_its_seed_coverage` matches that literal substring against
`_seed_span()` computed from the data.

**Applies to failures #3, #4** (new `generalization_sweep_per_camera.csv` →
`experiments/results/e6_provenance.json`; `generalization_sweep_per_camera_band.csv` →
`e6_seed_band_provenance.json` **and must contain the literal `seeds 42-47`**, else #7 fails in
its place) and **#5, #6** (`exp1_band.csv` / `exp1_parameter_band.csv`: `seeds 42-51` →
`seeds 42-45`, per Ruling A1 of 2026-08-15, which cut E1's band from ten seeds to four — annotate
the change in the entry's prose in the `# CORRECTED <date> (plan …)` style).

#### Idiom C — the discovery-helper asymmetry (failure #8b)

`_discover_csv_files()` filters through `_is_tracked()`; `_discover_json_files()` does not:

```python
def _discover_json_files() -> list[pathlib.Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.rglob("*.json"))          # <-- no _is_tracked filter


def _discover_csv_files() -> list[pathlib.Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(p for p in RESULTS_DIR.glob("*.csv") if _is_tracked(p))
```

The fix is to make the JSON helper match its CSV sibling. `_is_tracked()` (`:313-339`) already
carries the full rationale in its docstring — *"The CSV suite documents its scope as files
'committed under experiments/results/', but discovers them by globbing the working tree. Those
two sets diverge whenever an experiment writes an output that is deliberately excluded…"* — which
applies word for word to the gitignored 2.1 MB `calibration.json` that is producing failure #8.
Extend that docstring with the JSON case rather than writing a new one.

Note the second, deliberate difference: `rglob` (JSON, to reach `e4_cells/<cell>/benchmark.json`)
vs `glob` (CSV, top level only). **Preserve `rglob`;** change only the filter.

Per RESEARCH Pitfall 5: **do not** paper over #8 by adding `calibration.json` to
`SELF_DESCRIBING_JSON` — it is not committed, so it has no business in a committed-artifact
carve-out.

#### Idiom D — assertion messages name the file and prescribe the fix

```python
        assert path.name in CSV_TO_RECORD, (
            f"{path.name} is committed under experiments/results/ but has no "
            "entry in CSV_TO_RECORD -- add one naming the provenance record "
            "that covers it (T-19.2-50)."
        )
```

```python
        assert seed is not None, (
            f"{path} carries schema_version but no solver_config['seed'], and is "
            "not in SEEDLESS_LEGACY_RECORDS -- either stamp a seed at write time "
            "or add it to the carve-out with a reason."
        )
```

Every message: the offending filename, what is wrong, the two available remedies, and a
requirement/task id in parens. Any new assertion added during the repairs matches this shape.
Skips likewise name their subject — `pytest.skip(f"{path.name} carries no seed column")`.

#### Verification command (from RESEARCH § *Validation Architecture*)

```bash
python -m pytest tests/unit/test_experiments_provenance.py -q   # ~23 s; 8 failed -> 0 failed
```

Full-suite expectation: **11 failed before the repairs, exactly 3 after** (D4's ruled anchors).

---

## Shared Patterns

### Path anchoring — repo root from the file's own location

**Source:** `tests/unit/test_experiments_provenance.py:31-35` (and identically
`tests/unit/_baseline_paths.py:70`)
**Apply to:** any new file that resolves a repo path from inside `tests/`

```python
# Anchored to the repository root via this file's own location, not the
# process working directory -- a gate that resolves relative to cwd can
# vanish from a run silently just because pytest was invoked from elsewhere
# (WR-06). tests/unit/test_experiments_provenance.py -> parents[2] == repo root.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
```

One-off analysis scripts use the looser cwd-relative form instead
(`e4_check_detail.py`, `analyze_e7_spread.py`) — see the E2 section above.

### Retry + verified round trip

**Source:** `src/aquacal/datasets/download.py:54-120`
**Apply to:** `scripts/zenodo_upload.py`
Reopen-per-attempt, `2**attempt` backoff, `except (requests.RequestException, RuntimeError)`,
terminal `RuntimeError(f"… after {max_retries} attempts")`, `"algorithm:hash"` checksum compare.

### Comment-as-decision-record

**Source:** `tests/unit/_baseline_paths.py:1-64` (a 64-line module docstring recording *why*
`ARCHIVE` still names the older tree), `test_experiments_provenance.py:37-52` and `:101-134`
**Apply to:** every file this phase creates or modifies
The project encodes rulings as dated, plan-numbered comments at the constant they govern
(`# CORRECTED 2026-08-18 (plan 26-13).`, `# Plan 26-14: resolved, not hardcoded.`,
`# ⚠ Phase 30 / POST-03 PURGES the archive.`). Repairs annotate the superseded rationale rather
than deleting it, and forward hazards get a `⚠` line naming the phase that must decide.

### Ruff surface

**Source:** `pyproject.toml:94-110` — `line-length = 88`, `target-version = "py311"`,
select `E4,E7,E9,F,W,I`, `quote-style = "double"`
**Apply to:** all new `.py` files. Implicit string concatenation inside parens is the
established way to stay under 88 columns (see `CSV_TO_RECORD`). Import order must satisfy `I`:
`__future__` → stdlib → third-party → first-party.

### Google-style docstrings with `Args:` / `Returns:` / `Raises:`

**Source:** `src/aquacal/datasets/download.py:35-51`, `scripts/extract_frames.py:39-44, 150-157`
**Apply to:** every new public function in `scripts/`

```python
    """Download a file with progress bar and checksum validation.

    Args:
        url: URL to download from
        dest: Destination file path
        expected_checksum: Expected checksum in format "algorithm:hash"
            (e.g., "md5:abc123..." or "sha256:def456...")
        max_retries: Maximum number of retry attempts on failure

    Raises:
        RuntimeError: If download fails after max retries or checksum mismatch
    """
```

---

## Do Not Touch

| File / tree | Why |
|---|---|
| `experiments/results*/` (all six trees), `experiments/run_experiment_suite_state.*` | D-29-08 — the run's outputs are immutable. Copied and committed byte-for-byte; never edited. |
| `experiments/check_rerun_gates.py` | Inside the frozen tree; grading re-invokes it unchanged (D-29-11, CONTEXT § Canonical References). |
| `experiments/_run_manifest.py`, `suite_expectations.json`, `FROZEN-ROWS.md`, `e2_real_rig.py`, `reconstruction_bootstrap.py` | Inside the frozen tree. The `_manifest.py` repoint touches four of these — RESEARCH recommends it as Phase 30 / POST-01 work. |
| `tests/unit/_baseline_paths.py` | **No change expected.** `resolve_results_dir()` already flips from `archive` to `live` by itself the moment the tree is populated — that is the module's whole design. Read its docstring before touching any provenance test (CONTEXT § Canonical References); a change here would be a silent subject switch. |
| `src/aquacal/datasets/data/manifest.json`, `download.py`, `loader.py` | The Zenodo pin repoint is deferred/flagged, not this phase's (CONTEXT § Deferred Ideas; RESEARCH § *`_manifest.py` Blast Radius*). |
| `.pre-commit-config.yaml`, `.gitignore` | D-29-17: no ignore-rule changes during this phase. Hooks stay uninstalled (RESEARCH § *The Byte-Integrity Hazard*). |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/zenodo_upload.py` — the **HTTP-write half** | utility | streaming upload | No authenticated write to any HTTP API exists anywhere in the repo. `download.py` supplies the retry/checksum/progress *structure* but is read-only, unauthenticated and public-URL. For the request shapes themselves (draft `POST`, bucket `PUT`, metadata `PUT`, `related_identifiers` vocabulary, `deposit:write` scope), the planner must use **RESEARCH.md § *Zenodo REST API* and § *Code Examples* → *Zenodo draft + bucket upload***, which carries a verified, in-house-idiom-matched reference implementation. Do not adopt a third-party Zenodo client (RESEARCH § *Package Legitimacy Audit*). |

---

## Metadata

**Analog search scope:** `src/aquacal/datasets/`, `scripts/`, `experiments/` (read-only),
`tests/unit/`, `.planning/phases/*/`, `.planning/probes/*/`
**Files read this session:** `src/aquacal/datasets/download.py` (full),
`scripts/extract_frames.py` (:1-60, :150-246),
`.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py` (full),
`tests/unit/_baseline_paths.py` (full),
`tests/unit/test_experiments_provenance.py` (:1-60, :78-180, :280-420, :465-485, :623-700, :739-784,
plus a class/def index), `.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py` (:1-30)
**Pattern extraction date:** 2026-08-26
