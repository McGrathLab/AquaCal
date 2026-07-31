#!/usr/bin/env bash
# Plan 19.2-24 + D-36 combined seed sweep, 2026-07-31.
#
# Regenerates E7 and E1 on guarded code (plan 24) across five seeds so a SPREAD
# can be reported rather than a single-seed point estimate (D-36). E7's refined
# arms swing >10 mm across seeds -- larger than the shared-vs-per-camera gap the
# experiment exists to measure -- so its directional claim is currently
# unsupported by its own method.
#
# Runs strictly SEQUENTIALLY. Every one of these is a production run and the box
# is exclusive: two concurrent runs would make each other's timings and memory
# measure contention, and on a 15.7 GB box they would page against each other.
#
# Writes ONLY under $ROOT -- never into experiments/results/, whose committed
# values are the comparison baseline. Nothing here overwrites a committed
# artifact.
set -u  # NOT -e: one seed failing must not abandon the remaining seeds.

ROOT="/c/Users/tucke/Desktop/Aqua/AquaCal/seed_sweep_19_2"
SEEDS="42 43 44 45 46"
REPO="/c/Users/tucke/PycharmProjects/AquaCal"

mkdir -p "$ROOT"
cd "$REPO" || exit 1

{
  echo "=== plan 19.2-24 + D-36 seed sweep ==="
  echo "started : $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC"
  echo "HEAD    : $(git rev-parse HEAD)"
  echo "seeds   : $SEEDS"
  echo "root    : $ROOT"
  echo
} | tee "$ROOT/sweep.log"

run_one() {
  local exp="$1" seed="$2"
  local out="$ROOT/${exp}/seed_${seed}"
  mkdir -p "$out"
  local t0 t1
  t0=$(date +%s)
  echo "--- START ${exp} seed=${seed} at $(date -u '+%H:%M:%SZ') ---" | tee -a "$ROOT/sweep.log"
  python -u -m "experiments.${exp}" --seed "$seed" --out "$out" --force \
    > "$out/run.log" 2>&1
  local rc=$?
  t1=$(date +%s)
  if [ $rc -eq 0 ]; then
    echo "--- OK    ${exp} seed=${seed} rc=0 elapsed=$((t1-t0))s ---" | tee -a "$ROOT/sweep.log"
  else
    # Recorded, not fatal: a failed seed is data (which seed, which code), and
    # abandoning the sweep would waste the remaining hours.
    echo "--- FAILED ${exp} seed=${seed} rc=${rc} elapsed=$((t1-t0))s ---" | tee -a "$ROOT/sweep.log"
    tail -20 "$out/run.log" | sed 's/^/      /' | tee -a "$ROOT/sweep.log"
  fi
}

# E7 first: it is the D-36 blocker. If the window runs out mid-sweep, the
# experiment whose manuscript claim is currently unsupported is the one that
# must have finished.
for s in $SEEDS; do run_one e7_interface_ablation "$s"; done
for s in $SEEDS; do run_one e1_refractive_comparison "$s"; done

{
  echo
  echo "=== SWEEP COMPLETE $(date -u '+%Y-%m-%dT%H:%M:%SZ') UTC ==="
  grep -cE '^--- OK' "$ROOT/sweep.log" | sed 's/^/  succeeded: /'
  grep -cE '^--- FAILED' "$ROOT/sweep.log" | sed 's/^/  failed:    /'
} | tee -a "$ROOT/sweep.log"
