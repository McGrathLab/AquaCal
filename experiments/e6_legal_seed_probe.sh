#!/usr/bin/env bash
# E6 at naturally-legal non-42 seeds. Answers the one question the
# e6-seed-locked-clearance-floor debug report could NOT establish: legality is
# not convergence, and no non-42 seed has ever completed a single E6
# configuration.
#
# These seeds need NO source change -- both the calibration array (seed) and the
# holdout array (seed + 1_000_000) already clear the frozen GRID_DEPTH_RANGE[0]
# = 1.181852154281008. Verified 2026-08-03: 29 of seeds 0-499 are legal.
#
#   seed 62  calib 1.178591  holdout 1.179652   (widest margin under 100)
#   seed 28  calib 1.180858  holdout 1.179234
#
# Two seeds, not one, because anti-pattern 7 is blocking: a single seed cannot
# distinguish "E6 converges off 42" from a coincidence. Sequential, so seed 62's
# result is banked before 28 starts.
#
# Expect ~96 min per seed. Check `status` counts, NEVER the exit code -- E6
# records a failed configuration as a row and still exits 0.

set -u

ROOT="/c/Users/tucke/PycharmProjects/AquaCal"
export PYTHONPATH="$ROOT/src"

LOG="$ROOT/experiments/e6_legal_seed_probe.log"
STATE="$ROOT/experiments/e6_legal_seed_probe_state.tsv"

echo -e "seed\tstarted\tfinished\texit\tminutes" > "$STATE"

{
  echo "=== e6_legal_seed_probe start $(date -Is) ==="
  echo "HEAD $(git -C "$ROOT" rev-parse HEAD)"
  echo
} >> "$LOG"

for SEED in 62 28; do
  OUT="$ROOT/seed_sweep_19_3/e6/seed_${SEED}"
  mkdir -p "$OUT"

  T0=$(date +%s)
  STARTED=$(date -Is)
  echo "=== seed $SEED start $STARTED -> $OUT ===" >> "$LOG"

  python -u -m experiments.e6_generalization_sweep \
      --seed "$SEED" --out "$OUT" --force >> "$OUT/stdout.log" 2>&1
  RC=$?

  T1=$(date +%s)
  MINS=$(( (T1 - T0) / 60 ))
  echo -e "${SEED}\t${STARTED}\t$(date -Is)\t${RC}\t${MINS}" >> "$STATE"
  echo "=== seed $SEED done exit=$RC ${MINS}min ===" >> "$LOG"

  # Exit code is not evidence. Report the status column directly.
  if [ -f "$OUT/generalization_sweep.csv" ]; then
    python - "$OUT/generalization_sweep.csv" <<'PY' >> "$LOG" 2>&1
import collections, csv, sys
with open(sys.argv[1], newline="") as fh:
    rows = list(csv.DictReader(fh))
print("  rows:", len(rows), "status:", dict(collections.Counter(r.get("status") for r in rows)))
PY
  else
    echo "  NO CSV WRITTEN" >> "$LOG"
  fi
  echo >> "$LOG"
done

echo "=== e6_legal_seed_probe complete $(date -Is) ===" >> "$LOG"
