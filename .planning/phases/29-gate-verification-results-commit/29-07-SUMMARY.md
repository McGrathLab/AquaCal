---
phase: 29-gate-verification-results-commit
plan: 07
subsystem: data-publication
tags: [zenodo, rest-api, dataset, results-package, md5, doi, supersession, reproducibility]

# Dependency graph
requires:
  - phase: 29-03
    provides: "the E2 same-seed control (n_comparisons 7762 exact, §3 headline drift 4.90e-09 at seed 42, worst-case 3.63e-08, RESULT PASS) — D-29-05's second gate, and the evidence that discharges the folded todo's round-trip obligation without re-running a stage"
  - phase: 29-04
    provides: "Record A's production deposition 22116461 with a verified md5 round trip, its flat-root layout finding, and the placeholder-prose defect class that this plan's description review is built to catch"
  - phase: 29-05
    provides: "the returned suite committed at 70e783f, so reference_outputs/ and run_manifest.json are landed artifacts rather than loose files"
  - phase: 29-01
    provides: "scripts/zenodo_upload.py (run unchanged here), scripts/zenodo_metadata_b.json, and 29-RECORD-COMPOSITION.md's research-default payload ruling"
provides:
  - "Record B's results package at ~/zenodo-record-b/real-rig-results-2.1.0.zip — 9,503,394 bytes, md5 f033538e1c9da165aa6267f4ae5d4f78, 11 entries, built to the ruled composition from THIS run's outputs"
  - "Zenodo PRODUCTION deposition 22117061, an UNPUBLISHED draft holding that archive under the key real-rig-results-2.1.0.zip"
  - "Byte-level round-trip proof: server-returned checksum and size equal the local digest and length of the exact bytes uploaded"
  - "The author's `sequential` linkage ruling, and Record A's minted DOIs (version 10.5281/zenodo.22116461, concept 10.5281/zenodo.22116460), both measured resolving"
  - "scripts/zenodo_metadata_b.json finalised: isDerivedFrom -> Record A's version DOI, description prose at 2.1.0, zero version relations against 21889922"
  - "29-zenodo-record-b.txt — the repository's only handle on the draft (id, links.bucket, links.html), the full evidence transcript, and the two outstanding human actions"
  - "An evidence-derived resolution of which diagnostics.json is this run's canonical copy, for any future results package"
affects: [29-08, phase-30-dataset-pin, RUN-05, manuscript-data-availability]

actuals:
  tokens: 14809
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Two-call deposit shape carried over from 29-04: create the draft and commit its id/bucket/html BEFORE a payload byte moves"
    - "Prove arrival, never assume it — a transfer that completed without a matching digest is a failed transfer"
    - "Negative assertion by digest: prove the superseded copies are ABSENT, not merely that the fresh ones are present"
    - "Placeholder review by DEFECT CLASS on rendered prose, not by token grep — the token is gone by the time the defect ships"
    - "Derive an ambiguous source from evidence and record the derivation, rather than choosing the plausible path silently"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-zenodo-record-b.txt
  modified:
    - scripts/zenodo_metadata_b.json

key-decisions:
  - "Record B's isDerivedFrom targets Record A's VERSION DOI 10.5281/zenodo.22116461, not the concept DOI: Record B derives from those exact bytes, and a concept DOI follows the latest version, so it would silently re-point provenance at frames these numbers were never computed from if Record A were ever re-versioned"
  - "reference_outputs/diagnostics.json is taken from experiments/results_e2_invocations/e2_classification/ — the ONLY directory in this run holding both a diagnostics.json and a calibration.json byte-identical to the canonical one, which makes the choice forced rather than preferred"
  - "README.md ships in the zip although it is not a composition-ruling member; the plan mandates it, and the deviation from the ruled list is recorded explicitly in the evidence file so the 'nothing extra' assertion stays auditable"
  - "ZIP_DEFLATED rather than 29-04's ZIP_STORED: this payload is JSON/CSV/YAML text and compresses 2.3x, where Record A's was 3,967 already-compressed PNGs"
  - "Record A's missing isSourceOf back-link is recorded as the accepted consequence of the sequential ruling and left for the author's manual UI edit, not worked around"

patterns-established:
  - "An apparent digest collision inside a payload is explained in the evidence rather than silently tolerated — reference_calibration.json legitimately shares a digest with the archive's old calibration.json because it IS the archived comparison target"
  - "conceptrecid is not a DOI: name it explicitly in the unpublished assertion so a reader cannot misread a reserved record id as a reserved identifier"
  - "Record a documented fallback as NOT TAKEN rather than leaving its absence to be inferred from silence"

requirements-completed: []

coverage:
  - id: D1
    description: "Record B's payload is exactly the research-default member list, sourced from THIS run's outputs and not the published archive's superseded copies"
    requirement: "RUN-05"
    verification:
      - kind: integration
        ref: "per-file md5, payload vs source: all 10 members IDENTICAL to their counterparts under experiments/results/ (diagnostics.json from the derived e2_classification source) and aquacal_data/real-rig/real-rig/"
        status: pass
      - kind: integration
        ref: "negative assertion — all 6 reference_outputs/ digests DIFFER from the published archive's copies of the same names"
        status: pass
      - kind: automated_ui
        ref: "zipfile listing of real-rig-results-2.1.0.zip: 11 entries, top level == the 5 ruled members + README.md, testzip() returns None"
        status: pass
    human_judgment: false
  - id: D2
    description: "The package reached Zenodo production intact and is addressable in an unpublished draft with no registered DOI"
    requirement: "RUN-05"
    verification:
      - kind: integration
        ref: "bucket PUT response checksum md5:f033538e1c9da165aa6267f4ae5d4f78 == local digest; size 9503394 == local size; version_id f82ee9f1-f44b-4c71-9da4-865c903d62cb"
        status: pass
      - kind: integration
        ref: "read-only GET /api/deposit/depositions/22117061 at 19:15:10Z — state unsubmitted, submitted false, doi/doi_url/conceptdoi/links.record all null, 1 file"
        status: pass
    human_judgment: false
  - id: D3
    description: "The record carries the labelling and supersession language a reviewer needs, and the A<->B relationship the author ruled"
    requirement: "RUN-05"
    verification:
      - kind: automated_ui
        ref: "README.md carries the optimality sentence with all three measured properties, the 21889922 supersession statement, the provenance line (tag/sha/window/20-of-20/gate) and Record A's minted DOI"
        status: pass
      - kind: automated_ui
        ref: "metadata related_identifiers checked structurally: isDerivedFrom -> 10.5281/zenodo.22116461, references -> 10.5281/zenodo.21889922, zero version relations"
        status: pass
    human_judgment: true
    rationale: "Whether the title, description prose, licence and cross-links are right for a permanent record the paper will cite is a publication-facing editorial judgement. Publish is the author's act under D-29-01 and reaches its blocking checkpoint at plan 29-08."

# Metrics
duration: 26min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 07: Record B — Build and Production Draft Summary

**Record B's 9.5 MB results package is built from this run's own verified outputs, labelled where a number needed labelling, superseding the old archive in words, streamed into Zenodo production deposition 22117061 with a matching md5 round trip, and left sitting as an unpublished draft — with Record A now published at 10.5281/zenodo.22116461 and cited as its structured provenance.**

## Performance

- **Duration:** ~26 min of execution, plus a blocking checkpoint the author resolved mid-plan
- **Tasks:** 3 of 3
- **Files modified:** 2 tracked (1 created, 1 modified), plus build artifacts outside the repository

## Accomplishments

- **Rules on the A↔B linkage and captured a real identifier.** The author chose `sequential` and published Record A. Both DOIs were measured resolving: version `10.5281/zenodo.22116461` and concept `10.5281/zenodo.22116460`, each landing on `https://zenodo.org/records/22116461` at HTTP 200. The published file's md5 equals plan 29-04's local digest, so the bytes that were built are the bytes that got a DOI.
- **Pointed the structured relation at the version DOI, deliberately.** Record B derives from *those exact bytes*. A concept DOI is a moving target by design — it follows the latest version — so a concept-DOI relation would silently re-point Record B's provenance at frames its numbers were never computed from if Record A were ever re-versioned.
- **Built the payload to exactly the ruled composition.** All five `research-default` members present, nothing else added except the README the plan mandates — and that exception is written into the evidence file rather than left for a reader to notice, so "nothing extra" stays an auditable claim instead of a slogan.
- **Proved the outputs are this run's, twice, in both directions.** Positively: all ten members are md5-identical to the artifacts they were copied from. Negatively: all six `reference_outputs/` digests **differ** from the published archive's copies of the same names. The second check is the one that matters — it proves the supersession is real and not a relabelling.
- **Derived the ambiguous sixth file from evidence instead of guessing.** `diagnostics.json` is not in `experiments/results/`; research said only that it is "written per-run". Every candidate in the run was enumerated and each one's sibling `calibration.json` md5-compared against the canonical result. Exactly one directory holds both a `diagnostics.json` and a byte-identical `calibration.json`, which makes the choice forced rather than preferred. Its reported `reconstruction_num_comparisons` is 7762 and its `reprojection_rms` reproduces the archived value to ~3.1e-09.
- **Wrote a README that labels the number the ROADMAP said to label.** `optimality_stage3_interface_optimization` is stated as a *real* gradient (a central-difference Jacobian reproduces it to five significant figures), *volatile* at a fixed solution (~43× range, severe ill-conditioning), *not comparable across parameter blocks* (Coleman-Li scalings of 1, ~700 and ~2e-12), with *reliability depending on magnitude* (44% disagreement measured at 0.001). Plus the supersession statement naming 21889922, the full provenance line, and Record A's DOI.
- **Streamed 9,503,394 bytes and proved arrival.** Server checksum `md5:f033538e1c9da165aa6267f4ae5d4f78` equals the local digest; server size equals local size; `version_id`, `mimetype` and bucket recorded as corroboration. First attempt, zero retries, ~1.5 s.
- **Asserted the draft is unpublished with measured values.** An independent read-only re-read at 19:15:10Z returned `state: "unsubmitted"`, `submitted: false`, `doi: null`, `doi_url: null`, `conceptdoi: null`, `links.record: null`, one file. The tool still contains no `/actions/` path and the `deposit:write`-only token could not authorise one if it did.

## Task Commits

1. **Pre-checkpoint: linkage options and Record A's live state** — `67d0b9b` (docs)
2. **Task 1: the `sequential` ruling and Record A's minted DOIs** — `cc08fa5` (docs)
3. **Task 2: payload built from this run's fresh outputs** — `00db4ac` (feat)
4. **Task 3 step 1: metadata finalised with the ruled linkage** — `edd9f1b` (feat)
5. **Task 3 step 2: draft handles recorded before any byte moved** — `ca3f044` (docs)
6. **Task 3 steps 3-5: upload and round-trip proof** — `37717eb` (feat)

## Files Created/Modified

- `.planning/phases/29-gate-verification-results-commit/29-zenodo-record-b.txt` — created. The evidence transcript: D-29-05 precondition gates, Record A's live state and minted DOIs, the linkage ruling and its version-vs-concept reasoning, the composition assertion, the `diagnostics.json` derivation, per-file md5 tables in both directions, the README audit, the round-trip citation, the draft's handles, the bucket response, the unpublished assertion, and the outstanding human actions.
- `scripts/zenodo_metadata_b.json` — modified, three edits: the `__RECORD_A_URL__` placeholder resolved to the minted version DOI in both the description prose and the `isDerivedFrom` relation (whose `scheme` moved `url` → `doi`), and the description's "AquaCal 2.0.1" corrected to "2.1.0".
- `~/zenodo-record-b/` — created, **outside the repository, deliberately untracked**: the payload tree, `README.md` (7,197 bytes), `real-rig-results-2.1.0.zip` (9,503,394 bytes) and its `.md5` sidecar.
- Zenodo production deposition 22117061 — new service-side state, unpublished.

`git status --porcelain experiments/ src/` is empty and `git diff --quiet -- src/ experiments/` exits 0.

## Decisions Made

**1. The `isDerivedFrom` target is the version DOI, not the concept DOI.** Recorded with its reasoning in the evidence file because the two look interchangeable and are not. Record B's numbers were computed from one specific 4,341,018,405-byte frameset. The concept DOI resolves to whatever the latest version of Record A happens to be; today that is the same record, but the whole point of a concept DOI is that this can change. Pinning provenance to a moving target is a defect that would only surface years later, in exactly the situation where provenance matters.

**2. `diagnostics.json` comes from `experiments/results_e2_invocations/e2_classification/`.** See Accomplishments. The important property is not that this directory is plausible — several were — but that it is *unique*: it is the only one whose sibling calibration is byte-identical to the canonical result, so the diagnostics describe the calibration Record B actually ships and no other. The derivation is written down so a future results package does not have to redo it.

**3. `README.md` ships despite not being a composition-ruling member.** The ruling is the authority on payload contents and this file is not on its list; the plan separately mandates a README carrying four specific elements. Rather than let the two documents quietly disagree, the README is recorded in the evidence file as an explicit, plan-authorised addition. An acceptance criterion that says "none extra" is only meaningful if the one extra is named.

**4. ZIP_DEFLATED, not ZIP_STORED.** Record A used stored because its payload was 3,967 already-compressed PNGs. This payload is JSON, CSV and YAML text, which deflates 2.3× — 22 MB on disk to 9.5 MB uploaded.

**5. Record A's missing back-link is recorded, not worked around.** Publishing A before B existed means A carries no `isSourceOf` → B. Adding it needs `deposit:actions`, which the token deliberately lacks. This is the accepted, ruled cost of `sequential`, logged as an outstanding human action with the exact UI steps and the fact that editing published metadata neither cuts a new version nor changes the DOI.

## Deviations from Plan

None — plan executed as written. Three resolutions taken inside the plan's own authority, all documented in the evidence file, none of which adds or removes a byte from the ruled composition:

- **The `diagnostics.json` source** (decision 2). The plan names six filenames and asserts all six exist in this run's output; it does not say where the sixth lives, and it is not in `experiments/results/`. Resolved by measurement with a unique answer.
- **The README's status against the composition ruling** (decision 3). Resolved toward explicitness.
- **An apparent digest collision, explained rather than tolerated.** `reference_calibration.json` carries md5 `0ac5dbd16938ebd2711c1a25fbeb217a`, which is also the digest of the archive's *old* `reference_outputs/calibration.json`. This looks exactly like a superseded output leaking into the payload, which is the thing the negative assertion exists to prevent. It is not: `reference_calibration.json` **is** the archived calibration, retained as the comparison target a regression check runs *against*, and the composition ruling assigns it to Record B for that reason. Both the evidence file and the README's contents table say so, so no reviewer — and no future auditor reading the digest table — misreads it as this run's output.

### Coordinator-directed corrections applied (Task 3)

- **`AquaCal 2.0.1` → `2.1.0` in the description prose.** Flagged at the checkpoint, confirmed by the coordinator. The `version` field was already `2.1.0`; the prose contradicted it. Both now agree.
- **ORCID verified, not re-added.** `0000-0003-4074-7128` was already present from orchestrator commit `cd83a99`. Checked rather than applied twice.

## Issues Encountered

**The placeholder defect class, and why a grep does not catch it.** Record A shipped `(linked below once Record B exists)` in its published-draft description — prose that reads as unfinished to a human but contains no token, because plan 29-04 had already substituted the token away. An orchestrator grep for `__RECORD_B_URL__` therefore returned a clean result on text that was visibly broken, and only the author reading the record caught it. Record B's description and README were consequently checked for the **defect class** — unresolved token forms, TBD/TODO/FIXME/XXX, "placeholder", "once … exists", "linked below", `<insert`, `{{ }}`, lorem — and then read end to end as rendered prose. Zero matches, and the substitution was written to fix the awkward `URL .` spacing at the same time. The general lesson: a token-based check verifies that a *substitution ran*, not that its *result is finished text*.

**`conceptrecid` looks like a reserved identifier and is not.** The draft returns `conceptrecid: "22117060"`, allocated by Zenodo at draft creation. D-29-03 forbids reserving a DOI, so this field is named explicitly in the unpublished assertion, alongside `conceptdoi: null`, to head off a later reader concluding the prohibition was violated.

**`pre-commit` is not on the session PATH.** It lives in the project conda environments; `detect-secrets` was run from `aquacal-freeze01`'s copy, scoped with `--files` throughout. `pre-commit run --all-files` was never run — 143 committed artifacts deliberately lack a final newline and the whitespace hooks would rewrite them.

## Known Stubs

None. The payload is real, the digests were measured in both directions, the draft is real, and the round trip was proved rather than asserted.

The one intentional incompleteness is **Record A's absent `isSourceOf` back-link**, which is not a stub but the recorded, author-accepted consequence of the `sequential` ruling. It has a named owner (the author), exact UI steps, and a carry-forward in plan 29-08.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change was introduced. The plan's threat register was implemented rather than extended:

| Threat | How it was mitigated here |
|---|---|
| T-29-44 publish/tamper | No action endpoint called; `grep -v '^\s*#' scripts/zenodo_upload.py \| grep -c '/actions/'` still returns 0; tool run unmodified; draft measured `unsubmitted` after upload |
| T-29-45 payload source | Reference outputs taken from this run and md5-compared file by file; the archive's superseded copies asserted absent by digest, all six differing |
| T-29-46 superseded record | Supersession statement in both the README and the Zenodo description, each naming 21889922; record 21889922 read once and not modified, deleted or re-versioned |
| T-29-47 the `optimality` column | ROADMAP-mandated labelling sentence in the README covering all three caveats |
| T-29-48 bucket round trip | Local md5 computed before transfer and compared to the server checksum; `size` and `version_id` recorded as corroboration |
| T-29-49 A↔B relationship | Linkage expressed only through the author-ruled mechanism with a real, resolving DOI; zero version relations against 21889922, checked structurally on the array rather than by text grep |
| T-29-50 token disclosure | Environment-only; never a CLI argument; `detect-secrets` passed scoped to both touched files; a direct scan confirms the token appears in no artifact, no log and no committed diff |
| T-29-51 dataset pin | Deliberately untouched; `git diff --quiet -- src/ experiments/` exits 0; transferred to Phase 30 / POST-01 and recorded in plan 29-08 |

## User Setup Required

`ZENODO_TOKEN` was already exported. No new setup.

**Three human actions are outstanding and are deliberately not automatable:**

1. **Review and publish Record B** at **https://zenodo.org/deposit/22117061**. This mints its permanent DOI over exactly the 9,503,394 bytes whose digest is recorded. Blocking checkpoint at plan 29-08.
2. **Then add Record A's back-link by hand** at https://zenodo.org/records/22116461 → Edit → Related identifiers: `isSourceOf` → Record B's minted version DOI, scheme `doi`. Editing published metadata does not cut a new version and does not change the DOI.
3. **Report both DOIs to the manuscript session.** The paper's DOI citation and data-availability wording are that session's edits (D-29-19), not this repository's.

## Next Phase Readiness

**Ready for plan 29-08.** Both drafts now exist as finished, byte-verified artifacts — Record A published at `10.5281/zenodo.22116461`, Record B unpublished at deposition 22117061 — so 29-08's blocking human checkpoint has something real to point at. It should also carry forward the Record A back-link edit as a todo, and the `manifest.json` repoint as Phase 30 / POST-01 work.

**RUN-05 is NOT complete and was not marked complete.** It requires the results package to be **published** before the paper is submitted. Record B is built, uploaded and verified — but unpublished. RUN-05 closes at 29-08 on the author's confirmation. Plan 29-04 had to revert a premature completion of this same requirement; that was not repeated.

**Carried to Phase 30, not blocking.** Repointing `src/aquacal/datasets/data/manifest.json` will need Record B's md5 `f033538e1c9da165aa6267f4ae5d4f78` and size `9503394` alongside Record A's, two-record fetch-and-merge logic, and awareness that **both** archives have flat roots with no `real-rig/` prefix to strip. `loader.py:90`'s search for a non-existent `config.yaml` remains a pre-existing silent no-op, untouched — worth noting that neither record ships a file by that name, so the split does not make it any less of a no-op.

**No blockers.** Nothing irreversible was done by automation: no DOI minted, no record published, no existing record altered, `experiments/` and `src/` untouched, branch still `results/rerun-freeze-02`, nothing pushed.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

All six claimed artifacts exist on disk (`29-zenodo-record-b.txt`, `29-07-SUMMARY.md`,
`scripts/zenodo_metadata_b.json`, `~/zenodo-record-b/README.md`, the zip and its `.md5`
sidecar) and all seven claimed commits are present in git history (`67d0b9b`, `cc08fa5`,
`00db4ac`, `edd9f1b`, `ca3f044`, `37717eb`, `c227048`). The zip's digest and byte size were
freshly recomputed and agree with every figure quoted above. Nothing claimed here is unbacked.
