---
created: 2026-08-26T00:00:00.000Z
title: Pre-existing — `.planning/STATE.md`'s body has no "Current Plan" or "Progress" fields, so `gsd-tools query state.advance-plan` and `state.update-progress` error out
area: planning
resolves_phase: 30
files:
  - .planning/STATE.md
---

## Not caused by Phase 29

**This predates Phase 29 and several of its plans hit it.** It is filed so that the next executor
who sees the error recognises it as known rather than treating it as damage they caused, and so that
whoever reshapes `STATE.md` does it deliberately.

## What fails

```
gsd-tools query state.advance-plan    -> "Cannot parse Current Plan or Total Plans"
gsd-tools query state.update-progress -> "Progress field not found"
```

## Why

The handlers expect those fields in the **document body**. This project's `STATE.md` carries its
position and progress in the **YAML frontmatter** instead:

```yaml
current_phase: 29
current_phase_name: Gate Verification & Results Commit
stopped_at: Completed 29-07-PLAN.md
progress:
  total_phases: 10
  completed_phases: 7
  total_plans: 63
  completed_plans: 62
  percent: 70
```

The body's section headings are `## Project Reference`, `## Current Position`,
`## Roadmap Summary (v2.1)`, `## Deferred Items`, `## Accumulated Context`,
`## Session Continuity`, `## Performance Metrics` — **none of which contains a `Current Plan`,
`Total Plans` or `Progress` field for the handlers to parse.** [Measured 2026-08-26.]

The frontmatter is accurate and hand-maintained; nothing is lost. Only the two automated handlers
are unable to act on it.

## Why no plan fixed it

**Rewriting a project's state document to satisfy a parser is not a change any single plan should
make unilaterally.** `STATE.md` is read by every workflow and by the author; its `## Current
Position` section carries several hundred lines of hand-written phase narrative that the handler
format does not accommodate. Reshaping it is a project-level decision with a blast radius across
every future plan, not a Phase 29 side effect.

Every affected plan updated the frontmatter by hand instead, which is why the counts are correct
despite the handlers failing.

## What would fix it

One of:

1. **Add the body fields the handlers parse** alongside the existing frontmatter, accepting one
   duplicated source of truth and the drift risk that carries; or
2. **Teach the handlers to read the frontmatter** when the body fields are absent — the better
   shape, since the frontmatter is already this project's actual source of truth; or
3. **Ratify the divergence**: record that this project maintains `STATE.md` by hand and that the two
   handlers are not used here, so the error is expected rather than a finding.

Whichever is chosen, **do not silently reshape `## Current Position`** — the narrative in it is the
context a resuming session reads first.

## Evidence

- `.planning/STATE.md` — frontmatter and section headings, read 2026-08-26
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Open items handed
  forward*, item 11
