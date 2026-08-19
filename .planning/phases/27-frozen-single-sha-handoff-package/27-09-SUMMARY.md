---
phase: 27-frozen-single-sha-handoff-package
plan: 09
subsystem: experiments-driver-docs
tags: [handoff, environment, freeze, documentation, declared-reduction]
requires:
  - "27-01's target measurements (27-TARGET-FACTS.md)"
  - "27-02's is_stage_complete fix (the resume paragraph describes it as shipped)"
  - "27-05's experiments/_env_lock.py (environment_lock.txt)"
provides:
  - "experiments/HANDOFF.md -- the environment requirements and run procedure inside the frozen sha"
affects:
  - "27-08 (driver/config/expectations edits this note describes as intended end state)"
  - "27-11 (pre-push redaction audit)"
  - "27-12 (on-target clean-clone verification; the OpenBLAS confirmation lands in its SUMMARY)"
tech-stack:
  added: []
  patterns:
    - "in-repo operator note in EXPECTATIONS.md house style"
    - "intended-end-state paragraphs, explicitly flagged, for concurrently-edited files"
key-files:
  created:
    - experiments/HANDOFF.md
  modified: []
decisions:
  - "Described 27-08's in-flight driver changes (E2 release config default, PRELAUNCH_GATE_PYTHON resolution, the _env_lock call site) as INTENDED END STATE with an explicit 'the driver is authoritative' note, rather than asserting them as fact"
  - "Recommended the run log land outside both the output tree and the clone, because a log written into experiments/results/ before launch trips the driver's own non-empty-output refusal"
  - "Used ASCII hyphens for the runtime figures so the numbers survive a byte-oriented grep"
metrics:
  duration: ~25 min
  tasks: 2
  files: 1
  completed: 2026-08-19
---

# Phase 27 Plan 09: Handoff Note Summary

`experiments/HANDOFF.md` — 351 lines, the environment-requirements and run-procedure document the
Linux run machine reads, written inside the frozen sha so the package is self-describing.

## What was built

**§1 Environment requirements (ROADMAP criterion 3).**

- Python `>=3.11`, and the two measured target facts that change how the environment is built:
  there is **no bare `python` on the target's PATH at all** (only `/usr/bin/python3` at 3.10.12,
  below the floor), and **`conda` is not on the PATH for non-interactive SSH**. Because ~25 stage
  invocation lines run bare `python -u -m experiments.<module>`, the note requires the suite to be
  launched from a shell with the frozen environment already activated.
- The hard `opencv-python==4.13.*` pin with its measured reason (4.14.0 detected **1.95% fewer
  corners** and moved reconstruction RMSE **+7.8%**), plus `scipy>=1.16` and unpinned NumPy, and a
  plain statement that `pyproject.toml` is the shipped package's contract and is deliberately not
  tightened for one internal run.
- **Two callouts carrying wave 1's worst findings.** Do not reuse the pre-existing environment (it
  carries the excluded 4.14.0), and **assert** rather than assume where `aquacal` imports from —
  the editable-install `.pth` hazard produces artifacts stamped with the frozen sha while running a
  different checkout, silently, with the sha gate green. The note gives the exact
  `import aquacal; print(aquacal.__file__)` assertion.
- What is captured automatically — `run_manifest.json` (16 named provenance fields plus the BLAS
  two-regime record) and `environment_lock.txt` (the transitive set) — with an instruction not to
  hand-edit either.
- What must be confirmed on the target and is not in the sha: the **OpenBLAS build**, recorded in
  27-12's SUMMARY rather than by editing this file, because editing anything inside the frozen sha
  costs a new tag.
- Resources: the measured RSS classes, `SUITE_WORKERS` 4–5 with the at-most-one-200-frame rule and
  a do-not-re-tune instruction, the 20 GiB free-space floor against ~662 GiB measured, and the
  corrected runtime — **~22-26 h serial, ~15-16 h pooled**, dominated by `e6_band` at ~8.9 h, with
  the older ~50 h figure explicitly marked superseded and wrong.

**§2 Run procedure and declared gaps (D-21, criterion 4).**

- The invocation: `nohup ... & disown`, why the log lands **outside** the output tree (a log written
  into `experiments/results/` before launch trips the non-empty-output refusal), and that unbuffered
  output is already handled by the driver's own `python -u` call sites.
- That `experiments/results/` is **tracked**, so the run dirties its own working tree, and that the
  absence of a dirty-tree refusal is deliberate — such a check fires on resume and would refuse
  every restart after the first crash. Do not add one back.
- All five pre-flight override flags, copied from `--help`, one line each, plus the two refusals
  that have **no** override; and the governing rule that pre-flight is the only place permitted to
  abort.
- Resume: the sha-derived state file, and that after 27-02's fix a stage that **ran AND FAILED**
  re-runs rather than being skipped — the failure mode most likely to cost a single-shot night.
- **The D-21 section.** `e7_focal_standoff` (no `--smoke` branch, hardcoded cwd-relative production
  path) and `e4_repeat` (both invocation shapes refuse `--smoke`), with the consequence stated in a
  warning callout: **neither line is exercised by any rehearsal, including the on-target
  verification, so a failure will first appear during the production run.** Naming them is the
  mitigation.
- What a green verification does not prove — existence/row count are not correctness, `--smoke`
  cannot catch a wrong `--config` path, and a green sha gate does not prove the code that ran was
  the frozen code.
- Criterion 4's rule: a missing piece sends the freeze back to Phase 27 (fix → commit → next
  `rerun-freeze-NN` tag → re-verify), and **tags are never moved**.

## Deviations from Plan

**None affecting scope.** Two judgement calls worth recording:

1. **Concurrent-file description.** The plan's `<read_first>` pointed at `run_experiment_suite.sh`
   line ranges and asked for flags copied from `--help`; that was done against the driver as it
   stands in the base. But plan 27-08 is concurrently repointing `E2_RELEASE_CONFIG`, deleting the
   conda-env-by-name `GATE_PYTHON` rung (D-29) and adding the `_env_lock` call site. Those are
   written as **intended end state** in two explicitly-flagged blockquotes, each ending "if the
   driver and this paragraph disagree, the driver is authoritative", per the orchestrator's
   instruction. The orchestrator should reconcile after the merge.
2. **ASCII hyphens for the runtime figures.** The rest of the document uses en dashes in house
   style, but `~22-26 h` / `~15-16 h` are written with ASCII hyphens so the numbers survive a
   byte-oriented grep — the plan's own acceptance criterion failed against the en-dash form under a
   C-locale `grep`.

No auto-fixes under Rules 1–3 were needed; nothing under Rule 4 arose.

## Verification

- `bash experiments/run_experiment_suite.sh --help` exits 0.
- All five override flags appear in both the note and `--help`, one occurrence each, spot-checked
  by a `grep -o | sort | uniq -c` on both sides — the two lists match exactly.
- `grep` confirms: `4.13` present, the 1.95% / +7.8% reason present, `run_manifest.json` and
  `environment_lock.txt` both named, `15-16 h` present, the single `50 h` occurrence explicitly
  labelled superseded, `e7_focal_standoff` and `e4_repeat` both named in the never-rehearsed
  section, the tracked-results/no-dirty-tree-refusal statement present, and the tags-are-never-moved
  rule present.
- `git status --short` showed only `experiments/HANDOFF.md`; neither `pyproject.toml`,
  `requirements.txt`, `run_experiment_suite.sh`, `suite_expectations.json` nor `EXPECTATIONS.md` was
  touched. STATE.md and ROADMAP.md untouched.
- Redaction scan (`grep -i 'tucke|lab-pc|ssh -|id_ed25519|\.ssh|/home/'`) returned nothing. Paths
  are written as `$HOME/aquacal-frozen-<tag>` and `<conda-root>/envs/<frozen-env>/bin/python`.
- Not run, per the plan and CLAUDE.md: the full test suite (orchestrator's post-merge gate) and the
  driver in any real mode.

## Known Stubs

None. The two `<tag>` / `<conda-root>` placeholders in §2.1 are deliberate — the tag does not exist
until plan 27-10/27-11 cuts it, and writing a literal conda root would put a personal identifier
into a file that becomes public.

## Threat Flags

None. The one information-disclosure surface (T-27-09-01) is the file itself becoming public at
27-11's push, and it is mitigated as designed: the machine is referred to by class only, no
hostname, username, key path or key material appears, and home-relative paths are written as
`$HOME/…`.

## Self-Check: PASSED

- `experiments/HANDOFF.md` — FOUND (351 lines)
- `900d835` — FOUND
- `801eb81` — FOUND
