#!/usr/bin/env bash
#
# Phase 19.4 -- the ~9 h 30 min overnight re-run (D-19.4-13, D-19.4-16).
#
# Eight stages, run SERIALLY, one calibration at a time on the box -- never two
# concurrent production runs -- in RISK-FIRST order (D-19.4-16), NOT the
# cheapest-first order 19.3 used:
#
#   1. e6_repeat1  (~100 min)  cumulative ~100 min
#   2. e4          (~132 min)  cumulative ~232 min   <-- highest-risk stage
#   3. e6_repeat2  (~96 min)   cumulative ~328 min
#   4. e6_seed43   (~100 min)  cumulative ~428 min
#   5. e7 + band   (~56 min)   cumulative ~484 min
#   6. e1 + band   (~63 min)   cumulative ~547 min
#   7. e5          (~22 min)   cumulative ~569 min
#   8. e3          (~12 s)     cumulative ~569 min  (9 h 30)
#
# WHY RISK-FIRST. 19.3's queue ran cheapest-first, which optimises for "most
# stages finished" rather than "earliest signal on the riskiest path" -- e4 did
# not start until 230 min in. E4 is the highest-risk stage: it is the only one
# exercising the n_cameras axis, it carries the 10.26 GiB peak on its 16-camera
# cells, and it is 132.5 min of exposure. Under this order both high-risk
# stages complete inside 4 h instead of 6. Total wall clock is unchanged.
#
# ============================================================================
# ABORT PROTOCOL (D-19.4-16) -- PRE-COMMITTED, so it is not decided mid-run.
# ============================================================================
#   1. A src defect discovered at ANY stage means ABORT THE QUEUE, fix it, and
#      RESTART FROM STAGE 1. Not resume. Not patch-and-continue.
#   2. NEVER edit src/ or experiments/ while the queue is in flight. 19.3's run
#      holds ONE git sha across every artifact; a midstream edit destroys that
#      silently and yields a result set assembled from two different trees.
#      That is unreportable, and the damage is invisible until someone diffs
#      provenance.
#   3. Each stage records its git sha. A cross-stage sha MISMATCH is a HARD
#      FAILURE, not a warning (check_rerun_gates.py enforces this).
#   4. COMMIT NOTHING while the queue runs. A per-cell `git rev-parse` would
#      split an artifact's recorded sha across the boundary.
#
# Front-loading risk is what makes rule 1 affordable: restarting after 100
# minutes is a nuisance; restarting after 400 is how people talk themselves
# into the midstream edit.
#
# THIS SCRIPT PERFORMS NO TREE-MUTATING GIT OPERATION -- no staging,
# committing, tagging, checking out, or pushing -- on any path, including the
# resume path. It reads `git rev-parse HEAD` exactly once, at the very start,
# purely to log which commit the whole night's artifacts are attributable to.
#
# TWO RESUME SEMANTICS, AND THEY ARE NOT INTERCHANGEABLE:
#   - Automatic resume (a stage with a recorded completion line is skipped) and
#     `bash experiments/rerun_19_4.sh N` (start from the 1-indexed stage N)
#     exist for INFRASTRUCTURE failures only: a box reboot, a 3 a.m. process
#     kill, a full disk.
#   - They are NEVER the recovery path for a src defect. That is always
#     restart-from-stage-1 per rule 1 above, because a partial result set
#     spanning two trees is exactly what rule 2 forbids.
# A stage that started and then died carries a start line with NO matching
# completion line, and is re-run FROM SCRATCH on resume -- never treated as
# done.
#
# THE e7 AND e1 BAND RUNS ARE FOLDED INTO THEIR STAGES rather than split into
# separate state-file entries, matching D-19.4-16's own eight-row table.
# run_stage_e7 runs the single-seed production run first, then the 10-seed
# band; run_stage_e1 does the same. This is safe because the abort rule is
# already "restart from stage 1", not "resume". TRADEOFF, stated explicitly: a
# death midway through a band re-runs that stage's single-seed portion too.
#
# e6_seed43 WRITES TO ITS OWN OUTPUT DIRECTORY, and must. E6's
# _SCENARIO_IDENTITY_KEYS omits `seed`, and `seed` is not in its `config` at
# all, so two runs at different seeds into ONE output directory compare
# identical and the second silently RESUMES the first. That is a real latent
# defect found 2026-08-04; it is a Deferred Idea and is NOT fixed here. The
# separate output directory is the workaround.
#
# e6_repeat2 LIKEWISE writes to its own isolated directory (D-19.3-20): E6
# checkpoints and resumes by design, and two repeats that can see the same
# checkpoints would silently degrade the determinism measurement into a
# file-copy check reporting perfect (and meaningless) reproduction.
#
# E3'S TWO INVOCATIONS, IN THIS EXACT ORDER, AND THE ORDER IS LOAD-BEARING:
#   (a) `--check` FIRST -- records the pre-regeneration state of all three
#       tiers.
#   (b) `--force` SECOND -- regenerates the committed tier CSVs/LaTeX
#       fragments. Running `--force` first would regenerate tier 2 before its
#       pre-fix state was ever recorded, destroying the only evidence of what
#       moved and why.
# A resumed e3 stage always re-runs BOTH invocations from scratch.
#
# NO STAGE PASSES --no-fail-fast. The queue runs unattended, and D-19.4-11's
# fail-fast is precisely what an unattended run needs: before it, E4 and E6
# recorded a failure as a status="failed" row and exited 0, which burned 74 and
# 84 minutes at seeds 47 and 50 while reporting success.
#
# EVERY invocation runs unbuffered (`python -u`). Python block-buffers stdout to
# a pipe; without `-u` a detached run's log is empty whether it is progressing
# normally or hung on the first video -- the two are indistinguishable, and a
# real stall stays invisible until the timeout (CLAUDE.md).
#
# STAGE-LEVEL RECOVERY STATE: every stage transition is appended to
# experiments/rerun_19_4_state.tsv as
# `<stage>\t<index>\t<event>\t<iso-time>\t<exit-code>`. A start line is written
# BEFORE a stage launches and a completion line only AFTER it returns.
#
# GATE VERDICTS ARE FINDINGS, NOT AUTOMATIC ABORTS. After each stage,
# check_rerun_gates.py runs against that stage's output directory and its
# PASS/FAIL/N-A verdict is written into the log inside a delimited block. A
# gate FAIL does NOT abort the queue -- that is 19.3's proven behaviour and this
# script must not silently exceed it. The abort-on-src-defect rule above is an
# OPERATOR judgment made by reading gate verdicts and logs, never an automatic
# script behaviour.
#
# Detached launch (used by plan 19.4-09), for the record:
#   nohup bash experiments/rerun_19_4.sh > experiments/rerun_19_4.log 2>&1 & disown
# NEVER run_in_background -- that harness kills background commands at
# 35-50 min, and this project has already lost three sweeps to it.

set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}" || exit 1

OUT_DIR="experiments/results"
OUT_DIR_E6_REPEAT2="experiments/results_e6_repeat2"
OUT_DIR_E6_SEED43="experiments/results_e6_seed43"
STATE_FILE="experiments/rerun_19_4_state.tsv"

# The 10-seed bands for E7 and E1 (D-19.4-14). E4 and E6 deliberately do NOT
# get bands in this phase: E6 x10 is 16.6 h and E4 x10 is 22.1 h, ~39 h
# together, and neither carries an accuracy claim a band would defend.
BAND_SEEDS="42,43,44,45,46,47,48,49,50,51"

# check_rerun_gates.py imports pandas, so it needs the AquaCal env, not Git
# Bash's bare `python` (which is Anaconda base on this box). Same pin and
# override variable as prelaunch_gate.sh. Falls back to bare `python` only if
# the pinned interpreter is absent, so a missing env degrades the GATE to a
# logged finding rather than aborting a production stage.
GATE_PYTHON="${PRELAUNCH_GATE_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
if [ ! -x "${GATE_PYTHON}" ] && ! command -v "${GATE_PYTHON}" >/dev/null 2>&1; then
  echo "WARNING: pinned gate interpreter not found at ${GATE_PYTHON}; falling back to bare 'python'. Gate verdicts may fail to import pandas." >&2
  GATE_PYTHON="python"
fi

STAGES=(e6_repeat1 e4 e6_repeat2 e6_seed43 e7 e1 e5 e3)
START_STAGE="${1:-1}"

log() {
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*"
}

is_stage_complete() {
  # A stage counts as complete only if the state file carries a "complete"
  # event line for it -- a start-only line (started, then died) never matches.
  # Matched with awk, deliberately: the Perl-regex grep mode produced a live
  # locale warning on this box, so it is not used anywhere in this script.
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
  # PINNED INTERPRETER, and it matters: check_rerun_gates.py imports pandas, so
  # it is NOT stdlib-only and does depend on the AquaCal env. Git Bash's bare
  # `python` on this box is Anaconda base, where the import fails -- 19.3's
  # plan 09 flagged exactly this as a pitfall. Same pin and same override
  # variable as prelaunch_gate.sh, with a bare-`python` fallback so a gate
  # invocation degrades to a logged finding rather than taking down a stage.
  "${GATE_PYTHON}" experiments/check_rerun_gates.py "${target_dir}"
  local gate_exit=$?
  echo "----- END GATE VERDICT: stage=${stage_name} exit=${gate_exit} -----"
  # Recorded as a finding, never acted on automatically (D-19.4-16) -- this
  # function's own exit is always 0 so a gate FAIL never aborts the queue.
  return 0
}

_dry_run_active() {
  # Used ONLY by plan 19.4-08's own mechanics tests (stage sequencing, gate
  # invocation, kill-mid-stage recovery). Every acceptance and production run
  # is at full scale, never substituted. Deliberately NOT the `--smoke` flag
  # every experiment shares: `--smoke` exercises real (if smaller) code paths
  # and is explicitly not evidence at production scale (blocking anti-pattern
  # 4). This is a stronger substitution used only to prove the QUEUE's own
  # control flow, and is never cited as evidence about geometry or convergence.
  [ -n "${RERUN_19_4_DRY_RUN:-}" ]
}

_dry_run_stub() {
  eval "${RERUN_19_4_DRY_RUN_CMD:-true}"
}

run_stage_e6_repeat1() {
  # Never silently reuse a stale partial checkpoint set from an earlier died
  # attempt at THIS stage: clear e6's own artifacts under the shared OUT_DIR
  # before (re-)running, then --force regenerates everything from scratch.
  # This is the production E6 re-run AND determinism repeat 1 at once.
  # The cleanup is guarded by the dry-run check, and MUST stay guarded:
  # generalization_sweep.csv, e6_provenance.json and e6_configs/ are TRACKED
  # files. An unguarded `rm` here would delete 14 committed artifacts every time
  # anyone exercised the queue's control flow.
  if _dry_run_active; then
    log "e6_repeat1: DRY RUN -- skipping the destructive pre-run cleanup of ${OUT_DIR}"
    _dry_run_stub
  else
    log "e6_repeat1: clearing any partial E6 state under ${OUT_DIR} before running"
    rm -rf "${OUT_DIR}/e6_configs"
    rm -f "${OUT_DIR}/generalization_sweep.csv" "${OUT_DIR}/e6_provenance.json"
    python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"
  fi
}

run_stage_e4() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"
}

run_stage_e6_repeat2() {
  # D-19.3-20, carried forward: repeat 2 writes to its OWN, isolated output
  # directory -- never the shared OUT_DIR, and never `--force` against a shared
  # directory as the isolation mechanism. A died prior attempt leaves this
  # directory removed wholesale before retrying (it holds nothing but E6's own
  # artifacts), so a resume can never silently reuse its stale checkpoints.
  if _dry_run_active; then
    log "e6_repeat2: DRY RUN -- skipping the pre-run clear of ${OUT_DIR_E6_REPEAT2}"
    _dry_run_stub
    local exit_code=$?
  else
    log "e6_repeat2: clearing ${OUT_DIR_E6_REPEAT2} before running (isolated dir)"
    rm -rf "${OUT_DIR_E6_REPEAT2}"
    mkdir -p "${OUT_DIR_E6_REPEAT2}"
    local stage_log="${OUT_DIR_E6_REPEAT2}/repeat2_stdout.log"
    python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR_E6_REPEAT2}" 2>&1 | tee "${stage_log}"
    local exit_code="${PIPESTATUS[0]}"
    # Positive re-solve signal: every configuration must have been genuinely
    # computed, never skipped via a cached checkpoint -- the checkpoint-skip
    # log line must appear ZERO times in a genuine re-solve.
    local skip_lines
    skip_lines="$(grep -c "already exists (resumability)" "${stage_log}" || true)"
    log "e6_repeat2: positive re-solve signal -- ${skip_lines} 'already exists (resumability)' skip line(s) found in ${stage_log} (0 expected for a genuine re-solve)"
  fi
  return "${exit_code}"
}

run_stage_e6_seed43() {
  # E6 at the formerly-failing seed 43. Its own output directory is MANDATORY,
  # not tidiness: E6's _SCENARIO_IDENTITY_KEYS omits `seed` and `seed` is not
  # in its `config` at all, so a seed-43 run into ${OUT_DIR} would compare
  # identical to the seed-42 run already there and SILENTLY RESUME it,
  # producing a seed-42 result labelled seed 43. That latent defect is a
  # Deferred Idea (it needs its own migration decision, since committed
  # checkpoints carry no config["seed"]) and must NOT be fixed here.
  #
  # Note on what this stage now proves: D-19.4-15 established that post-fix the
  # derived floor is identical at every seed (one distinct value across 3,000
  # draws), so the original rationale -- "the raised-floor path has never been
  # run" -- no longer applies. This is now a general robustness check, retained
  # because E6's brokenness is this phase's origin and completing at a
  # formerly-failing seed is the end-to-end evidence that the origin defect is
  # gone.
  if _dry_run_active; then
    log "e6_seed43: DRY RUN -- skipping the pre-run clear of ${OUT_DIR_E6_SEED43}"
    _dry_run_stub
    return $?
  fi
  log "e6_seed43: clearing ${OUT_DIR_E6_SEED43} before running (isolated dir -- seed is NOT in E6's config identity)"
  rm -rf "${OUT_DIR_E6_SEED43}"
  mkdir -p "${OUT_DIR_E6_SEED43}"
  python -u -m experiments.e6_generalization_sweep --force --seed 43 --out "${OUT_DIR_E6_SEED43}"
}

run_stage_e7() {
  # Single-seed production run FIRST, then the 10-seed band (D-19.4-14).
  # E7 is INERT under this phase's fix -- it runs the "realistic" scenario,
  # which resolves to generate_real_rig_array()'s frozen shared WATER_Z, and
  # never calls generate_camera_array. Its committed interface_ablation.csv is
  # expected to reproduce byte-for-byte; a mismatch is a real defect signal,
  # never an expected move. The band exists for REPRODUCIBILITY: MF-05's
  # per-arm bands are the milestone's only surviving accuracy claim, and today
  # they live only in gitignored seed_sweep_19_3/ output.
  log "e7: single-seed production run"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"
  fi
  log "e7: single-seed exit=$?"
  log "e7: 10-seed band (${BAND_SEEDS}) -> interface_ablation_band.csv"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e7_interface_ablation --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"
  fi
  local band_exit=$?
  log "e7: band exit=${band_exit}"
  return "${band_exit}"
}

run_stage_e1() {
  # Single-seed production run FIRST, then the 10-seed band (D-19.4-14).
  # E1 is INERT under this phase's fix for the same reason as E7: its
  # production SCENARIO_NAME is "realistic", not "ideal". The band makes MF-08's
  # 97-178x deepest-point ratio spread and its "2 of 10 seeds exceed 2 mm"
  # finding regenerable rather than trusted from a planning document.
  log "e1: single-seed production run"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"
  fi
  log "e1: single-seed exit=$?"
  log "e1: 10-seed band (${BAND_SEEDS}) -> exp1_band.csv"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e1_refractive_comparison --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"
  fi
  local band_exit=$?
  log "e1: band exit=${band_exit}"
  return "${band_exit}"
}

run_stage_e5() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"
}

run_stage_e3() {
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

  state_start "${name}" "${idx}"
  log ">>> STAGE ${idx}/${#STAGES[@]}: ${name} starting"

  case "${name}" in
    e6_repeat1) run_stage_e6_repeat1 ;;
    e4) run_stage_e4 ;;
    e6_repeat2) run_stage_e6_repeat2 ;;
    e6_seed43) run_stage_e6_seed43 ;;
    e7) run_stage_e7 ;;
    e1) run_stage_e1 ;;
    e5) run_stage_e5 ;;
    e3) run_stage_e3 ;;
    *)
      log "UNKNOWN STAGE ${name}"
      return 1
      ;;
  esac
  local exit_code=$?

  state_complete "${name}" "${idx}" "${exit_code}"
  log "<<< STAGE ${idx}/${#STAGES[@]}: ${name} finished exit=${exit_code}"

  case "${name}" in
    e6_repeat2) run_gate_check "${OUT_DIR_E6_REPEAT2}" "${name}" ;;
    e6_seed43) run_gate_check "${OUT_DIR_E6_SEED43}" "${name}" ;;
    *) run_gate_check "${OUT_DIR}" "${name}" ;;
  esac
}

main() {
  log "Phase 19.4 re-run queue starting. HEAD at queue start: $(git rev-parse HEAD)"
  log "Risk-first order (D-19.4-16): ${STAGES[*]}"
  log "Resuming from stage index ${START_STAGE} (stages already marked complete are skipped regardless)."

  local idx=1
  for stage in "${STAGES[@]}"; do
    run_one_stage "${stage}" "${idx}"
    idx=$((idx + 1))
  done

  log "Phase 19.4 re-run queue finished all ${#STAGES[@]} stages. See ${STATE_FILE} for the full stage-completion record."
}

main "$@"
