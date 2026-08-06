#!/usr/bin/env bash
#
# Phase 19.5 -- the ONE risk-first overnight production queue (D-19.5-02).
#
# Five stages, run SERIALLY, one calibration at a time on the box -- never two
# concurrent production runs -- in RISK-FIRST order:
#
#   1. prelaunch_probe  (~5 min)    cumulative ~5 min     <-- HARD ABORT on FAIL
#   2. e6_band          (~10.6 h)   cumulative ~10.6 h     <-- highest-risk stage
#   3. e4_repeat        (~0.8 h)    cumulative ~11.4 h
#   4. e2_band          (~3.5 h)    cumulative ~14.9 h
#   5. e5_band          (~2.2 h)    cumulative ~17.1 h  (~17 h nominal)
#
# REVISED 2026-08-06 for six-seed E6/E5 bands (was ~15 h nominal at five
# seeds). E6 runs ~1.76 h/seed and E5 ~0.36 h/seed, so the sixth seed adds
# ~2.2 h nominal. At 19.4's observed 1.6x overrun this totals ~27 h.
#
# WALL-CLOCK CEILING: the planner proposed 26 h at five seeds. The six-seed
# projection (~27 h) exceeds it. The user approved the sixth seed on
# 2026-08-06 with that consequence stated explicitly, so the ceiling is
# RAISED TO 30 HOURS rather than left silently violated. If exceeded, the
# orchestrator stops after the currently-running stage completes and reports
# which stages landed -- risk-first ordering means COV-03/COV-04 are already
# banked by hour ~11.
#
# The 1.6x figure is 19.4's OBSERVED overrun, cause unresolved
# (19.4-RUNTIME-OBSERVATION.md, n=1). It is used here as a budgeting factor
# only. Do NOT read a stage's actual runtime as evidence about any code
# change -- that attribution is a standing prohibition in this project.
#
# WHY e6_band IS FIRST AND NOT THE CHEAPEST STAGE. It is the longest, it
# carries TWO requirements (COV-03 and COV-04), and it is the only stage
# running brand-new code (the `--seeds` band and the `cameras` axis from plan
# 19.5-06). If it has a defect, the ABORT PROTOCOL below requires aborting and
# restarting the WHOLE queue from stage 1 -- that must happen at hour 1, not
# hour 18. Risk-first ordering banks the highest-value stage first: if the
# ceiling is ever exceeded, COV-03/COV-04 are already banked.
#
# WHY 6 SEEDS AND NOT 5 OR 10 (E6, E5) / 3 (E2). A ten-seed unanimous sign
# test gives p = 2^-10 one-sided. FIVE gives p = 2^-5 = 0.031 one-sided but
# 2 x 2^-5 = 0.0625 TWO-SIDED, which does NOT clear 0.05 -- so a five-seed
# result is significant or not depending purely on which convention a reader
# applies. This project has already been bitten by exactly that ambiguity:
# MF-05's p-values are one-sided (0.00098 = 2^-10) and a prior reading
# conflated the two conventions, which is why plan 19.5-03 named its field
# `p_one_sided` rather than `p`. At ten seeds the distinction was academic
# (two-sided still 0.00195); at five it is decisive.
#
# SIX seeds gives two-sided p = 2 x 2^-6 = 0.031, clearing 0.05 under EITHER
# convention. One extra seed buys immunity to the argument, at ~+1.8 h on E6
# and ~+0.36 h on E5. Raised to the user before launch 2026-08-06 and approved
# with the ceiling consequence stated (see the runtime budget above).
#
# E2 gets three: D-19.5-05 already narrows E2's band to split variance on
# FIXED data, three runs support a stated range with n=3 (not an interval),
# and seed 42 reproduces the committed record for free. E2 runs no sign test,
# so the one-sided/two-sided question does not arise for it.
#
# ============================================================================
# ABORT PROTOCOL -- PRE-COMMITTED (restated verbatim from rerun_19_4.sh, not
# paraphrased, per D-19.5-02's binding consequence), so it is not decided
# mid-run.
# ============================================================================
#   1. A src defect discovered at ANY stage means ABORT THE QUEUE, fix it, and
#      RESTART FROM STAGE 1. Not resume. Not patch-and-continue.
#   2. NEVER edit src/ or experiments/ while the queue is in flight. This run
#      holds ONE git sha across every artifact; a midstream edit destroys that
#      silently and yields a result set assembled from two different trees.
#      That is unreportable, and the damage is invisible until someone diffs
#      provenance.
#   3. Each stage's artifacts record their git sha. A cross-stage sha
#      MISMATCH is a HARD FAILURE, not a warning (check_rerun_gates.py's
#      gate3_git_sha_consistency enforces this).
#   4. COMMIT NOTHING while the queue runs. A per-cell `git rev-parse` would
#      split an artifact's recorded sha across the boundary
#      (.planning/knowledge-base.md "Commit nothing during a production run").
#
# THIS PHASE'S OWN LINE: the detached launch is
#   nohup bash experiments/rerun_19_5.sh > experiments/rerun_19_5.log 2>&1 & disown
# run by the ORCHESTRATOR, never by a subagent and never via
# `run_in_background` -- that harness kills background commands, and this
# project has already lost multiple sweeps to it (CLAUDE.md "Never let a
# subagent background a long run and return").
#
# THIS SCRIPT PERFORMS NO TREE-MUTATING GIT OPERATION -- no staging,
# committing, tagging, checking out, or pushing -- on any path, including the
# resume path. It reads `git rev-parse HEAD` exactly once, at the very start,
# purely to log which commit the whole night's artifacts are attributable to.
#
# TWO RESUME SEMANTICS, AND THEY ARE NOT INTERCHANGEABLE:
#   - Automatic resume (a stage with a recorded completion line is skipped) and
#     `bash experiments/rerun_19_5.sh N` (start from the 1-indexed stage N)
#     exist for INFRASTRUCTURE failures only: a box reboot, a 3 a.m. process
#     kill, a full disk.
#   - They are NEVER the recovery path for a src defect. That is always
#     restart-from-stage-1 per rule 1 above, because a partial result set
#     spanning two trees is exactly what rule 2 forbids.
# A stage that started and then died carries a start line with NO matching
# completion line, and is re-run FROM SCRATCH on resume -- never treated as
# done.
#
# prelaunch_probe IS THE ONE STAGE WHOSE FAILURE IS A HARD ABORT. Every other
# stage's gate is a finding (never an automatic abort, matching 19.3/19.4's
# proven behaviour) -- but an illegal seed means the seed list itself is
# wrong, so continuing past it would spend hours computing something that
# cannot be reported (D-19.5-04, T-19.5-09-03).
#
# e6_band'S PER-SEED ISOLATION IS HANDLED INSIDE e6_generalization_sweep.py
# ITSELF (plan 19.5-06's `_run_seed_band`): each seed's run goes into its own
# `${OUT_DIR}/e6_band/seed_<N>/` directory, wiped and recreated before every
# seed, because E6's checkpoint cache is seed-blind
# (`_SCENARIO_IDENTITY_KEYS` omits `seed`). This queue does NOT re-implement
# that isolation -- it is mandatory correctness inside the experiment script,
# not queue-level tidiness.
#
# e4_repeat's TWO REPEATS RUN BACK-TO-BACK, NOT INTERLEAVED WITH ANY OTHER
# STAGE. COV-06's deliverable is `seconds_total_spread_pct` -- run-to-run
# wall-clock spread. This is a Windows box (15.7 GiB) and one repeat cell
# (16, 100) will page rather than OOM; if the two repeats of a cell met
# different memory pressure because something else ran between them, the
# "spread" would measure paging, not the algorithm -- a decomposition of pure
# noise (this project's most recurrent error). This queue enforces the
# adjacency structurally: the three repeat cells run one after another inside
# a single stage function, both repeats immediately after each other, nothing
# else scheduled in between.
#
# e2_band's PER-SEED CONFIGS AND OUTPUT LIVE IN AN ISOLATED IN-REPO
# DIRECTORY (${OUT_DIR_E2_BAND} = experiments/results_e2_band/), NOT under
# the release tree (`emit_seed_variant_configs` refuses to write into or
# under the release config's own parent directory) and NOT under ${OUT_DIR}
# itself (so a `--check`/gate run against ${OUT_DIR} never confuses band
# output with the single production E2 run's own artifacts).
# `check_e2_band` (plan 19.5-09 Task 2) already knows to look at
# `${OUT_DIR}.parent / "results_e2_band"`.
#
# NO STAGE PASSES --no-fail-fast (E6) OR bypasses E4's own fail-fast. The
# queue runs unattended, and D-19.4-11's fail-fast is precisely what an
# unattended run needs: before it, E4 and E6 recorded a failure as a
# status="failed" row and exited 0, burning tens of minutes while reporting
# success.
#
# EVERY invocation runs unbuffered (`python -u`). Python block-buffers stdout
# to a pipe; without `-u` a detached run's log is empty whether it is
# progressing normally or hung on the first video -- the two are
# indistinguishable, and a real stall stays invisible until the timeout
# (CLAUDE.md).
#
# STAGE-LEVEL RECOVERY STATE: every stage transition is appended to
# experiments/rerun_19_5_state.tsv as
# `<stage>\t<index>\t<event>\t<iso-time>\t<exit-code>`. A start line is
# written BEFORE a stage launches and a completion line only AFTER it
# returns.
#
# GATE VERDICTS ARE FINDINGS, NOT AUTOMATIC ABORTS (except prelaunch_probe,
# above). After each stage, check_rerun_gates.py runs against that stage's
# output directory and its PASS/FAIL/N-A verdict is written into the log
# inside a delimited block. The abort-on-src-defect rule above is an
# OPERATOR judgment made by reading gate verdicts and logs, never an
# automatic script behaviour.
#
# Detached launch (used by plan 19.5-10), for the record:
#   nohup bash experiments/rerun_19_5.sh > experiments/rerun_19_5.log 2>&1 & disown
# NEVER run_in_background.

set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}" || exit 1

OUT_DIR="experiments/results"
OUT_DIR_E4_REPEAT="experiments/results_e4_repeat"
OUT_DIR_E2_BAND="experiments/results_e2_band"
# A DRY RUN MUST NOT WRITE THE REAL RUN'S STATE FILE. Automatic resume skips
# any stage carrying a completion line, so a dry run -- which "completes" all
# five stages in about a second -- would otherwise leave a state file that
# makes the NEXT real launch a silent no-op: five stages skipped, exit 0, no
# artifacts, and a queue that looks like it succeeded. Found 2026-08-06 by
# dry-running this script and inspecting what it left behind. Separate paths
# are the structural fix; remembering to delete the file is not.
if [ -n "${RERUN_19_5_DRY_RUN:-}" ]; then
  STATE_FILE="experiments/rerun_19_5_state.dryrun.tsv"
else
  STATE_FILE="experiments/rerun_19_5_state.tsv"
fi

# D-19.5's six-seed bands (E6, E5) and three-seed band (E2) -- see the
# header's "WHY 6 SEEDS AND NOT 5 OR 10 / 3" rationale above. The pre-launch
# legality probe reads E6_BAND_SEEDS from THIS file rather than keeping its
# own copy, so these lists cannot silently diverge from what is probed.
E6_BAND_SEEDS="42,43,44,45,46,47"
E5_BAND_SEEDS="42,43,44,45,46,47"
E2_BAND_SEEDS="42,43,44"

# The three camera counts the prelaunch legality probe and E4's repeat cells
# both use (D-19.5-04's queue-scoped legality check).
PROBE_N_CAMERAS="8,12,16"

# E4's repeat subset (COV-06, plan 19.5-08): exactly the three 100-frame
# cells MF-03's runtime-inversion finding rests on. The 200-frame cells are
# near_physical_ceiling (11.3 GiB peak on a 15.7 GiB box) -- repeating those
# risks an OOM that would abort the whole overnight queue for a number
# nobody is quoting.
E4_REPEAT_CELLS=("8x100" "12x100" "16x100")

# E2's production release config -- the source `emit_seed_variant_configs`
# reads from and refuses to write into/under (release-tree write refusal,
# plan 19.5-07, T-19.5-07-01).
E2_RELEASE_CONFIG="C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml"

# check_rerun_gates.py imports pandas AND aquacal.datasets.synthetic /
# experiments.e4_benchmark_grid (plan 19.5-09's legality_probe), so it needs
# the AquaCal env, not Git Bash's bare `python` (which is Anaconda base on
# this box). Same pin and override variable as prelaunch_gate.sh. Falls back
# to bare `python` only if the pinned interpreter is absent, so a missing env
# degrades the GATE to a logged finding rather than aborting a production
# stage -- EXCEPT prelaunch_probe, whose own failure (including an absent
# interpreter) is a hard abort per the ABORT PROTOCOL above.
GATE_PYTHON="${PRELAUNCH_GATE_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
if [ ! -x "${GATE_PYTHON}" ] && ! command -v "${GATE_PYTHON}" >/dev/null 2>&1; then
  echo "WARNING: pinned gate interpreter not found at ${GATE_PYTHON}; falling back to bare 'python'. Gate verdicts may fail to import pandas." >&2
  GATE_PYTHON="python"
fi

STAGES=(prelaunch_probe e6_band e4_repeat e2_band e5_band)
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
  # PINNED INTERPRETER, and it matters: check_rerun_gates.py imports pandas
  # and aquacal, so it is NOT stdlib-only. Same pin and same override
  # variable as prelaunch_gate.sh, with a bare-`python` fallback so a gate
  # invocation degrades to a logged finding rather than taking down a stage.
  "${GATE_PYTHON}" experiments/check_rerun_gates.py "${target_dir}"
  local gate_exit=$?
  echo "----- END GATE VERDICT: stage=${stage_name} exit=${gate_exit} -----"
  # Recorded as a finding, never acted on automatically -- this function's
  # own exit is always 0 so a gate FAIL never aborts the queue.
  return 0
}

_dry_run_active() {
  # Used ONLY by this plan's (19.5-09) own mechanics tests (stage sequencing,
  # gate invocation, resume). Every acceptance and production run is at full
  # scale, never substituted. Deliberately NOT the `--smoke` flag every
  # experiment shares: `--smoke` exercises real (if smaller) code paths and
  # is explicitly not evidence at production scale. This is a stronger
  # substitution used only to prove the QUEUE's own control flow, and is
  # never cited as evidence about geometry or convergence.
  [ -n "${RERUN_19_5_DRY_RUN:-}" ]
}

_dry_run_stub() {
  eval "${RERUN_19_5_DRY_RUN_CMD:-true}"
}

run_stage_prelaunch_probe() {
  # THE ONE STAGE WHOSE FAILURE IS A HARD ABORT (see header). A structural
  # geometry check, no calibration solve, seconds not minutes.
  if _dry_run_active; then
    log "prelaunch_probe: DRY RUN"
    _dry_run_stub
    return $?
  fi
  log "prelaunch_probe: legality_probe over seeds ${E6_BAND_SEEDS} x n_cameras ${PROBE_N_CAMERAS}"
  "${GATE_PYTHON}" - <<'PY'
from experiments.check_rerun_gates import legality_probe

seeds = [42, 43, 44, 45, 46]
camera_counts = [8, 12, 16]
results = legality_probe(seeds, camera_counts)
n_fail = sum(1 for r in results if r.verdict == "FAIL")
for r in results:
    print(f"[{r.verdict:4s}] {r.gate} -- {r.detail}")
print()
print(f"TOTAL: {len(results)} checked, {n_fail} FAIL")
raise SystemExit(1 if n_fail else 0)
PY
}

run_stage_e6_band() {
  # Per-seed isolation is handled INSIDE e6_generalization_sweep.py's own
  # _run_seed_band (plan 19.5-06) -- see the header comment above. No rm -rf
  # of OUT_DIR is needed or wanted here: the band CSV write always forces
  # (regenerating a band on demand is the point), and the shared production
  # generalization_sweep.csv/e6_provenance.json/e6_configs/ at OUT_DIR's own
  # root are never touched by the --seeds path.
  if _dry_run_active; then
    log "e6_band: DRY RUN"
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e6_generalization_sweep \
    --seeds "${E6_BAND_SEEDS}" --out "${OUT_DIR}" --force
}

run_stage_e4_repeat() {
  # Isolated directory, wiped before running -- never the shared OUT_DIR,
  # matching rerun_19_4.sh's run_stage_e6_repeat2 template. Three cells,
  # BOTH repeats of each cell run back-to-back inside this one function
  # (header's "e4_repeat's TWO REPEATS RUN BACK-TO-BACK" note) -- nothing
  # else is scheduled between repeat 1 and repeat 2 of any cell.
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

  # Positive re-solve signal, copied verbatim from rerun_19_4.sh's
  # run_stage_e6_repeat2: every cell of both repeats must have been
  # genuinely computed, never skipped via a cached checkpoint.
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
  # Isolated in-repo directory, wiped before running. Two phases: (1) emit
  # the three seed-variant configs + e2_band_scope.json (no calibration),
  # (2) run each variant's calibration SEQUENTIALLY (48-87 min each). Never
  # writes into or under the release tree (T-19.5-07-01).
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

run_stage_e5_band() {
  if _dry_run_active; then
    log "e5_band: DRY RUN"
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e5_index_sensitivity \
    --seeds "${E5_BAND_SEEDS}" --out "${OUT_DIR}" --force
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
    prelaunch_probe) run_stage_prelaunch_probe ;;
    e6_band) run_stage_e6_band ;;
    e4_repeat) run_stage_e4_repeat ;;
    e2_band) run_stage_e2_band ;;
    e5_band) run_stage_e5_band ;;
    *)
      log "UNKNOWN STAGE ${name}"
      return 1
      ;;
  esac
  local exit_code=$?

  state_complete "${name}" "${idx}" "${exit_code}"
  log "<<< STAGE ${idx}/${#STAGES[@]}: ${name} finished exit=${exit_code}"

  if [ "${name}" = "prelaunch_probe" ]; then
    # HARD ABORT: an illegal seed means the seed list itself is wrong.
    # Every other stage's gate is a finding; this one stops the queue.
    if [ "${exit_code}" -ne 0 ]; then
      log "FATAL: prelaunch_probe FAILed (exit=${exit_code}) -- ABORTING THE QUEUE. The seed list is illegal at at least one (seed, n_cameras, draw); see the legality_probe output above. Do NOT resume past this point -- fix the seed list and restart from stage 1."
      exit "${exit_code}"
    fi
    return 0
  fi

  case "${name}" in
    e4_repeat) run_gate_check "${OUT_DIR_E4_REPEAT}" "${name}" ;;
    e2_band) run_gate_check "${OUT_DIR_E2_BAND}" "${name}" ;;
    *) run_gate_check "${OUT_DIR}" "${name}" ;;
  esac
}

main() {
  log "Phase 19.5 production queue starting. HEAD at queue start: $(git rev-parse HEAD)"
  log "Risk-first order (D-19.5-02): ${STAGES[*]}"
  log "Resuming from stage index ${START_STAGE} (stages already marked complete are skipped regardless)."
  log "Runtime budget: ~15 h nominal, ~24 h at 19.4's observed 1.6x overrun, 26 h proposed ceiling."

  local idx=1
  for stage in "${STAGES[@]}"; do
    run_one_stage "${stage}" "${idx}"
    idx=$((idx + 1))
  done

  log "Phase 19.5 production queue finished all ${#STAGES[@]} stages. See ${STATE_FILE} for the full stage-completion record."
}

main "$@"
