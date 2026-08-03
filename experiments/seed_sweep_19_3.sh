#!/usr/bin/env bash
#
# Phase 19.3 overnight seed sweep -- measures the noise floors that MF-08
# currently has to reason around.
#
# WHY THIS EXISTS
#
# MF-08 gates every "accuracy unaffected" claim on a measured seed band
# (D-19.3-17). Two gaps forced it to be more restrictive than it might need
# to be:
#
#   1. E1 carries only a PARTIAL claim. Its post-fix z_position_error moved
#      +0.252 mm against a 5-seed band of 0.105 mm -- 2.41x, i.e. outside seed
#      noise. But that band was measured on the PRE-fix geometry (19.2 plan 24),
#      and this phase deliberately changed the working volume (deeper,
#      re-centred). Comparing a post-fix delta to a pre-fix band is the weakest
#      inference in MF-08. This re-measures E1's band ON THE CORRECTED GEOMETRY
#      so the comparison is like-for-like.
#
#   2. E6 has NEVER had a seed sweep, which is why MF-08 can say nothing at all
#      about its accuracy. This measures one.
#
# Both are measurements, not gates. Whatever they show is what gets reported --
# including "the band is narrow and E1's movement is real", which would confirm
# the partial claim rather than lift it.
#
# ISOLATION: every invocation writes under seed_sweep_19_3/, NEVER
# experiments/results/. The committed artifacts from the 2026-08-02 production
# run carry a single git_sha (22e75ef) and must not be touched -- overwriting
# them would destroy the provenance plan 09 spent nine hours establishing.
# A fresh --out per seed also makes E6's checkpoint resume structurally
# impossible, which is the D-19.3-20 lesson: a distinct directory is the
# isolation mechanism, not --force.
#
# COMMIT NOTHING while this runs. Same freeze discipline as plan 09.
#
# python -u throughout (CLAUDE.md): without it a stalled run and a healthy one
# look identical in the log.
#
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

PY="${SEED_SWEEP_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
OUT_ROOT="seed_sweep_19_3"
SEEDS="42 43 44 45 46"
STATE="${OUT_ROOT}/state.tsv"

mkdir -p "$OUT_ROOT"
: > "$STATE"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

log() { echo "[$(ts)] $*"; }

run_stage() {
  local exp="$1" seed="$2" module="$3"
  local out="${OUT_ROOT}/${exp}/seed_${seed}"
  if grep -q "^${exp}	${seed}	complete	" "$STATE" 2>/dev/null; then
    log "SKIP ${exp} seed=${seed} (already complete)"
    return 0
  fi
  mkdir -p "$out"
  printf '%s\t%s\tstart\t%s\t\n' "$exp" "$seed" "$(ts)" >> "$STATE"
  log ">>> ${exp} seed=${seed} starting -> ${out}"
  "$PY" -u -m "$module" --seed "$seed" --out "$out" --force \
      > "${out}/stdout.log" 2>&1
  local rc=$?
  printf '%s\t%s\tcomplete\t%s\t%s\n' "$exp" "$seed" "$(ts)" "$rc" >> "$STATE"
  log "<<< ${exp} seed=${seed} finished exit=${rc}"
  return 0
}

log "Seed sweep starting. HEAD: $(git rev-parse HEAD)"
log "Writing under ${OUT_ROOT}/ -- experiments/results/ is NOT touched."

# E1 first: ~6 min per seed, ~35 min total. This is the one that can change
# MF-08's E1 verdict, so it lands early enough to be actionable even if the
# night is cut short.
for s in $SEEDS; do
  run_stage e1 "$s" experiments.e1_refractive_comparison
done
log "E1 sweep complete."

# E6 second: ~100 min per seed, ~8 h total. Fills the gap that currently forces
# MF-08 to make no accuracy statement about E6 at all.
for s in $SEEDS; do
  run_stage e6 "$s" experiments.e6_generalization_sweep
done
log "E6 sweep complete."

log "Seed sweep finished. State file: ${STATE}"
