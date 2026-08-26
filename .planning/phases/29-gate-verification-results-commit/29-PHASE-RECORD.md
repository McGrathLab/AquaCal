# 29-PHASE-RECORD — grading, committing and archiving the v2.1 production run

**This is the document Phase 29.2 and Phase 30 open first**, the way
`.planning/phases/28-full-suite-production-run/28-RUN-RECORD.md` was the document Phase 29 opened
first. Every number below was measured by a plan in this phase and is quoted from an evidence file
sitting beside this one. Nothing here is recalled, and nothing here is re-derived.

Where a figure disagrees with an earlier record, the earlier record is **annotated with a dated
note**, never rewritten. That is this project's standing rule.

---

## Header

| | |
|---|---|
| **Phase** | 29 — Gate Verification & Results Commit |
| **Dates** | 2026-08-26 (all eight plans executed the same day) |
| **Branch** | `results/rerun-freeze-02` — never changed, never merged, nothing force-pushed |
| **Run being graded** | tag `rerun-freeze-02` (annotated `533f79fb`), sha `7005a2771aa115e4f4c1284cec7e145739586a4a` (`v2.0.1-346-g7005a27`) |
| **Artifacts commit** | `70e783f` — `results(29): full production suite at rerun-freeze-02`, 227 files, 40,497 insertions, zero deletions, pushed to `origin` |
| **Rails-repair commit** | `5799b14` — `fix(29):`, exactly one file (`tests/unit/test_experiments_provenance.py`) |
| **Second independent copy of the run** | `~/aquacal-frozen-rerun-freeze-02-prod`, detached at `7005a277…`, verified unmutated before and after all bulk reads |
| **Zenodo Record A (inputs)** | deposition **22116461** — `https://zenodo.org/deposit/22116461` → **PUBLISHED** at `https://zenodo.org/records/22116461` |
| **Zenodo Record B (results)** | deposition **22117061** — `https://zenodo.org/deposit/22117061` → **STAGED, UNPUBLISHED** |

### Evidence files this record is derived from

| File | What it holds |
|---|---|
| `29-gates-full.txt` | `check_rerun_gates.py --profile full` over the landed (pre-commit) tree |
| `29-gates-committed.txt` | the same gate over the **committed** tree, byte-identical over all 185 stdout lines |
| `29-e2-control.txt` | the E2 same-seed control, seed 42 vs seed 42, three trees |
| `29-e7-before-after.txt` | the E7 before/after exact paired sign test, both pairings, both trees |
| `29-commit-manifest.txt` | the 227-path admitted set, per-path breakdown, size check, two-directional attempt-1 diff |
| `29-rails-before.txt` / `29-rails-after.txt` | the provenance rails node id by node id, before and after repair |
| `29-zenodo-sandbox-rehearsal.txt` | the D-29-06 sandbox rehearsal and the author's dated approval |
| `29-zenodo-record-a.txt` / `29-zenodo-record-b.txt` | both production deposits: handles, payload audits, md5 round trips |
| `29-RECORD-COMPOSITION.md` | the author's `research-default` Record A / Record B payload ruling |
| `analyze_e2_control.py` / `analyze_e7_before_after.py` | the committed, re-runnable producers of the two scientific verdicts |

---

## Verdict

**Criteria 1 through 5 are satisfied and measured. Criterion 6 is the only one open, and it is
open by construction rather than by failure** — Phase 29 cannot observe the paper's submission
event, and the phase was built to close against its other five criteria rather than to fabricate
a closure it cannot evidence.

D-29-10's three-item stop list — the phase's actual publication gate — was evaluated in full and
**not one item fired**. Under D-29-09 the outputs are scientifically valid and are to be published.

One published conclusion moved. It is raised in its own section below, and it is **not** in §3's
primary claim. See *The E7 refined-pairing move*.

---

## The six ROADMAP success criteria, one row each

| # | Criterion (abbreviated) | Measured value | Evidence file | Verdict |
|---|---|---|---|---|
| 1 | `check_rerun_gates.py` passes over the complete returned run, Gate 3 included | `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, exit 0, zero `[FAIL` lines; `gate3_git_sha_consistency` PASS on the single sha `7005a2771aa115e4f4c1284cec7e145739586a4a`; all four `gate3_run_manifest_*` PASS, 17/17 environment fields non-null | `29-gates-full.txt`, `29-gates-committed.txt` | **PASS** |
| 2 | E2 reproduces its pre-run numbers to ~1e-8, same seed only | seed 42 vs seed 42: worst scalar relative drift **2.5146e-08** (≈ `2.52e-08`) on `inter_corner_rmse_mm`; §3 headline `mean_per_camera_reprojection_px` **4.8962e-09** (≈ `4.90e-09`); worst including compound leaves 3.6317e-08; `n_comparisons` exact at **7762** | `29-e2-control.txt` | **PASS** |
| 3 | E7's ablation conclusion compared before and after, explicitly | fixed-intrinsics pairing **HELD** at `10/10`, p = 1/1024 = **0.00098** in both trees; refined pairing **MOVED** `8/10` (p = 56/1024 = 0.05469) → `7/10` (p = 176/1024 = 0.17188) | `29-e7-before-after.txt` | **DISCHARGED — and flagged to the author** |
| 4 | The returned results are committed with provenance intact | `70e783f`: **227** files, **147** under `experiments/results/`, a strict superset of attempt 1's **209** by exactly 18 stage logs with zero paths lost; 40,497 insertions, zero deletions; largest admitted file **119,406** bytes; both md5 anchors unchanged across the commit | `29-commit-manifest.txt`, `29-gates-committed.txt` | **PASS** |
| 5 | Every §3-facing number traceable to this run | all three generated LaTeX fragments (`benchmark_grid.tex`, `cpr_derived_values.tex`, `cpr_grouping.tex`) are inside the committed 147, at the frozen sha, with `gate3_git_sha_consistency` supplying the single-sha proof | `29-commit-manifest.txt`, `29-gates-committed.txt` | **PASS, repo-side (D-29-19)** |
| 6 | The Zenodo results package is published before the paper is submitted | Record A **published**, version DOI `10.5281/zenodo.22116461`, concept DOI `10.5281/zenodo.22116460`. Record B **built, uploaded, verified, UNPUBLISHED** at deposition 22117061 | `29-zenodo-record-a.txt`, `29-zenodo-record-b.txt` | **OPEN — awaiting Publish** |

---

## Criterion 1 — the gate over the complete returned run

`python experiments/check_rerun_gates.py experiments/results --profile full`, run twice: once by
plan 29-02 over the landed-but-uncommitted tree, once by plan 29-05 over the **committed** tree.

- `TOTAL: 176 PASS, 7 N/A, 0 FAIL` — both times, at **exit code 0**, with **zero** lines beginning
  `[FAIL`.
- All five Gate 3 lines PASS, including `gate3_git_sha_consistency` on the single sha
  `7005a2771aa115e4f4c1284cec7e145739586a4a` and `gate3_run_manifest_fields` with all **17**
  environment fields present and non-null.
- The two captures are **byte-identical over all 185 stdout lines** (`diff` of lines 1–185 returns
  0 differing lines). There is no timestamp difference, because the gate reads timestamps recorded
  inside the artifacts rather than the wall clock.
- Against Phase 28's own post-run capture `freeze02-gates-full.txt`, the raw diff is **126** lines
  and the path-normalised diff is **empty**; all 126 changed lines carry the embedded absolute
  clone path and nothing else. **Both numbers are recorded**, not only the flattering one.

### What "the complete returned run" was taken to mean

The edge probe flagged this as unclassified and plan 29-02 declined to auto-resolve it. The reading
that was **graded** is: *all six output trees, plus the stagelogs directory, plus the two loose
state artifacts — nine paths — at their original relative paths.* That is **461** files:
423 across the six output trees + 36 in the stagelogs directory + 2 loose state files.

This reading is necessary rather than convenient: `check_e2_band` resolves a **sibling** of
`out_dir`, so a partial tree would silently degrade the roll-up instead of reporting a gap. The
`461` file count and the `176/7/0` roll-up together are the evidence the reading was satisfied.
Whether that is what RUN-03 *meant* remains the author's call — it is evidenced, not ruled.

---

## Criterion 2 — the E2 same-seed control

`analyze_e2_control.py`, committed in this directory and re-runnable. It reads each tree's own
`benchmark.json` `solver_config["seed"]`, **asserts the seeds agree before comparing any value**,
and stamps `seed 42 vs seed 42` on every one of its 27 comparison lines. A cross-seed comparison
fails closed and prints nothing — at this tolerance a cross-seed number is not merely wrong, it is
actively misleading, because E2's *seed* band on `mean_per_camera_reprojection_px` spans
0.761 → 0.910 px.

**Two baselines, proving two different things:**

| Comparison | What it proves | Worst scalar drift |
|---|---|---|
| `experiments/pre_rerun_baseline/results/` → freeze-02 (Windows / aquacal 1.8.0 / `6c7f930b`) | **the criterion's comparison** — the solve reproduces across the whole Windows→Linux, 1.8.0→v2.1 span | **2.5146e-08** on `inter_corner_rmse_mm` (≈ `2.52e-08`) |
| `experiments/freeze01_run_output/` → freeze-02 (attempt 1, same OS, same version) | the weaker statement, labelled as such: the two attempts are byte-identical | exactly **0.0** on every field |

- §3 headline `mean_per_camera_reprojection_px`: `0.8240385366779744` → `0.8240385407126619`,
  relative drift **4.8962e-09** (≈ `4.90e-09`).
- Worst case including flattened compound leaves: **3.6317e-08** on `reprojection_range_px[1]`.
  The exit code gates on this stronger figure, not on the headline one.
- Integer field `n_comparisons` is **exactly equal at 7762** in both comparisons.
- `DRIFT_LIMIT` is `1e-06`. The worst observed figure is four orders of magnitude below it.

**DEGEN-02 did not perturb the solve.** DEGEN-02 touched `_optim_common.py`, which is precisely why
this control is the phase's designated solver-correctness check. It reproduces at ~1e-8.

**D-29-10 stop-list item 1 does not fire.**

The control's own failure mode was verified by injection rather than asserted: scaling
`inter_corner_rmse_mm` by 1.001 in a scratchpad copy drives it to `RESULT: FAIL` at exit 1, and
forcing a seed to 43 produces `SEEDS DISAGREE` / `SEED MISMATCH` with no values compared.

---

## Criterion 3 — E7's ablation conclusion, before and after

`analyze_e7_before_after.py`. One-tailed exact paired sign test on `camera_height_drift_mm`,
statistic transferred verbatim from `.planning/phases/19.2-…/analyze_e7_spread.py`, with `n`
derived from the data (`len(per.columns)`, not hard-coded) and the verdict headers computed from
the booleans rather than written as prose.

| Pairing | Before (`pre_rerun_baseline`) | After (`rerun-freeze-02`) | Moved? |
|---|---|---|---|
| `shared_fixed` vs `percamera_fixed` (**published primary**, supplement §14) | **10/10**, p = 1/1024 = **0.00098**, r = +0.5567 | **10/10**, p = 1/1024 = **0.00098**, r = +0.5059 | **No — HELD** |
| `shared_refined` vs `percamera_refined` (**published secondary**, supplement §14 / MF-05) | **8/10**, p = 56/1024 = **0.05469**, r = +0.8372 | **7/10**, p = 176/1024 = **0.17188**, r = +0.8435 | **YES — MOVED** |

The primary conclusion held. FIX-02's two extra free parameters per interface did **not** soften
the fixed-intrinsics arm. Under D-29-16 that half is a line in the record and nothing more.

### ⚠ THE E7 REFINED-PAIRING MOVE — D-29-16's flag-to-author case

**A published number moved. It is raised here, in this record, rather than being discovered later
during manuscript re-verification. That is the entire reason ROADMAP criterion 3 exists.**

**What moved:** the secondary refined pairing's sign-test result went from **8/10 (p = 0.05469)**
to **7/10 (p = 0.17188)**. Both figures are published, in **supplement §14 / MF-05**.

**What did not move:** the *conclusion*. The refined arm was already non-significant at
p = 0.055 and is now more clearly so at p = 0.172. Nothing that was claimed significant has
stopped being significant, and the primary 10-of-10 result at p = 0.00098 is untouched.

**The move is dated, and it is not a re-run artefact.** `interface_ablation_band.csv` carries md5
**`b6515ed77ed04268608b74217716020b`** in *both* attempt 1's tree and attempt 2's tree —
byte-identical. The 8→7 move therefore landed **before attempt 1**, which makes it a Phase 23–26
(**FIX-02**) effect. **Do not attribute it to the re-run.**

**What Phase 29 did about it: nothing, deliberately.** No manuscript file was opened, read for
editing, or written. `main.tex` is not in this repository. **§3 edits stay the author's** (D-29-16,
D-29-19), and the manuscript-side half belongs to **POST-01, Phase 30**.

**Caveat carried with the number:** n = 10 seeds before and after. This measures scenario-generator
seed variation only, on one metric (`camera_height_drift_mm`). It is not a bound on real-data
variation, and a sign test on n seeds cannot resolve an effect smaller than one seed's worth of
flips.

---

## Criterion 4 — the results committed with provenance intact

`70e783f  results(29): full production suite at rerun-freeze-02`, on `results/rerun-freeze-02`,
pushed to `origin` (`70e783fd8433c0d75616911d1bdd4c436c9a417e`), never forced.

| Measure | Value |
|---|---|
| Files in the commit | **227**, every one under `experiments/` — zero source, test or planning files |
| Under `experiments/results/` | **147** — matching attempt 1's 147 exactly |
| Insertions / deletions | 40,497 / **0**; 227 creates, **zero modifications** |
| Against attempt 1's `83da9b3` | **209** common, **18** added, **0** lost — a strict superset, stated in both directions |
| Largest admitted file | `interface_ablation_band.csv` at **119,406** bytes (`stat` reads `119406`; `--maxkb=1000` non-binding) |
| Staged-set verification | sorted staged list `diff`s to **zero differences** against `29-commit-manifest.txt`'s pre-enumerated 227 paths |

**The +18 is a deliberate ignore-rule widening, not drift.** The 18
`run_experiment_suite_state.*.stagelogs/*.log` files are admitted by `.gitignore:507`'s
re-inclusion, added in Phase 28 by commit `f399615`. The commit message carries that arithmetic so
no later reviewer can read it as a leak.

**Byte integrity, proven positively rather than by absence of failure:**

| Check | Reading |
|---|---|
| md5 `experiments/results/real_rig_metrics.json` | `57279708f6106f411d1fe03ed2698291` — before staging, after the scoped hook runs, and after the commit |
| md5 `experiments/results/interface_ablation_band.csv` | `b6515ed77ed04268608b74217716020b` — the same three readings |
| `git show HEAD \| grep -c '^\ No newline at end of file'` | **143** — exactly the count `end-of-file-fixer` would have rewritten. They reached the object store still missing their final newline |
| `git diff --check HEAD~1 HEAD \| grep -c 'trailing whitespace'` | 439 advisories about the artifacts' own bytes, added verbatim; nothing acted on |
| `ls .git/hooks/ \| grep -vc '\.sample$'` | **0**, before staging and after the commit |

`git commit --no-verify` was used and the commit message **says why**: the two formatting hooks
would rewrite 147 of the 227 artifacts. Exactly three hooks were run, each scoped as
`pre-commit run <id> --files <227 explicit paths>` — `check-added-large-files`, `detect-secrets`,
`check-yaml` — all three Passed. **`pre-commit run --all-files` was never invoked anywhere in this
phase**, and the two formatting hooks were never run at all. `.gitignore` and
`.pre-commit-config.yaml` are untouched (D-29-17).

The 234 gitignored files are recorded by `~/rerun-freeze-02-output.tar.gz`
(sha256 `3b21b88323bd7c04e9712ae2742cc09d423f925620e729ea7bbe2d391c9f030e`) and ship via Zenodo
Record B. **227 + 234 = 461**, reconciling exactly with `28-RUN-RECORD.md`.

---

## Criterion 5 — traceability, and the D-29-19 narrowing stated plainly

**RUN-04's own wording is the authority: *"every §3-facing number is traceable to this run."***
ROADMAP criterion 5 restates it as *"every §3-facing number in the manuscript"*, which reaches
outside this repository. D-29-19 narrows the criterion back to the requirement.

**The mechanism is this run's own output.** §3 `\include`s the generated LaTeX fragments rather
than hand-copying digits:

| Fragment | Size | Location |
|---|---|---|
| `benchmark_grid.tex` | 10,438 B | inside the committed 147 |
| `cpr_derived_values.tex` | 131 B | inside the committed 147 |
| `cpr_grouping.tex` | 938 B | inside the committed 147 |

All three sit beside the artifacts that produced them, at a sha `gate3_git_sha_consistency` proves
is **single**. Committing them **is** the traceability mechanism.

**Stated plainly, because it is the thing most likely to be misread later:**

- **Phase 29 built no mapping document against the manuscript.**
- **`main.tex` is not in this repository** — it lives under
  `OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/`.
- **The manuscript-side half is POST-01, in Phase 30.** Nothing in Phase 29 touched §3, `main.tex`,
  the DOI citation, or the data-availability wording.

---

## Criterion 6 — the Zenodo results package

**AMENDED 2026-08-25 by the author: a calendar date became an event.** The criterion read
*"before the 2026-08-21 submission"*; that date passed while the re-freeze and re-run were in
flight, which made the criterion ungradeable as written. It is now scoped to the **ordering** —
publication must precede submission, whenever submission happens.

**Phase 29 cannot observe the submission event and does not pretend to.**

### Record A — immutable inputs — **PUBLISHED**

| | |
|---|---|
| Deposition | **22116461** |
| Version DOI | **`10.5281/zenodo.22116461`** — measured resolving, HTTP 200 |
| Concept DOI | **`10.5281/zenodo.22116460`** — measured resolving, HTTP 200 |
| Payload | `real-rig-inputs.zip`, **4,341,018,405** bytes, md5 **`d95a1abc3f7089443ea2bc7ea12fb599`** |
| Contents | `extrinsic/`, `intrinsic/`, `README.md` — 3,996 entries, **zero** containing `reference_outputs` |
| Round trip | server checksum and size equal the local digest and length of the exact bytes uploaded |
| Creator record | ORCID `0000-0003-4074-7128` |

### Record B — versioned results package — **STAGED, UNPUBLISHED**

| | |
|---|---|
| Deposition | **22117061** — `https://zenodo.org/deposit/22117061` |
| Payload | `real-rig-results-2.1.0.zip`, **9,503,394** bytes, md5 **`f033538e1c9da165aa6267f4ae5d4f78`** |
| State at last read (19:15:10Z) | `state: "unsubmitted"`, `submitted: false`, `doi: null`, `doi_url: null`, `conceptdoi: null`, `links.record: null`, 1 file |
| Structured provenance | `isDerivedFrom` → **`10.5281/zenodo.22116461`** (Record A's **version** DOI, deliberately not the concept DOI) |
| Supersession | `references` → `10.5281/zenodo.21889922`, plus prose in the description and README. **Zero** version relations against `21889922` |
| `version` field | **`2.1.0`** |
| `optimality` labelling | present in the packaged README, covering all three ROADMAP-mandated caveats |

Payload provenance was proven in **both** directions: all ten members are md5-identical to the
artifacts they were copied from, and all six `reference_outputs/` digests **differ** from the
published archive's copies of the same names. The second check is the one that proves the
supersession is real rather than a relabelling.

### The A↔B linkage ruling

The author ruled **`sequential`**: publish A, then build B against A's minted DOI. The accepted
cost is that **Record A carries no structured `isSourceOf` back-link to Record B** — adding one
requires `deposit:actions`, which the automation token deliberately does not hold. This is a named
manual UI task, carried forward below, not a defect.

### Status of criterion 6 as of this record

**OPEN — awaiting Publish on Record B.** What remains:

1. **v2.1.0 must be cut first.** Record B's metadata and README cite `2.1.0`, which **does not yet
   exist as a released version**. Publishing before the release cut would mint a permanent record
   naming a version that does not exist.
2. The author opens `https://zenodo.org/deposit/22117061`, **reads the rendered description end to
   end**, and presses Publish.
3. The author then adds Record A's `isSourceOf` back-link by hand.
4. The author confirms the ordering against submission.

**Both of items 1 and 2 are owned by Phase 29.2** (see *Phase 29.2 owns the release and the
publication*, below). Criterion 6 closes on the author's explicit, dated confirmation — never on
an inference by this phase.

> **Ruling on Task 3's one-way door:** *(to be recorded here with its option id and date when the
> author rules — this record is written before that checkpoint resolves.)*

---

## Test and gate state

| Measure | Before | After | Note |
|---|---|---|---|
| `tests/unit/test_experiments_provenance.py` | **8 failed**, 279 passed, 20 skipped | **0 failed**, 287 passed, 20 skipped | all eight were assertions encoding expectations that moved by design (D-29-13) |
| `pytest tests/` (full suite) | **11 failed** | **3 failed**, 2394 passed, 21 skipped | the three are D4's ruled exact-equality anchors |
| Five tree-keyed control modules | — | **245 passed** | rules out any other tree-sensitive contributor |

**Three is the expected count. Zero and four are both anomalies** (D-29-15). The three, by node id:

- `tests/unit/test_discard_accounting.py::test_matches_frozen_anchor`
- `tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector`
- `tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`

**Nothing was silenced.** No `pytest.skip`, no `xfail`, no `--deselect`, no `-k`, no loosened
tolerance, no artifact edited, and `tests/unit/_baseline_paths.py` untouched. The repair is one
commit (`5799b14`) touching exactly one file, landing strictly after and leaving unamended the
`70e783f` artifacts commit.

**The 4→8 flip was predicted and is not a regression.** `_is_tracked()` reads the git *index*, so
the CSV rails could not see the artifacts until 29-05 staged them. The count moved 4 → 8 at the
moment of staging, exactly as `28-RUN-RECORD.md`'s D1 predicted, and then 8 → 0 on repair.

**One measured figure did not match the plan's prose and is recorded as measured** (D-29-12): the
plan predicted `2407 passed, 26 skipped`; the suite reported `2394 passed, 21 skipped`. The gated
quantity — the failure count — is exactly 3 with exactly the three ruled node ids, and collected
totals reconcile cleanly at 2418 before and after.

---

## D-29-10's stop list, evaluated

D-29-10 names the only three findings that block publication. Anything outside them is fixed if
cheap, ruled on if not, and **never blocks**. All three were evaluated:

| # | Stop-list item | Measured verdict | Evidence |
|---|---|---|---|
| 1 | **The E2 same-seed control fails** (seed 42 vs seed 42, ~1e-8) | **DID NOT FIRE.** Worst case 3.6317e-08 against a `DRIFT_LIMIT` of 1e-06 — four orders of magnitude clear. `RESULT: PASS` | `29-e2-control.txt` |
| 2 | **`gate3_git_sha_consistency` stops holding on the committed tree** | **DID NOT FIRE.** PASS on the single sha `7005a2771aa115e4f4c1284cec7e145739586a4a`, over the **committed** tree, which is the form the stop list cares about | `29-gates-committed.txt` |
| 3 | **A §3-facing number traces to an artifact that disagrees with it** | **DID NOT FIRE, repo-side.** Criterion 2: the §3 headline reproduces to 4.8962e-09. Criterion 3: the primary published sign test is unchanged at 10/10, p = 0.00098; the secondary refined pairing moved 8/10 → 7/10, and **the artifact and the record agree with each other — it is the *manuscript* that now carries a superseded digit.** That is a manuscript-side reconciliation (POST-01, Phase 30), raised here as D-29-16 requires, and it is a *disagreement between the paper and the artifact*, not between two artifacts | `29-e2-control.txt`, `29-e7-before-after.txt`, `29-commit-manifest.txt` |

**D-29-09 governs everything outside those three:** the outputs are scientifically valid and are to
be published, *"barring a finding that refutes that."* No such finding was made.

---

## Open items handed forward

Everything Phase 29 deliberately did **not** do, written down so a later session acts on a written
record rather than re-deriving anything.

### 1. Publish Record B — and read its rendered description first

Filed as `.planning/todos/pending/2026-08-26-publish-record-b-and-add-record-a-back-link.md`,
which also carries item 2 below and the v2.1.0 ordering constraint from item 4.

`https://zenodo.org/deposit/22117061`. **Read the rendered description end to end before pressing
Publish.** Record A shipped with placeholder-looking prose — `(linked below once Record B exists)` —
that a token-based grep did **not** catch, because plan 29-04 had already substituted the token
away. It was fixed pre-publication only because the author read the record. *A token-based check
verifies that a substitution ran, not that its result is finished text.*

### 2. Then add Record A's `isSourceOf` back-link by hand

`https://zenodo.org/records/22116461` → Edit → Related identifiers → `isSourceOf` → Record B's
minted DOI, scheme `doi`. **Editing published metadata neither cuts a new version nor changes the
DOI.** This is the accepted, ruled cost of the author's `sequential` linkage choice: **Record A
currently carries NO structured A→B link.** The automation token cannot do it — `deposit:actions`
is deliberately absent. Filed with item 1, in
`.planning/todos/pending/2026-08-26-publish-record-b-and-add-record-a-back-link.md`.

### 3. Phase 29.2 owns the release and the publication — cross-reference it

`.planning/ROADMAP.md` § **Phase 29.2: Merge, Release, and Publish** was inserted 2026-08-26 and
carries all of the following. It is the owner; Phase 29 stops at its boundary.

- **Fix CI's `pre-commit` job.** `test.yml` runs `pre-commit run --all-files` on **both**
  `push: [main]` **and** `pull_request: [main]`. 143 committed artifacts deliberately lack a final
  newline (plus 439 trailing-whitespace hits). The job modifies the runner's checkout and exits
  non-zero — it cannot write back, so this is a **blocked merge, not data corruption**. Resolve by
  scoping the job to changed files or excluding `experiments/results/`.
  `.pre-commit-config.yaml` is editable again there; **D-29-17's fence was Phase-29-scoped.**
- **PR into `main` with a MERGE COMMIT — never a squash.** A squash collapses 406 commits into one
  message, and semantic-release parses only that message; if it reads as `docs:`, **no release
  fires at all and the failure is silent.**
- **Verify `release.yml` cuts `v2.1.0`** — 43 `feat`, 29 `fix`, zero breaking-change markers across
  the 406 commits yields a **minor** bump. Confirm **`secrets.RELEASE_TOKEN` exists** before
  relying on the workflow.
- **Then publish**, A's back-link included.

### 4. Record B cites `2.1.0`, which does not exist yet

Record B's `version` field and its README both name **`2.1.0`**. **v2.1.0 must be cut before Record
B is published**, or the permanent record names a version that does not exist. This is Phase 29.2
criterion 3 gating Phase 29.2 criterion 4, and it is the reason the release was inserted *before*
Phase 30 rather than inside it.

### 5. The `zenodo_record_id` pin — ten sites, Phase 30 / POST-01, flagged not decided

`src/aquacal/datasets/data/manifest.json` and `src/aquacal/datasets/_manifest.py`'s consumers still
pin **`zenodo_record_id: 21889922`**. The split changes what consumers should download. **Scoped
forward, not decided here** — nothing in Phase 29 needed the pin to move, and four of the ten
affected sites are **inside the frozen `experiments/` tree**.

Filed with its full ten-site table as
`.planning/todos/pending/2026-08-26-repoint-the-dataset-manifest-after-the-zenodo-split.md`.

Two `loader.py` findings from plan 29-01 travel with it:

- **`loader.py:79-86`** resolves `reference_calibration.json` from the **same extracted directory as
  the frames**. After the split, `load_example('real-rig')` needs **both records fetched and
  merged** into one cache layout.
- **`loader.py:90`** looks for a **`config.yaml`** that exists in **neither** archive (both ship
  `config_paper.yaml`) — a **pre-existing silent no-op**, untouched, and no worse after the split.

### 6. Record A's zip root is FLAT — Phase 30's loader work strips a different prefix

Record A's archive puts `extrinsic/`, `intrinsic/` and `README.md` at the **root**, with **no
`real-rig/` wrapper**. Published record `21889922` wraps everything in `real-rig/` — which is why
extracting it into `aquacal_data/real-rig/` yields the doubled `aquacal_data/real-rig/real-rig/`.
**Record B's archive is flat too.** New extraction logic is required under any split; the flat root
only changes *which* prefix that logic strips. Record A: md5
`d95a1abc3f7089443ea2bc7ea12fb599`, size `4341018405`. Record B: md5
`f033538e1c9da165aa6267f4ae5d4f78`, size `9503394`.

### 7. Phase 30's dependency still names the passed 2026-08-21 submission date — roadmap hygiene

`.planning/ROADMAP.md` § Phase 30 reads *"Depends on: Phase 29, and the 2026-08-21 SoftwareX
submission (calendar dependency)"*. **That date has passed.** Phase 29's criterion 6 was amended
away from that exact date on 2026-08-25 for exactly this reason; Phase 30 will mis-gate the same
way until it gets the same treatment — re-scope the dependency from a **date** to the **submission
event**. Recorded as a roadmap-hygiene item; not fixed here, because amending a phase's dependency
is the author's ruling, as the 2026-08-25 amendment was. Filed as
`.planning/todos/pending/2026-08-26-phase-30-dependency-still-names-the-passed-2026-08-21-submission-date.md`.

### 8. The legacy Zenodo deposit API's deprecation posture — MEDIUM confidence

`developers.zenodo.org` carries **no deprecation banner** for the deposit API, and it is what Zenodo
documents and what its own maintainer's reference upload uses. Community reporting says new
integrations should not rely on it long term; InvenioRDM's native `/api/records/{id}/draft` exists
alongside and **replaces the whole draft resource including metadata**, which is a sharper edge for
a two-record link job. **MEDIUM-confidence community sourcing, not an official statement.** The risk
is only that a future re-upload needs rework. Filed as
`.planning/todos/pending/2026-08-26-legacy-zenodo-deposit-api-deprecation-posture.md`.

### 9. Do not open a pull request from `results/rerun-freeze-02` into `main` without the CI fix

No PR was opened by this phase. Attempt 1's branch was never merged either. Opening one today
fires `pre-commit run --all-files` against **147** artifacts in CI. Filed as
`.planning/todos/pending/2026-08-26-no-pull-request-into-main-until-ci-pre-commit-is-scoped.md`,
and owned by **Phase 29.2 criterion 1**.

### 10. D-29-14 fall-throughs — the residuals from `29-rails-after.txt` §7

D-29-14 says anything neither assertion-wrong nor cheaply fixable becomes a post-submission todo
naming what fails and what would fix it, rather than being forced.

**All eight D1 provenance-rail failures were assertion-wrong and all eight were repaired; none had
to be deferred.** Two residuals were recorded:

| Residual | What fails | What would fix it | Disposition |
|---|---|---|---|
| **1 — D4's three exact-equality anchors** | the three node ids listed under *Test and gate state* | re-capture the three anchors on Linux, **or** convert the three exact-equality assertions to a documented ULP-scale comparison with the cross-platform reason stated at the constant | Already **RULED** in the `rerun-freeze-02` tag annotation and `29.1-PREPUSH-AUDIT.md` §1; D-29-15 names three as the expected count. Repairing here would be the over-correction that decision exists to forbid. Filed as `.planning/todos/pending/2026-08-26-d4-exact-equality-anchors-are-platform-pinned.md` |
| **2 — the suite runs serially at 30–90 minutes** | nothing; a wall-clock cost, not a defect | `pytest-xdist` | **Already filed**: `2026-08-17-parallelize-the-test-suite.md` and its `-with-pytest-xdist` twin. Noted only because it is why 29-06's full-suite "before" run could not be completed inside that plan |

### 11. Pre-existing STATE.md format divergence — not caused by this phase

`gsd-tools query state.advance-plan` and `state.update-progress` error against this project's
`STATE.md` body with *"Cannot parse Current Plan or Total Plans"* and *"Progress field not found"*.
Several plans in this phase hit it. **It predates Phase 29** and no plan attempted to reshape
`STATE.md` to satisfy the tooling — rewriting a project's state document to please a parser is not
a change any single plan should make unilaterally. Filed as
`.planning/todos/pending/2026-08-26-state-md-body-format-diverges-from-gsd-state-handlers.md`.

### 12. The E1 four-seed correction has a twin site

29-06's `seeds 42-51` → `seeds 42-45` correction is the same defect class as the completed todo
`2026-08-20-e1-band-scope-string-still-claims-ten-seeds-after-ruling-A1-cut-it-to-four.md`, which
corrected the **sidecar's** `scope` string in `e1_refractive_comparison.py`. Anyone auditing Ruling
A1's blast radius should treat those two sites as a pair.

---

## Things this phase deliberately did not touch

| | |
|---|---|
| `main.tex`, §3, the DOI citation, the data-availability wording | Not in this repository. The author's edits (D-29-19). **No manuscript file was opened, read for editing, or written.** |
| `experiments/` | Immutable and committed. `git status --porcelain experiments/` is empty; no stage was re-run, no artifact regenerated. |
| `.gitignore`, `.pre-commit-config.yaml` | Unchanged (D-29-17). |
| `src/aquacal/datasets/data/manifest.json`, the two `tests/` assertions on `21889922` | Scoped to Phase 30 / POST-01, not decided (item 5). |
| `~/aquacal-frozen-rerun-freeze-02-prod` | The second independent copy of the run. Read only; verified unmutated. |
| Zenodo record `21889922` | Read once for a reachability probe. Not modified, deleted, re-versioned or withdrawn. |
| `pre-commit run --all-files` | **Never invoked**, in any plan. Every hook run was scoped with `--files`. |
| Publishing from automation | **No publish code path exists** in `scripts/zenodo_upload.py` — not dead code, not commented scaffolding. The token carries `deposit:write` only. Publish is the author's act in the web UI (D-29-01). |

---

*Phase: 29-gate-verification-results-commit*
*Record written: 2026-08-26*
