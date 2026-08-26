---
created: 2026-08-26T00:00:00.000Z
title: Legacy Zenodo deposit API deprecation posture — `scripts/zenodo_upload.py` builds on an API that is documented and working but informally discouraged for new integrations
area: infra
resolves_phase: 30
files:
  - scripts/zenodo_upload.py
---

## Confidence

**MEDIUM — community sourcing, not an official Zenodo statement.** Recorded so that a future
re-upload does not rediscover it under time pressure. **This is not a defect and nothing is broken
today.**

## What was measured (2026-08-26, during Phase 29 research)

- **`developers.zenodo.org` carries NO deprecation banner for the deposit API.** [VERIFIED — fetched
  that session.] It documents the Deposit / Records / Files APIs as current.
- It is what Zenodo documents, and what Zenodo's own maintainer's reference upload gist uses.
- Zenodo migrated its backend to **InvenioRDM**, whose native draft API
  (`/api/records/{id}/draft`) exists **alongside** the legacy deposit API.
- Community reporting says the legacy deposit API *"remains functional"* but that *"new integrations
  should not rely on the feature being available in the future."* [ASSUMED — community sources; no
  official Zenodo statement was found.]

## Why Phase 29 built on the legacy API anyway

D-29-07 already specified it, and three things favour it for a two-record link job:

1. It is the documented surface, and the one whose **bucket semantics are stable**.
2. InvenioRDM's `PUT /api/records/{id}/draft` **replaces the whole draft resource including
   metadata** — a sharper edge when a record's `related_identifiers` must be edited in place to
   express an A↔B link.
3. The whole path was rehearsed end to end on `sandbox.zenodo.org` before a production byte moved
   (D-29-06), so the shape is proven against a live instance.

`scripts/zenodo_upload.py` ran unchanged against production for both records, first attempt, zero
retries, with matching md5 round trips on 4,341,018,405 and 9,503,394 bytes.

## The risk, stated exactly

**The only risk is that a future re-upload needs rework.** Nothing that has already been published
depends on the API staying available: a published record is served by Zenodo's public records API
and by DOI resolution, neither of which is in question.

## What would resolve this

Re-target `scripts/zenodo_upload.py` at InvenioRDM's `/api/records/{id}/draft` **when a re-upload is
actually needed**, not before — and re-rehearse on `sandbox.zenodo.org` first, because the draft
resource's replace-whole-document semantics differ from the deposit API's merge semantics and that
difference is exactly where a metadata field gets silently dropped.

Do **not** rebuild on it speculatively. The current tool is proven against production on two live
records; replacing proven code with unproven code to pre-empt a deprecation that has not been
announced trades a measured asset for an assumed one.

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-RESEARCH.md` § *Zenodo REST API
  (RUN-05)* → *Which API surface is live*; § *State of the Art*; Assumptions Log row **A1**
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Open items handed
  forward*, item 8
- `.planning/phases/29-gate-verification-results-commit/29-zenodo-sandbox-rehearsal.txt` — the
  rehearsal that proved the legacy shape end to end
