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
#   The mechanism is `SUITE_FAILED`: a stage that exits non-zero, or whose gate
#   verdict reports a FAIL, appends a line to the run's FAILURE LOG. `main`
#   reprints that log as a terminal summary block and exits `${SUITE_FAILED}`.
#   The failure log is a FILE rather than a shell variable because concurrent
#   stages run in child processes and a child cannot set its parent's variable.
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
# THREE CHECK POINTS (D-02), AND WHY THE LAST ONE IS NOT REDUNDANT.
# ============================================================================
#
#   1. PRE-FLIGHT, before stage 1 -- preconditions. Aborts (D-03).
#   2. AFTER EACH STAGE -- `run_gate_check` against that stage's out dir. A
#      FAIL is sticky, never fatal.
#   3. END-OF-RUN ROLL-UP over the WHOLE tree at the run's profile. A FAIL is
#      sticky, and it is the check whose ABSENCE produced F-001.
#
# The roll-up is not covered by (2), and it is specifically not covered by
# Gate 3: `_check_git_sha_consistency` (`check_rerun_gates.py:1749-1754`)
# returns PASS over an EMPTY tree -- "no git_sha values found across any
# artifact to compare" is a PASS. A cross-artifact consistency gate that
# succeeds BECAUSE there are no artifacts cannot be evidence of a complete run.
# Do NOT weaken Gate 3 to cover this; the roll-up is the right owner, because
# it is the only check that judges what is ABSENT rather than what it finds.
#
# ============================================================================
# CONCURRENCY (D-52). SELECTIVE, NOT GENERAL.
# ============================================================================
#
# Measured 2026-08-18 (`.planning/probes/2026-08-18-solver-concurrency/`): a
# solve holds a MEDIAN 0.99 cores of 20, mean 1.20, p95 2.01, peak 2.56, stable
# through Stage 3. So ~30 of the target box's 32 cores idle during every
# accuracy stage. Running the accuracy stages 4-5 wide takes the serial
# ~22-26 h estimate to ~15-16 h and requires NO change to any experiment.
#
# `SUITE_WORKERS` DEFAULTS TO 4 AND IS BOUNDED TO 4-5. The probe reports
# `recommended_workers: 16`; DO NOT WIDEN THE POOL ON IT. The probe's own
# caveat is load-bearing -- E1 is the cheapest and smallest solve in the suite
# (peak RSS 0.61 GiB) and its peak RSS does not transfer. Peak RSS tracks FRAME
# COUNT: 30 frames < 1 GiB (E5), 100 frames 2.7-3.5 GiB (E6's band, all 102
# rows at n_frames=100), 200 frames 9.3-11.3 GiB (E2, E4).
#
# THREE HARD CONSTRAINTS, all enforced by the scheduler from the MANIFEST's
# per-stage attributes rather than a hardcoded stage list:
#
#   1. `e6_repeat1` and `e6_band` MUST NEVER OVERLAP. `run_stage_e6_repeat1`
#      does `rm -rf ${OUT_DIR}/e6_configs` and removes
#      `generalization_sweep.csv` / `e6_provenance.json` under the SHARED
#      `OUT_DIR` that `e6_band` also writes. Expressed as `e6_band`'s
#      `depends_on` edge, because a pool can honour a dependency and cannot
#      honour a comment. An overlap here is a real `rm -rf` collision, not a
#      bookkeeping error.
#   2. AT MOST ONE `frame_class == "200"` STAGE IN FLIGHT. Five 3.5 GiB stages
#      plus one 200-frame stage is 27.8 of ~31 GiB, too tight.
#   3. A `concurrency == "serial_alone"` STAGE RUNS ALONE, and nothing starts
#      until it finishes -- `e4`, `e4_repeat`, `e2_timing`, `e2_memory`. The
#      constraint protects TIMING INTEGRITY (review H4), which is why it is
#      about those four stages specifically and not about memory.
#
# `SUITE_SERIAL=1` forces the fully serial path -- the escape hatch if the pool
# ever looks implicated in a result. `SUITE_WORKERS` sets the width.
#
# NOT ATTEMPTED, DELIBERATELY: splitting `e6_band` across processes by seed. It
# attacks the critical path (8.9 h, ~40% of the suite) but needs a merge step
# and provenance handling INSIDE the experiment; CONTEXT § E declines it.
#
# Phase 27's Linux smoke pass confirms the same OpenBLAS build behaves the same
# way on the target box. That is two minutes there, not a reason to defer the
# pool here.
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

# `SUITE_OUT_DIR` exists so the driver's own dry-run tests can sandbox every
# path they touch under a tmp_path. A production run never sets it.
OUT_DIR="${SUITE_OUT_DIR:-experiments/results}"
OUT_DIR_E4_REPEAT="experiments/results_e4_repeat"
OUT_DIR_E2_BAND="experiments/results_e2_band"
# E2's timing and memory runs get their OWN output directories so the
# completeness gate can attribute every `benchmark.json` to the invocation that
# produced it. Three E2 runs sharing one directory would overwrite each other's
# benchmark.json and the surviving file would silently be whichever ran last.
OUT_DIR_E2_TIMING="experiments/results_e2_timing"
OUT_DIR_E2_MEMORY="experiments/results_e2_memory"

# The frozen sha. Read ONCE, here, and never again -- see D-27 above. Short
# form only; it names the state file. `--short` is portable across the git
# versions on both boxes; `git describe` is deliberately not used here (it
# needs a tag and would be empty on an untagged commit).
FROZEN_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "unknownsha")"

# `SUITE_STATE_DIR` is a test-sandbox override, exactly like SUITE_OUT_DIR. It
# does NOT touch the dry-run/real separation below -- both paths are derived
# from it, so a test can still assert that a dry run leaves the REAL path
# absent, which is the property the 19.5 fix exists to guarantee.
STATE_DIR="${SUITE_STATE_DIR:-experiments}"
mkdir -p "${STATE_DIR}"

# D-23 as halved by D-48 (sha-derived path) + the 19.5 dry-run separation.
if [ -n "${RUN_EXPERIMENT_SUITE_DRY_RUN:-}" ]; then
  STATE_FILE="${STATE_DIR}/run_experiment_suite_state.${FROZEN_SHA}.dryrun.tsv"
else
  STATE_FILE="${STATE_DIR}/run_experiment_suite_state.${FROZEN_SHA}.tsv"
fi

# D-01's sticky-failure record. A FILE and not a shell variable: concurrent
# stages run in child processes, and a child cannot set its parent's variable.
# Each line is one finding; `main` reprints the whole file as the terminal
# summary and exits non-zero if it is non-empty.
#
# TRUNCATED AT THE START OF EVERY INVOCATION, deliberately. A resume re-runs
# only the stages that have no completion line, so carrying a previous
# invocation's findings forward would report failures the current run has
# already fixed. The durable per-stage record is the state file's exit-code
# column, which is never truncated.
SUITE_FAILURE_LOG="${STATE_FILE%.tsv}.failures.txt"

# Per-stage stdout logs. Interleaved stdout from four concurrent stages is
# unreadable, so each stage also gets its own file; the console still sees
# everything via `tee`.
STAGE_LOG_DIR="${STATE_FILE%.tsv}.stagelogs"
STAGE_DONE_DIR="${STAGE_LOG_DIR}/.done"

# TWO SNAPSHOTS TAKEN HERE AND NOWHERE ELSE, because pre-flight destroys the
# evidence for both: `run_one_stage` writes the state file's first line before
# `run_stage_preflight` is even called, and pre-flight's first act is to write
# `run_manifest.json` INTO the output tree. Evaluating either condition inside
# pre-flight would therefore always answer "state file exists, output tree
# non-empty" and the D-24 refusal would be dead code.
if [ -f "${STATE_FILE}" ]; then
  STATE_FILE_PREEXISTED=1
else
  STATE_FILE_PREEXISTED=0
fi
if [ -d "${OUT_DIR}" ] && [ -n "$(ls -A "${OUT_DIR}" 2>/dev/null)" ]; then
  OUT_DIR_WAS_NONEMPTY=1
else
  OUT_DIR_WAS_NONEMPTY=0
fi

# D-01. Set to 1 by any stage failure, any gate FAIL, or any roll-up FAIL.
# `main` exits with it. Nothing in this file may abort the queue once stage 1
# has begun (D-50); this variable is how a failure is carried to the end
# instead.
SUITE_FAILED=0

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
# E1's band is a UNIFORM grid (ruling A1): FOUR seeds x the four levels of
# NOISE_LEVELS. See run_stage_e1_band for the arithmetic and for why four and
# not ten.
E1_BAND_SEEDS="42,43,44,45"

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

# E2's THREE production invocation configs are GENERATED from the release
# config at run time (plan 26-06's `--emit-invocation-configs`), never
# committed: committing them would hard-code the absolute release path three
# more times and Phase 27 would have to edit every copy. The variants differ
# only in `internals` keys, which are YAML settings and not CLI flags (D-15,
# D-16) -- that is why each invocation needs its own config at all.
E2_INVOCATION_DIR="${SUITE_E2_INVOCATION_DIR:-experiments/results_e2_invocations}"
E2_PRODUCTION_CONFIG="${E2_INVOCATION_DIR}/config_e2_classification.yaml"
E2_TIMING_CONFIG="${E2_INVOCATION_DIR}/config_e2_timing.yaml"
E2_MEMORY_CONFIG="${E2_INVOCATION_DIR}/config_e2_memory.yaml"

# The archived pre-re-run baseline `--check` reads FROM (D-12). Plan 26-01
# moved the old committed results here as pure renames; without it E2's ~1e-8
# control and E3's tier diff both compare against the tree the run is
# simultaneously overwriting, which is not a control at all. Overridable so
# Phase 27 can repoint it on the run machine.
BASELINE_DIR="${SUITE_BASELINE_DIR:-experiments/pre_rerun_baseline/results}"

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

# THE STAGE LIST. Every entry here has a matching entry in
# `experiments/suite_expectations.json` and a matching `run_stage_<id>`
# function below; `tests/unit/test_suite_stage_list.py` asserts BOTH directions
# and proves this array is a topological order of the manifest's `depends_on`
# edges. If you add a stage, add it in all three places or that test fails --
# which is the point: F-001 was an invocation that existed in no driver.
#
# Order is a topological sort of the dependency edges, SHORTEST-FIRST within
# each dependency level (D-37), using the est_hours in the manifest:
#
#   level 0  preflight(0.02)
#   level 1  prelaunch_probe(0.01) e3(0.005) fd_jacobian(0.05) e1(0.09)
#            e7(0.09) e5(0.76) e2_production(0.8-1.45) e6_repeat1(2.78)
#   level 2  reconstruction_bootstrap(0.06) e2_timing e2_memory e7_band(1-2)
#            e5_band(2.34) e2_band(2.42) e1_band(2.8) e4(3.57) e6_band(8.9)
#   level 3  e7_focal_standoff(0.02) e4_repeat(0.99)
#
# ONE DELIBERATE INVERSION OF SHORTEST-FIRST: `prelaunch_probe` (0.01 h) is
# placed before `e3` (0.005 h). The difference is about twenty seconds, and the
# probe is a HARD-ABORT stage (D-03) while `e3 --force` REWRITES committed tier
# CSVs. Aborting after mutating tracked artifacts, to save twenty seconds, is a
# bad trade.
STAGES=(
  preflight
  prelaunch_probe
  e3
  fd_jacobian
  e1
  e7
  e5
  e2_production
  e6_repeat1
  reconstruction_bootstrap
  e2_timing
  e2_memory
  e7_band
  e5_band
  e2_band
  e1_band
  e4
  e6_band
  e7_focal_standoff
  e4_repeat
)

# --- Arguments --------------------------------------------------------------
#
# EVERY FLAG BELOW EXCEPT --profile/--remaining-hours/--start-stage IS AN
# OVERRIDE FOR ONE PRE-FLIGHT REFUSAL (D-50). That is the whole design: a
# refusal that cannot be bypassed is a check that can cost a night, so every
# refusal message names its own flag and every flag disables exactly one
# refusal. They are enumerated in `suite_expectations.json`'s
# `preflight.overrides` as well, so the manifest and the parser can be diffed
# against each other.
SKIP_E2=0
ALLOW_NONEMPTY_OUT=0
ALLOW_LOW_DISK=0
ALLOW_FRAMESET_MISMATCH=0
ALLOW_GATE_PRECHECK_FAILURE=0
PROFILE="full"
REMAINING_HOURS=""
START_STAGE=1

usage() {
  cat <<'USAGE'
Usage: bash experiments/run_experiment_suite.sh [N] [options]

  N, --start-stage N        Start from the 1-indexed stage N (infrastructure
                            recovery only -- never the recovery path for a src
                            defect, which is always restart-from-stage-1).
  --profile {smoke,full}    Expectation profile for the completeness gate.
                            Default: full.
  --remaining-hours H       Warn (never abort) if the estimated wall clock
                            exceeds H hours (D-38).

Pre-flight overrides (D-50 -- each disables exactly one refusal):
  --skip-e2                 DECLARE that the E2 frameset is absent. The run
                            becomes synthetic-only, the omission is announced
                            at launch and reprinted in the end-of-run roll-up,
                            and E2's artifacts still count as missing.
  --allow-frameset-mismatch Proceed although the frameset's identity signature
                            does not match the manifest.
  --allow-nonempty-out      Proceed although the output tree is non-empty and
                            no state file exists for this sha.
  --allow-low-disk          Proceed although free space is below the manifest's
                            crude absolute floor.
  --allow-gate-precheck-failure
                            Proceed although the completeness gate could not be
                            invoked at pre-flight.

Environment:
  SUITE_WORKERS=4           Concurrency width (bounded to 4-5; D-52).
  SUITE_SERIAL=1            Force the fully serial path.
  SUITE_OUT_DIR             Output tree (test sandboxing only).
  SUITE_STATE_DIR           State-file directory (test sandboxing only).
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-e2) SKIP_E2=1 ;;
    --allow-nonempty-out) ALLOW_NONEMPTY_OUT=1 ;;
    --allow-low-disk) ALLOW_LOW_DISK=1 ;;
    --allow-frameset-mismatch) ALLOW_FRAMESET_MISMATCH=1 ;;
    --allow-gate-precheck-failure) ALLOW_GATE_PRECHECK_FAILURE=1 ;;
    --profile) PROFILE="${2:-}"; shift ;;
    --profile=*) PROFILE="${1#*=}" ;;
    --remaining-hours) REMAINING_HOURS="${2:-}"; shift ;;
    --remaining-hours=*) REMAINING_HOURS="${1#*=}" ;;
    --start-stage) START_STAGE="${2:-1}"; shift ;;
    --start-stage=*) START_STAGE="${1#*=}" ;;
    -h|--help) usage; exit 0 ;;
    ''|*[!0-9]*)
      echo "ERROR: unrecognised argument '$1'." >&2
      usage >&2
      exit 2
      ;;
    *) START_STAGE="$1" ;;
  esac
  shift
done

case "${PROFILE}" in
  smoke|full) ;;
  *) echo "ERROR: --profile must be 'smoke' or 'full', got '${PROFILE}'." >&2; exit 2 ;;
esac

# D-52: bounded to 4-5. NOT the probe's recommended_workers: 16 -- see the
# concurrency section of the header for why that number does not transfer.
SUITE_WORKERS="${SUITE_WORKERS:-4}"
case "${SUITE_WORKERS}" in
  4|5) ;;
  *)
    echo "WARNING: SUITE_WORKERS=${SUITE_WORKERS} is outside the sanctioned 4-5 band (D-52); clamping to 4. Widen this only with a measurement, never on the probe's recommended_workers: 16, which was taken on E1 -- the cheapest and smallest solve in the suite." >&2
    SUITE_WORKERS=4
    ;;
esac

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

# MILLISECOND RESOLUTION, and it is not cosmetic. Under D-52's pool these
# stamps are the ONLY record of which stages overlapped, and the driver's own
# dry-run tests assert `e6_band.start > e6_repeat1.complete` from them. At
# whole-second resolution a dry run -- every stage of which finishes in
# milliseconds -- produces ties, and a tie cannot distinguish "ordered
# correctly" from "overlapped". The format stays ISO-8601 and stays parseable
# by `datetime.fromisoformat` once the trailing Z is handled.
#
# `%3N` is a GNU date extension. It is present in Git Bash (MINGW64) and on the
# Linux run machine; the probe below degrades to whole seconds anywhere else
# rather than writing the literal string "%3N" into the timing record.
if date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null | grep -q 'N'; then
  STATE_TIME_FMT="%Y-%m-%dT%H:%M:%SZ"
else
  STATE_TIME_FMT="%Y-%m-%dT%H:%M:%S.%3NZ"
fi

state_start() {
  local name="$1" idx="$2"
  printf '%s\t%s\tstart\t%s\t\n' "${name}" "${idx}" "$(date -u +"${STATE_TIME_FMT}")" >>"${STATE_FILE}"
}

state_complete() {
  local name="$1" idx="$2" exit_code="$3"
  printf '%s\t%s\tcomplete\t%s\t%s\n' "${name}" "${idx}" "$(date -u +"${STATE_TIME_FMT}")" "${exit_code}" >>"${STATE_FILE}"
}

record_failure() {
  # D-01. Append one finding to the sticky failure log. Called from the parent
  # AND from concurrent child processes, which is why it appends to a file:
  # a child cannot set `SUITE_FAILED` in its parent. A single short `printf`
  # to an O_APPEND file descriptor is not interleaved by the kernel.
  printf '%s\n' "$*" >>"${SUITE_FAILURE_LOG}"
}

# The gate exit code from the LAST `run_gate_check`. D-01 is a change to that
# function's CALLER, not to the function: `run_gate_check` still always returns
# 0, so a gate FAIL can never abort the queue, and the caller reads the verdict
# from here to set the sticky flag.
LAST_GATE_EXIT=0

run_gate_check() {
  local target_dir="$1" stage_name="$2"
  # THE DRY-RUN SEAM, inserted ahead of the real body so no line of it moves.
  # Without this a "dry" run would still invoke check_rerun_gates.py 18 times
  # against the real results tree -- which is neither dry nor fast, and would
  # make every dry run report FAILs it did not cause.
  if _dry_run_active; then
    echo "----- GATE VERDICT: stage=${stage_name} out_dir=${target_dir} (DRY RUN) -----"
    _dry_run_stub
    LAST_GATE_EXIT=$?
    echo "----- END GATE VERDICT: stage=${stage_name} exit=${LAST_GATE_EXIT} (DRY RUN) -----"
    return 0
  fi
  echo "----- GATE VERDICT: stage=${stage_name} out_dir=${target_dir} -----"
  # PINNED INTERPRETER, and it matters: check_rerun_gates.py imports pandas and
  # aquacal, so it is NOT stdlib-only. Never a bare `python` here -- that was a
  # real 19.3 defect, fixed in 19.4/19.5 and asserted by
  # tests/unit/test_suite_stage_list.py.
  "${GATE_PYTHON}" experiments/check_rerun_gates.py "${target_dir}" --profile "${PROFILE}" --stage "${stage_name}"
  local gate_exit=$?
  LAST_GATE_EXIT="${gate_exit}"
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

run_stage_preflight() {
  # PRE-FLIGHT (D-03, DRIVER-02). A HARD-ABORT stage: it runs before any long
  # stage, so a refusal here costs minutes and nothing is lost.
  #
  # Emits the one-shot suite run manifest. NOTHING HAS EVER CALLED THIS
  # EMITTER: `experiments/_run_manifest.py` exists (plan 26-02) and no driver
  # invoked it, which is the same shape of gap as F-001 itself. It records the
  # git describe, the installed package version and the environment the whole
  # run is attributable to -- the provenance spine that fractured into six
  # shas because it was never written once at the top.
  #
  # Uses GATE_PYTHON rather than the run's own interpreter: this is tooling, it
  # imports the same stack the gates do, and pre-flight must not be the place a
  # bare Anaconda-base interpreter surfaces.
  #
  # ------------------------------------------------------------------------
  # WHAT PRE-FLIGHT DELIBERATELY DOES *NOT* REFUSE. Do not "restore" these.
  # D-24 asked for four refusals; D-46 and D-47 SUPERSEDE it and cut two, and
  # D-48 cut a third from D-23. TWO SURVIVE: the frameset identity check and
  # the state-file/output-tree consistency check.
  #
  #   * NO DIRTY-TREE REFUSAL (D-47). `experiments/results/` is TRACKED, so the
  #     run dirties its own working tree. The refusal would fire on RESUME and
  #     refuse every restart after the first crash -- a check that kills a run
  #     which would otherwise have succeeded. Gate 3 records dirtiness
  #     post-hoc (D-21), which can never kill a run, and the run manifest
  #     records `git_dirty`.
  #   * NO DISK-HEADROOM ESTIMATOR (D-46). A wrong estimate is precisely the
  #     malformed-check failure mode the de-scoping targets. Free space is
  #     LOGGED and compared against a crude absolute floor instead.
  #   * NO HEAD-VS-STATE-FILE REFUSAL (D-48). The sha-derived state path
  #     already makes a foreign state file structurally unreachable; the
  #     refusal is the half that can wrongly block a 3 a.m. resume.
  #
  # D-50 binds every surviving refusal: each prints the exact override flag
  # that bypasses it, and the flags are enumerated in the manifest's
  # `preflight.overrides` as well.
  # ------------------------------------------------------------------------
  if _dry_run_active; then
    log "preflight: DRY RUN"
    _dry_run_stub
    return $?
  fi

  # 1. THE RUN MANIFEST (D-19).
  # `--force` is passed deliberately. The manifest is written ONCE PER RUN, and
  # a stage without a completion line is always re-run from scratch, so a
  # resume after a crash mid-pre-flight must be able to rewrite it. Without
  # `--force` that resume dies on FileExistsError at the one stage whose
  # failure aborts the queue.
  log "preflight: writing the suite run manifest into ${OUT_DIR}"
  "${GATE_PYTHON}" -m experiments._run_manifest --out "${OUT_DIR}" --force
  local manifest_exit=$?
  if [ "${manifest_exit}" -ne 0 ]; then
    log "PREFLIGHT REFUSAL: the run manifest could not be written (exit=${manifest_exit}). Every artifact's provenance anchors to it, so a run without one is unreportable. There is NO override for this refusal -- fix the emitter or the output directory and restart from stage 1."
    return "${manifest_exit}"
  fi

  # 2. E2 FRAMESET IDENTITY, NOT PRESENCE (D-17).
  #    OVERRIDE: --skip-e2 when it is ABSENT (which DECLARES a synthetic-only
  #    run), --allow-frameset-mismatch when it is present but not the archive
  #    the manifest describes. Two mistakes, two flags.
  _preflight_frameset || return $?

  # 3. NON-EMPTY OUTPUT TREE WITH NO MATCHING STATE FILE FOR THIS SHA (D-24).
  #    Phrased exactly this way so a GENUINE RESUME still proceeds: if a state
  #    file for this sha exists, the non-empty tree is this run's own output
  #    and refusing would brick the recovery path the driver was built around.
  #    Both conditions were snapshotted at script start -- see the comment
  #    there for why they cannot be evaluated here.
  if [ "${OUT_DIR_WAS_NONEMPTY}" -eq 1 ] && [ "${STATE_FILE_PREEXISTED}" -eq 0 ]; then
    if [ "${ALLOW_NONEMPTY_OUT}" -eq 1 ]; then
      log "preflight: ${OUT_DIR} was non-empty at launch with no state file for sha ${FROZEN_SHA} -- proceeding because --allow-nonempty-out was passed. Artifacts from a previous run may be mistaken for this one's."
    else
      log "PREFLIGHT REFUSAL: ${OUT_DIR} is NOT EMPTY and there is no state file for sha ${FROZEN_SHA} (${STATE_FILE}). This is a FRESH run into a tree that already holds someone else's artifacts, and the completeness gate would report them as this run's. Move them aside (plan 26-09's archive-aside), or OVERRIDE with: --allow-nonempty-out"
      return 1
    fi
  fi

  # 4. FREE SPACE -- LOGGED, and refused only below the manifest's crude
  #    absolute floor. NO ESTIMATOR (D-46). OVERRIDE: --allow-low-disk.
  _preflight_free_space || return $?

  # 5. D-02's FIRST CHECK POINT: the completeness gate, at the run's profile,
  #    with no --stage selector. OVERRIDE: --allow-gate-precheck-failure.
  _preflight_completeness_gate || return $?

  # 6. D-38: warn, NEVER abort, when the estimated wall clock exceeds the
  #    window the operator says they have.
  _preflight_wall_clock_warning

  log "preflight: all checks passed. Profile=${PROFILE}, workers=${SUITE_WORKERS}, serial=${SUITE_SERIAL:-0}, skip_e2=${SKIP_E2}."
  return 0
}

_preflight_frameset() {
  # D-17: IDENTITY, not mere presence. The signature is read FROM THE MANIFEST
  # and never written as a literal in this script -- not even in a comment.
  # That is exactly how the RETIRED archive's usable/validation/comparison
  # counts survived in a code comment on this branch (FIX-06) while the
  # verified signature said something else; both signatures now live in
  # `suite_expectations.json`'s `preflight.frameset`, which is the only place
  # either may be written. A presence-only check passes cleanly on the wrong
  # archive and hands you a control that reads red for a reason nobody would
  # guess at 3 a.m.
  #
  # Exit codes from the probe below: 0 present and matching, 2 absent, 3
  # present but mismatched. Absence and mismatch are DIFFERENT refusals with
  # DIFFERENT overrides, because they are different mistakes.
  local probe_out probe_exit
  probe_out="$(SUITE_E2_RELEASE_CONFIG="${E2_RELEASE_CONFIG}" "${GATE_PYTHON}" - <<'PY'
import json
import os
import pathlib
import sys

manifest = json.loads(
    pathlib.Path("experiments/suite_expectations.json").read_text(encoding="utf-8")
)
frameset = manifest["preflight"]["frameset"]
cheap = frameset["cheap_check"]

print(
    "frameset signature required by the manifest: "
    f"{frameset['usable_frames']} usable -> {frameset['validation_frames']} "
    f"validation -> {frameset['comparisons']} comparisons "
    f"({frameset['verified']})"
)

config_path = pathlib.Path(os.environ["SUITE_E2_RELEASE_CONFIG"])
if not config_path.is_file():
    print(f"ABSENT: the E2 release config does not exist at {config_path}")
    sys.exit(2)

import yaml  # noqa: E402  (only needed once the config is known to exist)

config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
declared = config.get("paths", {}).get("extrinsic_videos", {}) or {}
paths = [pathlib.Path(p) for p in declared.values()]
present = [p for p in paths if p.is_file()]
total_bytes = sum(p.stat().st_size for p in present)

expected_n = cheap["n_extrinsic_videos"]
min_bytes = cheap["min_total_bytes"]
print(
    f"observed: {len(paths)} extrinsic video path(s) declared, {len(present)} "
    f"present, {total_bytes} total bytes"
)
print(f"expected: {expected_n} present, at least {min_bytes} total bytes")

if not present:
    print("ABSENT: no extrinsic video declared by the release config exists.")
    sys.exit(2)

problems = []
if len(present) != expected_n:
    problems.append(
        f"expected {expected_n} extrinsic videos, found {len(present)} present "
        f"of {len(paths)} declared"
    )
if total_bytes < min_bytes:
    retired = frameset["retired_signature"]
    problems.append(
        f"total frameset size {total_bytes} B is below the floor {min_bytes} B "
        f"-- this looks like the RETIRED, ~4.3x-subsampled archive "
        f"({retired['usable_frames']} usable -> {retired['validation_frames']} "
        f"validation -> {retired['comparisons']} comparisons), not the "
        "verified one"
    )
if problems:
    for problem in problems:
        print(f"MISMATCH: {problem}")
    sys.exit(3)

print("MATCH: the frameset's cheap identity check agrees with the manifest.")
sys.exit(0)
PY
)"
  probe_exit=$?
  printf '%s\n' "${probe_out}"

  case "${probe_exit}" in
    0)
      log "preflight: E2 frameset identity check PASSED."
      return 0
      ;;
    2)
      if [ "${SKIP_E2}" -eq 1 ]; then
        log "preflight: E2 frameset is ABSENT and the omission was DECLARED via --skip-e2. See the DECLARED REDUCTION banner; this run is SYNTHETIC-ONLY."
        _write_declared_reduction_marker
        return 0
      fi
      log "PREFLIGHT REFUSAL: the E2 frameset is ABSENT (D-14). E2's production, timing, memory and band stages cannot run, and E4 silently drops its real-rig row without E2's benchmark.json. If you meant to run without it, DECLARE it with: --skip-e2"
      return 1
      ;;
    3)
      if [ "${ALLOW_FRAMESET_MISMATCH}" -eq 1 ]; then
        log "preflight: E2 frameset identity MISMATCH, proceeding because --allow-frameset-mismatch was passed. E2's ~1e-8 reproduction control is NOT valid against a different frameset."
        return 0
      fi
      log "PREFLIGHT REFUSAL: the E2 frameset is present but its identity does NOT match the manifest (D-17). E2's ~1e-8 reproduction only means anything if the fresh run reads the SAME frames; this project has already shipped a frameset mix-up. Point SUITE_E2_RELEASE_CONFIG at the right archive, or OVERRIDE with: --allow-frameset-mismatch"
      return 1
      ;;
    *)
      log "PREFLIGHT REFUSAL: the frameset identity probe itself failed (exit=${probe_exit}) -- the check is broken, not necessarily the frameset. Read its output above. If you have verified the frameset by hand, OVERRIDE with: --allow-frameset-mismatch"
      if [ "${ALLOW_FRAMESET_MISMATCH}" -eq 1 ]; then
        log "preflight: proceeding anyway because --allow-frameset-mismatch was passed."
        return 0
      fi
      return 1
      ;;
  esac
}

_write_declared_reduction_marker() {
  # D-14: a *silent* skip must be impossible. "Loud" alone is a log line and
  # nobody reads the log overnight, so the declaration is also a FILE that the
  # end-of-run roll-up reprints -- and E2's artifacts still count as missing,
  # so the run's exit code is non-zero regardless.
  local marker
  marker="${OUT_DIR}/$("${GATE_PYTHON}" -c "
import json, pathlib
print(json.loads(pathlib.Path('experiments/suite_expectations.json').read_text(encoding='utf-8'))['preflight']['declared_reduction_marker'])
" 2>/dev/null || echo declared_reductions.json)"
  printf '%s\n' "{\"skip_e2\": true, \"declared_at\": \"$(date -u +"${STATE_TIME_FMT}")\", \"frozen_sha\": \"${FROZEN_SHA}\", \"note\": \"--skip-e2 was passed: the E2 frameset was absent and the omission was DECLARED. This run is SYNTHETIC-ONLY. E2's artifacts are still expected by the completeness gate and their absence still makes the final exit non-zero.\"}" >"${marker}"
  log "preflight: wrote the DECLARED REDUCTION marker to ${marker}"
}

_preflight_free_space() {
  # LOGGED, and refused only below a CRUDE ABSOLUTE FLOOR (D-46). There is
  # deliberately no estimate of the run's output footprint here: a wrong
  # estimate is the malformed-check failure mode this de-scoping targets.
  local floor_gib avail_kib avail_gib
  floor_gib="$("${GATE_PYTHON}" -c "
import json, pathlib
print(json.loads(pathlib.Path('experiments/suite_expectations.json').read_text(encoding='utf-8'))['preflight']['free_space_floor_gib'])
" 2>/dev/null)"
  if [ -z "${floor_gib}" ]; then
    log "preflight: WARNING -- could not read preflight.free_space_floor_gib from the manifest; skipping the free-space refusal rather than guessing."
    return 0
  fi
  avail_kib="$(df -Pk . 2>/dev/null | awk 'NR==2 {print $4}')"
  if [ -z "${avail_kib}" ]; then
    log "preflight: WARNING -- could not read free space via df; skipping the free-space refusal rather than guessing."
    return 0
  fi
  avail_gib=$((avail_kib / 1024 / 1024))
  log "preflight: free space on the output filesystem: ${avail_gib} GiB (crude absolute floor: ${floor_gib} GiB)."
  if [ "${avail_gib}" -lt "${floor_gib}" ]; then
    if [ "${ALLOW_LOW_DISK}" -eq 1 ]; then
      log "preflight: free space ${avail_gib} GiB is below the ${floor_gib} GiB floor, proceeding because --allow-low-disk was passed."
      return 0
    fi
    log "PREFLIGHT REFUSAL: free space ${avail_gib} GiB is below the manifest's crude floor of ${floor_gib} GiB. A suite that fills the disk at hour 14 loses every stage after it. Free some space, or OVERRIDE with: --allow-low-disk"
    return 1
  fi
  return 0
}

_preflight_completeness_gate() {
  # D-02's FIRST CHECK POINT. Note carefully WHAT IS BEING CHECKED: at
  # pre-flight the output tree is empty by construction, so the completeness
  # gate is EXPECTED to report FAILs. Those FAILs are not the signal and never
  # abort. The signal is whether the gate RAN AT ALL -- a malformed manifest,
  # a broken import or a missing interpreter discovered at hour 18 is exactly
  # the class of failure pre-flight exists to convert into a two-minute one.
  #
  # The gate exits 1 both on "some artifacts are missing" and on an uncaught
  # exception, so the exit code cannot distinguish them. Its terminal "TOTAL:"
  # line can: it is printed only after every gate has produced a verdict.
  local gate_out
  gate_out="$("${GATE_PYTHON}" experiments/check_rerun_gates.py "${OUT_DIR}" --profile "${PROFILE}" 2>&1)"
  printf '%s\n' "${gate_out}" | tail -n 5
  if printf '%s\n' "${gate_out}" | grep -q '^TOTAL:'; then
    log "preflight: the completeness gate is invokable at profile '${PROFILE}' and its manifest parses. (FAILs over the pre-run empty tree are EXPECTED and are not a refusal.)"
    return 0
  fi
  if [ "${ALLOW_GATE_PRECHECK_FAILURE}" -eq 1 ]; then
    log "preflight: the completeness gate could not be invoked, proceeding because --allow-gate-precheck-failure was passed. The end-of-run roll-up will not be able to judge this run."
    return 0
  fi
  printf '%s\n' "${gate_out}"
  log "PREFLIGHT REFUSAL: the completeness gate could not be invoked (no TOTAL line -- it crashed rather than reporting verdicts). The end-of-run roll-up is what turns a missing artifact into a non-zero exit, so a run whose gate cannot run is a run that can exit 0 while producing nothing. Fix it, or OVERRIDE with: --allow-gate-precheck-failure"
  return 1
}

_preflight_wall_clock_warning() {
  # D-38. A WARNING and never a refusal: an estimate that aborts a run is the
  # malformed-check failure mode again, and this one is an estimate by
  # construction.
  [ -n "${REMAINING_HOURS}" ] || return 0
  SUITE_REMAINING_HOURS="${REMAINING_HOURS}" SUITE_WORKERS_FOR_EST="${SUITE_SERIAL:-0}" "${GATE_PYTHON}" - <<'PY'
import json
import os
import pathlib

manifest = json.loads(
    pathlib.Path("experiments/suite_expectations.json").read_text(encoding="utf-8")
)
summary = manifest["wall_clock_summary"]
serial = os.environ.get("SUITE_WORKERS_FOR_EST", "0") not in ("", "0")
key = "serial_total_hours" if serial else "expected_total_with_concurrency_hours"
low, high = summary[key]
remaining = float(os.environ["SUITE_REMAINING_HOURS"])
mode = "serial" if serial else "pooled"
if high > remaining:
    print(
        f"WARNING (D-38): the {mode} wall-clock estimate is {low}-{high} h and "
        f"you declared {remaining} h remaining. The estimate is for the "
        f"Windows planning box ({summary['machine']}); the run machine is "
        f"{summary['target_machine']}. This is a WARNING and nothing is "
        "aborted -- but the dominant stage is "
        f"{summary['dominant_stage']} at {summary['dominant_stage_hours']} h, "
        "which is where hours are found if they must be."
    )
else:
    print(
        f"D-38: the {mode} wall-clock estimate is {low}-{high} h, within the "
        f"{remaining} h you declared remaining."
    )
PY
  return 0
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
  # `invocation` exists so the ORDER of the two invocations is observable from
  # outside: the dry-run seam reads it, which is what lets the driver's tests
  # assert this stage's atomicity (--check strictly before --force, both inside
  # one start/complete window) under the CONCURRENT scheduler rather than only
  # under the serial one. It changes neither invocation.
  local invocation="--check"
  log "e3: --check FIRST (tier-by-tier snapshot of the pre-regeneration state)"
  if _dry_run_active; then
    _dry_run_stub
  else
    # `--baseline-dir` (D-12) only goes on `--check`: e3's parser rejects it
    # with `--force`, because it names the directory --check reads baselines
    # FROM and --force writes new ones. Without it the "control" is the tree
    # this very stage is about to overwrite.
    python -u -m experiments.e3_derived_quantities \
      --check --baseline-dir "${BASELINE_DIR}" --out "${OUT_DIR}"
  fi
  log "e3: --check exit=$?"
  invocation="--force"
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

run_stage_fd_jacobian() {
  # ORPHAN SCRIPT #3 (M6). Never invoked by any driver, which is why its
  # artifacts were absent from the committed tree while the manuscript's
  # Jacobian-accuracy statement rested on them.
  #
  # No external input, so it depends on nothing but pre-flight, and it takes
  # seconds. Placed early on purpose: it exercises the queue's whole plumbing
  # -- state file, dispatch, gate invocation -- at negligible cost, which is
  # exactly what D-37's shortest-first ordering is for.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.fd_jacobian_accuracy --out "${OUT_DIR}" --force
}

run_stage_e1() {
  # Single-seed production run. E1's production SCENARIO_NAME is "realistic".
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"
}

run_stage_e1_band() {
  # E1's NOISE-AXIS BAND (M7). The seventh invocation no driver has ever run,
  # and the reason E1's noise axis exists only in planning documents.
  #
  # RULING A1: a UNIFORM grid, and NO NEW E1 FLAG IS NEEDED OR WANTED.
  # `_run_band` is already a strict cartesian product of the requested seeds
  # with NOISE_LEVELS (`e1_refractive_comparison.py:217`, already
  # [0.25, 0.5, 0.82, 1.2]), so `--seeds` alone produces the whole grid. It
  # cannot express a RAGGED grid, and two invocations would overwrite each
  # other rather than compose -- the band writers force.
  #
  # THE ARITHMETIC, so a future reader can check the row counts rather than
  # trust them: 4 seeds x 4 noise levels x 16 rows per cell = 256 rows of
  # exp1_band.csv, and x 24 rows per cell = 384 rows of
  # exp1_parameter_band.csv. (At ten seeds with no noise axis the committed
  # files were 160 and 240 rows, which is what pins 16 and 24 per cell.)
  #
  # FOUR seeds and not ten: ten seeds x four levels was sized at about 7 h in
  # Phase 25; the uniform 4-seed grid is 16 of those 40 cells, about 2.8 h.
  # 0.5 px IS one of the four levels, and that matters: the headline 97-178x
  # ratio band and all sixteen ledger numbers backed by exp1_band.csv live at
  # 0.5 px. A grid that dropped it would regenerate everything except the
  # numbers actually cited.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e1_refractive_comparison \
    --seeds "${E1_BAND_SEEDS}" --out "${OUT_DIR}"
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

run_stage_e7_focal_standoff() {
  # ORPHAN SCRIPT #1 (M4). Never invoked by any driver.
  #
  # ORDERING CONSTRAINT O1, AND IT IS NOT A PREFERENCE. This script reads the
  # HARDCODED, cwd-relative path
  # `Path("experiments/results") / "interface_ablation_band.csv"`
  # (`e7_focal_standoff_analysis.py:389`). Its own docstring says that is
  # deliberate -- "never the --out directory". So `e7_band` must have landed
  # first, and the `cd "${REPO_ROOT}"` at the top of this file is what makes
  # the path resolve at all. Reordering this stage above e7_band produces a
  # missing-file error, not a wrong number, which is the friendlier of the two
  # failure modes but still a wasted stage.
  #
  # It ignores --smoke entirely, which is why its artifact is expected under
  # the `full` profile only.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e7_focal_standoff_analysis --out "${OUT_DIR}"
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
  #
  # THE DRY-RUN CHECK COMES FIRST, BEFORE THE `rm`s, AND THAT ORDER IS A FIX.
  # rerun_19_3.sh ran the cleanup unconditionally and only then consulted the
  # dry-run seam, so a control-flow rehearsal DELETED committed artifacts under
  # experiments/results (a tracked directory). rerun_19_4.sh corrected it; the
  # correction is preserved here rather than the 19.3 shape.
  if _dry_run_active; then
    log "e6_repeat1: DRY RUN -- skipping the destructive pre-run cleanup of ${OUT_DIR}"
    _dry_run_stub
    return $?
  fi
  log "e6_repeat1: clearing any partial E6 state under ${OUT_DIR} before running"
  rm -rf "${OUT_DIR}/e6_configs"
  rm -f "${OUT_DIR}/generalization_sweep.csv" "${OUT_DIR}/e6_provenance.json"
  python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"
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
  #
  # The axis selection below (D-40, plan 26-05) DROPS THE SCALE AXIS,
  # cutting the band from 17 configurations to 14 and giving 14 x 6 = 84 rows.
  # The scale axis appears in ZERO rows of the manuscript's numbers. This is
  # the suite's dominant stage at ~8.9 h and its critical path under any
  # scheduling, so the cut is where the hours actually are.
  #
  # `--include-per-camera-latex` STAYS OFF (D-11) -- see run_stage_e6_repeat1.
  python -u -m experiments.e6_generalization_sweep \
    --seeds "${E6_BAND_SEEDS}" --axes index,layout,cameras \
    --out "${OUT_DIR}" --force
}

run_stage_e4() {
  # ORDERING CONSTRAINT O4, AND THIS ONE IS A SILENT WRONG NUMBER, NOT A CRASH.
  # `resolve_e2_benchmark_path` (`e4_benchmark_grid.py:298`) looks for E2's
  # `benchmark.json`; when it is absent, E4 quietly DROPS the real-rig row and
  # `benchmark_grid.csv` comes back with 9 rows instead of 10. Nothing fails,
  # nothing warns loudly, and the missing row is the only one tying the
  # synthetic grid to the real rig. `e4` therefore depends on `e2_production`
  # -- an edge in suite_expectations.json, not a comment, because a concurrency
  # pool can honour a dependency and cannot honour a comment.
  #
  # `serial_alone` (D-52): E4 is a 200-frame-class stage whose runtime is
  # itself the reported quantity.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"
}

_emit_e2_invocation_configs() {
  # Generate the three E2 invocation configs from the release config. Shared by
  # the production, timing and memory stages so a resume that starts at
  # e2_timing regenerates them rather than depending on a directory an earlier
  # stage happened to leave behind.
  #
  # The generator REFUSES to write into or under the release config's own
  # parent directory (T-26-17), so the target is always in-repo.
  log "e2: emitting invocation configs from ${E2_RELEASE_CONFIG} into ${E2_INVOCATION_DIR}"
  python -u -m experiments.e2_real_rig \
    --emit-invocation-configs \
    --config "${E2_RELEASE_CONFIG}" \
    --invocation-dir "${E2_INVOCATION_DIR}"
}

run_stage_e2_production() {
  # E2's PRODUCTION / CLASSIFICATION RUN (M1). Absent from every existing
  # driver, and it is the run the largest number of downstream things need:
  # `benchmark.json` (which e4 silently drops a row without),
  # `real_rig_metrics.json` and `reconstruction_errors.csv` (which
  # reconstruction_bootstrap reads by hardcoded path), plus the classification
  # sidecars.
  #
  # It carries `internals.log_all_observation_depths: true`, which is a YAML
  # key and NOT a CLI flag (D-16) -- that is the whole reason this invocation
  # needs a generated config rather than an extra argument.
  if _dry_run_active; then
    log "e2_production: DRY RUN"
    _dry_run_stub
    return $?
  fi
  _emit_e2_invocation_configs
  local emit_exit=$?
  log "e2_production: emit-invocation-configs exit=${emit_exit}"
  if [ "${emit_exit}" -ne 0 ]; then
    return "${emit_exit}"
  fi
  python -u -m experiments.e2_real_rig \
    --config "${E2_PRODUCTION_CONFIG}" --out "${OUT_DIR}" --force
}

run_stage_e2_timing() {
  # E2's TIMING RUN (M2). `internals.benchmark_memory: false`, and it carries
  # NEITHER of the two instrumentation keys -- that is D-15, and it is
  # non-negotiable: memory instrumentation costs 2.7-5.5% wall clock, so a run
  # that reports both a timing and a peak-RSS number reports a timing that was
  # inflated by the measurement of the other.
  #
  # `serial_alone` (D-52 / review H4): it produces a TIMING number, so nothing
  # may share the box with it. This file only DECLARES the constraint (the
  # manifest carries `concurrency: serial_alone`); plan 26-08's pool enforces
  # it.
  #
  # Its own out dir, so its benchmark.json is attributable to it.
  if _dry_run_active; then
    log "e2_timing: DRY RUN"
    _dry_run_stub
    return $?
  fi
  _emit_e2_invocation_configs
  local emit_exit=$?
  if [ "${emit_exit}" -ne 0 ]; then
    return "${emit_exit}"
  fi
  mkdir -p "${OUT_DIR_E2_TIMING}"
  python -u -m experiments.e2_real_rig \
    --config "${E2_TIMING_CONFIG}" --out "${OUT_DIR_E2_TIMING}" --force
}

run_stage_e2_memory() {
  # E2's MEMORY RUN (M3). `internals.benchmark_memory: true`. Distinct from the
  # timing run by D-15 -- see run_stage_e2_timing. Also `serial_alone`: a
  # peak-RSS number measured while another calibration held 3.5 GiB is a
  # measurement of the queue, not of the algorithm.
  if _dry_run_active; then
    log "e2_memory: DRY RUN"
    _dry_run_stub
    return $?
  fi
  _emit_e2_invocation_configs
  local emit_exit=$?
  if [ "${emit_exit}" -ne 0 ]; then
    return "${emit_exit}"
  fi
  mkdir -p "${OUT_DIR_E2_MEMORY}"
  python -u -m experiments.e2_real_rig \
    --config "${E2_MEMORY_CONFIG}" --out "${OUT_DIR_E2_MEMORY}" --force
}

run_stage_reconstruction_bootstrap() {
  # ORPHAN SCRIPT #2 (M5). Never invoked by any driver.
  #
  # ORDERING CONSTRAINT O2: it reads
  # `experiments/results/reconstruction_errors.csv` and the hardcoded
  # `REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")`
  # (`reconstruction_bootstrap.py:56`), both written by e2_production. The
  # dependency is an edge in the manifest, not just this comment.
  if _dry_run_active; then
    _dry_run_stub
    return $?
  fi
  python -u -m experiments.reconstruction_bootstrap --out "${OUT_DIR}" --force
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
  # Mirrors the manifest's per-stage `out_dir`. Keep the two in step: a gate
  # pointed at the wrong directory reports PASS against artifacts a different
  # stage produced.
  case "$1" in
    e4_repeat) printf '%s\n' "${OUT_DIR_E4_REPEAT}" ;;
    e2_band) printf '%s\n' "${OUT_DIR_E2_BAND}" ;;
    e2_timing) printf '%s\n' "${OUT_DIR_E2_TIMING}" ;;
    e2_memory) printf '%s\n' "${OUT_DIR_E2_MEMORY}" ;;
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

  # D-03 HARD ABORT, and ONLY here. `preflight` and `prelaunch_probe` are the
  # two pre-flight stages: both run before any long stage, so a refusal costs
  # minutes and nothing is lost. Every stage after them obeys D-01 -- a failure
  # is a finding that makes the FINAL exit non-zero and never stops the queue.
  # Nothing may abort once a real stage has begun (D-50).
  case "${name}" in
    preflight|prelaunch_probe)
      if [ "${exit_code}" -ne 0 ]; then
        log "FATAL: pre-flight stage ${name} FAILed (exit=${exit_code}) -- ABORTING THE QUEUE before any production stage runs. See the output above. Do NOT resume past this point: fix the cause and restart from stage 1."
        # D-50: a refusal that cannot be bypassed is a check that can cost a
        # night. The specific refusal above names its own flag; this restates
        # the full set so an operator at 3 a.m. does not have to find them.
        log "FATAL: OVERRIDE FLAGS, one per refusal -- --skip-e2 (frameset absent, DECLARES a synthetic-only run), --allow-frameset-mismatch (frameset identity), --allow-nonempty-out (non-empty output tree with no state file for this sha), --allow-low-disk (free space below the crude floor), --allow-gate-precheck-failure (the completeness gate could not be invoked). Run with --help for the full list."
        if [ "${name}" = "prelaunch_probe" ]; then
          log "FATAL: the seed list itself is illegal at at least one (seed, n_cameras, draw). Fix the seed lists at the top of this file -- resuming would spend hours computing something that cannot be reported. There is deliberately NO override for this one: an illegal seed makes the band unreportable, not merely suspect."
        fi
        exit "${exit_code}"
      fi
      return 0
      ;;
  esac

  # D-01, AND THIS IS THE WHOLE OF IT: the STAGE's own failure is sticky.
  if [ "${exit_code}" -ne 0 ]; then
    record_failure "STAGE FAILED: ${name} (stage ${idx}) exited ${exit_code}. Its artifacts are missing or partial; see ${STAGE_LOG_DIR}/${name}.log."
  fi

  run_gate_check "$(_gate_dir_for_stage "${name}")" "${name}"
  # D-01 is a change to run_gate_check's CALLER, not to run_gate_check: that
  # function still always returns 0, so a gate FAIL can never abort the queue.
  # The verdict is read from LAST_GATE_EXIT and carried to the FINAL exit code.
  if [ "${LAST_GATE_EXIT}" -ne 0 ]; then
    record_failure "GATE FAIL: ${name} (stage ${idx}) -- check_rerun_gates.py reported at least one FAIL against $(_gate_dir_for_stage "${name}") at profile '${PROFILE}'. The queue continued (D-01); the final exit code is non-zero."
  fi
  return 0
}

# =============================================================================
# THE SCHEDULER (D-52).
# =============================================================================

declare -A STAGE_DEPS=()
declare -A STAGE_CONCURRENCY=()
declare -A STAGE_FRAME_CLASS=()
declare -A STAGE_EST_HOURS=()
declare -A STAGE_INDEX=()

_load_stage_attributes() {
  # Read `depends_on`, `concurrency`, `frame_class` and `est_hours` FROM THE
  # MANIFEST. Bash cannot parse JSON reliably, so a one-shot Python call emits
  # a TSV and this reads that. The scheduler therefore hardcodes NO stage list
  # and NO stage name: adding a stage to the manifest is enough for the pool to
  # honour its constraints, which is the difference between a dependency a pool
  # can enforce and a comment it cannot.
  local line name deps conc frame est
  while IFS=$'\t' read -r name deps conc frame est; do
    [ -n "${name}" ] || continue
    STAGE_DEPS["${name}"]="${deps}"
    STAGE_CONCURRENCY["${name}"]="${conc}"
    STAGE_FRAME_CLASS["${name}"]="${frame}"
    STAGE_EST_HOURS["${name}"]="${est}"
  done < <("${GATE_PYTHON}" - <<'PY'
import json
import pathlib

manifest = json.loads(
    pathlib.Path("experiments/suite_expectations.json").read_text(encoding="utf-8")
)
for stage in manifest["stages"]:
    est = stage["est_hours"]["value"]
    # A range sorts on its LOW bound: shortest-first (D-37) is about surfacing
    # a systematic failure early, and the low bound is the optimistic case that
    # ordering is trying to exploit.
    low = est[0] if isinstance(est, list) else est
    print(
        "\t".join(
            [
                stage["id"],
                ",".join(stage["depends_on"]),
                stage["concurrency"],
                str(stage["frame_class"]),
                f"{float(low):012.5f}",
            ]
        )
    )
PY
  )

  local i=1
  for name in "${STAGES[@]}"; do
    STAGE_INDEX["${name}"]="${i}"
    i=$((i + 1))
    if [ -z "${STAGE_CONCURRENCY[${name}]:-}" ]; then
      log "FATAL: stage '${name}' has no entry in experiments/suite_expectations.json, so the scheduler cannot know whether it may run concurrently. Add it there."
      exit 1
    fi
  done
}

_stage_worker() {
  # One concurrent stage, in its own process.
  #
  # `tee` writes the per-stage log AND keeps the console stream, so the
  # detached run's single log still holds everything; the per-stage file is
  # what makes four interleaved stages readable afterwards. PIPESTATUS[0] is
  # mandatory: `tee` eats the real exit code, and losing it here would lose the
  # stage failure that D-01 exists to carry to the final exit.
  local name="$1" idx="$2" done_file="$3" stage_log="$4"
  run_one_stage "${name}" "${idx}" 2>&1 | tee -a "${stage_log}"
  local exit_code="${PIPESTATUS[0]}"
  # The sentinel is written LAST and is how the parent detects completion. A
  # sentinel file rather than `wait -n`: `wait -n -p` needs bash >= 5.1, and
  # this driver must behave identically on the Git Bash planning box and the
  # Linux run machine (D-35).
  printf '%s\n' "${exit_code}" >"${done_file}"
  return "${exit_code}"
}

_run_serial() {
  # The fully serial path -- `SUITE_SERIAL=1`, and the escape hatch if the pool
  # is ever suspected of touching a result. Identical semantics to every
  # historical driver.
  local name
  for name in "$@"; do
    run_one_stage "${name}" "${STAGE_INDEX[${name}]}"
  done
}

_run_pool() {
  # D-52's pool. Admission is decided ENTIRELY from the manifest's per-stage
  # attributes:
  #
  #   * every `depends_on` must be done -- this is what keeps `e6_band` from
  #     ever overlapping `e6_repeat1`, whose `rm -rf` under the shared OUT_DIR
  #     would delete the band's own tree out from under it;
  #   * a `serial_alone` stage runs with nothing else in flight, and nothing
  #     starts while it runs (timing integrity: e4, e4_repeat, e2_timing,
  #     e2_memory);
  #   * at most one `frame_class == 200` stage in flight (9.3-11.3 GiB each);
  #   * at most SUITE_WORKERS in flight;
  #   * ties broken SHORTEST-FIRST within the ready set (D-37).
  local -a pending=("$@")
  local -A status=()
  local -A pid_of=()
  local -A done_file_of=()
  local name dep ready_ok launched running_count serial_running frame200_running

  for name in "${STAGES[@]}"; do
    status["${name}"]="done"
  done
  for name in "${pending[@]}"; do
    status["${name}"]="pending"
  done

  while true; do
    # --- reap ---------------------------------------------------------------
    for name in "${pending[@]}"; do
      if [ "${status[${name}]}" = "running" ] && [ -f "${done_file_of[${name}]}" ]; then
        wait "${pid_of[${name}]}" 2>/dev/null
        status["${name}"]="done"
        log "<<< POOL: ${name} finished (exit=$(cat "${done_file_of[${name}]}" 2>/dev/null || echo '?'))"
      fi
    done

    # --- census -------------------------------------------------------------
    running_count=0
    serial_running=0
    frame200_running=0
    for name in "${pending[@]}"; do
      if [ "${status[${name}]}" = "running" ]; then
        running_count=$((running_count + 1))
        [ "${STAGE_CONCURRENCY[${name}]}" = "serial_alone" ] && serial_running=1
        [ "${STAGE_FRAME_CLASS[${name}]}" = "200" ] && frame200_running=1
      fi
    done

    # --- done? --------------------------------------------------------------
    local remaining=0
    for name in "${pending[@]}"; do
      [ "${status[${name}]}" != "done" ] && remaining=$((remaining + 1))
    done
    if [ "${remaining}" -eq 0 ]; then
      break
    fi

    # --- launch -------------------------------------------------------------
    launched=0
    if [ "${serial_running}" -eq 0 ]; then
      # `pending` is already in the driver's shortest-first topological order,
      # so a single forward scan IS the shortest-first ready set.
      for name in "${pending[@]}"; do
        [ "${status[${name}]}" = "pending" ] || continue
        [ "${running_count}" -lt "${SUITE_WORKERS}" ] || break

        ready_ok=1
        for dep in ${STAGE_DEPS[${name}]//,/ }; do
          if [ -n "${status[${dep}]:-}" ] && [ "${status[${dep}]}" != "done" ]; then
            ready_ok=0
            break
          fi
        done
        [ "${ready_ok}" -eq 1 ] || continue

        if [ "${STAGE_CONCURRENCY[${name}]}" = "serial_alone" ]; then
          # Runs alone AND blocks every later launch until it is done.
          [ "${running_count}" -eq 0 ] || continue
        fi
        if [ "${STAGE_FRAME_CLASS[${name}]}" = "200" ] && [ "${frame200_running}" -eq 1 ]; then
          continue
        fi

        done_file_of["${name}"]="${STAGE_DONE_DIR}/${name}.done"
        rm -f "${done_file_of[${name}]}"
        log ">>> POOL: launching ${name} (concurrency=${STAGE_CONCURRENCY[${name}]}, frame_class=${STAGE_FRAME_CLASS[${name}]}, est=${STAGE_EST_HOURS[${name}]} h, in flight $((running_count + 1))/${SUITE_WORKERS})"
        _stage_worker "${name}" "${STAGE_INDEX[${name}]}" "${done_file_of[${name}]}" "${STAGE_LOG_DIR}/${name}.log" &
        pid_of["${name}"]=$!
        status["${name}"]="running"
        running_count=$((running_count + 1))
        launched=1
        [ "${STAGE_CONCURRENCY[${name}]}" = "serial_alone" ] && break
        [ "${STAGE_FRAME_CLASS[${name}]}" = "200" ] && frame200_running=1
      done
    fi

    if [ "${launched}" -eq 0 ] && [ "${running_count}" -eq 0 ]; then
      log "FATAL: the scheduler is deadlocked -- stages remain but none is runnable. This means a depends_on cycle in experiments/suite_expectations.json."
      record_failure "SCHEDULER DEADLOCK: stages remain but none is runnable; suspect a depends_on cycle in the manifest."
      break
    fi
    [ "${launched}" -eq 0 ] && sleep 0.1
  done
}

_run_rollup() {
  # D-02's THIRD CHECK POINT, and the one whose ABSENCE produced F-001: a run
  # that exited 0 and looked green while a band CSV was never produced at all.
  # It runs over the WHOLE tree with no --stage selector, so it judges what is
  # MISSING rather than what it happens to find.
  #
  # This is deliberately NOT Gate 3's job. `_check_git_sha_consistency`
  # (`check_rerun_gates.py:1749-1754`) returns PASS over an EMPTY tree -- "no
  # git_sha values found across any artifact to compare" is a PASS -- so a
  # cross-artifact consistency gate succeeds precisely when there is nothing to
  # be consistent about. Do NOT weaken Gate 3 to cover this class; the roll-up
  # is the right owner.
  echo "============================================================"
  echo "END-OF-RUN COMPLETENESS ROLL-UP (D-02, profile=${PROFILE})"
  echo "============================================================"
  if _dry_run_active; then
    local stage_name="rollup"
    log "rollup: DRY RUN"
    _dry_run_stub
    local stub_exit=$?
    if [ "${stub_exit}" -ne 0 ]; then
      record_failure "ROLL-UP FAIL (dry run stub): the end-of-run roll-up reported a failure."
    fi
    return 0
  fi
  "${GATE_PYTHON}" experiments/check_rerun_gates.py "${OUT_DIR}" --profile "${PROFILE}"
  local rollup_exit=$?
  echo "============================================================"
  if [ "${rollup_exit}" -ne 0 ]; then
    record_failure "ROLL-UP FAIL: the end-of-run completeness roll-up over ${OUT_DIR} at profile '${PROFILE}' reported at least one FAIL. Read the verdict block above: every 'NOT FOUND' line names an artifact this run was expected to produce and did not."
  fi
  return 0
}

_announce_declared_reductions() {
  # D-14. Printed at LAUNCH and again in the terminal summary, because "loud"
  # alone is a log line and nobody reads the log overnight. A silent skip must
  # be impossible.
  [ "${SKIP_E2}" -eq 1 ] || return 0
  echo "############################################################"
  echo "# DECLARED REDUCTION: --skip-e2"
  echo "#   The E2 frameset is declared ABSENT. This run is"
  echo "#   SYNTHETIC-ONLY: E2's production, timing, memory and band"
  echo "#   stages cannot produce their artifacts, and E4 silently"
  echo "#   drops its real-rig row without E2's benchmark.json."
  echo "#   The completeness gate still expects those artifacts, so"
  echo "#   this run's final exit code will be NON-ZERO by design."
  echo "############################################################"
}

_print_terminal_summary() {
  # D-01's LOUD SUMMARY. Every missing or short artifact, every failed stage,
  # every gate FAIL, in one block at the end -- the thing an operator reads
  # first at 7 a.m.
  _announce_declared_reductions
  if [ -s "${SUITE_FAILURE_LOG}" ]; then
    SUITE_FAILED=1
    echo "############################################################"
    echo "# SUITE FAILED. $(wc -l <"${SUITE_FAILURE_LOG}" | tr -d ' ') finding(s):"
    echo "############################################################"
    local line
    while IFS= read -r line; do
      echo "#   ${line}"
    done <"${SUITE_FAILURE_LOG}"
    echo "############################################################"
    echo "# The queue ran to completion regardless (D-01): every stage's"
    echo "# measurements are still wanted. The non-zero exit code is what"
    echo "# makes this impossible to mistake for a green run -- F-001 was"
    echo "# a run that EXITED 0 while a band CSV was never produced."
    echo "# Full record: ${STATE_FILE}"
    echo "# Findings:    ${SUITE_FAILURE_LOG}"
    echo "# Stage logs:  ${STAGE_LOG_DIR}/"
    echo "############################################################"
  else
    echo "############################################################"
    echo "# SUITE COMPLETE. No stage failure, no gate FAIL, and the"
    echo "# end-of-run roll-up found every expected artifact at"
    echo "# profile '${PROFILE}'."
    echo "############################################################"
  fi
}

main() {
  log "AquaCal experiment suite driver starting. Frozen sha: ${FROZEN_SHA} (HEAD $(git rev-parse HEAD 2>/dev/null || echo unknown))"
  log "Stage order (D-37, shortest-first subject to depends_on): ${STAGES[*]}"
  log "State file: ${STATE_FILE}"
  log "Resuming from stage index ${START_STAGE} (stages already marked complete are skipped regardless)."
  log "Profile: ${PROFILE}. Concurrency: $([ -n "${SUITE_SERIAL:-}" ] && echo "SERIAL (SUITE_SERIAL is set)" || echo "pooled, ${SUITE_WORKERS} wide (D-52)")."
  _announce_declared_reductions

  mkdir -p "${STAGE_LOG_DIR}" "${STAGE_DONE_DIR}"
  rm -f "${STAGE_DONE_DIR}"/*.done
  : >"${SUITE_FAILURE_LOG}"

  _load_stage_attributes

  # THE TWO PRE-FLIGHT STAGES RUN IN THE PARENT, SERIALLY, AND BEFORE THE POOL
  # EXISTS. They are the only stages permitted to abort (D-03), and an `exit`
  # from a pooled child would abort the child and leave the parent scheduling
  # happily on. Everything else depends on them transitively anyway.
  local name idx
  local -a queued=()
  for name in "${STAGES[@]}"; do
    case "${name}" in
      preflight|prelaunch_probe) run_one_stage "${name}" "${STAGE_INDEX[${name}]}" ;;
      *) queued+=("${name}") ;;
    esac
  done

  if [ -n "${SUITE_SERIAL:-}" ]; then
    _run_serial "${queued[@]}"
  else
    _run_pool "${queued[@]}"
  fi

  _run_rollup
  _print_terminal_summary

  log "Suite driver finished all ${#STAGES[@]} stages. See ${STATE_FILE} for the full stage-completion record."
  exit "${SUITE_FAILED}"
}

main "$@"
