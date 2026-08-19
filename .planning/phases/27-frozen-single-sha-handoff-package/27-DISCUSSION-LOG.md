# Phase 27: Frozen Single-Sha Handoff Package - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-19
**Phase:** 27-frozen-single-sha-handoff-package
**Areas discussed:** Freeze anchor & verification venue, Package contents & the two Windows paths,
Environment specification strength, Emitter coverage for every §3 number, Smoke-profile artifact
mismatch (added by the author)

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Freeze anchor & verification venue | What the sha is pinned to, and where the clean-checkout run is proven | ✓ |
| Package contents & the two Windows paths | What travels, and the `GATE_PYTHON` / `E2_RELEASE_CONFIG` literals | ✓ |
| Environment specification strength | Prose spec vs lockfile vs tighter pyproject pins | ✓ |
| Emitter coverage for every §3 number | Criterion 5 — a hand-asserted number cannot be made traceable later | ✓ |
| *(author-added)* Smoke-profile artifact mismatch | Phase 26 open item #1 | ✓ |

---

## Freeze anchor & verification venue

### How the code reaches the target, and what names the frozen sha

| Option | Description | Selected |
|--------|-------------|----------|
| Push branch + tag, clone on target | Real clean checkout, git provenance survives; CI risk checked first | ✓ |
| `git archive` tarball, no push | No CI risk, but no `.git` on target — breaks sha derivation, state path, `git describe`, Gate 3 | |
| Frozen branch only, no tag | Same clean-checkout property, but a branch can move | |

**User's choice:** Push the branch + tag.
**Notes:** Workflows were checked before committing to this. `publish.yml` fires only on `v*` tags,
`release.yml` only on push to `main`, `test.yml` only on main-push or PR-to-main — so pushing
`experiments/full-suite-rerun` plus a non-`v*` tag triggers **no CI at all**. The tag must not start
with `v`; that is the entire constraint.

### Where clean-checkout verification is proven

| Option | Description | Selected |
|--------|-------------|----------|
| On the Linux target — dry-run + short real stage | Only venue that catches a Linux-only failure; also where the OpenBLAS confirmation belongs | ✓ |
| Both: fresh local clone, then target | Separates packaging defects from Linux defects; strictly more work | |
| Fresh local clone only | Cheapest; violates criterion 4's spirit | |

**User's choice:** On the Linux target.

### Access model

| Option | Description | Selected |
|--------|-------------|----------|
| User runs a handed script, pastes output | Works whether or not the box is reachable; one round trip per defect | |
| SSH available — Claude drives it directly | Defect found and fixed in one loop | ✓ |
| No separate target yet | Would force verification back to a local clone | |

**User's choice:** SSH is available.
**Notes:** Connection details were not supplied during the discussion and must be obtained before
the first on-target step. `CLAUDE.md`'s never-background-a-long-run policy binds every SSH call.

### Re-freeze rule

| Option | Description | Selected |
|--------|-------------|----------|
| New tag per attempt, old tags never moved | Abandoned tags become the audit trail; avoids the F-002 shape | ✓ |
| One tag name, force-moved | Simpler to reference; destroys the record of the failed attempt | |
| Freeze once, patch on target | Fastest; re-creates the multi-sha fracture F-001/F-002 exist to prevent | |

**User's choice:** New tag per freeze attempt.
**Notes:** Consequence surfaced later — the lockfile can only be captured after the target env is
built but must live inside the frozen sha, so ≥2 tags are expected by construction, not as failure.

---

## Package contents & the two Windows paths

### How the E2 frameset reaches the target

| Option | Description | Selected |
|--------|-------------|----------|
| Download Zenodo 21889922 on the target | The exact artifact the identity signature was verified against | |
| scp the 10.57 GB local raw capture | Byte-identical to prior measurements; heavy, weaker provenance | |
| Already on target — verify only | No transfer; Phase 27 verifies what is there | ✓ |

**User's choice (free text):** *"image set (not video set) should already be on target, just
verify"*.
**Notes:** This correction is what surfaced the D-09 defect — the pre-flight check assumes files.

### E2 config and the image-set pre-flight

| Option | Description | Selected |
|--------|-------------|----------|
| Commit a Linux image-set config + make pre-flight path-kind agnostic | Inputs inside the frozen sha; check accepts dirs | ✓ |
| Fix pre-flight only, config stays off-repo | Smaller diff; provenance stays outside the artifact (F-001 shape) | |
| Verify on target first, then decide | One round trip before the fix can be planned | |

**User's choice:** Commit the config **and** fix pre-flight.
**Notes:** Two findings drove the options — `run_experiment_suite.sh:955-957` uses `p.is_file()`, so
directories read as ABSENT and push the run to `--skip-e2` (synthetic-only); and the Desktop config
has `frame_step: 30` while the manifest's verified signature is `frame_step: 1` /
`max_calibration_frames: 200`, so the Desktop config does not produce the signature pre-flight
asserts. The library is unaffected — `io/detection.py:134` auto-selects `ImageSet` for a directory.

### The two Windows literals

| Option | Description | Selected |
|--------|-------------|----------|
| Detect, then fall back, warn loudly either way | Keeps the Git Bash box working; no new refusal | ✓ |
| Require both as env vars, no defaults | Maximally explicit; adds a refusal that fires on every resume | |
| Hardcode the Linux values | Simplest; breaks the machine where defects get diagnosed | |

**User's choice:** Detect-then-fallback.

### Intrinsic sources on the target

| Option | Description | Selected |
|--------|-------------|----------|
| Image sets for intrinsics too — same treatment | One data story; the path-kind fix covers both blocks | ✓ |
| Not sure — check over SSH first | Removes the largest unknown, costs a round trip | |
| Cached intrinsics rather than raw frames | Would shorten E2 and remove intrinsics from pre-flight's concern | |

**User's choice:** Image sets for both.

---

## Environment specification strength

### How tightly the environment is specified

| Option | Description | Selected |
|--------|-------------|----------|
| Exact lockfile committed at the freeze | Environment gets the same provenance as the code | ✓ |
| Prose requirements doc, no lockfile | Lighter; leaves `numpy` unpinned as a reproducibility hole | |
| Tighten `pyproject.toml` pins | Strongest guarantee; degrades the shipped package for every pip user | |

**User's choice:** Committed lockfile.

### Thread control

| Option | Description | Selected |
|--------|-------------|----------|
| Pin OMP/MKL/OPENBLAS in the driver, record the value | Probe shows a solve holds ~1 core, so a cap costs nothing | ✓ |
| Leave unset, measure and record on target | Zero freeze-window code risk; timing stages depend on an unstated default | |
| Pin only concurrent stages, leave timing stages free | Most surgical; two thread regimes in one run | |

**User's choice:** Pin in the driver, record in the manifest.

### Worker count

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 4–5, confirm RSS on target, do not re-tune | Preserves a measured bound rather than a guess | ✓ |
| Re-derive workers from measured RSS on target | A short stage's RSS is a floor, not the binding constraint | |
| Run fully serial | Removes concurrency risk; gives back the ~8–10 h D-52 saved | |

**User's choice:** Keep 4–5.

---

## Emitter coverage for every §3 number

### What the repo side does

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical cross-check now, written report, no gate | Gaps get fixed inside the freeze window | ✓ |
| Same cross-check wired as a gate | Stronger for RUN-04; its input lives outside the repo — the "gate that cannot pass" shape | |
| Receiving procedure only | Least duplicated effort; nothing verifies completeness before the freeze | |

**User's choice:** Cross-check + report, no gate.
**Notes:** The ledger was read during the discussion: 131 rows, 27 distinct artifacts, 78
`KEEP-VERIFIED` / 46 `EDIT` (all applied) / 7 `KEEP-FROZEN-5f`; 21 artifact-less rows, 11 of them
non-`EDIT`. Most of the 11 are inputs, apparatus facts or physical constants; the genuine candidates
are `M-L281-19mm`, `M-L281-135x` and `RL-determinism`.

### If a gap is found

| Option | Description | Selected |
|--------|-------------|----------|
| Add the emitter, then re-freeze | Criterion 5's stated remedy; an emitter is additive, low risk | ✓ |
| Case by case — emitter, or drop/soften the number | Shortest freeze window; needs a per-row judgement call | |
| Record the gap, decide post-submission | Zero risk; contradicts criterion 5 | |

**User's choice:** Add the emitter, then re-freeze.

### Rows backed by trees this run will not regenerate

| Option | Description | Selected |
|--------|-------------|----------|
| Classify each as deliberately-frozen, record why, in-repo | Turns stale reference into stated provenance; feeds Phase 30 | ✓ |
| Also verify the cited trees survive the archive-aside | More thorough; extra path-by-path work | |
| Out of scope — Phase 30's audit covers it | Phase 30 is post-submission, so the paper ships without the statement | |

**User's choice:** Classify and record in-repo.

---

## Smoke-profile artifact mismatch *(author-added area)*

### How far the fix goes

| Option | Description | Selected |
|--------|-------------|----------|
| Make the whole smoke profile truthful — target exit 0 | Manifest/gate-side only; a green smoke becomes a usable signal on the target | ✓ |
| Fix only the three mis-tagged artifacts | Smallest diff; smoke still cannot exit 0 | |
| Fix the manifest AND make smoke paths write the sidecars | Edits three experiment scripts in the freeze window | |

**User's choice:** Make the whole profile truthful.
**Notes:** The three mis-tagged artifacts are 4 of 12 pre-existing failures; the rest are 4× E6
`gate4_optimality` on collapsed smoke solves, 1× E6 cameras-axis, 2× E4 missing `benchmark_grid.csv`,
plus the roll-up aggregate.

### The two stages skipped rather than reduced

| Option | Description | Selected |
|--------|-------------|----------|
| Leave skipped as DECLARED REDUCTIONs | No freeze-window code for diagnostic-only benefit | ✓ |
| Add a smoke path for `e7_focal_standoff` | Removes a hardcode; edits an experiment script | |
| Rehearse both via targeted dry run instead | Proves the command line, not the code path | |

**User's choice:** Leave skipped — with the gap stated explicitly in the handoff note.

### The other two Phase 26 open items

| Option | Description | Selected |
|--------|-------------|----------|
| Resume skips a stage that ran AND FAILED (`:669`) | Most likely single failure mode to cost a 15–16 h run; one-column `awk` fix | ✓ |
| `reconstruction_bootstrap.py:56` hardcodes its output path | Matters more now that smoke is the target's verification signal | ✓ |
| Neither — both stay deferred | Narrowest freeze window | |

**User's choice:** Both in scope. This reverses the 2026-08-18 deferral of the resume defect.

---

## Claude's Discretion

- Tag naming beyond `rerun-freeze-NN`; the lockfile's filename and location.
- The precise thread-cap value (bounded by the probe: ~1 core median, p95 2.01).
- Format of the emitter cross-check report and the location of the frozen-row note.
- Whether the frame-count check replaces or supplements the byte floor — decide from target
  measurements.

## Deferred Ideas

Recorded in `27-CONTEXT.md` § Deferred Ideas. Nothing raised during this discussion was scope creep;
the one addition the author made (the smoke profile) was an existing Phase 26 open item that
directly gates this phase's chosen verification venue.
