# Deferred Items — Phase 21

Out-of-scope discoveries found during plan execution, logged per the executor's SCOPE BOUNDARY
rule. Not fixed here.

## From plan 21-03

- **`src/aquacal/datasets/synthetic.py:generate_board_trajectory` docstring — Sphinx docutils
  error.** `sphinx-build -W --keep-going -b html docs docs/_build/html` on a clean `docs/_build`
  emits `ERROR: Unexpected indentation. [docutils]` at
  `src/aquacal/datasets/synthetic.py:docstring of
  aquacal.datasets.synthetic.generate_board_trajectory:7`, which `-W` promotes to a build
  failure. This is unrelated to plan 21-03's files (`docs/tutorials/03_cli_walkthrough.md`,
  `docs/tutorials/index.md`) — `synthetic.py` was last touched by `091e97d
  fix(19.4-02): relocate generate_camera_array jitter from water_z to C_z`, a prior phase. The
  docstring's line 7 (a `depth_range` argument doc line) likely has inconsistent indentation
  relative to the Google-style docstring block above it. Confirmed pre-existing: a clean build
  of only 21-03's own additions (`docs/tutorials/03_cli_walkthrough.md`,
  `docs/tutorials/index.md`) introduces zero new warnings once the two `../guide/benchmarking.md`
  markdown-link cross-references were rewritten as plain-text mentions (the target page,
  `docs/guide/benchmarking.md`, is created by a sibling wave-1 plan not present in this
  worktree). Whoever runs the post-merge full `sphinx-build -W` gate should either fix this
  docstring's indentation or confirm it was already fixed by a sibling plan.
