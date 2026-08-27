---
phase: 21-new-feature-documentation-dataset-refresh
plan: 09
status: complete
completed: 2026-08-11
requirements: [DATA-02]
---

# 21-09: The archive is published — record 21889922, DOI minted

Both blockers from 21-08 were resolved by the user on 2026-08-11 (MF-19 answered by updating
§3 to current-library numbers; `reference_outputs/` fixed by shipping the gate-1 run's own
pair). The zip was rebuilt, all four D-15 gates read **PASS**, and the archive was published
manually through the Zenodo web UI.

## Task 1 — pre-flight

`21-ARCHIVE-MANIFEST.md`'s gate table carries four **PASS** rows, zero FAIL, zero HALT:

| Gate | Description | Status |
|---|---|---|
| 1 | Section 3 reproduction from the archive | PASS (2026-08-11) — archive verified faithful; §3 updated to current-library values per the user's decision |
| 2 | Checksum, size, extraction layout | PASS — re-verified against the 2026-08-11 rebuild |
| 3 | CLI tutorial commands run verbatim | PASS — walkthrough table regenerated from the shipped `diagnostics.json` |
| 4 | Both configs load and validate under v2.0.0 | PASS |

The rebuild superseded the 21-08 bytes. The values that were transcribed are the rebuild's,
and only those:

```
zenodo_filename: real-rig-calib.zip
size_bytes:      4350418046
checksum:        md5:dff1012fb772d627e0f3f106d5c6de84
```

The superseded pre-rebuild pair (`4350417815`, `md5:729f002c132f88e10224146e5b407a57`) was
never uploaded, and the manifest says so explicitly so it cannot be transcribed by mistake.

**Frame spot-check:** performed by the user before publishing, per D-15 and T-21-06-01.
Nothing unintended appears in frame. The specific filenames opened were not written down;
that is the one acceptance item this summary records as satisfied-but-unlogged.

## Task 2 — the manual publish (D-13, D-14)

The user uploaded and published through https://zenodo.org in a browser. **No API token
entered the session or the repository**, no upload script was written, and no `zenodo`
dependency was added (D-14). `git log` for this plan contains no code change at all — the
only tracked edit is the manifest document.

Published as **version 2.0.0** of the existing dataset record via **New version**, not as a
fresh record, so the citation lineage survives (D-13):

| Field | Value |
|---|---|
| New version record id | **21889922** |
| Version DOI | `10.5281/zenodo.21889922` |
| Concept DOI (unchanged) | `10.5281/zenodo.18645384` |
| Previous record (parent) | `18645385` |
| Filename | `real-rig-calib.zip` |

### The 4.35 GB browser upload was not truncated

This was the real risk in a manual upload of this size (T-21-09-02). Checked against the
live API after publish, both values match the pre-upload computation **exactly**:

| Quantity | Pre-upload (local zip) | Zenodo reports |
|---|---:|---:|
| size | 4350418046 | 4350418046 |
| md5 | `dff1012fb772d627e0f3f106d5c6de84` | `dff1012fb772d627e0f3f106d5c6de84` |

`HEAD https://zenodo.org/records/21889922/files/real-rig-calib.zip` returns 200 with a
matching `content-length`. Plan 21-10 then re-proved it the expensive way, by downloading
the whole thing from a cold cache and re-running the md5.

## Deviation — the evidence block is not a `## Published` heading

The plan's acceptance asked for a `## Published` section. The evidence went into
`21-ARCHIVE-MANIFEST.md` as a bolded **PUBLISHED 2026-08-11** block directly under the
transcription values instead, alongside the `zenodo_record_id`, `zenodo_version_doi` and
`zenodo_concept_doi` lines it describes. Every required fact is present — record id, both
DOIs, the publication date, the size/md5 confirmation, and the D-14 statement — but the
plan's literal `'## Published' in m` assertion would not fire. Substance satisfied, heading
form differs; recorded rather than silently retro-fitted.

## Release status — read this before assuming anything shipped

Two things carry the name "2.0.0" and they are different objects:

- **Zenodo dataset version 2.0.0** = record 21889922. Published, DOI minted, publicly
  downloadable. This is what plans 21-10 and 21-11 depend on, and it is done.
- **The AquaCal Python package.** `v2.0.0` and `v2.0.1` were cut by python-semantic-release
  off this work and the tags are pushed, but **PyPI publication of v2.0.1 is still pending a
  manual approval gate** (`Publish to PyPI` workflow run `31543691065`, state `waiting`) that
  the user will action separately. `v2.0.0` can never reach PyPI: `publish.yml` gates the
  build on a test job that failed on the Linux runner, so the fix had to ride a new tag
  (`eea0a83`). **Nothing is on PyPI yet.**

## What this unblocked

DATA-02 could not be closed against a Zenodo draft — a draft is not publicly downloadable,
which is the entire reason D-15 front-loaded four gates before the irreversible step. With
the DOI minted, plan 21-10 could point `manifest.json` at a live record and plan 21-11 could
finally remove the repository copies that were, until this moment, the only copies.

## Self-Check: PASSED

- `21-ARCHIVE-MANIFEST.md:21-23` carries `zenodo_record_id: 21889922`, the version DOI and the
  concept DOI; the record id is not `18645385`
- Four PASS rows, zero FAIL, zero HALT in the gates table
- Zenodo's reported size and md5 equal the pre-upload values digit for digit
- No credential, token or upload script anywhere in the diff for this plan
