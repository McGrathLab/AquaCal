---
phase: 26-full-suite-driver-handoff-readiness
plan: 06
subsystem: experiments
tags: [e2, config-generation, check-verdict, d-15, d-16, ruling-a4]
requires:
  - "experiments/_io.py: add_baseline_dir_argument, resolve_baseline_dir, compare_experiment_csv_if_present (plan 26-04)"
  - "src/aquacal/config/schema.py: internals.benchmark_memory, internals.log_all_observation_depths (unchanged)"
provides:
  - "experiments/e2_real_rig.py --emit-invocation-configs / --invocation-dir"
  - "E2_INVOCATION_VARIANTS: the declarative classification/timing/memory table"
  - "build_internals_variant_config, emit_invocation_configs, _fold_check_reports"
  - "e2_invocation_scope.json: sha256-stamped per-invocation attribution sidecar"
  - "experiments/e2_real_rig.py --baseline-dir with a DATA-01b N/A verdict"
affects:
  - "plan 26-07 (driver stages that invoke these configs)"
  - "the completeness gate (per-invocation output_dir attribution)"
tech-stack:
  added: []
  patterns:
    - "Text-to-text YAML transform (no safe_load/safe_dump round-trip) so 'only N lines changed' stays assertable"
    - "Missing-baseline guard lives in the caller, never in compare_experiment_csv"
key-files:
  created:
    - tests/unit/test_e2_invocation_configs.py
  modified:
    - experiments/e2_real_rig.py
decisions:
  - "Variant output dirs are derived as <invocation-dir>/e2_{name}, giving each invocation its own tree so every artifact is attributable (D-16)"
  - "Rewriting an internals key preserves its trailing inline comment: a generated production config's only review is a human diff"
metrics:
  duration: ~35 min
  completed: 2026-08-18
---

# Phase 26 Plan 06: E2 Invocation Configs and an Honest `--check` Summary

E2's classification, timing and memory runs are now generated as three distinct config
YAMLs from one release config — no variant sets both perturbing `internals` keys — and
E2's `--check` reads from `--baseline-dir`, reports N/A for a DATA-01b-gitignored
baseline instead of raising after a 50–87 minute calibration, and exits nonzero when
every baseline is absent.

## What Shipped

### Task 1 — `--emit-invocation-configs` (commit `64f0dc6`, tests `d1bc006`)

`build_internals_variant_config(source_text, output_dir, overrides)` is a pure
text-to-text transform, a sibling of the untouched `build_seed_variant_config`. It
rewrites `paths.output_dir` and replaces each `internals.<key>` in place when present,
inserts it at the end of the `internals:` block when absent, and creates the block at
end-of-file when there is none. Deliberately no `yaml.safe_load`/`safe_dump` round-trip:
that would destroy comments and reorder keys, which is exactly what makes the
"only `1 + len(overrides)` lines changed" assertion possible. `--smoke` cannot catch a
bad production YAML, so the human diff is the only review these configs get before a
48–87 minute run.

`emit_invocation_configs(source_path, target_dir)` writes, in order:

| Variant | `log_all_observation_depths` | `benchmark_memory` | output_dir |
|---|---|---|---|
| `config_e2_classification.yaml` | **true** | false | `<dir>/e2_classification` |
| `config_e2_timing.yaml` | false | false | `<dir>/e2_timing` |
| `config_e2_memory.yaml` | false | **true** | `<dir>/e2_memory` |

D-15 and D-16 are both structural here, not documentary: no variant sets both keys true,
and the timing run carries neither. Each variant writes its own `output_dir`, so the
completeness gate can attribute every E2 artifact to its owning invocation. The
`e2_invocation_scope.json` sidecar records the source config's `hashlib.sha256`, plus
each variant's filename, `internals` settings, output dir and purpose — reusing the band
generator's existing integrity-provenance mechanism rather than inventing one.

The release-tree write refusal (T-19.5-07-01) is preserved verbatim in spirit: a
`target_dir` that resolves to, or under, `source_path.parent` raises `ValueError`. Two
tests cover it (equal-to and nested-under).

CLI: `--emit-invocation-configs` and `--invocation-dir`, requiring `--config`, rejected
against `--check`, `--smoke`, `--force` and `--emit-band-configs` with a message naming
the offending pair. The help text states the operative reason (2.7–5.5% wall-clock cost,
~11 MB per-stage sidecar), and the module docstring records why the variants are
generated rather than committed: the release config's absolute Windows path would
otherwise be hard-coded three times and Phase 27 would have to edit each copy.

### Task 2 — `--baseline-dir` and the N/A verdict (same commit)

`_run_check` now resolves baselines under `resolve_baseline_dir(args.baseline_dir,
args.out)` and routes all three comparisons through 26-04's
`compare_experiment_csv_if_present`. Verdict folding moved into `_fold_check_reports`,
which is what the tests drive — no calibration is run anywhere in this plan's test suite.

- baseline present and matching → unchanged pass line, exit 0
- baseline present and differing → unchanged failure line, exit 1
- baseline absent → `N/A` line naming the file and the DATA-01b reason, not a failure
- **all three absent → exit 1 with an explicit `VACUOUS CHECK` message**

That last case is T-26-18: an all-N/A `--check` compared nothing, so it must never read
as a reproduction claim.

`_run_check`'s docstring now carries the honest contract that DRIVER-03's table must
inherit uncorrected: only `camera_parameters.csv` has a committed baseline;
`reprojection_residuals.csv` and `reconstruction_errors.csv` are gitignored by deliberate
DATA-01b policy (`.gitignore:238-239`) and ship only in the Zenodo archive. It also names
the better-anchored alternative — `check_e2_band` compares `real_rig_metrics.json`
numerically at `_E2_METRICS_RTOL = 1e-6` (`check_rerun_gates.py:1340`), which is a working
mechanism where this `--check` is, on two of three artifacts, not.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_e2_invocation_configs.py -q` | 28 passed |
| `pytest tests/unit/test_e2_split_band.py -q` (band regression) | 19 passed |
| `pytest tests/unit/test_expectations.py tests/unit/test_stale_provenance_strings.py -q` | 88 passed |
| `git diff experiments/_io.py` | empty — 26-04's helpers consumed, not altered |
| band generator removed/modified? | `git diff \| grep '^-' \| grep -c 'def emit_seed_variant_configs'` → 0 |
| `_run_check` guard count | `compare_experiment_csv_if_present(` × 3; zero bare `compare_experiment_csv(` |
| `--help` | lists `--emit-invocation-configs`, `--invocation-dir`, `--baseline-dir` and the four pre-existing extras |

No calibration, no E2 run, no full suite — every assertion is over text transforms,
argument parsing and report folding.

## Deviations from Plan

**1. [Rule 3 – Blocking] `%` in argparse help crashed `format_help()`**
- **Found during:** Task 1
- **Issue:** `argparse` runs help strings through `%`-formatting, so the literal
  "2.7-5.5% wall clock" raised `ValueError: unsupported format character 'w'` whenever
  `--help` was rendered.
- **Fix:** Escaped as `%%` in the `--emit-invocation-configs` help string only. The other
  two occurrences (module comment, sidecar `scope` text) are not argparse strings and
  stay literal.
- **Commit:** `64f0dc6`

**2. [Rule 2 – Missing critical functionality] Trailing inline comments were being dropped**
- **Found during:** Task 1
- **Issue:** Rewriting `benchmark_memory: false  # Opt-in: per-stage peak RSS` discarded
  the comment. For a config whose only pre-run review is a human diff, silently deleting
  the schema's own documentation is a real loss.
- **Fix:** The key rewrite now preserves any trailing `#` comment. Covered by
  `test_rewriting_a_key_preserves_its_trailing_inline_comment`.
- **Commit:** `64f0dc6`

**3. [Process] One implementation commit instead of two**
- Tasks 1 and 2 touch interleaved regions of a single file and were verified together.
  The RED test commit (`d1bc006`) is separate as TDD requires, but the two GREEN task
  implementations landed in one `feat` commit rather than two. No behavioural impact;
  noted so the commit-per-task expectation is not silently assumed met.

**4. [Scope] The plan's `1 + len(overrides)` assertion needed a precondition**
- The rule holds only when every override value actually *differs* from the source. The
  fixture's `log_all_observation_depths` was already `false`, so setting it to `false`
  changed zero lines. The test now uses two genuinely differing values and says so in a
  comment. This is a sharpening of the acceptance criterion, not a weakening: a no-op
  override producing a no-op line is the correct behaviour.

## Not Done (by design)

- **No driver changes.** Plan 26-07 owns the stages that invoke these configs. Nothing in
  `experiments/*.sh` was touched.
- **No manifest edit.** `files_modified` scopes this plan to `e2_real_rig.py` and its
  test; invocation attribution is carried by the distinct `output_dir` per variant plus
  `e2_invocation_scope.json`, which is what the gate reads. If 26-07 or the gate wants
  these registered in `experiments/suite_expectations.json`, that registration belongs to
  the plan that owns the manifest.
- **No `schema.py` / `pipeline.py` changes.** The `internals.*` keys already exist and
  work; this plan only generates configs that set them.

## Threat Register Outcomes

| Threat ID | Disposition | Evidence |
|---|---|---|
| T-26-17 | mitigated | `emit_invocation_configs` raises `ValueError` for a target inside/under the source dir; two tests |
| T-26-18 | mitigated | `_fold_check_reports` returns 1 with a `VACUOUS CHECK` message when all baselines are absent; test asserts it |
| T-26-19 | mitigated | Three variants; `test_no_variant_sets_both_internals_flags_true` asserts it over both the written files and `E2_INVOCATION_VARIANTS` |
| T-26-20 | mitigated | `e2_invocation_scope.json` records `hashlib.sha256` of the source config; test compares against a recomputed digest |
| T-26-SC | mitigated | No package installed; `pyproject.toml` untouched |

## Known Stubs

None.

## Self-Check: PASSED

- `experiments/e2_real_rig.py` — FOUND (modified)
- `tests/unit/test_e2_invocation_configs.py` — FOUND
- commit `d1bc006` — FOUND
- commit `64f0dc6` — FOUND
