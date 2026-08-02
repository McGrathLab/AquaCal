#!/usr/bin/env bash
#
# Phase 19.3 -- the ~9 h chained overnight re-run (D-19.3-18).
#
# Seven stages, run SERIALLY, one calibration at a time on the box (review H4 --
# never two concurrent production runs), shortest-first so a systematic failure
# surfaces in seconds or minutes rather than after the longest stage:
#
#   1. e3          (~10 s,   no calibration -- two invocations, see below)
#   2. e7          (~7 min)
#   3. e1          (~20-25 min)
#   4. e5          (~21 min)
#   5. e6_repeat1  (~107 min -- the production E6 re-run; this IS determinism repeat 1)
#   6. e6_repeat2  (~107 min -- an ISOLATED second E6 pass, D-19.3-20)
#   7. e4          (~3.15-3.5 h)
#
# Total expected wall clock ~= 9 h (D-19.3-13: the paired sweep costs +1.8 h, not
# +3.6 h, because repeat 1 IS the production re-run the sequence needed anyway).
#
# ONE CALIBRATION AT A TIME (review H4): stages never overlap. e3 runs no
# calibration and would not need the box to itself on that basis alone, but it
# still runs serially inside this same frozen window so its provenance carries
# the identical git_sha every other stage's artifacts do.
#
# COMMIT NOTHING WHILE A RUN IS IN FLIGHT: per-cell git_sha capture would split
# one night's artifacts across two commits if anything landed mid-run. This
# script itself performs no tree-mutating operation of that kind -- staging,
# committing, tagging, checking out, or pushing -- on any path, including the
# resume path. It reads `git rev-parse HEAD` exactly once, at the very start,
# purely to log which commit the whole night's artifacts are attributable to.
#
# E3'S TWO INVOCATIONS, IN THIS EXACT ORDER, AND THE ORDER IS LOAD-BEARING:
#   (a) `--check` FIRST -- records the pre-regeneration state of all three
#       tiers. Tier 2 (Newton-iteration diagnostics) is geometry-dependent and
#       is EXPECTED to move (134 mismatched cells were measured in plan
#       19.3-05); tiers 1 and 3 (declared solver constants; camera/frame-count
#       derived P/group counts) are NOT geometry-dependent and are expected to
#       stay put -- this run confirms that by measuring it, not by assuming it.
#   (b) `--force` SECOND -- regenerates the committed tier CSVs/LaTeX
#       fragments. Running `--force` first would regenerate tier 2 before its
#       pre-fix state was ever recorded, destroying the only evidence of what
#       moved and why.
# A resumed e3 stage always re-runs BOTH invocations from scratch -- it must
# never resume into the second invocation alone, which would silently lose the
# tier-by-tier `--check` output that only the first invocation produces.
#
# E6'S PAIRED DETERMINISM SWEEP (D-19.3-13/D-19.3-20): repeat 2 writes to its
# OWN, isolated output directory (never the shared one `--force`-overwritten,
# and never re-using repeat 1's `e6_configs/` checkpoints) -- E6 checkpoints
# and resumes by design, and two repeats that can see the same checkpoints
# would silently degrade the determinism measurement into a file-copy check
# reporting perfect (and meaningless) reproduction.
#
# EVERY invocation below runs unbuffered (the `-u` interpreter flag). Python
# block-buffers stdout to a pipe; without it a stalled run and a healthy one
# look identical in the log
# for the whole night (CLAUDE.md).
#
# STAGE-LEVEL RECOVERY STATE: every stage transition is appended to
# experiments/rerun_19_3_state.tsv as `<stage>\t<index>\t<event>\t<iso-time>\t<exit-code>`.
# A start line is written BEFORE a stage launches and a completion line only
# AFTER it returns, so a stage that started and then died (a 3 a.m. process
# kill) is distinguishable from one that finished: it carries a start line
# with no matching completion line, and a resume re-runs it FROM SCRATCH --
# never treating a started-but-died stage as done.
#
# RESUMING: `bash experiments/rerun_19_3.sh [N]`, where `N` is the 1-indexed
# stage to (re)start from (default 1, i.e. resume automatically). Regardless
# of `N`, any stage already carrying a successful completion line in the state
# file is skipped rather than re-run -- `N` only lets an operator additionally
# skip stages below it without consulting the state file. After each stage,
# `check_rerun_gates.py` is invoked against that stage's output directory and
# its PASS/FAIL/N-A verdict is written into the log inside a clearly delimited
# block. A gate FAIL is recorded as a finding and does NOT abort the queue --
# the remaining measurements are still wanted, and the verdicts are read
# afterwards, not acted on automatically.
#
# Detached launch (used by plan 19.3-09), for the record:
#   nohup bash experiments/rerun_19_3.sh > experiments/rerun_19_3.log 2>&1 & disown
# NEVER run_in_background -- that harness kills background commands at
# 35-50 min, and this project has already lost three sweeps to it.

set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}" || exit 1

OUT_DIR="experiments/results"
OUT_DIR_E6_REPEAT2="experiments/results_e6_repeat2"
STATE_FILE="experiments/rerun_19_3_state.tsv"

STAGES=(e3 e7 e1 e5 e6_repeat1 e6_repeat2 e4)
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
  python experiments/check_rerun_gates.py "${target_dir}"
  local gate_exit=$?
  echo "----- END GATE VERDICT: stage=${stage_name} exit=${gate_exit} -----"
  # Recorded as a finding, never acted on automatically (D-19.3-18) -- this
  # function's own exit is always 0 so a gate FAIL never aborts the queue.
  return 0
}

_dry_run_active() {
  # Used ONLY by this plan's own mechanics tests (stage sequencing, gate
  # invocation, kill-mid-stage recovery) -- every acceptance and production run
  # is at full scale, never substituted. Named without the reduced-size CLI
  # flag every experiment shares, since that flag exercises real (if smaller)
  # code paths and is explicitly not evidence at production scale (D-19.3-18's
  # anti-pattern #4); this is a stronger substitution used only to prove the
  # QUEUE's own control flow, never cited as evidence about geometry or
  # convergence.
  [ -n "${RERUN_19_3_DRY_RUN:-}" ]
}

_dry_run_stub() {
  eval "${RERUN_19_3_DRY_RUN_CMD:-true}"
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

run_stage_e7() {
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"
  fi
}

run_stage_e1() {
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"
  fi
}

run_stage_e5() {
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"
  fi
}

run_stage_e6_repeat1() {
  # Never silently reuse a stale partial checkpoint set from an earlier died
  # attempt at THIS stage: clear e6's own artifacts under the shared OUT_DIR
  # before (re-)running, then --force regenerates everything from scratch.
  # This is the production E6 re-run AND determinism repeat 1 at once
  # (D-19.3-13).
  log "e6_repeat1: clearing any partial E6 state under ${OUT_DIR} before running"
  rm -rf "${OUT_DIR}/e6_configs"
  rm -f "${OUT_DIR}/generalization_sweep.csv" "${OUT_DIR}/e6_provenance.json"
  if _dry_run_active; then
    _dry_run_stub
  else
    python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"
  fi
}

run_stage_e6_repeat2() {
  # D-19.3-20: repeat 2 writes to its OWN, isolated output directory -- never
  # the shared OUT_DIR, and never `--force` against a shared directory as the
  # isolation mechanism. A died prior attempt at repeat 2 leaves this
  # directory removed wholesale before retrying (it holds nothing but E6's own
  # artifacts), so a resume can never silently reuse its stale checkpoints.
  log "e6_repeat2: clearing ${OUT_DIR_E6_REPEAT2} before running (isolated dir, D-19.3-20)"
  rm -rf "${OUT_DIR_E6_REPEAT2}"
  mkdir -p "${OUT_DIR_E6_REPEAT2}"
  if _dry_run_active; then
    _dry_run_stub
    local exit_code=$?
  else
    local stage_log="${OUT_DIR_E6_REPEAT2}/repeat2_stdout.log"
    python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR_E6_REPEAT2}" 2>&1 | tee "${stage_log}"
    local exit_code="${PIPESTATUS[0]}"
    # Positive re-solve signal (plan 19.3-08 Task 1): every configuration must
    # have been genuinely computed, never skipped via a cached checkpoint --
    # the checkpoint-skip log line must appear ZERO times in a genuine re-solve.
    local skip_lines
    skip_lines="$(grep -c "already exists (resumability)" "${stage_log}" || true)"
    log "e6_repeat2: positive re-solve signal -- ${skip_lines} 'already exists (resumability)' skip line(s) found in ${stage_log} (0 expected for a genuine re-solve)"
  fi
  return "${exit_code}"
}

run_stage_e4() {
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"
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
    e3) run_stage_e3 ;;
    e7) run_stage_e7 ;;
    e1) run_stage_e1 ;;
    e5) run_stage_e5 ;;
    e6_repeat1) run_stage_e6_repeat1 ;;
    e6_repeat2) run_stage_e6_repeat2 ;;
    e4) run_stage_e4 ;;
    *)
      log "UNKNOWN STAGE ${name}"
      return 1
      ;;
  esac
  local exit_code=$?

  state_complete "${name}" "${idx}" "${exit_code}"
  log "<<< STAGE ${idx}/${#STAGES[@]}: ${name} finished exit=${exit_code}"

  if [ "${name}" = "e6_repeat2" ]; then
    run_gate_check "${OUT_DIR_E6_REPEAT2}" "${name}"
  else
    run_gate_check "${OUT_DIR}" "${name}"
  fi
}

main() {
  log "Phase 19.3 re-run queue starting. HEAD at queue start: $(git rev-parse HEAD)"
  log "Resuming from stage index ${START_STAGE} (stages already marked complete are skipped regardless)."

  local idx=1
  for stage in "${STAGES[@]}"; do
    run_one_stage "${stage}" "${idx}"
    idx=$((idx + 1))
  done

  log "Phase 19.3 re-run queue finished all seven stages. See ${STATE_FILE} for the full stage-completion record."
}

main "$@"
