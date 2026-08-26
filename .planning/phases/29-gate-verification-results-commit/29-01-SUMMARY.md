---
phase: 29-gate-verification-results-commit
plan: 01
subsystem: infra
tags: [zenodo, rest-api, requests, tqdm, md5, doi, data-publication, secrets]

requires:
  - phase: 28-full-suite-production-run
    provides: the completed production run whose outputs become Record B's payload
  - phase: 29-gate-verification-results-commit
    provides: "29-05's committed 227-file results tree, which Record B ships the gitignored half of"
provides:
  - "scripts/zenodo_upload.py — creates an UNPUBLISHED Zenodo draft, streams a file into its bucket URL, and verifies the round trip by md5. Cannot publish, cannot discard, cannot reserve a DOI."
  - "scripts/zenodo_metadata_a.json / _b.json — the author-reviewable metadata blocks for both records, with __RECORD_A_URL__ / __RECORD_B_URL__ placeholders for the cross-link"
  - "29-RECORD-COMPOSITION.md — the authorised Record A / Record B payload split (Task 1, option research-default)"
  - "29-zenodo-sandbox-rehearsal.txt — the D-29-06 sandbox transcript plus the author's dated approval, which plan 29-04 Task 2 asserts before its first production call"
  - "Measured evidence that production zenodo.org was unreachable on 2026-08-26"
affects: [29-04, 29-07, 29-08]

actuals:
  tokens: 17525
  tasks: 4
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Streaming PUT with reopen-per-attempt retry and md5 round-trip verification"
    - "Credential read from the environment only, scrubbed from every log line and re-raised error"
    - "Required mutually-exclusive host selector with no default on either arm"

key-files:
  created:
    - scripts/zenodo_upload.py
    - scripts/zenodo_metadata_a.json
    - scripts/zenodo_metadata_b.json
    - .planning/phases/29-gate-verification-results-commit/29-RECORD-COMPOSITION.md
    - .planning/phases/29-gate-verification-results-commit/29-zenodo-sandbox-rehearsal.txt
  modified: []

key-decisions:
  - "Record A = extrinsic/ + intrinsic/ + README.md (~4.1 GB); Record B = both configs + reference_calibration.json + this run's reference_outputs/ + run_manifest.json (~21 MB). Option research-default, ruled by the author."
  - "No publish and no discard code path exists in the tool at all — enforced by grep gates, and independently by a deposit:write-only token."
  - "A/B cross-link uses isSourceOf (A) / isDerivedFrom (B), never isNewVersionOf; supersession of 21889922 is prose in the descriptions plus a `references` related_identifier on B."
  - "Metadata lives in JSON files rather than dict literals in the script, because those files are the D-29-02 author review surface."
  - "detect-secrets' false positive on the payload md5 was annotated inline with `pragma: allowlist secret` rather than by widening .secrets.baseline or the hook's exclude."

patterns-established:
  - "Placeholder-then-substitute for cross-record identifiers: the committed metadata carries literal __RECORD_A_URL__ / __RECORD_B_URL__ because no DOI exists until Publish (D-29-03), and substitution happens at deposit time."
  - "Evidence transcripts append machine-written JSON records under hand-written prose section headers, so a reader gets both the raw response and why it was made."

requirements-completed: []

coverage:
  - id: D1
    description: "scripts/zenodo_upload.py creates an unpublished draft, uploads to links.bucket, and verifies the server md5 against a local digest"
    requirement: RUN-05
    verification:
      - kind: e2e
        ref: "python scripts/zenodo_upload.py --sandbox ... (4 live sandbox calls; transcript in 29-zenodo-sandbox-rehearsal.txt)"
        status: pass
      - kind: other
        ref: "ruff check scripts/zenodo_upload.py && ruff format --check scripts/zenodo_upload.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "The tool has no publish path, no discard path, no DOI reservation, and no command-line credential surface"
    requirement: RUN-05
    verification:
      - kind: other
        ref: "grep -v '^\\s*#' scripts/zenodo_upload.py | grep -c '/actions/' -> 0; same for 'prereserve' -> 0; '\"--token\"|.--access.token.' -> 0; 'os.environ' -> 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both sandbox drafts render correctly in the Zenodo web UI (D-29-06 confirmation)"
    requirement: RUN-05
    verification:
      - kind: manual_procedural
        ref: "author opened sandbox drafts 592888 and 592890; verdict recorded verbatim in 29-zenodo-sandbox-rehearsal.txt § 3"
        status: pass
    human_judgment: true
    rationale: "D-29-06 exists precisely because rendered metadata is a judgement call — title, creator, license and description prose are publication-facing and no assertion can stand in for the author reading them."
  - id: D4
    description: "The Record A / Record B payload split is ruled and written where plan 29-04 can read it"
    requirement: RUN-05
    verification:
      - kind: manual_procedural
        ref: "29-RECORD-COMPOSITION.md — author selected option research-default"
        status: pass
    human_judgment: true
    rationale: "One-way: Record A is immutable once published. A missing input is fixable only by cutting a new version, which breaks the citation the record exists to make."

duration: 104min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 01: Zenodo Upload Tooling and Sandbox Rehearsal Summary

**A publish-incapable Zenodo deposit tool that streams to `links.bucket` and proves arrival by md5, plus the full A/B record split driven end to end on sandbox and approved by the author — with production zenodo.org measured unreachable on the same day.**

## Performance

- **Duration:** 104 min
- **Started:** 2026-08-26T15:18:59Z
- **Completed:** 2026-08-26T17:02:32Z
- **Tasks:** 4
- **Files modified:** 5 created, 0 pre-existing files changed

## Accomplishments

- **The phase's tracer is proven.** The Zenodo write path had no analog anywhere in this repository — `src/aquacal/datasets/download.py` is read-only, unauthenticated and public-URL. It now has a production-quality implementation that has been driven end to end against a live instance.
- **The full A/B split works, not just one call.** Four live sandbox calls exercised create-draft, bucket PUT, create-draft, and update-metadata: draft 592888 (Record A, carrying the dummy file), draft 592890 (Record B, metadata-only), cross-linked `isSourceOf` / `isDerivedFrom`, both `unsubmitted`. Zenodo echoed every metadata field back unchanged.
- **The md5 round trip verified.** Local `md5:534db625b3b9e3ffa6d615abfb4772d3` equalled the server's returned `checksum` exactly. That symmetry is free because Zenodo returns the same `algorithm:hash` shape `download.py` already parses.
- **The one-way risk is structurally closed twice over.** The tool contains no publish and no discard code path at all — not dead code, not commented scaffolding — and the token carries `deposit:write` without the publish-actions scope, so a publish call would fail at Zenodo rather than at code review.
- **The payload split is ruled and written down**, so plan 29-04 has an authorised byte list before it starts a 4.35 GB transfer.
- **Production Zenodo was measured down**, which is a finding 29-04 needs and would otherwise have had to re-diagnose mid-transfer.

## Task Commits

1. **Task 1: Rule on what goes into Record A and Record B** — `a96da07` (docs, checkpoint:decision)
2. **Task 2: Mint the two Zenodo access tokens** — `75a33cb` (docs, checkpoint:human-action)
3. **Task 3: TRACER — one draft, one file, one round trip, both records, on sandbox** — `240ed00` (feat)
4. **Task 4: Author confirms both sandbox drafts render correctly** — `0b56022` (docs, checkpoint:human-verify)

## Files Created/Modified

- `scripts/zenodo_upload.py` — the deposit tool. `build_arg_parser()` / `main(argv) -> int`, `resolve_token()`, `load_metadata()`, `md5_of()`, `create_draft()`, `update_metadata()`, `put_file()`, `scrub_headers()`.
- `scripts/zenodo_metadata_a.json` — Record A's metadata: inputs-only description, `isSourceOf` link to B, version `1.0.0`.
- `scripts/zenodo_metadata_b.json` — Record B's metadata: supersession notice naming `21889922`, `isDerivedFrom` link to A, `references` the superseded DOI.
- `.planning/phases/29-gate-verification-results-commit/29-RECORD-COMPOSITION.md` — the authorised payload split (Task 1).
- `.planning/phases/29-gate-verification-results-commit/29-zenodo-sandbox-rehearsal.txt` — credential gate record, rehearsal transcript, author verdict, three findings.

## Decisions Made

- **Record A gets `intrinsic/` and `README.md` on top of `extrinsic/`** (~4.1 GB, up from 3.6 GB), because a record whose citation reads "these are the frames the run consumed" has to be a complete input set. `reference_calibration.json` is a *result* used as a comparison target, so it travels with Record B.
- **Both metadata blocks live in JSON files, not in the script.** That is the D-29-02 review surface: the author corrects what will be deposited without reading Python.
- **Cross-record identifiers are literal placeholders in the committed files.** No DOI exists until Publish (D-29-03) and A must be created before B exists, so `__RECORD_A_URL__` / `__RECORD_B_URL__` are substituted at deposit time. Plan 29-07 does the same substitution with real minted DOIs.
- **`isNewVersionOf` was deliberately not used against `21889922`.** Zenodo's versioning is a first-class mechanism; asserting it in `related_identifiers` against a different concept record misrepresents the relationship. Supersession is prose in the description plus a `references` identifier on B.
- **License `cc-by-4.0`, affiliation "Georgia Institute of Technology", no ORCID.** All three were surfaced explicitly at the Task 4 checkpoint rather than chosen silently; the author approved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `put_file()` gained an optional `expected_md5` parameter**
- **Found during:** Task 3 (writing the tool)
- **Issue:** The plan's signature `put_file(bucket_url, token, path, name, max_retries, read_timeout)` computes the local digest internally. `main()` also needs that digest for the evidence record, so the plan's exact signature forces two full reads of the file — on 29-04's 4.35 GB payload that is a wasted multi-gigabyte pass on the phase's critical path.
- **Fix:** Added a keyword parameter `expected_md5: str | None = None`, computed once in `main()` and passed through. The specified signature remains a valid call; omitting the argument still self-computes.
- **Files modified:** `scripts/zenodo_upload.py`
- **Verification:** `ruff check` / `ruff format --check` clean; the live sandbox PUT verified the round trip with the passed digest.
- **Committed in:** `240ed00`

**2. [Rule 3 - Blocking] `detect-secrets` false positive on the payload md5**
- **Found during:** Task 3 (pre-commit verification)
- **Issue:** The `HexHighEntropyString` plugin flagged the dummy payload's md5 in the rehearsal transcript. Zenodo's deposition response repeats each file's digest as a **bare** 32-hex string, whereas the bucket PUT response uses the prefixed `md5:` form the plugin ignores. The flagged value is the round-trip evidence itself. The hook would have blocked the commit.
- **Fix:** Annotated the two affected transcript lines with detect-secrets' own inline `# pragma: allowlist secret` marker and added a paragraph to the transcript explaining why it is there. Chose this over widening `.secrets.baseline` or the hook's `exclude` pattern: a false positive gets annotated where a reader can see the reasoning, and the repository's secret-scanning tripwire stays exactly as strict as it was.
- **Files modified:** `.planning/phases/29-gate-verification-results-commit/29-zenodo-sandbox-rehearsal.txt`
- **Verification:** `pre-commit run detect-secrets --files ...` passes, scoped (never `--all-files`). `.secrets.baseline`, `.pre-commit-config.yaml` and `.gitignore` are untouched — confirmed by `git status --porcelain`.
- **Committed in:** `240ed00`

**3. [Rule 1 - Bug] Record B's `references` identifier was a URL under the `doi` scheme**
- **Found during:** Task 4 (author checkpoint)
- **Issue:** `scripts/zenodo_metadata_b.json` supplied `https://doi.org/10.5281/zenodo.21889922` with `"scheme": "doi"`. Zenodo's `doi` scheme expects a bare DOI. Sandbox accepted the URL and silently normalised it, so the rehearsal alone would not have caught this — a permanent published record should not depend on that normalisation.
- **Fix:** Changed the identifier to `10.5281/zenodo.21889922`. The `<a href="https://doi.org/...">` links inside the description prose are correct as URLs and were deliberately left unchanged.
- **Files modified:** `scripts/zenodo_metadata_b.json`
- **Verification:** JSON parses; the prose href is intact (grep). The rehearsal was **not** re-run: the author had already approved and production was unreachable. Plan 29-07 uses the corrected file.
- **Committed in:** `0b56022`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 1 blocking, 1 bug)
**Impact on plan:** No scope creep. One is a signature widening on the phase's critical path, one keeps a security control from being loosened, one corrects a metadata field before it becomes permanent.

## Issues Encountered

**Production zenodo.org is down or severely degraded (measured 2026-08-26).** All six `zenodo.org` A records complete a TLS handshake with a valid certificate and then the backend stalls ~25 s or never answers. `sandbox.zenodo.org` returns HTTP 200 in ~0.6 s; `github.com` in 0.16 s; `doi.org/10.5281/zenodo.21889922` resolves correctly (302) and then dies at Zenodo's end. Not the local network, not DNS, not IPv6, not a firewall, and not a bad record id — `21889922` is pinned identically in five places in this repository.

This is why the sandbox rehearsal is the only end-to-end evidence at the close of this plan. It also makes the D-29-06 rehearsal look better than it did when it was planned: the shape got proven on the instance that *was* reachable. Written up in the transcript so 29-04 does not re-diagnose it.

**A sandbox quirk that reads as a red flag and is not.** The sandbox server volunteers an unrequested `metadata.prereserve_doi` reading `10.5281/zenodo.592888` — the *production* prefix, not the `10.5072` test prefix the docs describe. The tool never asks for a reserved DOI, both drafts' actual `doi` is null, and both are `unsubmitted`. Documented in the transcript so the same alarm is not raised twice.

## User Setup Required

Both Zenodo access tokens are already exported in the working shell (`ZENODO_SANDBOX_TOKEN`, `ZENODO_TOKEN`), each `deposit:write`-only and neither written to disk. No further setup for 29-04 beyond production becoming reachable.

## Known Stubs

None. `scripts/zenodo_upload.py` is production code that plans 29-04 and 29-07 run unchanged against production; it has no stubbed function, no mocked response, and no placeholder branch.

The two metadata files contain deliberate literal placeholders — `__RECORD_A_URL__` in `zenodo_metadata_b.json` and `__RECORD_B_URL__` in `zenodo_metadata_a.json`. These are **not** stubs. No DOI exists until the author publishes (D-29-03) and Record A must be created before Record B exists, so the cross-link identifier cannot be a literal at rest. Substitution happens at deposit time; plan 29-07 performs it with the minted DOIs.

## Next Phase Readiness

**Ready for 29-04 (Record A production upload):**
- The payload list is authorised in `29-RECORD-COMPOSITION.md`.
- The author's D-29-06 verdict is on disk, which is what 29-04 Task 2 asserts.
- The tool and Record A's metadata are committed and rehearsed.

**Blocking 29-04:** production `zenodo.org` was unreachable at the close of this plan. **29-04 must re-probe reachability before starting the transfer** — beginning a multi-hour PUT against a degraded backend is how a transfer dies at 90%.

**Blocking 29-07 (Record B) — an open decision that is the author's, not made here:** `zenodo_metadata_b.json` carries `version: "2.0.1"`, taken from the run manifest's `aquacal_version_declared`. That is measurably misleading. `run_manifest.json` records `git_describe: v2.0.1-346-g7005a27` — the run sha is 346 commits past the `v2.0.1` tag, and 14 files in the packaged library `src/aquacal/` changed across that span (+1663/−67), including `_optim_common.py`, `interface_estimation.py`, `refinement.py`, `pipeline.py` and `refractive_geometry.py`. So `2.0.1` names an installable release that does **not** reproduce this record's numbers — exactly the class of discrepancy Record B's supersession notice exists to prevent. `src/` is byte-identical between `7005a277` and current HEAD, so a release cut now would legitimately describe the code that ran. The author is deciding between cutting `v2.1.0` and alternatives. **The field is left untouched pending that ruling; 29-07 must not create Record B's production draft until it is made.** Record A's `1.0.0` is unaffected — it is a dataset version, independent of the software release.

**Carried, not decided (unchanged from the plan):** `manifest.json`'s pinned `zenodo_record_id` describes one record and the split makes it describe two; the promote-vs-add-alongside ruling and its ten affected sites remain plan 29-08's. RUN-05's "published before the paper is submitted" half is closed by explicit human confirmation in 29-08, not asserted here.

## Self-Check: PASSED

- Files: all 5 created files FOUND on disk.
- Commits: `a96da07`, `75a33cb`, `240ed00`, `0b56022` all FOUND in `git log`.
- Branch is `results/rerun-freeze-02`; `git status --porcelain experiments/` is empty.
- `ruff check scripts/` and `ruff format --check scripts/` exit 0.
- `pre-commit run detect-secrets --files ...` passes, scoped.
- `tests/unit/test_experiments_provenance.py` unchanged at 8 failed, 279 passed, 20 skipped (the documented D1 flip, 29-06's job).
- No Zenodo credential in any committed file, log, command line, or this summary.
- No production Zenodo call was made by this plan.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*
