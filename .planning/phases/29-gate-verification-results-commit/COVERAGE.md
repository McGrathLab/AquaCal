# API Coverage — Zenodo legacy Deposit API (`https://zenodo.org/api`)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> Surface enumerated from `developers.zenodo.org` as fetched and recorded in
> `29-RESEARCH.md` § *Zenodo REST API*. This phase builds `scripts/zenodo_upload.py`
> against that surface (D-29-07). Several opt-outs here are not "not needed yet" —
> they are **structurally forbidden** by D-29-01 (the author publishes by hand) and
> are enforced by minting the automation token with `deposit:write` only, omitting
> `deposit:actions`.

| capability | decision | reason |
|---|---|---|
| `POST /deposit/depositions` (create draft) | INTEGRATE | |
| `PUT /deposit/depositions/{id}` (replace metadata) | INTEGRATE | |
| `GET /deposit/depositions/{id}` (retrieve draft) | INTEGRATE | |
| `PUT {links.bucket}/{name}` (bucket file upload) | INTEGRATE | |
| `GET /deposit/depositions` (list depositions) | OPT-OUT | not needed — both draft ids and `links.html` are recorded into the phase evidence set at creation time, which is the repo-side handle RESEARCH § *Runtime State Inventory* requires |
| `DELETE /deposit/depositions/{id}` (discard draft) | OPT-OUT | explicitly out of scope — D-29-01 makes draft disposition the author's action in the web UI; automation that can destroy a reviewed draft is the wrong capability to hold |
| `GET {links.bucket}` (list bucket contents) | OPT-OUT | not needed — the `PUT` response body (`key`, `size`, `checksum`, `version_id`) is the round-trip proof; a second listing adds no evidence |
| `DELETE {links.bucket}/{name}` (delete bucket file) | OPT-OUT | not needed — a failed `PUT` is retried by re-`PUT`ing the same key, which overwrites; no delete path is exercised |
| `POST /deposit/depositions/{id}/files` (legacy multipart form upload) | OPT-OUT | explicitly out of scope — 100 MB per-file cap cannot carry the 4.35 GB payload at all; superseded by the bucket API, which D-29-07 already specifies |
| `PUT /deposit/depositions/{id}/files` (sort files) | OPT-OUT | not needed — one file per record; there is no ordering to set |
| `POST /deposit/depositions/{id}/actions/publish` | OPT-OUT | explicitly out of scope — D-29-01: minting a permanent DOI is one-way and stays the author's act in the web UI. Not implemented at all, and the `deposit:write`-only token makes that structural |
| `POST /deposit/depositions/{id}/actions/edit` | OPT-OUT | explicitly out of scope — requires `deposit:actions`; post-publish edits are the author's |
| `POST /deposit/depositions/{id}/actions/discard` | OPT-OUT | explicitly out of scope — requires `deposit:actions`; see `DELETE` above |
| `POST /deposit/depositions/{id}/actions/newversion` | OPT-OUT | not needed yet — Record B's re-versioning against new results is Phase 30 / POST-01 work; record `21889922` is left untouched by decision |
| `metadata.prereserve_doi` (DOI reservation on a draft) | OPT-OUT | explicitly out of scope — excluded by D-29-03; reservation commits to an identifier the manuscript does not need before Publish |
| `GET /records` / `GET /records/{id}` (public search + retrieve) | OPT-OUT | not needed — the only public read path this project needs already exists as `src/aquacal/datasets/download.py`, and repointing it is deferred (RESEARCH § *`_manifest.py` Blast Radius*) |
| `GET /licenses`, `/communities`, `/funders`, `/grants` (vocabulary lookups) | OPT-OUT | not needed — both records' metadata is authored by hand into `scripts/zenodo_metadata_{a,b}.json` and reviewed by the author in the UI (D-29-02), so no runtime vocabulary resolution is required |
| OAuth authorization-code flow (`/oauth/authorize`, `/oauth/token`) | OPT-OUT | not needed — a personal access token in `Authorization: Bearer` is the documented path for a single-operator script; no third-party delegation exists here |

## Second-integration note

The **sandbox** instance (`https://sandbox.zenodo.org/api`, D-29-06) is a second integration
against the same need. It is re-decided from the same full-coverage baseline and lands on the
**identical** matrix above — same four INTEGRATE capabilities, same opt-outs, same
`deposit:write`-only scope. It is driven by the same `scripts/zenodo_upload.py` with a required
explicit `--sandbox` / `--base-url` selector and **no production default**, so no
first-class/fallback asymmetry accumulates between the two hosts.
