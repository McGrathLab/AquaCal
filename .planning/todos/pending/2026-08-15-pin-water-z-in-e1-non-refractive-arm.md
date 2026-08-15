---
created: 2026-08-15T00:00:00.000Z
title: Pin water_z in E1's non-refractive arm, where it is an exact null direction — this drives the arm's 14,949 degenerate observations to zero
area: experiments
resolves_phase: 23
files:
  - experiments/e1_refractive_comparison.py
  - src/aquacal/datasets/pipelines.py
  - .planning/HANDOFF.json
---

## Problem

E1's non-refractive arm (`n_water = 1.0`) reports **14,949** degenerate observations — every
observation in the arm. It is the only non-zero count in any committed synthetic artifact, it is
what makes the response letter's "zero out-of-domain observations" claim false (audit F-003
defect 1), and it is pure bookkeeping.

At unit index the refractive projector **is** the pinhole projector (pinned by
`tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity`, agreement to `atol=1e-12`).
So `water_z` cannot affect any projection — but it still gates the domain test that increments the
counter. Measured in `MANUSCRIPT-FINDINGS.md:892–903`:

- Holding all other parameters fixed and sweeping `water_z` over 1.5 m leaves the cost constant to
  **13 significant figures** (2.6e-15 relative) while the guard count climbs 0 → 374 → 5,572 →
  **14,949**. The n=1.333 control moves cost by five orders of magnitude over the same sweep, so
  the probe is not blind. `water_z` is an **exact null direction** in that arm.
- Re-running with `water_z` pinned at ground truth drives the guard count to **0** and optimality
  from 9e+02 to **5e-01**, while reproducing every non-refractive reconstruction number to ~4
  significant figures (2.5 m Z-RMSE 248.267 → 248.221 mm).

The solver is currently being asked to estimate a parameter that provably cannot influence the
fit, and the resulting free-floating estimate is what trips the guard 14,949 times.

## Solution

Pin `water_z` at ground truth in the non-refractive arm only, and record why in the arm's own
provenance so the asymmetry is self-explaining.

- The pin must be conditioned on the arm, not on a global flag. `MODELS` at
  `e1_refractive_comparison.py:137` is where the two arms diverge.
- Emit a field in `e1_benchmark_nonrefractive.json` stating that `water_z` was held, so a reader
  diffing the two benchmark records sees the difference rather than inferring it.
- Expect the arm's `degenerate_observations_at_solution` to read 0 afterwards. That is the check.

**Predicted magnitude, for the record only.** `HANDOFF.json:119` defers this item because it
"deliberately shifts a published number in its 4th significant figure". The measured shift is
**−0.019%**, against quantities the manuscript quotes at 2–3 significant figures. So the prediction
is that this change is invisible at printed precision. That is a prediction to check against the
new suite, **not a constraint on the fix** — see the sequencing note below.

**It also supports `main.tex:258`'s "sole experimental variable" framing — but that argument has to
be *supplied*, not written here.** The obvious objection is that pinning in one arm and not the
other makes the arms differ in two ways. The answer is that the pinned direction is exactly flat at
unit index, so removing it is a reparameterization of a null space rather than a model change, and
the agreement between pinned and free solves is the evidence.

**Deliverable for that: the evidence, not the sentence.** Emit the free-vs-pinned comparison as a
committed artifact (both arms' reported quantities, side by side, at the same seed) and record the
null-direction measurement in `MANUSCRIPT-FINDINGS.md`. Writing the §3 sentence is the manuscript
session's job.

## Do not

- **Do not pin `water_z` in the refractive arm.** `MANUSCRIPT-FINDINGS.md:972` is explicit and
  measured: there it is genuinely observable and estimating it is the method's contribution.
  Pinning inflates the headline ratio to a flattering **168×** and breaks §3's stable-anisotropy
  claim (free 1.95–2.19, matching the published ~2.3; pinned drifts 2.21 → 1.46).
- Do not present this as a correction to a wrong result. The comparison was never contaminated —
  MF's "bookkeeping, not contamination" finding stands, and this TODO makes the artifact agree
  with that finding instead of contradicting it.
- Do not treat the guard count going to zero as the goal in itself. The goal is not estimating a
  parameter that cannot be estimated; zero is the symptom clearing.
- Do not fold this into the refractive arm's configuration or a shared default. It is an arm-local
  property of unit index.

## Sequencing — deferral gate explicitly overridden

`HANDOFF.json:119` says "Do not action before the SoftwareX submission." **Author decision
2026-08-15: the full-suite re-run is pre-submission, so this lands before 2026-08-21, and the
deferral is explicitly overridden.**

The deferral's premise no longer holds. It was written to protect published digits from moving
under a spot fix; the re-run is instead a fresh single source of truth that replaces every prior
artifact, so numbers moving is expected. The precision argument above is retained only as a
*prediction* — it says this change should be invisible at the manuscript's quoted precision, which
is a useful thing to have been right or wrong about. It is not a reason to do or not do the pin,
and nothing in the fix should be shaped to preserve a value.

After the run, report the new `exp1_band.csv` values for the quantities the manuscript currently
quotes at `main.tex:269` (229 mm, 199–252 band) and in the abstract (~135×), so the manuscript
session can update the prose. **Do not edit the manuscript.**

## Related

- `2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` — this is that todo's
  deferred companion item; its step 3 (restart the n=1.0 arm from the ground-truth pose) is
  adjacent and still open.
- `.planning/MANUSCRIPT-FINDINGS.md:892–903` (the null-direction and pinned-run measurements),
  `:972` (do not pin the refractive arm), MF-18 at `:1816`.
- Retires audit finding **F-003 defect 1**: with the pin, the response letter's original
  "every calibration experiment reports a zero out-of-domain observation count" becomes true as
  written. The current package still needs the narrowing, because it describes the submitted state.
- `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — after this
  lands, the only surviving non-zero count in the suite is the real rig's 198.

## Scope boundary — artifacts, not prose

This TODO is library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/` —
`main.tex`, `supplement.tex`, `response-letter.md`, `numbers-ledger.tsv`) is **read-only from this
repo and must not be edited here**, including "obviously correct" single-number updates.

Where a fix has a manuscript consequence, the deliverable is the **evidence, not the sentence**:
emit the artifact, and record the derivation in `.planning/MANUSCRIPT-FINDINGS.md`. Incorporating
it into the paper — prose, ledger rows, captions, figure captions — happens in the manuscript
session, which owns that tree and the word budget.

References to `main.tex` / `supplement.tex` line numbers anywhere in this file are **motivation and
provenance**, never work orders.

---

## Strengthened by the P3 probe (2026-08-15): the pin retires the suite's ENTIRE degeneracy population

This todo argues from E1's 14,949 alone. Tracing every degenerate-observation line in
`experiments/rerun_19_4.log` shows the argument is broader than that — **all five are the
non-refractive arm**, no exceptions, and no refractive-arm occurrence exists anywhere in the file:

| log line | count | configuration |
|---|---|---|
| 877  | 14949 | E1 **single-seed production**, seed 42, non-refractive arm |
| 910  | 14949 | E1 **10-seed band**, seed 42 — identical, consistent |
| 941  | 14907 | E1 band, **seed 44** |
| 1000 | 2128  | E1 band, **seed 48** |
| 1033 | 1134  | E1 band, **seed 50** |

Every one is prefixed `n_water=1.0`. Since at unit index `water_z` is an exact null direction, the
same mechanism produces all five, and **this pin retires all of them** — not just the headline
14,949.

Two consequences:

- **The closing claim in § Related is now measured, not predicted.** "After this lands, the only
  surviving non-zero count in the suite is the real rig's 198" is confirmed against the queue log
  rather than inferred.
- **It settles the open question in
  `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md`.** That todo lists
  14907 / 2128 / 1134 as counts appearing in no committed artifact and asks whether any is a genuine
  geometric failure rather than a schema gap. None is. They are the same benign unit-index
  bookkeeping as E1's 14,949, so T-14 stays a column addition with no open question attached.

Note the counts are cross-stage sums — line 1033's `1134` is `70` (Stage 3) + `1064` (intrinsic
pass). That does not weaken the attribution (both stages are the same unit-index arm) but it is why
the raw numbers should not be quoted as solution-state counts.

Method and provenance: `Desktop/aquacal-scoping-probes-findings-2026-08-15.md` §2.
