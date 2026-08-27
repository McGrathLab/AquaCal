---
created: 2026-08-17T00:00:00.000Z
title: Revert model_profile from quality back to balanced in config.json after Phase 24 executes
area: tooling
resolves_phase: 25
files:
  - .planning/config.json
---

## Problem

`.planning/config.json` had `model_profile` changed from `balanced` to `quality` on 2026-08-17,
during Phase 24 planning. It is a **tracked, persistent** file, so the change applies to every
subsequent phase — 25 through 30 — until it is reverted. Nothing expires it.

Under `balanced`, `gsd-executor` resolves to **sonnet**; under `quality` it resolves to **opus**.
Every phase before 24 ran on `balanced`.

## Why `model_profile` and not the `models` map

The obvious lever — the per-phase-type map `"models": { "execution": "opus" }` documented in
`~/.claude/get-shit-done/references/model-profiles.md` — **silently does nothing on this
machine.** It was tried first and `init.execute-phase` kept returning `sonnet`.

Root cause: `gsd-sdk` does not run from `~/.claude/get-shit-done/`. It runs from an npx cache
copy — `AppData/Local/npm-cache/_npx/4db0de1f85c3165e/node_modules/get-shit-done-cc`,
**v1.42.3**. That package's `sdk/shared/model-catalog.json` carries the `phaseType` field, but
its `sdk/` code contains **no reader for it** — zero references to `AGENT_TO_PHASE_TYPE` or
`config.models`. The phase-type map (#3023) exists only in the newer source tree that supplies
the docs, so the docs describe a feature the running binary lacks.

**Generalize this:** when a GSD config knob appears not to work, check which copy of the SDK is
actually executing (`which gsd-sdk` → read the shim) before trusting
`~/.claude/get-shit-done/references/`. The two can be different versions.

`model_profile: quality` is a safe substitute here rather than a blunt instrument, because
`execute-phase` only ever spawns `gsd-executor` and `gsd-verifier`. Under `quality` those are
opus and sonnet; the researchers, roadmapper and codebase-mapper that also sit in the `quality`
column never run during execution. The one real side effect is that `/gsd:debug`, if invoked
during the phase, would run its debugger on opus.

## Why it was added

Phase 24 was a poor fit for a sonnet executor on two counts:

1. **Plan 24-01 accumulates context.** Its four tasks revisit the same five source files rather
   than partitioning by file, so reads accumulate instead of turning over — roughly 70-75% of a
   200k executor window before edits, against GSD's ~50% target. (Plan 24-02 reads more source
   in total, 7,462 lines vs 3,075, but its three tasks partition cleanly by file.)
2. **It edits `src/aquacal/core/refractive_geometry.py`**, the one file where a silent arithmetic
   change would invalidate Phase 29's E2 sanity control — days before the freeze. The revised
   D-06 confines the edit to an opt-in, `None`-defaulted reason array written at four existing
   failure branches, none inside the Newton loop, but the care required to keep it that way is
   exactly what the model tier buys.

It was raised for the whole phase rather than wave 1 alone because GSD resolves `executor_model`
**once** per `execute-phase` invocation — there is no per-wave or per-plan knob — so wave-scoping
would mean two `execute-plan` invocations with a config flip between them. Plan 24-02's Task 3
also edits `check_rerun_gates.py`, which decides whether Phase 29 accepts the frozen run, and
unlike 24-01's arithmetic that edit has no inertness test standing behind it.

## Solution

After Phase 24 is executed **and verified**, set `model_profile` back to `balanced` in
`.planning/config.json` and confirm the resolution reverted:

```bash
gsd-sdk query init.execute-phase 25 | grep executor_model   # expect "sonnet"
```

Then decide deliberately whether Phase 25 wants it back. Phase 25 (DEGEN-04 classification +
BAND-01) is analysis rather than sensitive-file surgery, so the default answer is no.

## Do not

- Do not revert it **during** Phase 24 execution — the model is resolved at invocation, so a
  mid-phase flip would either do nothing or split the phase across two tiers.
- Do not "fix" this by re-adding a `models` map. It is inert on the installed SDK (see above)
  and reads as a working override to anyone who does not check which binary is running.
