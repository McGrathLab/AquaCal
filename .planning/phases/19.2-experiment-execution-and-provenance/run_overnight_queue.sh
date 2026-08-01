#!/usr/bin/env bash
# Overnight queue, 2026-07-31 -> 2026-08-01. Approved by the user before launch.
#
# Runs three stages STRICTLY SEQUENTIALLY. Every stage is a production run and
# the box is exclusive (review H4): two concurrent runs would make each other's
# timings and memory measure contention, and on a 15.7 GB box they would page
# against each other.
#
#   1. E7 seeds 47-51        (~30 min)  -- D-36: takes MF-05's sign test from
#                                          p = 0.031 to 0.001 if unanimity holds.
#   2. Plan 19.2-23 wave 5   (~25 min)  -- E5 band re-run for provenance, then
#                                          E3's three tiers (~10 s).
#   3. E5 seeds 42-46        (~110 min) -- closes D-36's gap that E5's own
#                                          seed-noise band is unmeasured.
#
# NOTHING IS COMMITTED WHILE THIS RUNS. E6's checkpoints disagreed on git_sha
# because a docs commit landed mid-sweep and capture_environment calls
# `git rev-parse` per configuration. Every experiment here captures provenance
# the same way, so the whole batch is committed in the morning on a quiet box.
#
# set -u but NOT -e: a failing stage is data (which stage, which code). Later
# stages must still run -- abandoning the queue would waste the whole window.
set -u

REPO="/c/Users/tucke/PycharmProjects/AquaCal"
PY="/c/Users/tucke/anaconda3/envs/AquaCal/python.exe"
ROOT="/c/Users/tucke/Desktop/Aqua/AquaCal/seed_sweep_19_2"
SCRATCH="/c/Users/tucke/AppData/Local/Temp/claude/C--Users-tucke-PycharmProjects-AquaCal/c8a889b5-5879-4e57-beea-ded4703fc11a/scratchpad"
LOG="$SCRATCH/overnight.log"

# E5's --help crashes with UnicodeEncodeError on cp1252 (a Delta in the help
# text). Harmless here, but force UTF-8 so no stage dies on console encoding.
export PYTHONIOENCODING=utf-8

mkdir -p "$ROOT" "$SCRATCH"
cd "$REPO" || exit 1

{
  echo "=== overnight queue ==="
  echo "started : $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC"
  echo "HEAD    : $(git rev-parse HEAD)"
  echo "python  : $PY"
  echo
} | tee "$LOG"

stage_start() { echo "--- START $1 at $(date -u '+%H:%M:%SZ') ---" | tee -a "$LOG"; }
stage_end() {
  local name="$1" rc="$2" t0="$3"
  local el=$(( $(date +%s) - t0 ))
  if [ "$rc" -eq 0 ]; then
    echo "--- OK     $name rc=0 elapsed=${el}s ---" | tee -a "$LOG"
  else
    echo "--- FAILED $name rc=$rc elapsed=${el}s ---" | tee -a "$LOG"
  fi
}

run_seeded() {  # experiment, seed -> writes under $ROOT only
  local exp="$1" seed="$2" t0
  local out="$ROOT/${exp}/seed_${seed}"
  mkdir -p "$out"
  t0=$(date +%s); stage_start "${exp} seed=${seed}"
  "$PY" -u -m "experiments.${exp}" --seed "$seed" --out "$out" --force > "$out/run.log" 2>&1
  local rc=$?
  stage_end "${exp} seed=${seed}" "$rc" "$t0"
  [ "$rc" -ne 0 ] && tail -20 "$out/run.log" | sed 's/^/      /' | tee -a "$LOG"
  return 0
}

# ---------------------------------------------------------------- stage 1
# E7 first: it is the D-36 blocker and the only stage with a manuscript claim
# waiting on it. If the window is cut short, this is the one that must exist.
for s in 47 48 49 50 51; do run_seeded e7_interface_ablation "$s"; done

# ---------------------------------------------------------------- stage 2
# Plan 19.2-23. E5 --force OVERWRITES the committed index_sensitivity.csv, so
# capture the committed copy off-tree FIRST -- it is the comparison baseline
# and the plan's attribution gate is meaningless without it.
git show HEAD:experiments/results/index_sensitivity.csv > "$SCRATCH/index_sensitivity.committed.csv"
git show HEAD:experiments/results/code_constants.csv    > "$SCRATCH/code_constants.committed.csv"
git show HEAD:experiments/results/cpr_grouping.csv      > "$SCRATCH/cpr_grouping.committed.csv"
git show HEAD:experiments/results/newton_iterations.csv > "$SCRATCH/newton_iterations.committed.csv"
echo "captured committed baselines for plan 23 into $SCRATCH" | tee -a "$LOG"

t0=$(date +%s); stage_start "E5 band (plan 23 task 1)"
"$PY" -u -m experiments.e5_index_sensitivity --force > "$SCRATCH/e5_band.log" 2>&1
stage_end "E5 band (plan 23 task 1)" "$?" "$t0"

t0=$(date +%s); stage_start "E3 tiers (plan 23 task 2)"
"$PY" -u -m experiments.e3_derived_quantities --force > "$SCRATCH/e3_tiers.log" 2>&1
stage_end "E3 tiers (plan 23 task 2)" "$?" "$t0"

# ---------------------------------------------------------------- stage 3
# E5's own seed-noise band (D-36). Writes ONLY under $ROOT -- the committed
# artifact regenerated in stage 2 is not touched.
for s in 42 43 44 45 46; do run_seeded e5_index_sensitivity "$s"; done

{
  echo
  echo "=== QUEUE COMPLETE $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC ==="
  grep -cE '^--- OK'     "$LOG" | sed 's/^/  succeeded: /'
  grep -cE '^--- FAILED' "$LOG" | sed 's/^/  failed:    /'
  echo "NOTHING COMMITTED -- commit the batch in the morning on a quiet box."
} | tee -a "$LOG"
