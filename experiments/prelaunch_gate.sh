#!/usr/bin/env bash
#
# Phase 19.3 plan 09 Task 1 -- the scripted pre-launch abort gate for the ~9 h
# overnight re-run (`experiments/rerun_19_3.sh`). Extended by phase 19.5 plan
# 09 Task 1 with a sixth check, LEGALITY_PROBE (D-19.5-04), and by quick task
# 260813-clj with a seventh, ENV_VERSION_MATCH.
#
# THIS IS AN ABORT GATE, NOT A HUMAN-VERIFY GATE. Every one of the seven checks
# below is a file-existence test or a command exit code, so a script can
# actually run them and a sleeping human cannot. Per this project's gate
# taxonomy, a precondition verifiable by a command exit code is scripted and
# aborts on failure; it does not wait for a typed approval.
#
# Contract: exit 0 => the queue may launch. ANY non-zero exit => the caller
# MUST abort and MUST NOT launch the queue. Each check emits its own
# self-naming `PASS <NAME>` / `FAIL <NAME>` line so the abort message
# identifies which check failed.
#
# The seven checks:
#   1. TREE_CLEAN        -- `git status --porcelain` is empty.
#   2. ENV_VERSION_MATCH -- the INSTALLED aquacal distribution metadata matches
#                           `pyproject.toml`'s declared version. An editable
#                           install writes its metadata once and never refreshes
#                           it, so after a version bump the code that runs is
#                           the working tree while `capture_environment()`
#                           stamps the stale installed version onto every
#                           artifact. Another seconds-long structural check, so
#                           it sits beside LEGALITY_PROBE and ahead of
#                           SUITE_GREEN for the same reason -- and ahead of the
#                           probe itself, which imports the library this check
#                           is about.
#   3. LEGALITY_PROBE     -- D-19.5-04: `legality_probe` PASSes at every
#                           (seed, n_cameras, draw) the queue intends to run.
#                           A structural check, no calibration solve, seconds
#                           not minutes -- placed BEFORE the expensive
#                           SUITE_GREEN check so an illegal seed is caught in
#                           seconds, not after an hour of pytest.
#   4. SUITE_GREEN       -- the FULL, UNFILTERED test suite exits 0.
#   5. HEAD_RECORDED     -- HEAD's sha is captured, echoed, and written to disk.
#   6. ARCHIVES_PRESENT  -- the pre-fix archive set exists, read from a
#                           plan's SUMMARY rather than hardcoded, plus E3.
#   7. WORKTREES_CLEAN   -- no stray executor worktrees; the superseded 19.2-21
#                           evidence branch is absent or present-and-UNMERGED.
#
# WHY CHECK 4 CANNOT BE FILTERED: `-m "not slow"` deselects exactly the
# bit-identity, frozen-anchor and inertness suites that are this phase's
# evidence. A filtered run is not a valid gate. This script therefore accepts
# NO marker selector from the environment or from an argument, and fails if
# pytest reports any marker-caused deselection. This is the same rewrite that
# Phase 19.2's plan 06 launch gate needed.
#
# WHY THE PYTEST INTERPRETER IS PINNED: Git Bash's `python` on this box is
# Anaconda base, not the AquaCal env -- collection errors there are an
# interpreter problem, not a test failure.
#
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || { echo "FATAL: cannot cd to repo root"; exit 1; }

PYTHON_BIN="${PRELAUNCH_GATE_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
SHA_FILE="experiments/rerun_19_5_frozen_sha.txt"
# Phase 19.5's archiving plan (if any). Phase 19.5 makes NO non-inert `src/`
# change (D-19.5-03) and therefore archived NOTHING -- there is no
# `experiments/archive/eN-*-pre-interface-fix` set this phase, unlike 19.4.
#
# RESOLVED 2026-08-06 (was: "this check is EXPECTED to FAIL, treat it as
# benign"). A gate everyone knows to ignore is worse than no gate -- it is how
# a real failure gets waved through six months later. ARCHIVES_PRESENT now
# returns a third verdict, N/A, when it can PROVE its premise does not apply:
# the SUMMARY declares the absence AND no commit naming this phase touched
# src/. A phase that did move src/ and is missing its archives still FAILs.
# So "FAIL means stop" stays literally true and needs no asterisk.
PLAN03_SUMMARY=".planning/phases/19.5-experiment-coverage-and-uncertainty-bands/19.5-09-SUMMARY.md"
SUPERSEDED_BRANCH="worktree-agent-a1a99b5a5289e9e05"

FAILURES=()

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1 -- $2"; FAILURES+=("$1"); }
# N/A is a THIRD verdict, not a soft failure: the check ran, its premise did
# not apply, and it therefore says nothing either way. It must not enter
# FAILURES -- but it must also never be reachable just because a check could
# not find what it was looking for, or it becomes a way to launder a real
# FAIL. Every na() call site must prove the premise is inapplicable.
# check_rerun_gates.py already uses this vocabulary (`[N/A ]` verdicts).
na() { echo "N/A  $1 -- $2"; }

echo "=============================================================="
echo " Phase 19.5 pre-launch freeze gate"
echo " repo root: $REPO_ROOT"
echo " started:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================================="
echo

# ---------------------------------------------------------------------------
# 1. TREE_CLEAN
# ---------------------------------------------------------------------------
echo "--- 1. TREE_CLEAN -------------------------------------------"
DIRTY="$(git status --porcelain)"
if [ -z "$DIRTY" ]; then
  pass TREE_CLEAN
else
  echo "$DIRTY"
  fail TREE_CLEAN "git status --porcelain produced output; the tree must be clean so every artifact carries one sha"
fi
echo

# ---------------------------------------------------------------------------
# 2. ENV_VERSION_MATCH -- the installed distribution metadata must agree with
#    the version declared in pyproject.toml.
#
#    `aquacal.__version__` and `capture_environment()`'s `aquacal_version`
#    field both resolve through `importlib.metadata.version("aquacal")`, i.e.
#    INSTALLED distribution metadata. Under an editable install that metadata
#    is written once at `pip install -e .` time and is never refreshed by
#    editing pyproject.toml, while the `.pth` resolves imports to the working
#    tree. So after a version bump the two diverge silently and every artifact
#    produced in between records the wrong producing version -- a confident,
#    plausible, wrong provenance record that does not fail loudly.
#
#    Seconds-long and structural, so it runs before SUITE_GREEN for the same
#    reason LEGALITY_PROBE does, and before LEGALITY_PROBE because that check
#    imports the very library whose install this one is validating.
# ---------------------------------------------------------------------------
echo "--- 2. ENV_VERSION_MATCH ------------------------------------"
if [ ! -x "$PYTHON_BIN" ] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail ENV_VERSION_MATCH "interpreter not found at $PYTHON_BIN (Git Bash 'python' is Anaconda base, not the AquaCal env)"
else
  # Both versions are read under $PYTHON_BIN. pyproject.toml is parsed with
  # tomllib (stdlib on this project's >=3.11 floor) rather than grepped: a grep
  # for `version` would happily match the key of some other table.
  ENV_VERSION_LOG="$(mktemp)"
  PYPROJECT_PATH="$REPO_ROOT/pyproject.toml" "$PYTHON_BIN" - <<'PY' >"$ENV_VERSION_LOG" 2>&1
import os
import pathlib
import tomllib
from importlib.metadata import version as get_version

installed = get_version("aquacal")
declared = tomllib.loads(
    pathlib.Path(os.environ["PYPROJECT_PATH"]).read_text(encoding="utf-8")
)["project"]["version"]
print(f"installed (dist-info): {installed}")
print(f"declared (pyproject):  {declared}")
raise SystemExit(0 if installed == declared else 1)
PY
  ENV_VERSION_RC=$?
  cat "$ENV_VERSION_LOG"
  ENV_VERSION_DETAIL="$(tr '\n' ' ' < "$ENV_VERSION_LOG")"
  rm -f "$ENV_VERSION_LOG"
  if [ "$ENV_VERSION_RC" -eq 0 ]; then
    pass ENV_VERSION_MATCH
  else
    fail ENV_VERSION_MATCH "the installed aquacal version does not match pyproject.toml (${ENV_VERSION_DETAIL}) -- the working tree would be recorded under the stale installed version. Fix it now: run 'pip install -e . --no-deps' in the AquaCal env, then re-run this gate"
  fi
fi
echo

# ---------------------------------------------------------------------------
# 3. LEGALITY_PROBE (D-19.5-04) -- re-verify the 19.4 clearance-floor fix
#    EMPIRICALLY, at every seed and every n_cameras this queue intends to
#    run, BEFORE the expensive SUITE_GREEN check below. A structural check
#    over camera geometry only -- no calibration solve -- so an illegal seed
#    is caught in seconds, not after an hour of pytest (T-19.5-09-03).
# ---------------------------------------------------------------------------
echo "--- 3. LEGALITY_PROBE -----------------------------------------"
if [ ! -x "$PYTHON_BIN" ] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail LEGALITY_PROBE "interpreter not found at $PYTHON_BIN (Git Bash 'python' is Anaconda base, not the AquaCal env)"
else
  # Read the seed list from the driver rather than keeping a second copy here.
  # A duplicated hardcoded list is the one way this check can pass while the
  # queue runs a seed nobody probed -- exactly the failure the probe exists to
  # prevent. Union of E6's and E5's lists, since both are probed.
  #
  # Repointed from rerun_19_5.sh to run_experiment_suite.sh in plan 26-09, when
  # the two superseded drivers were archived (DRIVER-04 / ruling A3). The grep
  # is unchanged because the new driver declares the same two variables in the
  # same shape; what changed is that the seeds now come from the script that
  # will actually run, which is the whole point of not keeping a second copy.
  QUEUE_SH="$REPO_ROOT/experiments/run_experiment_suite.sh"
  PROBE_SEEDS="$(
    grep -E '^(E6|E5)_BAND_SEEDS=' "$QUEUE_SH" \
      | cut -d'"' -f2 | tr ',' '\n' | sort -n -u | paste -sd, -
  )"
  if [ -z "$PROBE_SEEDS" ]; then
    fail LEGALITY_PROBE "could not read E6/E5_BAND_SEEDS from $QUEUE_SH"
  fi
  echo "LEGALITY_PROBE: seeds read from run_experiment_suite.sh = ${PROBE_SEEDS}"
  LEGALITY_LOG="$(mktemp)"
  PROBE_SEEDS="$PROBE_SEEDS" "$PYTHON_BIN" - <<'PY' >"$LEGALITY_LOG" 2>&1
import os

from experiments.check_rerun_gates import legality_probe

seeds = [int(s) for s in os.environ["PROBE_SEEDS"].split(",") if s.strip()]
camera_counts = [8, 12, 16]
results = legality_probe(seeds, camera_counts)
n_fail = sum(1 for r in results if r.verdict == "FAIL")
for r in results:
    print(f"[{r.verdict:4s}] {r.gate} -- {r.detail}")
print()
print(f"TOTAL: {len(results)} checked, {n_fail} FAIL")
raise SystemExit(1 if n_fail else 0)
PY
  LEGALITY_RC=$?
  cat "$LEGALITY_LOG"
  rm -f "$LEGALITY_LOG"
  if [ "$LEGALITY_RC" -eq 0 ]; then
    pass LEGALITY_PROBE
  else
    fail LEGALITY_PROBE "one or more (seed, n_cameras, draw) combinations is illegal -- the queue's seed list is wrong; see output above"
  fi
fi
echo

# ---------------------------------------------------------------------------
# 4. SUITE_GREEN  (UNFILTERED -- no marker selector, ever)
# ---------------------------------------------------------------------------
echo "--- 4. SUITE_GREEN ------------------------------------------"
if [ ! -x "$PYTHON_BIN" ] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail SUITE_GREEN "interpreter not found at $PYTHON_BIN (Git Bash 'python' is Anaconda base, not the AquaCal env)"
else
  # No -m selector is passed, and none can be injected: the argument list here
  # is a literal. PYTEST_ADDOPTS is cleared so it cannot smuggle one in.
  echo "running: $PYTHON_BIN -m pytest tests/ -q   (UNFILTERED -- expect ~60-90 min)"
  PYTEST_LOG="$(mktemp)"
  env -u PYTEST_ADDOPTS "$PYTHON_BIN" -m pytest tests/ -q 2>&1 | tee "$PYTEST_LOG"
  PYTEST_RC="${PIPESTATUS[0]}"
  SUMMARY_LINE="$(grep -E '^[0-9]+ (passed|failed)|passed|failed|error' "$PYTEST_LOG" | tail -1)"
  if [ "$PYTEST_RC" -ne 0 ]; then
    fail SUITE_GREEN "unfiltered pytest exited $PYTEST_RC -- $SUMMARY_LINE"
  elif grep -qiE '[0-9]+ deselected' "$PYTEST_LOG"; then
    fail SUITE_GREEN "pytest reported marker-caused deselection; the gate suite must be UNFILTERED -- $SUMMARY_LINE"
  else
    echo "summary: $SUMMARY_LINE"
    pass SUITE_GREEN
  fi
  rm -f "$PYTEST_LOG"
fi
echo

# ---------------------------------------------------------------------------
# 5. HEAD_RECORDED
# ---------------------------------------------------------------------------
echo "--- 5. HEAD_RECORDED ----------------------------------------"
FROZEN_SHA="$(git rev-parse HEAD 2>/dev/null)"
if [ -z "$FROZEN_SHA" ]; then
  fail HEAD_RECORDED "git rev-parse HEAD produced nothing"
else
  printf '%s\n' "$FROZEN_SHA" > "$SHA_FILE"
  if [ -s "$SHA_FILE" ] && [ "$(cat "$SHA_FILE")" = "$FROZEN_SHA" ]; then
    echo "frozen sha: $FROZEN_SHA"
    echo "written to: $SHA_FILE"
    pass HEAD_RECORDED
  else
    fail HEAD_RECORDED "could not write the frozen sha to $SHA_FILE"
  fi
fi
echo

# ---------------------------------------------------------------------------
# 6. ARCHIVES_PRESENT
#
# The expected set is READ FROM THE ARCHIVING PLAN'S SUMMARY, not hardcoded --
# that plan is the authority on which experiments it archived, and hardcoding a
# count here would silently pass if it had covered a different set.
#
# PHASE 19.4: the expected set narrows to {e4, e6}. 19.3 archived six or seven
# experiments because its geometry fix moved nearly everything. This phase's fix
# moves only the grid family: E1, E3, E5 and E7 are PROVEN inert (none of them
# reaches generate_camera_array -- E1 and E7 run the "realistic" scenario, which
# resolves to generate_real_rig_array's frozen shared WATER_Z). Archiving an
# artifact that is about to be reproduced byte-for-byte records nothing, so
# D-19.4-10 was narrowed accordingly.
#
# 19.3's unconditional E3 special case is therefore REMOVED here, not repointed:
# E3 has no pre-interface-fix archive in this phase because E3 does not move.
# Its inertness is proven by byte-comparison in plan 10 instead.
# ---------------------------------------------------------------------------
echo "--- 6. ARCHIVES_PRESENT -------------------------------------"
if [ ! -f "$PLAN03_SUMMARY" ]; then
  fail ARCHIVES_PRESENT "plan 03 SUMMARY not found at $PLAN03_SUMMARY -- cannot derive the expected archive set"
else
  EXPECTED_DIRS="$(grep -oE 'experiments/archive/e[0-9]+-2026-08-04-pre-interface-fix' "$PLAN03_SUMMARY" \
                    | sort -u)"
  if [ -z "$EXPECTED_DIRS" ]; then
    # No archive set was declared. That is EITHER a phase that genuinely had
    # nothing to archive, OR a phase that archived something and forgot to
    # say so -- and those must not collapse to the same verdict. Distinguish
    # them with two independent conditions, BOTH required:
    #
    #   (a) the SUMMARY declares the absence in words, so a human asserted it;
    #   (b) no commit naming this phase touched src/, so the machine agrees.
    #
    # (b) is the one that cannot be talked around: archiving exists to
    # preserve a pre-fix baseline, so a phase that changed no src/ has no
    # baseline to preserve and the check's premise is genuinely absent. If
    # src/ DID move, a missing archive set is a real FAIL and stays one.
    PHASE_SRC_COMMITS="$(git log --oneline --grep='19\.5' -- src/ 2>/dev/null)"
    if grep -qiE 'archived nothing|archives? nothing' "$PLAN03_SUMMARY" \
       && [ -z "$PHASE_SRC_COMMITS" ]; then
      na ARCHIVES_PRESENT \
        "phase 19.5 declares it archived nothing (D-19.5-03 keeps src/ inert) and no commit naming 19.5 touched src/ -- nothing to archive, so this check's premise does not apply"
    else
      if [ -n "$PHASE_SRC_COMMITS" ]; then
        echo "  commits naming this phase that touched src/:"
        echo "$PHASE_SRC_COMMITS" | sed 's/^/    /'
      fi
      fail ARCHIVES_PRESENT "no archive directories could be parsed out of $PLAN03_SUMMARY (and the no-archive premise is not established: see above)"
    fi
  else
    echo "expected archive set, read from plan 03's SUMMARY:"
    MISSING=""
    COVERED=""
    while IFS= read -r D; do
      [ -z "$D" ] && continue
      EXPN="$(basename "$D" | cut -d- -f1)"
      if [ -d "$D" ]; then
        echo "  present: $D"
        COVERED="$COVERED $EXPN"
      else
        echo "  MISSING: $D"
        MISSING="$MISSING $EXPN"
      fi
    done <<< "$EXPECTED_DIRS"

    # 19.3's unconditional E3 archive check is deliberately absent -- see the
    # block comment above. E3 is inert under this phase's fix and is not
    # archived; proving that is plan 10's byte-comparison, not this gate's job.

    echo "archive set covers experiments:$COVERED"
    if [ -n "$MISSING" ]; then
      fail ARCHIVES_PRESENT "missing archive members for experiments:$MISSING"
    else
      pass ARCHIVES_PRESENT
    fi
  fi
fi
echo

# ---------------------------------------------------------------------------
# 7. WORKTREES_CLEAN
#
# The 19.2-21 branch is SUPERSEDED EVIDENCE ONLY and must never be merged.
# It is acceptable for it to exist; it is NOT acceptable for it to be merged
# into the current HEAD. Any OTHER stray executor worktree fails outright --
# this wave creates none, so one appearing means something else is running.
# ---------------------------------------------------------------------------
echo "--- 7. WORKTREES_CLEAN --------------------------------------"
git worktree list
STRAY=""
while IFS= read -r LINE; do
  WT_PATH="${LINE%% *}"
  case "$LINE" in
    *"[$SUPERSEDED_BRANCH]"*) continue ;;
  esac
  case "$LINE" in
    *"worktree-agent-"*) STRAY="$STRAY $WT_PATH" ;;
  esac
done < <(git worktree list)

WT_OK=true
if [ -n "$STRAY" ]; then
  fail WORKTREES_CLEAN "stray executor worktree(s) present:$STRAY"
  WT_OK=false
fi

if git show-ref --verify --quiet "refs/heads/$SUPERSEDED_BRANCH"; then
  if git merge-base --is-ancestor "$SUPERSEDED_BRANCH" HEAD 2>/dev/null; then
    fail WORKTREES_CLEAN "$SUPERSEDED_BRANCH is MERGED into HEAD -- it is superseded evidence and must never be merged"
    WT_OK=false
  else
    echo "$SUPERSEDED_BRANCH present and UNMERGED (correct -- evidence only)"
  fi
else
  echo "$SUPERSEDED_BRANCH absent (also acceptable)"
fi

[ "$WT_OK" = true ] && pass WORKTREES_CLEAN
echo

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
echo "=============================================================="
if [ "${#FAILURES[@]}" -gt 0 ]; then
  echo " GATE FAILED -- ABORT. Do NOT launch the queue."
  echo " failing check(s): ${FAILURES[*]}"
  echo "=============================================================="
  exit 1
fi

cat <<EOF
 GATE PASSED -- the queue may launch.

 Frozen sha: $FROZEN_SHA   (recorded in $SHA_FILE)

 THE TREE IS NOW FROZEN. From this moment until the queue finishes (~15-17 h
 with the 4-wide pool, ~28-31 h serial -- see experiments/EXPECTATIONS.md and
 experiments/run_experiment_suite.sh's own header):
   - NOTHING is committed, staged, tagged, checked out or pushed.
   - NO tests are run.
   - NO other work happens on this box -- one production calibration at a time.
 Every artifact produced tonight must carry the sha above. A commit landing
 mid-run splits one night's artifacts across two shas and breaks provenance.
==============================================================
EOF
exit 0
