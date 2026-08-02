#!/usr/bin/env bash
#
# Phase 19.3 plan 09 Task 1 -- the scripted pre-launch abort gate for the ~9 h
# overnight re-run (`experiments/rerun_19_3.sh`).
#
# THIS IS AN ABORT GATE, NOT A HUMAN-VERIFY GATE. Every one of the five checks
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
# The five checks:
#   1. TREE_CLEAN        -- `git status --porcelain` is empty.
#   2. SUITE_GREEN       -- the FULL, UNFILTERED test suite exits 0.
#   3. HEAD_RECORDED     -- HEAD's sha is captured, echoed, and written to disk.
#   4. ARCHIVES_PRESENT  -- the pre-fix archive set exists, read from plan 03's
#                           SUMMARY rather than hardcoded, plus E3.
#   5. WORKTREES_CLEAN   -- no stray executor worktrees; the superseded 19.2-21
#                           evidence branch is absent or present-and-UNMERGED.
#
# WHY CHECK 2 CANNOT BE FILTERED: `-m "not slow"` deselects exactly the
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
SHA_FILE="experiments/rerun_19_3_frozen_sha.txt"
PLAN03_SUMMARY=".planning/phases/19.3-scenario-geometry-and-convergence/19.3-03-SUMMARY.md"
SUPERSEDED_BRANCH="worktree-agent-a1a99b5a5289e9e05"

FAILURES=()

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1 -- $2"; FAILURES+=("$1"); }

echo "=============================================================="
echo " Phase 19.3 pre-launch freeze gate"
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
# 2. SUITE_GREEN  (UNFILTERED -- no marker selector, ever)
# ---------------------------------------------------------------------------
echo "--- 2. SUITE_GREEN ------------------------------------------"
if [ ! -x "$PYTHON_BIN" ] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail SUITE_GREEN "interpreter not found at $PYTHON_BIN (Git Bash 'python' is Anaconda base, not the AquaCal env)"
else
  # No -m selector is passed, and none can be injected: the argument list here
  # is a literal. PYTEST_ADDOPTS is cleared so it cannot smuggle one in.
  echo "running: $PYTHON_BIN -m pytest tests/ -q   (UNFILTERED -- expect ~24 min)"
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
# 3. HEAD_RECORDED
# ---------------------------------------------------------------------------
echo "--- 3. HEAD_RECORDED ----------------------------------------"
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
# 4. ARCHIVES_PRESENT
#
# The expected set is READ FROM PLAN 03'S SUMMARY, not hardcoded -- plan 03 is
# the authority on which experiments it archived, and hardcoding "five" here
# would silently pass if plan 03 had covered a different set. E3 is checked
# separately and unconditionally, because plan 03 did NOT archive it (E3 was
# added to scope after planning, Amendment A) and its tier-2 baseline is about
# to be overwritten.
# ---------------------------------------------------------------------------
echo "--- 4. ARCHIVES_PRESENT -------------------------------------"
if [ ! -f "$PLAN03_SUMMARY" ]; then
  fail ARCHIVES_PRESENT "plan 03 SUMMARY not found at $PLAN03_SUMMARY -- cannot derive the expected archive set"
else
  EXPECTED_DIRS="$(grep -oE 'experiments/archive/e[0-9]+-2026-08-02-pre-depth-fix' "$PLAN03_SUMMARY" \
                    | sort -u)"
  if [ -z "$EXPECTED_DIRS" ]; then
    fail ARCHIVES_PRESENT "no archive directories could be parsed out of $PLAN03_SUMMARY"
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

    # E3 -- not part of plan 03's set; checked unconditionally.
    E3_DIR="experiments/archive/e3-2026-08-02-pre-depth-fix"
    E3_OK=true
    for F in newton_iterations.csv code_constants.csv cpr_grouping.csv; do
      if [ -f "$E3_DIR/$F" ]; then
        echo "  present: $E3_DIR/$F"
      else
        echo "  MISSING: $E3_DIR/$F"
        E3_OK=false
      fi
    done
    if [ "$E3_OK" = true ]; then
      COVERED="$COVERED e3"
    else
      MISSING="$MISSING e3"
    fi

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
# 5. WORKTREES_CLEAN
#
# The 19.2-21 branch is SUPERSEDED EVIDENCE ONLY and must never be merged.
# It is acceptable for it to exist; it is NOT acceptable for it to be merged
# into the current HEAD. Any OTHER stray executor worktree fails outright --
# this wave creates none, so one appearing means something else is running.
# ---------------------------------------------------------------------------
echo "--- 5. WORKTREES_CLEAN --------------------------------------"
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

 THE TREE IS NOW FROZEN. From this moment until the queue finishes (~9 h):
   - NOTHING is committed, staged, tagged, checked out or pushed.
   - NO tests are run.
   - NO other work happens on this box -- one production calibration at a time.
 Every artifact produced tonight must carry the sha above. A commit landing
 mid-run splits one night's artifacts across two shas and breaks provenance.
==============================================================
EOF
exit 0
