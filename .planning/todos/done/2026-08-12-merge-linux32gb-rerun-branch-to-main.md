---
created: 2026-08-12T00:00:00.000Z
title: Merge experiments/linux32gb-rerun to main before the SoftwareX submission
area: experiments
files:
  - experiments/results_linux32gb/
  - .planning/MANUSCRIPT-FINDINGS.md
  - .planning/REQUIREMENTS.md
  - .gitignore
---

## Problem

The SoftwareX revision will cite performance numbers — and one substantive finding — that
currently exist **only on the branch `experiments/linux32gb-rerun`** (commit `1af0650`,
pushed 2026-08-12). Submitting a paper whose evidence lives on an unmerged branch is the
same class of problem MF-19 raised for a different reason: a reader following the repo
cannot reach what the manuscript points at.

What is on the branch and nowhere else:

- `experiments/results_linux32gb/` — the nine-cell E4 grid and the two E2 runs
  (`e2_timing/`, `e2_memory/`) measured on 32 GB Linux, plus per-cell `benchmark.json`
  records and `run.log`s.
- `linux32gb_scope.json` — the scope and confound-control statement. This is the file that
  makes the rest citable rather than merely present.
- **MF-20** in `.planning/MANUSCRIPT-FINDINGS.md` — the OpenCV detection-drift finding.
- Two `.planning/debug/` notes (the OpenCV 4.13-vs-4.14 isolation note, and a config
  help-text note about the retired Zenodo archive).
- `.gitignore` additions covering the new results tree.

Manuscript sections that will depend on it: the runtime/memory answer to reviewers R1.5
and R3.2, the rewrite of the "in minutes on consumer hardware" claim, the supplement's
computational-performance section, and the cross-platform reproducibility argument
(nine synthetic cells to 1e-13 against the real rig's ~2% detection drift).

## Solution

1. **Review and merge to `main`.** The branch adds only `experiments/results_linux32gb/`,
   planning documents, and `.gitignore` entries — per `linux32gb_scope.json`, **no
   committed artifact under `experiments/results/` was modified**, so the merge cannot
   move a published number. Confirm that claim holds at merge time rather than trusting
   it: `git diff main...experiments/linux32gb-rerun -- experiments/results/` should be
   empty.

2. **Decide how the results tree is named.** `results_linux32gb/` sits beside
   `results/`, `results_e2_band/`, `results_e4_repeat/` and `results_e6_repeat2/`, so the
   convention is already established — but this is the first sibling distinguished by
   *machine* rather than by experiment variant. Worth one line in
   `experiments/README.md` §2's provenance table so a reader knows which tree the paper's
   timing numbers come from and which tree its accuracy numbers come from. They are
   deliberately different trees; that needs to be legible.

3. **Do NOT let semantic-release cut a version off this merge.** The branch contains no
   `src/` change. Commit it so the release automation treats it as `chore:`/`docs:` —
   a version bump here would be meaningless and would desynchronise the C1 metadata the
   manuscript is about to freeze.

4. **Check `experiments/README.md`'s E4 note stays true.** E4's aggregator sources the
   real-rig row from a hardcoded `E2_BENCHMARK_PATH` (`e4_benchmark_grid.py:226`) that
   does not follow `--out`, which is why the Linux `benchmark_grid.csv` carries the nine
   synthetic cells only and the real-rig row was dropped. That is a genuine (small) defect
   in the aggregator, currently worked around by hand. Either note the workaround in the
   README or file it separately — do not leave it discoverable only from
   `linux32gb_scope.json`.

## Related

- The OpenCV half of this work is
  `2026-08-12-name-the-opencv-version-in-real-rig-reproducibility-claims.md`. The two are
  independent: the merge can land without resolving the pinning question.
- `HANDOFF.json`'s `pypi-approval` item is still open and unrelated, but both are release
  hygiene ahead of the 2026-08-21 deadline.
