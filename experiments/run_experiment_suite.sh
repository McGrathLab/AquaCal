#!/usr/bin/env bash
#
# ============================================================================
# THE SUITE DRIVER (DRIVER-01, D-25).
# ============================================================================
#
# This is THE entry point for the full experimental suite. One invocation
# covers every experiment in the paper. `experiments/rerun_19_3.sh` (renamed
# into this file via `git mv`, so `git log --follow` still reaches its whole
# history), `experiments/rerun_19_4.sh` and `experiments/rerun_19_5.sh` are
# HISTORICAL drivers; plan 26-09 archives them. Do not launch them.
#
# The name is `run_experiment_suite.sh`, not `run_suite.sh` (D-25): in this
# repository "run the suite" already means pytest in every CLAUDE.md warning,
# and a driver that answers to the same phrase as a 26-88 minute test run is a
# trap for the next operator.
#
# WHY THIS FILE EXISTS AT ALL. The audit's finding F-001 was not "a gate failed
# and we kept going". It was a run that EXITED 0 AND LOOKED GREEN while a band
# CSV was never produced at all, because no driver ever invoked the script that
# produces it. Coverage -- one driver invocation covering every invocation in
# the suite -- is the whole point. Nothing must be left for the run machine to
# discover is missing at hour 18.
#
# This file is the UNION of the three historical drivers, lifted from
# `rerun_19_5.sh` (the most evolved base: the hard-abort pre-flight probe, the
# pinned gate interpreter, the dry-run state-file separation) rather than
# extended from 19.3, plus the seven invocations no driver has ever run:
# E2's production/classification, timing and memory runs, the three orphan
# scripts (e7_focal_standoff_analysis, reconstruction_bootstrap,
# fd_jacobian_accuracy) and E1's noise-axis band.
#
# ============================================================================
# THE TWO ABORT RULES. THEY LOOK CONTRADICTORY. READ BOTH.
# ============================================================================
#
# D-01 -- A COMPLETENESS OR GATE FAILURE NEVER ABORTS THE QUEUE.
#   E1, E5, E6, E7, E2 and E4 are independent and their measurements are still
#   wanted even after one of them fails a check. A failure instead sets a
#   STICKY FLAG that makes the driver's FINAL exit non-zero, with a loud
#   terminal summary block naming every missing or short artifact.
#
#   Rationale, stated plainly because it is the reason the rule is shaped this
#   way: this project's injury has never been "we kept running after a gate
#   failed" -- it has been A RUN THAT EXITED 0 AND LOOKED GREEN WHILE A BAND
#   CSV WAS NEVER PRODUCED AT ALL (F-001). An exit code that cannot lie kills
#   that class of failure without discarding hours of valid work.
#
#   (The sticky flag and the end-of-run roll-up are implemented by plan 26-08.
#   This file's job is the stage list they schedule.)
#
# D-03 -- PRE-FLIGHT FAILURE ABORTS.
#   Pre-flight runs BEFORE stage 1, so nothing is lost, and the entire point is
#   trading minutes for twenty-plus hours. D-01's "never abort" governs stages
#   1..N only. `prelaunch_probe` is the historical instance of this rule: an
#   illegal seed means the seed list itself is wrong, so continuing past it
#   would spend hours computing something that cannot be reported.
#
# D-50 -- EVERY PRE-FLIGHT REFUSAL PRINTS THE EXACT OVERRIDE FLAG THAT BYPASSES
#   IT, AND NOTHING MAY ABORT ONCE STAGE 1 HAS BEGUN. A malformed check then
#   costs one minute and one flag, never a night. This is what makes the
#   surviving refusals safe rather than merely fewer.
#
# ============================================================================
# ORDERING (D-37), AND WHERE ORDERING IS NOT A HEURISTIC BUT A CORRECTNESS
# CONSTRAINT.
# ============================================================================
#
# Stages are sequenced SHORTEST-FIRST, so a systematic failure surfaces in
# seconds rather than after the longest stage. That purpose gets more valuable
# as the tail grows, not less.
#
# BUT `depends_on` WINS OVER WALL CLOCK wherever the two conflict. The
# dependency edges live in `experiments/suite_expectations.json` and are
# machine-readable; `tests/unit/test_suite_stage_list.py` proves this array is
# a topological order of them. Two edges are silent-wrong-number bugs rather
# than crashes if violated, so they are named here:
#
#   * `e4` MUST follow `e2_production`. `resolve_e2_benchmark_path`
#     (`experiments/e4_benchmark_grid.py:298`) silently DROPS the real-rig row
#     when E2's `benchmark.json` is absent, and `benchmark_grid.csv` comes back
#     with 9 rows instead of 10. Nothing fails; the number is just wrong.
#   * `e7_focal_standoff` MUST follow `e7_band`. It reads the hardcoded,
#     cwd-relative `Path("experiments/results")/interface_ablation_band.csv`
#     (`e7_focal_standoff_analysis.py:389`), deliberately ignoring `--out`.
#
# E3's `--check` and `--force` are ONE ATOMIC STAGE and the order inside it is
# load-bearing: `--check` FIRST records the pre-regeneration state of all three
# tiers; `--force` SECOND regenerates the committed tier CSVs and LaTeX
# fragments. Running `--force` first destroys the only evidence of what moved.
# A resumed e3 always re-runs BOTH invocations from scratch.
#
# ============================================================================
# STATE, RESUME AND THE STALE-STATE FOOTGUN (D-23 as halved by D-48).
# ============================================================================
#
# The state file's PATH EMBEDS THE FROZEN SHORT SHA:
#   experiments/run_experiment_suite_state.<short_sha>.tsv
# so a state file written at another commit is STRUCTURALLY UNREACHABLE rather
# than merely detected. The hazard being closed is exact: rename the script,
# keep the state file, and every stage is skipped -- the suite does nothing and
# EXITS 0. State files accumulate one per sha. That is acceptable and
# deliberate; they are small, and each is the timing record for its own run.
#
# There is deliberately NO refusal to start when a state file's sha disagrees
# with HEAD (D-48 cut it). That was the half of the protection that can wrongly
# block a 3 a.m. resume, which is the one moment the driver exists to survive.
#
# A DRY RUN MUST NOT WRITE THE REAL RUN'S STATE FILE. Automatic resume skips
# any stage carrying a completion line, so a dry run -- which "completes" every
# stage in about a second -- would otherwise leave a state file that makes the
# NEXT REAL LAUNCH A SILENT NO-OP: every stage skipped, exit 0, no artifacts,
# and a queue that looks like it succeeded. Found 2026-08-06 by dry-running
# `rerun_19_5.sh` and inspecting what it left behind. Separate paths are the
# structural fix; remembering to delete the file is not.
#
# TWO RESUME SEMANTICS, AND THEY ARE NOT INTERCHANGEABLE:
#   - Automatic resume (a stage with a recorded completion line is skipped) and
#     `bash experiments/run_experiment_suite.sh N` (start from the 1-indexed
#     stage N) exist for INFRASTRUCTURE failures only: a box reboot, a 3 a.m.
#     process kill, a full disk.
#   - They are NEVER the recovery path for a src defect. That is always
#     restart-from-stage-1, because a partial result set spanning two trees is
#     exactly what the abort protocol below forbids.
# A stage that started and then died carries a start line with NO matching
# completion line, and is re-run FROM SCRATCH on resume -- never treated as
# done.
#
# ============================================================================
# ABORT PROTOCOL -- PRE-COMMITTED, so it is not decided mid-run. Restated
# verbatim in substance from rerun_19_4.sh / rerun_19_5.sh.
# ============================================================================
#   1. A src defect discovered at ANY stage means ABORT THE QUEUE, fix it, and
#      RESTART FROM STAGE 1. Not resume. Not patch-and-continue.
#   2. NEVER edit src/ or experiments/ while the queue is in flight. This run
#      holds ONE git sha across every artifact; a midstream edit destroys that
#      silently and yields a result set assembled from two different trees.
#      That is unreportable, and the damage is invisible until someone diffs
#      provenance.
#   3. Each stage's artifacts record their git sha. A cross-stage sha MISMATCH
#      is a HARD FAILURE, not a warning (check_rerun_gates.py's
#      gate3_git_sha_consistency enforces this).
#
# D-27 -- THE COMMIT RULE, RESTATED PRECISELY FOR TWO-MACHINE OPERATION.
#   The real constraint is that THE RUN MACHINE'S TREE MUST NOT MOVE: no pull,
#   no checkout, no commit THERE. A per-stage `git rev-parse` would otherwise
#   split one run's artifacts across two shas.
#   Work on the PLANNING BOX, INCLUDING COMMITS AND PUSHES, IS SAFE and is
#   EXPECTED TO CONTINUE DURING THE RUN. The over-broad "commit nothing
#   anywhere" version would idle the planning box for the whole window for no
#   reason.
#   This script itself performs NO tree-mutating git operation -- no staging,
#   committing, tagging, checking out or pushing -- on any path, including the
#   resume path. It reads `git rev-parse HEAD` exactly once, at the very start,
#   purely to name the commit every artifact is attributable to.
#
# ============================================================================
# LAUNCH
# ============================================================================
#
#   nohup bash experiments/run_experiment_suite.sh > experiments/run_experiment_suite.log 2>&1 & disown
#
# NEVER via `run_in_background`, and NEVER from a subagent. That harness kills
# background commands at 35-50 min, and a subagent that backgrounds a long run
# and returns has stalled permanently -- this project has already lost multiple
# sweeps and multiple hours to both (CLAUDE.md, "Never let a subagent background
# a long run and return").
#
# EVERY experiment invocation runs UNBUFFERED (`python -u`). Python
# block-buffers stdout to a pipe; without `-u` a detached run's log is empty
# whether it is progressing normally or hung on the first video -- the two are
# indistinguishable, and a real stall stays invisible until the timeout.
#
# STAGE-LEVEL RECOVERY STATE: every stage transition is appended to the state
# file as `<stage>\t<index>\t<event>\t<iso-time>\t<exit-code>`. A start line is
# written BEFORE a stage launches and a completion line only AFTER it returns.
# These ISO stamps are the ONLY per-stage timing record that exists anywhere in
# this project -- `suite_expectations.json`'s measured wall-clock estimates are
# derived from them.
#
# GATE VERDICTS ARE FINDINGS, NOT AUTOMATIC ABORTS (except pre-flight, above).
# After each stage, check_rerun_gates.py runs against that stage's output
# directory and its PASS/FAIL/N-A verdict is written into the log inside a
# delimited block. The abort-on-src-defect rule is an OPERATOR judgment made by
# reading gate verdicts and logs, never an automatic script behaviour.

set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# The `cd` is load-bearing, not tidiness: e7_focal_standoff_analysis and
# reconstruction_bootstrap both read hardcoded, cwd-relative paths under
# `experiments/results`.
cd "${REPO_ROOT}" || exit 1

OUT_DIR="experiments/results"
OUT_DIR_E4_REPEAT="experiments/results_e4_repeat"
OUT_DIR_E2_BAND="experiments/results_e2_band"

# The frozen sha. Read ONCE, here, and never again -- see D-27 above. Short
# form only; it names the state file. `--short` is portable across the git
# versions on both boxes; `git describe` is deliberately not used here (it
# needs a tag and would be empty on an untagged commit).
FROZEN_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "unknownsha")"

# D-23 as halved by D-48 (sha-derived path) + the 19.5 dry-run separation.
if [ -n "${RUN_EXPERIMENT_SUITE_DRY_RUN:-}" ]; then
  STATE_FILE="experiments/run_experiment_suite_state.${FROZEN_SHA}.dryrun.tsv"
else
  STATE_FILE="experiments/run_experiment_suite_state.${FROZEN_SHA}.tsv"
fi

# --- Seed lists -------------------------------------------------------------
#
# WHY 6 SEEDS AND NOT 5 OR 10 (E6, E5) / 3 (E2). A ten-seed unanimous sign test
# gives p = 2^-10 one-sided. FIVE gives p = 2^-5 = 0.031 one-sided but
# 2 x 2^-5 = 0.0625 TWO-SIDED, which does NOT clear 0.05 -- so a five-seed
# result is significant or not depending purely on which convention a reader
# applies. SIX gives two-sided p = 0.031, clearing 0.05 under EITHER convention.
# E7 keeps TEN: its seed spread is itself the cited quantity in four
# response-letter rows, and the cut was offered and rejected.
#
# The pre-launch legality probe reads E6_BAND_SEEDS from THIS file rather than
# keeping its own copy, so the two cannot silently diverge. A hardcoded copy did
# exactly that on 2026-08-06 -- the log announced 42-47 while the probe still
# checked 42-46, so the one seed most in need of checking was the one skipped.
# Do not reintroduce a literal anywhere below.
BAND_SEEDS="42,43,44,45,46,47,48,49,50,51"
E6_BAND_SEEDS="42,43,44,45,46,47"
E5_BAND_SEEDS="42,43,44,45,46,47"
E2_BAND_SEEDS="42,43,44"

# The three camera counts the prelaunch legality probe and E4's repeat cells
# both use.
PROBE_N_CAMERAS="8,12,16"

# E4's repeat subset: exactly the three 100-frame cells MF-03's
# runtime-inversion finding rests on. The 200-frame cells are
# near_physical_ceiling (11.3 GiB peak on a 15.7 GiB box) -- repeating those
# risks an OOM that would abort the whole queue for a number nobody is quoting.
E4_REPEAT_CELLS=("8x100" "12x100" "16x100")

# E2's production release config -- the source `emit_seed_variant_configs` and
# `emit_invocation_configs` read from and refuse to write into or under
# (release-tree write refusal, T-19.5-07-01 / T-26-17). This path resolves on
# the WINDOWS PLANNING BOX ONLY, which is why it is an overridable variable
# rather than a literal: Phase 27 repoints it for the Linux run machine.
E2_RELEASE_CONFIG="${SUITE_E2_RELEASE_CONFIG:-C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml}"

# check_rerun_gates.py imports pandas AND aquacal.datasets.synthetic /
# experiments.e4_benchmark_grid (its legality_probe), so it needs the AquaCal
# env, not Git Bash's bare `python` (which is Anaconda base on this box). Same
# pin and override variable as prelaunch_gate.sh. Falls back to bare `python`
# only if the pinned interpreter is absent, so a missing env degrades the GATE
# to a logged finding rather than aborting a production stage -- EXCEPT
# pre-flight, whose own failure (including an absent interpreter) is a hard
# abort per D-03.
GATE_PYTHON="${PRELAUNCH_GATE_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
if [ ! -x "${GATE_PYTHON}" ] && ! command -v "${GATE_PYTHON}" >/dev/null 2>&1; then
  echo "WARNING: pinned gate interpreter not found at ${GATE_PYTHON}; falling back to bare 'python'. Gate verdicts may fail to import pandas." >&2
  GATE_PYTHON="python"
fi

# Stage list. Task 2 of plan 26-07 replaces this with the full suite; it is
# kept in topological order of suite_expectations.json's depends_on edges,
# shortest-first within each dependency level.
STAGES=(prelaunch_probe e3 e1 e7 e5 e2_band e6_repeat1 e4 e6_band e4_repeat e5_band)
START_STAGE="${1:-1}"

log() {
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*"
}

is_stage_complete() {
  # A stage counts as complete only if the state file carries a "complete"
  # event line for it -- a start-only line (started, then died) never matches.
  local name="$1"
  [ -f "${STATE_FILE}" ] || return 1
  awk -F'\t' -v stage="${name}" '$1 == stage && $3 == "complete" { found = 1 } END { exit !found }' "${STATE_FILE}"
}

state_start() {
  local name="$1" idx="$2"
  printf '%s\t%s\tstart\t%s\t\n' "${name}" "${idx}" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >>"${STATE_FILE}"
}

state_complete() {
  local name="$1" idx="$2" exit_code="$3"
  printf '%s\t%s\tcomplete\t%s\t%s\n' "${name}" "${idx}" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "${exit_code}" >>"${STATE_FILE}"
}

run_gate_check() {
  local target_dir="$1" stage_name="$2"
  echo "----- GATE VERDICT: stage=${stage_name} out_dir=${target_dir} -----"
  # PINNED INTERPRETER, and it matters: check_rerun_gates.py imports pandas and
  # aquacal, so it is NOT stdlib-only. Never a bare `python` here -- that was a
  # real 19.3 defect, fixed in 19.4/19.5 and asserted by
  # tests/unit/test_suite_stage_list.py.
  "${GATE_PYTHON}" experiments/check_rerun_gates.py "${target_dir}"
  local gate_exit=$?
  echo "----- END GATE VERDICT: stage=${stage_name} exit=${gate_exit} -----"
  # D-01: recorded as a finding, never acted on automatically -- this
  # function's own exit is always 0 so a gate FAIL never aborts the queue.
  # Plan 26-08 adds the sticky flag that carries it to the FINAL exit code.
  return 0
}

_dry_run_active() {
  # Used ONLY by the driver's own mechanics tests (stage sequencing, gate
  # invocation, resume). Every acceptance and production run is at full scale,
  # never substituted. Deliberately NOT the `--smoke` flag every experiment
  # shares: `--smoke` exercises real (if smaller) code paths and is explicitly
  # not evidence at production scale. This is a stronger substitution used only
  # to prove the QUEUE's own control flow, and is never cited as evidence about
  # geometry or convergence.
  [ -n "${RUN_EXPERIMENT_SUITE_DRY_RUN:-}" ]
}

_dry_run_stub() {
  eval "${RUN_EXPERIMENT_SUITE_DRY_RUN_CMD:-true}"
}

run_stage_prelaunch_probe() {
  # A HARD-ABORT stage (D-03). A structural geometry check, no calibration
  # solve, seconds not minutes.
  if _dry_run_active; then
    log "prelaunch_probe: DRY RUN"
    _dry_run_stub
    return $?
  fi
  log "prelaunch_probe: legality_probe over seeds ${E6_BAND_SEEDS} x n_cameras ${PROBE_N_CAMERAS}"
  PROBE_SEEDS="${E6_BAND_SEEDS}" PROBE_CAMS="${PROBE_N_CAMERAS}" \
  "${GATE_PYTHON}" - <<'PY'
import os

from experiments.check_rerun_gates import legality_probe

seeds = [int(s) for s in os.environ["PROBE_SEEDS"].split(",") if s.strip()]
camera_counts = [int(c) for c in os.environ["PROBE_CAMS"].split(",") if c.strip()]
results = legality_probe(seeds, camera_counts)
n_fail = sum(1 for r in results if r.verdict == "FAIL")
for r in results:
    print(f"[{r.verdict:4s}] {r.gate} -- {r.detail}")
print()
print(f"TOTAL: {len(results)} checked, {n_fail} FAIL")
raise SystemExit(1 if n_fail else 0)
PY
}

run_stage_e3() {
  # ONE ATOMIC STAGE, two invocations, and the order is load-bearing -- see the
  # header. A resume always re-runs both from scratch; it must never resume
  # into the second alone, which would silently lose the tier-by-tier `--check`
  # output only the first invocation produces.
  log "e3: --check FIRST (tier-by-tier snapshot of the pre-regeneration state)"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e3_derived_quantities --check --out "${OUT_DIR}"
  fi
  log "e3: --check exit=$?"
  log "e3: --force SECOND (regenerates the committed tier CSVs/LaTeX fragments)"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e3_derived_quantities --force --out "${OUT_DIR}"
  fi
  local force_exit=$?
  log "e3: --force exit=${force_exit}"
  return "${force_exit}"
}

run_stage_e1() {
  # Single-seed production run. E1's production SCENARIO_NAME is "realistic".
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"
}

run_stage_e7() {
  # Single-seed production run. E7 runs the "realistic" scenario, which
  # resolves to generate_real_rig_array()'s frozen shared WATER_Z and never
  # calls generate_camera_array.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"
}

run_stage_e7_band() {
  # MF-05's per-arm bands are the milestone's only surviving accuracy claim.
  # TEN seeds: the spread is itself the cited quantity (see the seed-list note).
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e7_interface_ablation \
    --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"
}

run_stage_e5() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"
}

run_stage_e5_band() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e5_index_sensitivity \
    --seeds "${E5_BAND_SEEDS}" --out "${OUT_DIR}" --force
}

run_stage_e6_repeat1() {
  # Never silently reuse a stale partial checkpoint set from an earlier died
  # attempt at THIS stage: clear e6's own artifacts under the shared OUT_DIR
  # before (re-)running, then --force regenerates everything from scratch.
  #
  # `--include-per-camera-latex` STAYS OFF (D-11). The flag renders
  # shared_interface=False rows into cpr_grouping.tex, but tab:cpr
  # (supplement.tex:449) has six rows that are ALL shared-interface, and the
  # generated fragment is not \input anywhere. Turning it on would produce a
  # LaTeX fragment nothing reads and invite a reader to believe it is the
  # source of a table it does not feed.
  log "e6_repeat1: clearing any partial E6 state under ${OUT_DIR} before running"
  rm -rf "${OUT_DIR}/e6_configs"
  rm -f "${OUT_DIR}/generalization_sweep.csv" "${OUT_DIR}/e6_provenance.json"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"
  fi
}

# -----------------------------------------------------------------------------
# `e6_repeat2` IS DELIBERATELY NOT A STAGE (D-42, which REVERSES CONTEXT's
# D-09). The paired determinism sweep was a Phase 19.3 deliverable; it is not
# part of the v2.1 suite and would add ~1.8 h for a number nothing cites.
# Its ISOLATION TEMPLATE is retained here because it is the correct shape for
# ANY future stage that must not reuse checkpoints -- E6 checkpoints and
# resumes by design, and `_SCENARIO_IDENTITY_KEYS` omits `seed`, so a second
# pass into a shared directory would silently degrade into a file-copy check
# reporting perfect (and meaningless) reproduction:
#
#   rm -rf "${OUT_DIR_ISOLATED}"; mkdir -p "${OUT_DIR_ISOLATED}"
#   stage_log="${OUT_DIR_ISOLATED}/stdout.log"
#   python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR_ISOLATED}" 2>&1 | tee "${stage_log}"
#   exit_code="${PIPESTATUS[0]}"                       # tee eats the real exit
#   grep -c "already exists (resumability)" "${stage_log}"   # 0 expected
#
# The last line is the POSITIVE re-solve signal: a genuine re-solve must show
# ZERO checkpoint-skip lines. `run_stage_e4_repeat` below uses this template.
# -----------------------------------------------------------------------------

run_stage_e6_band() {
  # Per-seed isolation is handled INSIDE e6_generalization_sweep.py's own
  # _run_seed_band: each seed's run goes into its own
  # ${OUT_DIR}/e6_band/seed_<N>/ directory, wiped and recreated before every
  # seed, because E6's checkpoint cache is seed-blind. This queue does NOT
  # re-implement that isolation -- it is mandatory correctness inside the
  # experiment script, not queue-level tidiness. No rm -rf of OUT_DIR is needed
  # or wanted here.
  if _dry_run_active; then
    log "e6_band: DRY RUN"
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e6_generalization_sweep \
    --seeds "${E6_BAND_SEEDS}" --out "${OUT_DIR}" --force
}

run_stage_e4() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"
}

run_stage_e4_repeat() {
  # Isolated directory, wiped before running -- never the shared OUT_DIR. Three
  # cells, BOTH repeats of each cell run back-to-back inside this ONE function.
  #
  # THE ADJACENCY IS ENFORCED STRUCTURALLY AND THAT IS THE POINT. COV-06's
  # deliverable is `seconds_total_spread_pct` -- run-to-run wall-clock spread.
  # One repeat cell (16, 100) pages rather than OOMs on a 15.7 GiB box; if the
  # two repeats of a cell met different memory pressure because something else
  # ran between them, the "spread" would measure paging, not the algorithm -- a
  # decomposition of pure noise, this project's most recurrent error.
  if _dry_run_active; then
    log "e4_repeat: DRY RUN -- skipping the pre-run clear of ${OUT_DIR_E4_REPEAT}"
    _dry_run_stub
    return $?
  fi
  log "e4_repeat: clearing ${OUT_DIR_E4_REPEAT} before running (isolated dir)"
  rm -rf "${OUT_DIR_E4_REPEAT}"
  mkdir -p "${OUT_DIR_E4_REPEAT}"
  local stage_log="${OUT_DIR_E4_REPEAT}/repeat_stdout.log"
  : >"${stage_log}"

  local cell exit_code=0
  local repeat
  for repeat in 1 2; do
    for cell in "${E4_REPEAT_CELLS[@]}"; do
      log "e4_repeat: repeat ${repeat}, cell ${cell}"
      python -u -m experiments.e4_benchmark_grid \
        --cell "${cell}" --out "${OUT_DIR_E4_REPEAT}" --force 2>&1 | tee -a "${stage_log}"
      local cell_exit="${PIPESTATUS[0]}"
      [ "${cell_exit}" -ne 0 ] && exit_code="${cell_exit}"
    done
  done

  # Positive re-solve signal (the isolation template above): every cell of both
  # repeats must have been genuinely computed, never skipped via a cached
  # checkpoint.
  local skip_lines
  skip_lines="$(grep -c "already exists (resumability)" "${stage_log}" || true)"
  log "e4_repeat: positive re-solve signal -- ${skip_lines} 'already exists (resumability)' skip line(s) found in ${stage_log} (0 expected for a genuine re-solve)"

  if [ "${exit_code}" -ne 0 ]; then
    return "${exit_code}"
  fi

  log "e4_repeat: splicing ${OUT_DIR_E4_REPEAT} against the committed benchmark_grid.csv"
  python -u -m experiments.e4_benchmark_grid \
    --splice-repeat "${OUT_DIR_E4_REPEAT}" --out "${OUT_DIR}"
}

run_stage_e2_band() {
  # Isolated in-repo SIBLING directory, wiped before running. Two phases:
  # (1) emit the three seed-variant configs + e2_band_scope.json (no
  # calibration), (2) run each variant's calibration SEQUENTIALLY (48-87 min
  # each). Never writes into or under the release tree (T-19.5-07-01), and not
  # under ${OUT_DIR} either, so a --check or gate run against ${OUT_DIR} never
  # confuses band output with the production E2 run's own artifacts.
  # KEEP IT A SIBLING: check_e2_band resolves it as
  # ${OUT_DIR}.parent / "results_e2_band".
  if _dry_run_active; then
    log "e2_band: DRY RUN -- skipping the pre-run clear of ${OUT_DIR_E2_BAND}"
    _dry_run_stub
    return $?
  fi
  log "e2_band: clearing ${OUT_DIR_E2_BAND} before running (isolated dir, in-repo, outside the release tree)"
  rm -rf "${OUT_DIR_E2_BAND}"
  mkdir -p "${OUT_DIR_E2_BAND}"

  python -u -m experiments.e2_real_rig \
    --emit-band-configs \
    --config "${E2_RELEASE_CONFIG}" \
    --band-seeds "${E2_BAND_SEEDS}" \
    --band-dir "${OUT_DIR_E2_BAND}"
  local emit_exit=$?
  log "e2_band: emit-band-configs exit=${emit_exit}"
  if [ "${emit_exit}" -ne 0 ]; then
    return "${emit_exit}"
  fi

  local seed exit_code=0
  IFS=',' read -ra _E2_SEEDS <<<"${E2_BAND_SEEDS}"
  for seed in "${_E2_SEEDS[@]}"; do
    log "e2_band: seed ${seed} calibration starting (48-87 min)"
    python -u -m experiments.e2_real_rig \
      --config "${OUT_DIR_E2_BAND}/config_seed${seed}.yaml" \
      --out "${OUT_DIR_E2_BAND}/seed_${seed}_e2_out" \
      --force
    local seed_exit=$?
    log "e2_band: seed ${seed} exit=${seed_exit}"
    [ "${seed_exit}" -ne 0 ] && exit_code="${seed_exit}"
  done
  return "${exit_code}"
}

_gate_dir_for_stage() {
  # The output directory a stage's gate verdict is taken against.
  case "$1" in
    e4_repeat) printf '%s\n' "${OUT_DIR_E4_REPEAT}" ;;
    e2_band) printf '%s\n' "${OUT_DIR_E2_BAND}" ;;
    *) printf '%s\n' "${OUT_DIR}" ;;
  esac
}

run_one_stage() {
  local name="$1" idx="$2"
  if is_stage_complete "${name}"; then
    log "SKIP stage ${idx} (${name}): already has a recorded completion line in ${STATE_FILE}"
    return 0
  fi
  if [ "${idx}" -lt "${START_STAGE}" ]; then
    log "SKIP stage ${idx} (${name}): below the requested start stage ${START_STAGE}"
    return 0
  fi

  # Dispatch by name rather than a `case` arm per stage: the STAGES array and
  # the run_stage_* definitions are then a SINGLE source of truth that cannot
  # drift, which is what tests/unit/test_suite_stage_list.py asserts. The
  # unknown-stage guard is preserved.
  if ! declare -F "run_stage_${name}" >/dev/null 2>&1; then
    log "UNKNOWN STAGE ${name}: no run_stage_${name} function is defined"
    return 1
  fi

  state_start "${name}" "${idx}"
  log ">>> STAGE ${idx}/${#STAGES[@]}: ${name} starting"

  "run_stage_${name}"
  local exit_code=$?

  state_complete "${name}" "${idx}" "${exit_code}"
  log "<<< STAGE ${idx}/${#STAGES[@]}: ${name} finished exit=${exit_code}"

  if [ "${name}" = "prelaunch_probe" ]; then
    # D-03 HARD ABORT: an illegal seed means the seed list itself is wrong.
    # Every other stage's gate is a finding; this one stops the queue, and it
    # runs before any long stage so nothing is lost.
    if [ "${exit_code}" -ne 0 ]; then
      log "FATAL: prelaunch_probe FAILed (exit=${exit_code}) -- ABORTING THE QUEUE. The seed list is illegal at at least one (seed, n_cameras, draw); see the legality_probe output above. Do NOT resume past this point -- fix the seed list and restart from stage 1."
      exit "${exit_code}"
    fi
    return 0
  fi

  run_gate_check "$(_gate_dir_for_stage "${name}")" "${name}"
}

main() {
  log "AquaCal experiment suite driver starting. Frozen sha: ${FROZEN_SHA} (HEAD $(git rev-parse HEAD 2>/dev/null || echo unknown))"
  log "Stage order (D-37, shortest-first subject to depends_on): ${STAGES[*]}"
  log "State file: ${STATE_FILE}"
  log "Resuming from stage index ${START_STAGE} (stages already marked complete are skipped regardless)."

  local idx=1
  for stage in "${STAGES[@]}"; do
    run_one_stage "${stage}" "${idx}"
    idx=$((idx + 1))
  done

  log "Suite driver finished all ${#STAGES[@]} stages. See ${STATE_FILE} for the full stage-completion record."
}

main "$@"
