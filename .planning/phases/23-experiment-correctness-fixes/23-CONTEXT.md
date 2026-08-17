# Phase 23: Experiment Correctness Fixes - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Six fixes that change what the experiment suite measures, records, or is licensed to claim —
landed before the Phase 27 freeze, because after the freeze a wrong number is a wrong number in
the archive the paper cites.

- **FIX-01** — pin `water_z` in E1's non-refractive arm (exact null direction at unit index)
- **FIX-02** — E1 and E7 solve with the interface normal free, matching production DOF
- **FIX-03** — E6 reports signed, gauge-corrected Z error plus the per-camera decomposition
- **FIX-04** — E7's `fixed` rows labelled vacuous-by-construction, not a measured verdict
- **FIX-05** — E4's aggregator resolves E2's benchmark row relative to `--out`
- **FIX-06** — stale provenance strings in `e2_real_rig.py` and `synthetic.py` corrected

**Not this phase:** degeneracy instrumentation (Phase 24), the 198 classification and E1's
`noise_std` axis (Phase 25), the driver and `--check` documentation (Phase 26), any run of the
full suite (Phase 28).

</domain>

<decisions>
## Implementation Decisions

### Pin mechanics (FIX-01)

- **D-01: `water_z` is held by a bounds freeze threaded from the experiment, not by a library
  `water_z_fixed` flag.** The parameter stays packed; a degenerate interval
  (`lb = ub ± 1e-12` around 1.031 m) prevents it moving. This is a genuine solve-time constraint,
  not a post-hoc adjustment, and it is arm-local by construction.

  *Why not the flag:* the closest precedent, `normal_fixed`, spans **101 references across 9
  files** including `_optim_common.py`, `schema.py` and the CLI. That is the same source-level
  surgery this milestone deliberately deferred for `normal_fixed` itself, six days before a
  freeze.

  *Why not post-hoc:* recomputing the guard at ground truth would report a counter for a
  configuration that was never solved. Defensible in principle — the direction is provably flat —
  but it is exactly the kind of thing a reviewer pressing on reproducibility calls cosmetic.

  *Implementation note:* `build_bounds` (`_optim_common.py:522`) already emits a dedicated bound
  for the `water_z` slot at `:571-575`, and `optimize_interface` already passes
  `bounds=(lower, upper)` to `least_squares` at `:357-364`. So the threading is narrow — a
  bounds override reaching `build_bounds` from the experiment — not a new mechanism.

- **D-02: the pinned + normal-free combination is probed BEFORE plans are written.** That
  configuration is what the re-run actually executes and no probe has reached it, because pinning
  did not exist. It costs ~3 min on the harness already built
  (`.planning/probes/2026-08-17-phase-23-recon/probe_normal_fixed.py`). Discovering a conditioning
  problem at the freeze, or on the Linux machine, is the expensive version.

  If it does degrade, the fallback is decided against whichever claim is load-bearing for the
  manuscript — not pre-committed here, because the probe is expected to make the question moot.

- **D-03: acceptance is the recovered `water_z` against ground truth 1.031 m.** The guard count
  reading 0 is corroboration reported alongside, never the test. Measured 2026-08-17: FIX-02 alone
  drives the count 14,949 → 0 with `water_z` at 0.0120 m, at a cost identical to the unpinned
  solve to 10 significant figures. See `REQUIREMENTS.md` FIX-01 and the todo's
  "§ The guard count is not a valid acceptance test".

- **D-04: the non-refractive arm's benchmark record states the held value, the mechanism, and the
  reason.** Not a bare boolean. A reader diffing the two arms' records should find both the
  asymmetry and its justification (exact null direction at unit index, with a pointer to the
  measurement) without leaving the artifact — that is what makes `main.tex`'s "sole experimental
  variable" framing defensible.

- **D-05: the hardcoded `[0.01, 2.0]` m `water_z` bound is a real generality defect, deferred to
  post-submission.** Discovered during this discussion:
  `_optim_common.py:571-575` sets both bounds as bare literals with no parameter, and
  `docs/guide/troubleshooting.md:99` tells users with a >2 m standoff to *"modify the bounds in
  the source code"*. Intrinsics bounds in the same function are data-relative (`0.5 * fx` to
  `2.0 * fx`), so this is two of five slots that never got converted, not a philosophy.

  Deferred because no published number moves — every production solve lands interior, and the two
  that hit the bound are the degenerate E1 arms FIX-01 pins anyway. Filed as
  `.planning/todos/pending/2026-08-17-POST-SUBMISSION-water-z-bounds-are-hardcoded-and-force-a-source-fork.md`.
  **Consequence for this phase:** FIX-01's pin is threaded as its own narrow change rather than
  riding on a general `water_z_bounds` parameter.

  `docs/guide/troubleshooting.md:99` is **not** to be "corrected" — it accurately describes a real
  limitation. It changes when the limitation does.

- **D-06: the bound-hit finding is recorded here; the general detector belongs to Phase 24.**
  Both degenerate arms terminated *on* a bound (1.990 m against the 2.0 ceiling; 0.0120 m against
  the 0.01 floor) rather than at a minimum — stronger evidence for the null direction than the
  cost-flatness sweep alone, and it goes in `MANUSCRIPT-FINDINGS.md`. Flagging *any* solve that
  terminates on the `water_z` box is degeneracy instrumentation: hand it to **DEGEN-02**, where
  "parameter resting on its bound" is naturally a failure *kind*, rather than widening Phase 23's
  diff.

### `--check` contract (FIX-05)

- **D-07: `--check` skips an explicit, named list of non-reproducible columns, and prints what it
  skipped on every run.** The list is `exit_code` and `status_reason` — artifacts of the checking
  path, not of the run. Measured 2026-08-17: all **33 metric columns already reproduce to 1e-6**;
  only these two fail, and they can never pass, because `_run_check` hardcodes
  `"exit_code": None` at `e4_benchmark_grid.py:1872` (no subprocess runs under `--check`).

  A named list beats a heuristic: the next such column should require a deliberate decision, not
  silently inherit an exemption. Rejected alternative — synthesizing `exit_code: 0` from a
  committed record — because it fabricates a field in a provenance artifact.

- **D-08: Phase 23 implements the exclusion; Phase 26 (DRIVER-03) documents it.** The contract is
  formally DRIVER-03's, but FIX-05 consumes it now, so it is decided here rather than invented
  locally. The two phases must not diverge.

- **D-09: FIX-05 covers TWO call sites.** `_run_check` at `e4_benchmark_grid.py:1876` passes the
  module-level `E2_BENCHMARK_PATH` directly. Fixing only the main aggregation path leaves
  `--check` under `--out` still importing another machine's real-rig row.

- **D-10: the always-red gate is recorded as a process finding in
  `.planning/knowledge-base.md`.** A verification gate that cannot pass is worse than no gate — it
  trains everyone to ignore it, so a genuine mismatch reads as the usual red. Same class as the
  decision-coverage gate that passed while parsing nothing. The entry is about the pattern, not
  this instance.

### Verification budget

- **D-11: cheap tier only — E1 both arms plus E4's smoke cells, ~6 minutes.** It covers exactly
  the three fixes whose outcome cannot be predicted by reading: FIX-01, FIX-02, and FIX-05's
  aggregation path. FIX-03 (schema), FIX-04 (re-analysis of an existing band) and FIX-06 (strings)
  are verifiable by inspection and tests.

  Explicitly **not** in-phase: E4's nine-cell grid (measured 3.5–4 h across the 19.3/19.4 queues),
  E1's 10-seed band (~1 h), and anything else. Those run once at the frozen sha in Phase 28.

- **D-12: every in-phase verification run goes to a dedicated, git-ignored `--out` directory**
  (e.g. `experiments/verify_23/`). Nothing leaks into the tree Phase 27 packages or that DRIVER-04
  later moves aside. Convenient side effect: this exercises FIX-05's `--out` path for free.

  *Consequence:* because those outputs are never committed, any evidence they produce must be
  **transcribed into `MANUSCRIPT-FINDINGS.md`**, not referenced as an artifact path.

### Plan decomposition

- **D-13: four plans, grouped by coupling.**
  1. **FIX-01 + FIX-02** — they interact, share the E1 arm, and one silently satisfies the other's
     stated criterion. FIX-01 lands first.
  2. **FIX-05** — two call sites plus the exclusion list.
  3. **FIX-03 + FIX-04** — E6/E7 reporting and labelling, no solver effect.
  4. **FIX-06** — four string sites plus the supersession header, touching no logic. Isolated so
     it can never be blamed for a number moving.

  The roadmap's "six independent single-file fixes" framing does not survive recon and should not
  drive the decomposition.

- **D-14: one commit per requirement, even inside a shared plan.** FIX-01 and FIX-02 ship as two
  commits in one plan, in that order, so they can be bisected apart if the combination misbehaves.
  Applies the v2.0.0 lesson directly — one commit per breaking change, learned when a CHANGELOG
  listed 1 of 7.

### Amendment 2026-08-17 — D-06 and D-12: no plan writes MANUSCRIPT-FINDINGS.md

**Decided by the user during planning, after the plans were drafted.** D-06 and D-12 as originally
written sent this phase's evidence into `.planning/MANUSCRIPT-FINDINGS.md`. That is withdrawn.

**Why.** The ledger's own charter, stated in its header, is *"measured results from the v1.9
experiment suite that contradict, understate, or otherwise require a change to prose in the
manuscript or supplement"*, where *"each entry names the artifact that is the citable source."*
Phase 23 fails that contract in both halves:

- **No citable artifact survives.** D-12 deliberately sends every in-phase run to a git-ignored
  directory. D-12's "transcribe as values, not paths" was a workaround for exactly this mismatch —
  it manufactures an entry the file's own contract says should cite measured data.
- **Nothing here is a new finding.** The findings these six fixes correspond to are already in the
  ledger: **MF-17** (E7's `fixed` arms are vacuous, not null) is FIX-04's; **MF-18** (unit-index
  pinhole identity) is FIX-01's null direction; **MF-12** (the E6 gauge decomposition) is FIX-03's.
  Phase 23 implements what those findings imply. It measures nothing new and discovers nothing.
- **Phase 28 is the real entry point**, when the suite runs at the frozen sha and produces artifacts
  that survive to be cited.

**What replaces it.** Each plan records its evidence in its own committed `23-0N-SUMMARY.md` under an
`## Evidence` heading — durable, phase-scoped, and still "as values, never as an artifact path,"
which was D-12's actual intent. Plan 01 additionally closes with a `### Ledger candidate` note
flagging the D-06 bound-hit table as the one item a reviewer would want in the ledger (it strengthens
MF-18's null-direction argument), so the item stays visible without an executor acting on it.
Transcribing it is the user's call, consistent with the standing rule that manuscript-ledger work is
not executor work.

**Consequence for the wave plan.** `MANUSCRIPT-FINDINGS.md` was the *only* file overlap among the
four plans — everything else was already disjoint, and the `depends_on` chain 01 → 02 → 03 existed
solely to serialize appends to it (plus an MF-NN numbering collision risk that a git merge would not
have flagged). With the ledger removed from every `files_modified`, all four plans are genuinely
disjoint and run in **wave 1**. There is no code coupling between them: FIX-01's bounds override is
arm-local by construction (D-01) and inert for plans 02–04, and plan 01's `e7_interface_ablation.py`
is a different file from plan 03's `e7_focal_standoff_analysis.py`.

### Claude's Discretion

- The exact mechanism for reaching `build_bounds` from `e1_refractive_comparison.py` (new kwarg on
  `optimize_interface` vs. a bounds override on the calibration entry point) — pick the least
  invasive route that still constrains the solve rather than the report. `_optim_common.py` may be
  touched, but minimally: this milestone's premise is that the suite stays attributable.
- The FIX-01 fallback if the pinned + normal-free probe degrades (D-02).
- Whether the `--check` exclusion list is E4-local or shared across experiments.

### Folded Todos

All six are bound to this phase by `resolves_phase: 23` frontmatter, so folding was not re-asked.

- `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md` — FIX-01. Carries the null-direction
  measurement and the corrected acceptance criterion.
- `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md` — FIX-02.
- `2026-08-15-e6-z-error-reporting-and-per-camera-gauge-decomposition.md` — FIX-03. Note its
  "run all six seeds" bullet is **already satisfied**; the reproducible difference is 0.3592 mm.
- `2026-08-15-e7-vacuous-fixed-rows-ship-as-measured-nulls.md` — FIX-04.
- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — FIX-05. Carries the two-call-site
  and always-red-`--check` corrections.
- `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md` — FIX-06. Carries the
  fourth site.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements and corrections
- `.planning/REQUIREMENTS.md` § Experiment Correctness (FIX) — the six requirement statements,
  each carrying a 2026-08-17 correction block
- `.planning/ROADMAP.md` § Phase 23 — six success criteria plus the "Note on independence"
- `.planning/probes/2026-08-17-phase-23-recon/PHASE-23-RECON-FINDINGS.md` — the 11 findings this
  discussion is built on
- `.planning/probes/2026-08-17-phase-23-recon/probe_normal_fixed.py` and
  `probe_normal_fixed.json` — the three-arm measurement behind D-02, D-03, D-06
- `.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py` — the 35-column enumeration
  behind D-07

### The six todos
- `.planning/todos/pending/2026-08-15-pin-water-z-in-e1-non-refractive-arm.md` — **read
  § The guard count is not a valid acceptance test before planning FIX-01**
- `.planning/todos/pending/2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md`
- `.planning/todos/pending/2026-08-15-e6-z-error-reporting-and-per-camera-gauge-decomposition.md`
- `.planning/todos/pending/2026-08-15-e7-vacuous-fixed-rows-ship-as-measured-nulls.md`
- `.planning/todos/pending/2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — **read
  § Two corrections measured 2026-08-17**
- `.planning/todos/pending/2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md`
  — **read § A fourth site**

### Domain and evidence
- `.planning/MANUSCRIPT-FINDINGS.md` :892-903 (null-direction and pinned-run measurements),
  :972 (do not pin the refractive arm), :1816 (MF-18, unit-index pinhole identity) — and the
  destination for every piece of evidence this phase produces
- `.planning/geometry.md` § 4.3 — `water_z` semantics; it is a Z-coordinate, not a distance
- `.planning/knowledge-base.md` § Known Issues — destination for D-10's process finding
- `docs/guide/optimizer.md` :131, :138-149, :163 — the documented bound set and why board Z is
  not bounded below `water_z`

### Deferred, but referenced by decisions here
- `.planning/todos/pending/2026-08-17-POST-SUBMISSION-water-z-bounds-are-hardcoded-and-force-a-source-fork.md`
  — D-05
- `.planning/todos/pending/2026-08-15-POST-SUBMISSION-reconcile-normal-fixed-defaults-between-config-and-library.md`
  — same shape, same file, same deferral reason

### Scope boundary
- The manuscript tree `Spinoffs/papers/aquacal/` (`main.tex`, `supplement.tex`,
  `response-letter.md`, `numbers-ledger.tsv`) is **read-only from this repo and must not be edited
  here.** Where a fix has a manuscript consequence the deliverable is *the evidence, not the
  sentence*: emit the artifact, record the derivation in `MANUSCRIPT-FINDINGS.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`build_bounds` (`_optim_common.py:522`)** already emits a dedicated bound pair for the
  `water_z` slot at `:571-575`, and `optimize_interface` already forwards `bounds=(lower, upper)`
  to `least_squares` at `:357-364`. FIX-01 tightens an existing slot rather than introducing a
  constraint mechanism.
- **`normal_fixed`** is the working precedent for a solver-level boolean threaded end to end
  (pack, unpack, sparsity, column grouping, schema, CLI) — 101 references across 9 files. It is
  the *cost benchmark* that ruled out the flag route, not a template to copy.
- **Intrinsics bounds (`_optim_common.py:588-591`)** are data-relative (`0.5 * fx` to `2.0 * fx`)
  — the pattern the deferred `water_z` bounds todo should follow.
- **`compute_residuals(..., invalid_count_out)`** is how the degeneracy count reaches callers.
- **`SMOKE_CELLS = [(3, 3), (3, 4)]` (`e4_benchmark_grid.py:218`)** exercises the aggregation path
  in seconds — the verification vehicle for FIX-05 now that `--check` cannot serve.
- **`compute_per_camera_errors(..., gauge_correct_z=...)`** — FIX-03 calls it twice and emits both.
- **`e7_focal_standoff.csv`** already has a free-text `scope` column that can host FIX-04's
  vacuous-by-construction label without a schema change.
- **`.planning/probes/2026-08-17-phase-23-recon/probe_normal_fixed.py`** mirrors `_run_one_model`
  with a single knob — reuse it for D-02's pinned + normal-free probe.

### Established Patterns

- `MODELS = [("refractive", 1.333), ("non_refractive", 1.0)]` at
  `e1_refractive_comparison.py:137` is where the two arms diverge — the anchor for anything
  arm-local.
- `_run_one_model` calls `calibrate_synthetic(...)` at `:312` with **no** `normal_fixed` argument,
  which is how the library's `True` default leaked in. FIX-02 makes it explicit.
- Experiments append columns rather than redefining them, so old artifacts stay readable
  (FIX-03 is bound by this).
- Config layer defaults `normal_fixed=False`; 18 library signatures default `True`. Reconciling
  that at the source is post-submission; FIX-02 fixes it at the experiment level only.

### Integration Points

- `e1_refractive_comparison.py` → `calibrate_synthetic` → `run_calibration` →
  `optimize_interface` → `build_bounds` — the chain FIX-01's bounds override must traverse.
- `_run_check` (`e4_benchmark_grid.py:1836`) → `build_grid_dataframe(out_dir, cell_statuses,
  E2_BENCHMARK_PATH)` at `:1876` — FIX-05's second call site.
- **DEGEN-02 (Phase 24) also modifies `_optim_common.py`.** Phase 29's E2 sanity control is what
  proves neither phase perturbed the solve — so keep both diffs in that file minimal and
  reviewable.

</code_context>

<specifics>
## Specific Ideas

- The author's own catch during discussion: *"are those hardcoded deep in the library to 0.1-2.0?
  If so, that makes the library a bit less general than we are claiming, doesn't it?"* — the
  bound is `[0.01, 2.0]`, it is hardcoded, and the answer was yes. See D-05.
- The bound-hit table is the phase's sharpest single piece of evidence and should survive into
  `MANUSCRIPT-FINDINGS.md` intact:

  | E1 arm | recovered `water_z` | landed |
  |---|---|---|
  | n=1.0, normal fixed | 1.990 m | on the 2.0 ceiling |
  | n=1.0, normal free | 0.0120 m | on the 0.01 floor |
  | n=1.333, normal free | 1.0236 m | interior (−7.43 mm from GT) |

- FIX-06's fourth site should be quoted verbatim in its plan — "60 usable frames → 12 validation →
  1,817 comparisons" against the verified 262 → 52 → 7,762 — so nobody fixes the help text and
  leaves the comment.

</specifics>

<deferred>
## Deferred Ideas

- **Parameterize the `water_z` bound, then derive it from data** — D-05. Filed as
  `2026-08-17-POST-SUBMISSION-water-z-bounds-are-hardcoded-and-force-a-source-fork.md`. Two steps
  deliberately: parameterize with today's default (bit-identical), then change the default.
- **The `±0.2` rad tilt bound** has the same hardcoded-absolute question. Less likely to bind;
  folded into the same todo rather than filed separately.
- **General bound-hit detection** — D-06. Handed to **DEGEN-02 in Phase 24** as a degeneracy
  *kind*, not deferred indefinitely.
- **Audit the other gates for always-red / always-green behaviour** — raised under D-10 and not
  taken. `check_rerun_gates.py` is what Phase 29 depends on, and Phase 27's freeze is the last
  cheap moment to check that it can actually fail. Worth reconsidering at the Phase 27 gate.
- **Source-level `normal_fixed` reconciliation** — already deferred post-submission by the
  milestone; unchanged by this discussion.

### Reviewed Todos (not folded)

The `todo.match-phase` matcher surfaced five todos on keyword similarity whose `resolves_phase`
frontmatter binds them elsewhere. Frontmatter is authoritative; all five stay out of Phase 23.

- `2026-08-15-narrow-the-degenerate-observation-warning.md` (scored 0.9) — DEGEN-03, **Phase 24**
- `2026-08-15-POST-SUBMISSION-reconcile-normal-fixed-defaults-between-config-and-library.md`
  (0.9) — deliberately untagged; post-submission
- `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` (0.6) — BAND-01, **Phase 25**
- `2026-08-15-classify-the-198-unprojectable-observations.md` (0.6) — DEGEN-04, **Phase 25**
- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` (0.6) — DRIVER-04,
  **Phase 26** / POST-03, **Phase 30**

</deferred>

---

*Phase: 23-Experiment Correctness Fixes*
*Context gathered: 2026-08-17*
