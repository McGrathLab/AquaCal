---
created: 2026-08-26T00:00:00.000Z
title: No local gate builds the docs, so docstring reStructuredText is unchecked until a pull request runs CI
area: tooling
resolves_phase: 30
files:
  - .pre-commit-config.yaml
  - docs/Makefile
  - .github/workflows/docs.yml
---

## What happened

Phase 29.2 opened PR #3 and `build-docs` failed on four docutils problems, every one of them
docstring markup in `src/aquacal/`:

- `src/aquacal/calibration/interface_estimation.py` — docstring of
  `DEGENERACY_WARNING_FRACTION_THRESHOLD`, line 10: `WARNING: Definition list ends without a blank
  line; unexpected unindent.`
- `src/aquacal/calibration/refinement.py` — docstring of
  `DEGENERACY_WARNING_FRACTION_THRESHOLD`, line 13: same warning.
- `src/aquacal/validation/diagnostics.py` — docstring of `save_diagnostic_report`, line 10:
  `ERROR: Unexpected indentation.`
- `src/aquacal/validation/diagnostics.py` — docstring of `save_diagnostic_report`, line 11:
  `WARNING: Block quote ends without a blank line; unexpected unindent.`

Phase 29.2 did not cause these. `git log --name-only 12291c6...cf14d0e -- src/` is empty — the
phase touched no source file at all. The docstrings were last written in phases 24/25
(`a212d5a`, `34b4354`, `ba59f84`).

## Why no local gate caught it

Nothing local builds the documentation.

The nine pre-commit hook ids — `ruff`, `ruff-format`, `trailing-whitespace`, `end-of-file-fixer`,
`check-yaml`, `check-added-large-files`, `detect-secrets`, `ruff-check-all`,
`ruff-format-check-all` — contain no doc build. `grep -in sphinx .pre-commit-config.yaml` returns
nothing. `.git/hooks/` holds only `.sample` files, so there is no prepush gate either.

Ruff lints Python. It does not parse the reStructuredText *inside* a docstring. Docstring markup
is only ever exercised by a doc build, and the sole doc build in this repository is
`.github/workflows/docs.yml:30`:

```
sphinx-build -W --keep-going -b html docs docs/_build/html
```

That is the only occurrence of `-W` anywhere in the project.

## The trap inside the trap

`docs/Makefile` sets `SPHINXOPTS ?=` — empty by default. So `make -C docs html` run locally
**succeeds** on exactly the tree where CI fails, because it omits `-W`. Someone who did think to
build the docs before pushing would still not have caught this. Any fix must pin `-W`, not merely
add a doc build.

`--keep-going` is why all four problems surfaced in one run rather than one per push.

## Why this is a real gap and not a diligence failure

Phase 29.2 mirrored CI locally with unusual care. Plan 29.2-04 installed unpinned
`pre-commit 4.6.2` into an isolated venv specifically to reproduce `test.yml:54`, and plan 29.2-03
ran CI's exact not-slow selection plus all seven experiment smoke invocations. Both mirrors were
accurate about the jobs they mirrored. Nobody mirrored the docs job, so its blind spot was
inherited whole.

## What to do

Add a doc build to the local gate, with `-W` pinned so local and CI agree. Either:

```yaml
- repo: local
  hooks:
    - id: sphinx-build-strict
      name: build docs with warnings as errors
      entry: sphinx-build -W --keep-going -b html docs docs/_build/html
      language: system
      pass_filenames: false
      files: ^(docs/|src/aquacal/.*\.py)$
```

or a documented prepush step. Weigh the cost first: the CI job takes ~1m15s including a pandoc
install, so a per-commit hook is likely too slow and a prepush or `files:`-scoped hook is the
better shape.

If a hook is added, note that it must not write `docs/_build/` into a tree that phase 29.2's
byte-integrity proof requires to stay clean — build to a temporary directory or confirm
`docs/_build/` is ignored.

See also [[2026-08-26-docs-yml-only-runs-on-pull-requests-into-main]] — the two together are why
four months of docstring edits accumulated behind an unwatched gate.
