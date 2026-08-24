---
created: 2026-08-20T00:00:00.000Z
title: E7's band carries the same benchmark-overwrite hazard E1's did, and phase 29.1 fixed only E1
area: experiments
files:
  - experiments/e7_interface_ablation.py
---

Filed 2026-08-24 by phase 29.1 plan 02, which fixed the identical defect at E1's site and
deliberately left E7's alone. **This todo exists so the asymmetry is discoverable from E7's
side**, not only from E1's comment.

> **`resolves_phase` removed 2026-08-24.** This todo was created BY phase 29.1 to record work
> that phase deliberately did NOT do, but carried `resolves_phase: 29.1` — which would have
> auto-closed it as resolved at phase completion, filing a live hazard as fixed. It is
> unscheduled on purpose: the fix touches `experiments/e7_interface_ablation.py`, which is
> inside the frozen `rerun-freeze-02` tag, so discharging it costs a re-freeze. Do not
> re-tag for it alone — fold it into the next re-freeze if one happens for another reason.
>
> **Measured 2026-08-24: the hazard does NOT fire in the production run.** `run_stage_e7_band`
> (`run_experiment_suite.sh:1522`) invokes e7 with `--seeds ... --out ...` and NO `--force`, so
> `force=False` reaches the call and `_io.py`'s resumability guard holds. The `--force` at
> `:1511` is the single-seed E7 stage, not the band. Latent, not live.
>
> **The file's closing question is answered: E5 is NOT affected.** `run_stage_e5_band` (`:1594`)
> does pass `--force`, but `e5_index_sensitivity.py` contains zero `write_direct_call_benchmark`
> calls — it has no benchmark record to overwrite.
>
> Residual risk: one manual `--force` band run at E7 fires it. Do not run E7's band by hand
> with `--force` against a populated tree.

## The hazard

`e7_interface_ablation.py`'s `_run_band` closes with a `write_direct_call_benchmark` call
(~:859-873) that passes `force=force` — the run's own `--force` — for
`e7_benchmark_<arm>.json`. Its docstring (~:778-781) says the opposite of what the call does:

> The `e{1,7}_benchmark_<arm>.json` records are seedless legacy records that band mode
> **must never overwrite**, so the seeds actually run have nowhere else to be recorded

The resumability guard in `write_direct_call_benchmark` (`_io.py:875-881`) is the *only* thing
honouring that policy today, and `--force` removes it. A forced band run silently republishes
every arm's record with `seeds[-1]`'s values. E7's band writes more arms than E1's two models,
so the blast radius is larger, not smaller.

Note E7's site does **not** carry E1's second defect: it prints nothing after the call, so
there is no false "Wrote" line to fix here. This is the write-policy half only.

## What E1 did (2026-08-24, phase 29.1 plan 02, D-06/D-07)

Resolved in favour of the comment, in the form that makes every reading true:

> Band mode may CREATE `e{N}_benchmark_<label>.json` when it is absent, and must NEVER
> overwrite one that exists — enforced at the call, not delegated to the resumability guard.

Concretely, at E1's site:

- the call passes the **literal** `force=False`, ignoring the run's `--force`, with a comment
  saying this is the one place `--force` is deliberately not honoured and why;
- the print is branched on the writer's return value — a write confirmation only on `True`, a
  distinct kept-existing line otherwise;
- `_run_band`'s docstring and the policy comment above the write were rewritten to state the
  enforced policy rather than an aspirational one.

Pinned by `tests/unit/test_e1_band_mode.py::TestBandBenchmarkWritePolicy`, whose
`test_force_band_run_leaves_existing_records_byte_identical` is the case that fails without
the literal.

## The asymmetry this leaves

Until this todo is discharged, E1 and E7's `--seeds` modes **do not behave the same way** under
`--force`, which breaks the "mirrors `e7_interface_ablation._run_band` exactly (D-19.4-14)"
symmetry both docstrings claim. E1's comment names the asymmetry and points here; this file
points back.

## Why E7 was out of scope

Phase 29.1 repairs the defects the 2026-08-20 production run surfaced. E7's band did not
surface one — the hazard is latent there, found by reading rather than by a failing gate — and
the phase's scope was fixed before it was found. Widening scope mid-phase to a file no gate
flagged is how a re-freeze slips.

## The fix

Apply E1's resolution verbatim at E7's site: literal `force=False` at the call, the same
comment stating the policy and the mechanism, the docstring corrected, and a
`TestBandBenchmarkWritePolicy`-shaped test in E7's band test module including the `--force`
byte-identity case. Then delete the asymmetry paragraph from E1's comment and close this todo.

Check `e5_index_sensitivity.py`'s band at the same time — it writes a band-owned degeneracy
sidecar and may carry the same call shape.
