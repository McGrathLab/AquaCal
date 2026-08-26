---
phase: 29-gate-verification-results-commit
plan: 04
subsystem: data-publication
tags: [zenodo, rest-api, dataset, archive, md5, doi, reproducibility]

# Dependency graph
requires:
  - phase: 29-01
    provides: "scripts/zenodo_upload.py (built and sandbox-rehearsed), scripts/zenodo_metadata_a.json, the author's D-29-06 rehearsal verdict, and 29-RECORD-COMPOSITION.md's `research-default` payload ruling"
provides:
  - "Record A's input-only archive at ~/zenodo-record-a/real-rig-inputs.zip — 4,341,018,405 bytes, md5 d95a1abc3f7089443ea2bc7ea12fb599, built to the ruled composition"
  - "Zenodo PRODUCTION deposition 22116461, an UNPUBLISHED draft holding that archive under the key real-rig-inputs.zip"
  - "Byte-level round-trip proof: the server-returned checksum and size equal the local digest and length of the exact bytes uploaded"
  - "29-zenodo-record-a.txt — the repository's only handle on the service-side draft (id, links.bucket, links.html) plus the full bucket response JSON"
  - "A recorded, deliberate difference from record 21889922: Record A's archive has no `real-rig/` wrapper directory, which Phase 30's loader work must account for"
affects: [29-07, 29-08, phase-30-dataset-pin, RUN-05]

actuals:
  tokens: 7991
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Detached multi-gigabyte transfer under nohup with a log-only progress channel; the transfer is never interrupted to inspect it"
    - "Two-call deposit shape: create the draft and commit its id/bucket/html to git BEFORE a payload byte moves, then upload against --deposition-id"
    - "Deposit-time placeholder substitution — the committed metadata keeps literal __RECORD_B_URL__; only the ephemeral deposited copy is substituted"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-zenodo-record-a.txt
  modified: []

key-decisions:
  - "Record A's archive root is flat (extrinsic/, intrinsic/, README.md) with no `real-rig/` wrapper, unlike published record 21889922 — required by the composition ruling's relative paths and this plan's acceptance criterion, and recorded as an explicit Phase 30 consequence"
  - "ZIP_STORED rather than deflate: the payload is 3,967 already-compressed PNGs, so compression would cost minutes and save nothing"
  - "The deposited metadata copy drops the not-yet-existing Record B related_identifier and replaces the description's __RECORD_B_URL__ placeholder — exactly the substitution the author approved on sandbox; scripts/zenodo_metadata_a.json stays unmodified because plan 29-07 Task 1 rules on the final linkage"

patterns-established:
  - "Record the service-side handle before the irreversible-cost operation: a deposit:write-only token cannot discard, so an unrecorded draft id is an unfindable draft"
  - "Prove arrival, never assume it: a transfer that completed without a matching digest is a failed transfer"
  - "Write self-referential assertions so they cannot match themselves — quoting a forbidden literal inside the check that forbids it makes the check always fail"

requirements-completed: []

coverage:
  - id: D1
    description: "Record A's input-only archive, built from the extracted cache to exactly the `research-default` ruling and no further"
    requirement: "RUN-05"
    verification:
      - kind: automated_ui
        ref: "python zipfile listing of ~/zenodo-record-a/real-rig-inputs.zip — top level == ['README.md','extrinsic','intrinsic'], 3996 entries, 0 containing 'reference_outputs', 0 Record B members"
        status: pass
      - kind: integration
        ref: "md5sum ~/zenodo-record-a/real-rig-inputs.zip == sidecar .md5 == d95a1abc3f7089443ea2bc7ea12fb599"
        status: pass
    human_judgment: false
  - id: D2
    description: "The 4.34 GB payload reached Zenodo production intact and is addressable in an unpublished draft"
    requirement: "RUN-05"
    verification:
      - kind: integration
        ref: "bucket PUT response checksum md5:d95a1abc3f7089443ea2bc7ea12fb599 == local digest; size 4341018405 == local size; round_trip_verified true"
        status: pass
      - kind: integration
        ref: "GET https://zenodo.org/api/deposit/depositions/22116461 — state unsubmitted, submitted false, doi null, doi_url null, conceptdoi null, 1 file"
        status: pass
    human_judgment: false
  - id: D3
    description: "The draft's metadata, description and file set are correct for a permanent scholarly record"
    verification: []
    human_judgment: true
    rationale: "Whether the title, description prose, licence, creators and the absence of a Record B cross-link are right for a record the paper will cite is a publication-facing editorial judgement. Publish is the author's act under D-29-01 and reaches its blocking checkpoint at plan 29-08 Task 4."

# Metrics
duration: 48min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 04: Record A — Build and Production Draft Summary

**Record A's 4.34 GB input-only archive is built to the ruled composition, streamed into Zenodo production deposition 22116461 on the first attempt with a matching md5 round trip, and left sitting as an unpublished draft for the author to press Publish on.**

## Performance

- **Duration:** ~48 min (dominated by a ~28 min transfer)
- **Started:** 2026-08-26T18:00Z (approx.)
- **Completed:** 2026-08-26T18:48Z
- **Tasks:** 2 of 2
- **Files modified:** 1 tracked file created (plus two untracked build artifacts outside the repository)

## Accomplishments

- **Built Record A's archive input-only, from the cache, to exactly the ruling.** `~/zenodo-record-a/real-rig-inputs.zip`, 4,341,018,405 bytes, md5 `d95a1abc3f7089443ea2bc7ea12fb599`, 3,996 entries. Top-level member set is `['README.md', 'extrinsic', 'intrinsic']` — identical to `29-RECORD-COMPOSITION.md`'s `research-default` list, with nothing added. The published `real-rig-calib.zip` was *not* reused; it is the 4,350,418,046-byte bundle that mixes inputs and outputs, and that mixing is the defect RUN-05 exists to repair. It remains byte-for-byte unmodified.
- **Proved the payload carries no results.** Zero entries contain `reference_outputs`; zero `config_paper.yaml`, `config_quickstart_not_paper.yaml` or `reference_calibration.json` entries; the only root-level file is `README.md`. Those four are Record B's members under the same ruling.
- **Re-probed production before committing to the transfer.** Plan 29-01 Finding 1 measured production Zenodo as down or severely degraded on the same day. Three fresh `GET /api/records/21889922` samples returned HTTP 200 in 0.45 s / 0.51 s / 0.50 s — recovered — and only then did the first production call go out.
- **Recorded the draft's handles before a payload byte moved.** Deposition `22116461`, `links.bucket` `.../files/66ec592f-a5a0-4b1d-a3a7-f826fdbc6aa9`, `links.html` `https://zenodo.org/deposit/22116461` were captured from the create response and committed to git in their own commit. The automation token is `deposit:write`-only and deliberately cannot discard, so an unrecorded id would have been an unfindable draft.
- **Transferred 4.34 GB detached, first attempt, zero retries.** ~28 minutes under `nohup` at 0.6–4.7 MB/s, with the progress bar going to a log rather than the session, so a dropped connection could not have killed it. The log was read; the transfer was never interrupted to check on it.
- **Proved arrival at the byte level.** Server-returned `checksum` `md5:d95a1abc3f7089443ea2bc7ea12fb599` equals the local digest of the exact bytes uploaded, and server `size` 4341018405 equals the local length. Full bucket response JSON — `key`, `size`, `checksum`, `version_id` `e8f8d567-9428-4896-94c0-b85b1625ef20` — is in the evidence file.
- **Asserted the draft is unpublished with measured values.** A read-only re-read at 18:43:09Z returned `state: "unsubmitted"`, `submitted: false`, `doi: null`, `doi_url: null`, `conceptdoi: null`, `links.record: null`, and exactly one file. Nothing irreversible happened.

## Task Commits

1. **Task 1: Build Record A's input archive from the extracted cache** — `f15f1ba` (docs)
2. **Task 2 step 1: Create the production draft and record its handles** — `b71ffe5` (docs)
3. **Task 2 steps 2–5: Stream the archive and prove the round trip** — `b6bec8d` (feat)

**Plan metadata:** see the final commit on this plan.

## Files Created/Modified

- `.planning/phases/29-gate-verification-results-commit/29-zenodo-record-a.txt` — created. The evidence transcript: precondition gates, the reachability re-probe, the archive's identity and audited composition, the draft's id/bucket/html, the transfer record, the md5 round-trip proof, the unpublished assertion, and both verbatim tool-appended JSON records plus the read-only re-read.
- `~/zenodo-record-a/real-rig-inputs.zip` — created, **outside the repository, deliberately untracked**. It is a multi-gigabyte upload artifact, not a repo artifact; its path, size and digest are recorded instead.
- `~/zenodo-record-a/real-rig-inputs.zip.md5` — created, outside the repository. Sidecar digest in `md5sum` format.
- Zenodo production deposition 22116461 — new service-side state, unpublished.

Nothing tracked was modified. `git status --porcelain experiments/ src/ aquacal_data/` is empty.

## Decisions Made

**1. Record A's archive root is flat — no `real-rig/` wrapper.** The published archive wraps everything in a top-level `real-rig/` directory, which is why extracting it into `aquacal_data/real-rig/` yields the doubled `aquacal_data/real-rig/real-rig/`. Record A's archive puts `extrinsic/`, `intrinsic/` and `README.md` at the root instead. Two reasons: the composition ruling states its paths relative to `aquacal_data/real-rig/real-rig/`, and this plan's acceptance criterion requires the top-level member set to *equal* the ruled list. The plan's other phrasing ("preserve the relative directory layout under the archive root so a consumer unzips the same tree the loader expects") could be read as arguing for the wrapper, so the tension was resolved explicitly rather than silently: the flat root satisfies the checkable criterion, and the difference is recorded in the evidence file under its own heading with the Phase 30 consequence spelled out. That consequence is not new work — `29-RECORD-COMPOSITION.md`'s carried-forward item 1 already records that splitting one record into two forces `load_example('real-rig')` to fetch two records and merge them into one cache layout. New extraction logic is required under any split; the flat root only fixes which prefix that logic strips.

**2. ZIP_STORED, not deflate.** The payload is 3,967 PNGs, already compressed. Storing them made the build take 5 seconds instead of many minutes and cost nothing in size.

**3. Deposit-time metadata substitution, committed file untouched.** `scripts/zenodo_metadata_a.json` carries a literal `__RECORD_B_URL__` because Record B does not exist yet and D-29-03 forbids reserving a DOI. The deposited copy — written to a scratchpad, never to the repository — drops that `related_identifier` (2 → 1 entries, leaving only the GitHub `isSupplementTo`) and replaces the placeholder in the description prose with "(linked below once Record B exists)". This is byte-for-byte the substitution the author reviewed and approved on sandbox at plan 29-01 Task 3 step 1, so it is the rehearsed shape rather than an improvisation. The committed metadata file stays as-is because plan 29-07 Task 1 is the checkpoint that rules on the final A↔B linkage.

## Deviations from Plan

None — plan executed as written. Two clarifications resolved inside the plan's own authority (neither adds nor removes a byte from the record):

- The archive-root question above, resolved toward the explicit acceptance criterion and documented.
- The plan's Task 2 acceptance criterion requires `grep -c 'sandbox.zenodo.org' 29-zenodo-record-a.txt` to return `0`, and an early draft of the evidence file quoted that command verbatim in its prohibitions list — which made the assertion match itself and fail. The line was rewritten to describe the check rather than quote the forbidden literal. The underlying fact was always true: every URL in the transcript is on the production host.

### State-update correction (Rule 1 — bug)

**RUN-05 was NOT marked complete, despite this plan's `requirements: [RUN-05]` frontmatter.**
The standard state update marked it `[x]` / `Complete` in `REQUIREMENTS.md`; that edit was
reverted on inspection, because it would have been a false claim. RUN-05 reads: *"The Zenodo
record is split into immutable inputs and a versioned results package, and the results package
matching this run's numbers is **published** before the paper is submitted."* This plan built and
uploaded the **inputs half only**, and published nothing. RUN-05 is shared by plans 29-01, 29-04,
29-07 and 29-08; it is 29-08's to close, after Record B exists and the author has published both.
`REQUIREMENTS.md` is unchanged by this plan and RUN-05 remains `Pending`.

## Issues Encountered

**Production Zenodo's earlier outage.** Plan 29-01 closed with production unreachable, which is why its sandbox rehearsal was the only end-to-end evidence available. Rather than trusting the orchestrator's earlier probe, reachability was re-measured immediately before the first production call (3 × HTTP 200, ~0.5 s) and the result recorded as a gate in the evidence file. Production had recovered and stayed healthy for the full 28-minute transfer.

**Transfer throughput varied by roughly 8×** (0.6–4.7 MB/s) over the 28 minutes. No retries fired, no timeout was approached (the read timeout is 3600 s), and the round trip matched. Nothing to fix; recorded because a future transfer at the low end of that range would take ~2 hours and should be budgeted accordingly.

## Known Stubs

None. The archive is real, the draft is real, and the round trip was measured, not asserted.

The one intentional incompleteness is the **absent A→B cross-link** on the draft's `related_identifiers`. That is not a stub: no DOI exists until Publish (D-29-03) and Record B does not exist yet. Plan 29-07 Task 1 is the blocking checkpoint that rules on the linkage, and it reads this plan's evidence file to do so.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change was introduced. The plan's threat register was implemented rather than extended:

| Threat | How it was mitigated here |
|---|---|
| T-29-22 publish/tamper | No action endpoint called; `grep -v '^\s*#' scripts/zenodo_upload.py \| grep -c '/actions/'` still returns 0; tool unmodified |
| T-29-23 truncated transfer | Local md5 computed before transfer, compared to the server checksum; size and `version_id` recorded as corroboration |
| T-29-24 payload composition | Built only from the ruling; zero `reference_outputs` entries asserted by listing the archive |
| T-29-25 token disclosure | Token read from the environment by the tool alone; a scan confirms it appears in neither the evidence file nor either log; never a CLI argument |
| T-29-26 wrong host | `--base-url https://zenodo.org/api` given explicitly; zero sandbox-host references in the transcript |
| T-29-27 self-inflicted DoS | Detached under `nohup`; bounded read timeout; bounded retries (0 fired) |
| T-29-28 record 21889922 | Read once for the reachability probe; still 4,350,418,046 bytes, not modified, deleted, re-versioned or withdrawn |
| T-29-29 supply chain | No package installed; `requests` and `tqdm` were already runtime dependencies |

## User Setup Required

`ZENODO_TOKEN` was already exported (minted in plan 29-01 Task 2, `deposit:write` scope only). No new setup.

**One human action is outstanding and is deliberately not automatable:** the author must review the draft at **https://zenodo.org/deposit/22116461** and press **Publish** there. That mints Record A's permanent DOI over exactly these 4,341,018,405 bytes. Nothing in this repository can do it — the token carries no publish scope — and the act reaches its blocking checkpoint at plan 29-08 Task 4.

## Next Phase Readiness

**Ready for plan 29-07.** Its Task 1 checkpoint needs Record A's draft id, its web URL and whether the round trip passed, in order to present the `sequential` / `prose-only` linkage options to the author. All three are in `29-zenodo-record-a.txt`: `22116461`, `https://zenodo.org/deposit/22116461`, round trip **passed**. If the author picks `sequential`, Record A is publishable immediately — its payload is final and audited.

**Ready for plan 29-08.** The draft is complete and unpublished; Task 4's blocking human checkpoint has something real to point at.

**Carried to Phase 30, not blocking.** Repointing `src/aquacal/datasets/data/manifest.json` remains explicitly deferred. When it happens it will need (a) Record A's md5 `d95a1abc3f7089443ea2bc7ea12fb599` and size `4341018405`, both recorded verbatim, (b) two-record fetch-and-merge logic, and (c) awareness that Record A's archive has no `real-rig/` prefix to strip. `loader.py:90`'s search for a non-existent `config.yaml` remains a pre-existing silent no-op, untouched.

**No blockers.** Nothing irreversible happened: no DOI minted, no existing record altered, `experiments/` untouched, branch still `results/rerun-freeze-02`.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

All four artifacts exist on disk (`29-zenodo-record-a.txt`, `29-04-SUMMARY.md`,
`~/zenodo-record-a/real-rig-inputs.zip`, `~/zenodo-record-a/real-rig-inputs.zip.md5`)
and all four commits are present in git history (`f15f1ba`, `b71ffe5`, `b6bec8d`,
`886bbda`). Nothing claimed above is unbacked.
