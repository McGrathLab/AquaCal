---
created: 2026-08-26T00:00:00.000Z
title: docs.yml triggers only on pull requests into main, so it went four months without running and accumulated a latent failure
area: ci
resolves_phase: 30
files:
  - .github/workflows/docs.yml
  - .github/workflows/test.yml
---

## The measurement

`.github/workflows/docs.yml` triggers on one event and one only:

```yaml
on:
  pull_request:
    branches: [main]
```

`.github/workflows/test.yml` triggers on two:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

The Documentation workflow has no `push` arm. It runs on a pull request into `main` and at no
other time — not on a push to `main`, not on any branch, not on a pull request into `dev`.

## What that cost

`gh run list --workflow=docs.yml` shows the last successful Documentation run on **2026-04-20**,
against `dev`. The next entry is phase 29.2's PR #3 on **2026-08-27** — and it failed on four
docutils problems in docstrings last edited in phases 24/25.

Roughly four months of source edits landed with the docs gate never once firing. The failure was
not introduced late; it was latent the whole time, behind a trigger narrow enough that nothing
routine reached it. Work in that window went to `dev` and to feature branches, and only a pull
request into `main` would have run it.

This is the "unknown rather than a risk" category phase 29.2 spent its effort converting into
measurements. The docs job was an unknown because it structurally could not run.

## Why it matters beyond this instance

The same latency recurs with the next docstring, and the shape generalises: a gate that fires only
on the rarest event in the workflow accumulates debt silently and then presents it all at once, on
the day the pull request into `main` is opened — which in this project is a release day, i.e. the
worst possible day to discover it.

Phase 29.2's other CI-facing plans could pre-measure their jobs precisely because those jobs run
often enough to have a known-good baseline. This one had none.

## What to do

Decide whether the narrow trigger is deliberate.

If it is not, widen it to match `test.yml`, and consider whether pull requests into `dev` should
run it too:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

If it *is* deliberate — for instance because the pandoc install and full Sphinx build are
considered too expensive to run per push — then the docstring markup check belongs in a local gate
instead, so the check exists somewhere that actually fires. See
[[2026-08-26-no-local-gate-builds-the-docs-so-docstring-markup-is-unchecked]], which is the other
half of this: no local gate builds the docs either, so between the two there was no point at which
this class of defect could surface before a release-day pull request.

Whichever way it is decided, record the ruling — the cost of leaving it implicit is exactly the
four months above.
