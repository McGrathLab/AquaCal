---
phase: quick/260811-e7s-pre-2-0-0-release-audit
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md
autonomous: true
requirements: [AUDIT-API, AUDIT-PKG, AUDIT-DOCS, AUDIT-ORPHAN]
must_haves:
  truths:
    - "Each of the three known deprecation shims is labelled CLEAN or DEPENDENTS with a complete file:line dependent list"
    - "The user can see what files actually land in the 2.0.0 wheel and sdist, and which required package data is missing"
    - "Every hand-crafted docs page has been read in full and its factual errors listed with file:line"
    - "The sphinx -W docstring blocker is confirmed LIVE or FIXED by an actual build, not by inference"
    - "Every finding carries a MUST-FIX-BEFORE-2.0.0 / SHOULD-FIX / OPTIONAL rank, evidence, and a fix-cost estimate"
    - "No repo file other than the audit document has been modified"
  artifacts:
    - path: ".planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md"
      provides: "Ranked pre-2.0.0 release findings with per-finding evidence"
      contains: "MUST-FIX-BEFORE-2.0.0"
  key_links:
    - from: "21-PRE-RELEASE-AUDIT.md"
      to: "source evidence"
      via: "file:line citation on every finding"
      pattern: "\\.(py|md|toml|yaml|rst|ipynb):[0-9]+"
---

<objective>
Produce a single ranked, read-only pre-release audit of the AquaCal repo covering public API
surface, packaging, hand-crafted docs accuracy, and orphaned files / false claims.

Purpose: 663 commits are unpushed. The first push triggers python-semantic-release and cuts
**v2.0.0**. Anything fixed before that push lands in 2.0.0 for free; anything missed becomes a
2.0.1+ trail, and public-API mistakes are locked until a 3.0.0. SoftwareX deadline is 2026-08-21,
so the deliverable must be a RANKED list the user can draw a line through — not exhaustive.

Output: `.planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md`,
committed. A separate follow-up task applies fixes after the user reviews.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/21-new-feature-documentation-dataset-refresh/deferred-items.md

Facts already established during planning — do NOT re-derive these:

- `MANIFEST.in` does **not** exist. sdist contents come from setuptools defaults only.
- `pyproject.toml` declares `[tool.setuptools.packages.find] where = ["src"]` and
  `[tool.setuptools.package-data] aquacal = ["datasets/data/**/*.json"]`. `version = "1.8.0"`
  (semantic-release owns it — never hand-edit).
- `docs/conf.py:36` sets `nbsphinx_execute = "never"`, so a sphinx build does NOT execute the
  notebooks and completes well inside the 600 s ceiling.
- `figures/` does not exist at repo root, confirming the `experiments/README.md:74` false claim.
- Repo root contains bulk that must not be mistaken for shipped content: `build/`, `dist/`,
  `tmp/`, `aquacal_data/`, `seed_sweep_19_3/`, `docs/_build/`, `.claude/worktrees/`.
- `__all__` is declared in: `src/aquacal/__init__.py:34`, `calibration/__init__.py:38`,
  `calibration/frame_rejection.py:36`, `config/__init__.py:27`, `core/__init__.py:16`,
  `datasets/__init__.py:59`, `io/__init__.py:4`, `triangulation/__init__.py:4`,
  `utils/__init__.py:12`, `validation/__init__.py:21`.

Hand-crafted docs surface (the complete list — there is no other hand-crafted page):
`README.md` (75 lines), `CONTRIBUTING.md` (141), `docs/index.md` (67), `docs/overview.md` (39),
`docs/contributing.md` (4), `docs/guide/index.md` (31), `docs/guide/benchmarking.md` (300),
`docs/guide/cli.md` (197), `docs/guide/configuration.md` (317), `docs/guide/coordinates.md` (204),
`docs/guide/glossary.md` (70), `docs/guide/optimizer.md` (389),
`docs/guide/refractive_geometry.md` (166), `docs/guide/troubleshooting.md` (314),
`docs/tutorials/index.md` (39), `docs/tutorials/01_full_pipeline.ipynb`,
`docs/tutorials/02_synthetic_validation.ipynb`.

`docs/tutorials/03_cli_walkthrough.md` was corrected today — **VERIFIED, do not re-flag**.
`docs/api/*.rst` is auto-generated API reference — **do NOT comb it function by function**.
</context>

<constraints>
These apply to EVERY task in this plan. Violating any one invalidates the deliverable.

1. **READ-ONLY.** The ONLY repo file that may be created or modified is
   `.planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md`, and
   only in Task 5. No source, docs, config, packaging, or experiment file may be touched — not
   even to fix an obvious one-character typo you find. Findings are *reported*, never *applied*.
   A separate follow-up task applies fixes after the user reviews.
2. **Do NOT run the full pytest suite.** It measures 56–88 minutes. If a finding needs test
   evidence, cite a specific test file by path and line; do not execute it. Targeted greps, file
   reads, one `sphinx-build`, and one `python -m build` are the only permitted heavy operations.
3. **Never background a long run and return.** Per CLAUDE.md, a subagent that backgrounds a
   command and ends its turn stalls permanently and never resumes. Every command must complete
   inline within the tool's 600 s ceiling. Do not use `run_in_background`, `&`, `nohup`, or
   `disown`. If a command might exceed the ceiling, split it into smaller commands.
4. **PYTHONPATH.** Any task that runs python must first `export PYTHONPATH="$(pwd)/src"` —
   otherwise the editable install resolves to main's code rather than the working tree.
5. **All build and scratch output goes outside the repo**, into `$SCRATCH`. Never write into
   `docs/_build/`, `build/`, or `dist/` — those already exist with stale content, and writing
   there is a repo modification.
6. **Evidence or silence.** Every finding must be independently verifiable from its cited
   `file:line`. Do not report a suspicion as a finding. If you believe something is wrong but
   cannot demonstrate it, mark it `UNVERIFIED` and state exactly what check would settle it.
7. **Rank by lock-in, not ugliness.** `MUST-FIX-BEFORE-2.0.0` means leaving it unfixed is
   materially harder or impossible to correct after the release cuts — public API shape, wheel
   contents, a release gate that will fail, or something that would be pushed and cannot be
   unpushed. Cosmetic problems are `OPTIONAL` no matter how annoying they look.
</constraints>

<scratch>
Set this at the start of every task:

```bash
export SCRATCH="/c/Users/tucke/AppData/Local/Temp/claude/C--Users-tucke-PycharmProjects-AquaCal/9006dedd-1abb-4237-8234-ac5841e52a60/scratchpad"
mkdir -p "$SCRATCH"
```

Tasks 1–4 each write a findings fragment into `$SCRATCH`, outside the repo. Task 5 merges, ranks,
and writes the single audit document. This keeps the repo untouched until the final step and
keeps each task's context bounded.

**Per-finding format** used by all four fragment tasks:

```
### <one-line title>
- Proposed rank: MUST-FIX-BEFORE-2.0.0 | SHOULD-FIX | OPTIONAL
- Evidence: <file:line>, <file:line>
- Why this rank: <is it locked in by the release, or not>
- Fix: <the concrete change>
- Fix cost: <N files touched, rough context-window fraction>
- Status: CONFIRMED | UNVERIFIED (<what check would settle it>)
```
</scratch>

<tasks>

<task type="auto">
  <name>Task 1: Public API surface — shim removability and hidden legacy surface</name>
  <files>$SCRATCH/audit-01-api.md (scratch only — NO repo files modified)</files>
  <action>
Highest-value scope: public API mistakes are locked until a 3.0.0.

Part A — the three known deprecation shims. For each, enumerate EVERY dependent and state
plainly whether removal is CLEAN (zero dependents outside the shim's own definition and its own
deprecation test) or has DEPENDENTS (each listed with file:line).

  - `initial_distances` config field — `src/aquacal/calibration/pipeline.py:282`
  - `refractive_project_fast()` — `src/aquacal/core/refractive_geometry.py:937`
  - `refractive_project_fast_batch()` — `src/aquacal/core/refractive_geometry.py:960`

Search the whole tree for each identifier, excluding `.git`, `build`, `dist`, `docs/_build`,
`__pycache__`, `.ipynb_checkpoints`, and `.claude/worktrees` (that last one is a stale agent
worktree, not shipped code — do not report its hits). Cover all of `src/`, `tests/`,
`experiments/`, `scripts/`, `docs/` (including the two `.ipynb` tutorials and any YAML under
docs), root-level `*.yaml`/`*.yml` configs, and `aquacal_data/` config files.

Classify each hit as: definition, deprecation test (a test whose purpose is to assert the warning
fires — these do not block removal, they get deleted alongside the shim), live internal caller,
doc mention, or config usage.

For `initial_distances`, the long-standing blocker was that the published Zenodo dataset shipped
a config using it. That blocker was cleared TODAY: the new archive's `config_paper.yaml` uses
`initial_water_z`. Verify that claim against
`.planning/phases/21-new-feature-documentation-dataset-refresh/21-ARCHIVE-MANIFEST.md` and any
`config_paper.yaml` present in the tree, and state whether it holds.

Part B — sweep for OTHER deprecated, legacy, or experimental public surface not on the above
list. Concretely:

  - Read each `__all__` block (locations listed in `<context>`) and check every exported name
    still resolves to something intended as public. Flag exports of internal helpers, names that
    no longer exist, and re-exports that duplicate another module's public name.
  - Grep `src/` case-insensitively for `deprecat`, `legacy`, `experimental`, `will be removed`,
    `TODO.*remove`, `DeprecationWarning`, `PendingDeprecation` to catch shims beyond the three
    named.
  - Look for kwargs accepted but ignored: a parameter present in a public signature that never
    appears again in the function body. Check the top-level public entry points first
    (`src/aquacal/__init__.py` exports, `calibration/pipeline.py`, `cli.py`, `datasets/`,
    `triangulation/`, `validation/`). Do NOT attempt this exhaustively across private helpers.
  - Check `cli.py` for flags parsed but unused, and for flag or subcommand names that a 2.0.0
    would be stuck with.

Do NOT modify any file. Do NOT run pytest.

Write findings to `$SCRATCH/audit-01-api.md` using the per-finding format in `<scratch>`.
  </action>
  <verify>
    <automated>test -s "$SCRATCH/audit-01-api.md" &amp;&amp; grep -q 'initial_distances' "$SCRATCH/audit-01-api.md" &amp;&amp; grep -q 'refractive_project_fast_batch' "$SCRATCH/audit-01-api.md" &amp;&amp; grep -qE '(CLEAN|DEPENDENTS)' "$SCRATCH/audit-01-api.md" &amp;&amp; [ "$(git status --porcelain | grep -vc '^?? ')" = "0" ]</automated>
  </verify>
  <done>
Fragment exists covering all three shims, each explicitly labelled CLEAN or DEPENDENTS with its
dependent list; Part B sweep results present; `git status --porcelain` shows zero modifications
to tracked files.
  </done>
</task>

<task type="auto">
  <name>Task 2: Packaging — actual wheel/sdist contents, plus the sphinx -W release gate</name>
  <files>$SCRATCH/audit-02-packaging.md (scratch only — NO repo files modified)</files>
  <action>
Part A — build and inspect. This is the first release anyone will `pip install` fresh, so the
decisive check is to build and list archive contents rather than reason about the config.

Build into scratch so nothing is written into the repo's existing `build/` or `dist/`:

```bash
export PYTHONPATH="$(pwd)/src"
python -m build --outdir "$SCRATCH/dist" . 2>&1 | tail -40
```

Run this in the FOREGROUND and let it finish; it should take a couple of minutes. Do not
background it. If `python -m build` is unavailable or errors during setup, record that as a
finding — a broken build is itself MUST-FIX — and fall back to
`pip wheel --no-deps -w "$SCRATCH/dist" .`. If it has not returned by the tool ceiling, report
that as a finding rather than retrying in the background.

Then list both archives:

```bash
python -c "import zipfile,glob;[print(n) for f in glob.glob('$SCRATCH/dist/*.whl') for n in sorted(zipfile.ZipFile(f).namelist())]"
python -c "import tarfile,glob;[print(n) for f in glob.glob('$SCRATCH/dist/*.tar.gz') for n in sorted(tarfile.open(f).getnames())]"
```

Assess two failure directions:

  - **Stray inclusions.** Planning fragments, test fixtures, large data files, `.planning/`,
    experiment outputs, `aquacal_data/`, `seed_sweep_19_3/`, logs, `__pycache__`,
    `.ipynb_checkpoints`. Record the sdist and wheel sizes and call out any single member over
    roughly 1 MB.
  - **Required data OMITTED.** Confirm specifically whether
    `src/aquacal/datasets/data/manifest.json` — and any sibling data the `datasets` module opens
    at runtime — is present in the wheel. `[tool.setuptools.package-data]` declares
    `aquacal = ["datasets/data/**/*.json"]`; verify the glob actually matched. Grep
    `src/aquacal/datasets/` for every file it opens at runtime and check each against the wheel
    namelist. A missing data file means a fresh `pip install aquacal` is broken, which is
    MUST-FIX.

There is no `MANIFEST.in`, so also note whether the sdist omits anything a source consumer needs
(tests, LICENSE, README, files referenced by `pyproject.toml`).

Also review `pyproject.toml` metadata for release-locked mistakes: classifiers that will be wrong
at 2.0.0 (notably `Development Status :: 4 - Beta`), dependency bounds too loose or too tight for
a major release, `requires-python`, and the `[project.urls]` targets. Do NOT propose editing
`version` — semantic-release owns it.

Part B — the sphinx `-W` release gate. `deferred-items.md` records a deferred docutils error in
`generate_board_trajectory`'s docstring (`src/aquacal/datasets/synthetic.py`), "ERROR: Unexpected
indentation. [docutils]", which `-W` promotes to a build failure. Determine whether it is still
LIVE by actually building into a clean scratch output dir — never `docs/_build/`:

```bash
sphinx-build -W --keep-going -b html docs "$SCRATCH/sphinx" 2>&1 | tail -60
```

`docs/conf.py:36` sets `nbsphinx_execute = "never"`, so this does not execute the notebooks and
is fast. Report the exit status, whether the `generate_board_trajectory` error is present, and
every OTHER warning `-W` would promote to a failure — each one is a release gate blocker. If
sphinx is not installed in the active environment, report UNVERIFIED with the exact command that
would settle it rather than guessing.

Do NOT modify any file. Do NOT run pytest.

Write findings to `$SCRATCH/audit-02-packaging.md` using the per-finding format in `<scratch>`.
  </action>
  <verify>
    <automated>test -s "$SCRATCH/audit-02-packaging.md" &amp;&amp; grep -qi 'manifest.json' "$SCRATCH/audit-02-packaging.md" &amp;&amp; grep -qi 'sphinx' "$SCRATCH/audit-02-packaging.md" &amp;&amp; [ "$(git status --porcelain | grep -vc '^?? ')" = "0" ]</automated>
  </verify>
  <done>
Wheel and sdist namelists inspected; presence or absence of `datasets/data/manifest.json` in the
wheel stated definitively; sphinx `-W` gate reported as LIVE, FIXED, or UNVERIFIED with the exact
settling command; zero modifications to tracked files.
  </done>
</task>

<task type="auto">
  <name>Task 3: Docs accuracy — every hand-crafted page, read in full</name>
  <files>$SCRATCH/audit-03-docs.md (scratch only — NO repo files modified)</files>
  <action>
Mid-depth review per explicit user decision. Read IN FULL every hand-crafted page listed in
`<context>`: the guides, the index and overview pages, root `README.md`, and `CONTRIBUTING.md`.

**Do NOT comb the auto-generated API reference (`docs/api/*.rst`) function by function.** Read
those files only far enough to check that their `automodule` and `autoclass` targets still exist.

**`docs/tutorials/03_cli_walkthrough.md` was corrected today — treat as VERIFIED, do not
re-flag.**

For the two notebooks, do NOT read the raw files — they are 430 KB and 720 KB because of embedded
outputs and will exhaust your context. Extract source cells only:

```bash
python - <<'PY'
import json
for p in ["docs/tutorials/01_full_pipeline.ipynb","docs/tutorials/02_synthetic_validation.ipynb"]:
    nb = json.load(open(p, encoding="utf-8"))
    print(f"===== {p} =====")
    for i, c in enumerate(nb["cells"]):
        print(f"--- cell {i} [{c['cell_type']}] ---")
        print("".join(c["source"]))
PY
```

Do NOT execute the notebooks.

Look for four classes of error, each cited with file:line:

  1. **Documented parameters or flags that no longer exist in code.** Cross-check every config
     key named in `docs/guide/configuration.md` against `src/aquacal/config/schema.py` and the
     parser in `src/aquacal/calibration/pipeline.py`. Cross-check every CLI flag in
     `docs/guide/cli.md` against `src/aquacal/cli.py`. Flag both directions: documented-but-gone,
     and exists-but-undocumented where the omission would mislead a user.
  2. **Examples that would fail if run.** Wrong import paths, renamed functions, changed
     signatures, stale file paths, deprecated call forms. Note especially any doc example still
     using `initial_distances` or `refractive_project_fast*` — cross-reference Task 1's fragment
     rather than re-deriving the shim status.
  3. **Numbers quoted from superseded calibration runs.** Reported errors, timings, memory
     figures, speedup ratios. Be careful here, per accumulated project knowledge: E3 and E4 carry
     no accuracy band at all; Stage 3 peak memory is 10.26 GiB and an older ~3.6 GB figure was
     never measured; E1's speedup is a 97–178x band, not a point estimate, so a doc quoting ~135x
     as a bare point value IS a finding but the band itself must NOT be "corrected". If a quoted
     number's provenance cannot be established, mark it UNVERIFIED rather than asserting it wrong.
  4. **Broken internal cross-references.** Every relative markdown link and every sphinx `:doc:`
     or `:ref:` target must resolve to a file that exists. Check the `toctree` entries in
     `docs/index.md`, `docs/guide/index.md`, `docs/tutorials/index.md`, and `docs/api/index.rst`
     against the actual file list.

Do NOT modify any file. Do NOT run pytest. Do NOT fix a single typo you encounter — record it.

Write findings to `$SCRATCH/audit-03-docs.md` using the per-finding format in `<scratch>`,
grouped by source page. Begin the fragment with an explicit "pages read in full" checklist naming
every path from the `<context>` list, so coverage is auditable.
  </action>
  <verify>
    <automated>test -s "$SCRATCH/audit-03-docs.md" &amp;&amp; for p in README.md CONTRIBUTING.md docs/index.md docs/overview.md docs/guide/benchmarking.md docs/guide/cli.md docs/guide/configuration.md docs/guide/coordinates.md docs/guide/glossary.md docs/guide/optimizer.md docs/guide/refractive_geometry.md docs/guide/troubleshooting.md docs/tutorials/01_full_pipeline.ipynb docs/tutorials/02_synthetic_validation.ipynb; do grep -q "$p" "$SCRATCH/audit-03-docs.md" || { echo "MISSING $p"; exit 1; }; done &amp;&amp; [ "$(git status --porcelain | grep -vc '^?? ')" = "0" ]</automated>
  </verify>
  <done>
Every hand-crafted page appears in the coverage checklist; findings cite file:line; notebooks
reviewed via source-cell extraction rather than raw read; zero modifications to tracked files.
  </done>
</task>

<task type="auto">
  <name>Task 4: Orphaned files and false claims</name>
  <files>$SCRATCH/audit-04-orphans.md (scratch only — NO repo files modified)</files>
  <action>
Two directions, the second of which is more serious than the first.

Part A — **false claims: references to files that do not exist.** These are worse than orphans
because a reader following one hits a dead end. Extract every file path mentioned in `README.md`,
`CONTRIBUTING.md`, `experiments/README.md`, the hand-crafted `docs/` pages, and `CITATION.cff`,
then test each for existence. One confirmed example to include: `experiments/README.md:74` cites
`figures/aquacal/zenodo_e2e.py`, and no `figures/` directory exists at repo root (verified during
planning). Find the rest.

Also check paths referenced from code and config that must exist at runtime or inside the wheel:
default config paths, dataset manifest entries, and any hardcoded relative path under
`src/aquacal/`. Cross-reference Task 2's wheel namelist fragment rather than rebuilding.

Part B — **orphaned files: things nothing references.** Scope this to what a 2.0.0 consumer or a
repo visitor would actually encounter. Check `src/aquacal/` for modules imported by nothing,
`scripts/` (only `extract_frames.py` is present), `experiments/` for scripts referenced by no
README or runner, and `docs/` for pages in no `toctree`.

Judgement call, and state it explicitly in the fragment: stale experiment logs and superseded
results directories are normal research residue and are OPTIONAL at most. Do NOT pad the audit
with dozens of `experiments/*.log` entries — report bulk residue as a single aggregate finding
with a count. What matters is (a) anything orphaned that nonetheless ships in the wheel or sdist,
and (b) anything orphaned that a reader is pointed AT.

Finally, confirm that `build/`, `dist/`, `tmp/`, `aquacal_data/`, `seed_sweep_19_3/`,
`docs/_build/`, and `.claude/worktrees/` are genuinely gitignored, using
`git check-ignore -v <path>` on each. Any of these that is NOT ignored would be pushed along with
the 663 commits and cannot be unpushed cleanly — that case is MUST-FIX. Also run
`git status --porcelain` and review the untracked list for anything large or private that would
be swept in.

Do NOT modify any file. Do NOT run pytest. Do NOT delete anything.

Write findings to `$SCRATCH/audit-04-orphans.md` using the per-finding format in `<scratch>`.
  </action>
  <verify>
    <automated>test -s "$SCRATCH/audit-04-orphans.md" &amp;&amp; grep -q 'figures/aquacal/zenodo_e2e.py' "$SCRATCH/audit-04-orphans.md" &amp;&amp; grep -qiE 'check-ignore|gitignor' "$SCRATCH/audit-04-orphans.md" &amp;&amp; [ "$(git status --porcelain | grep -vc '^?? ')" = "0" ]</automated>
  </verify>
  <done>
False-claim path list is complete and each entry tested for existence; the known
`figures/aquacal/zenodo_e2e.py` claim is recorded; gitignore status of every bulk directory is
confirmed; bulk residue aggregated rather than enumerated; zero modifications to tracked files.
  </done>
</task>

<task type="auto">
  <name>Task 5: Merge, rank, write the audit document, and commit</name>
  <files>.planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md</files>
  <action>
Read the four fragments from `$SCRATCH` and merge them into one document. This is the ONLY task
that writes into the repo, and `21-PRE-RELEASE-AUDIT.md` is the ONLY file it may write.

Re-rank globally. The per-task proposed ranks were assigned without cross-scope visibility; now
apply one consistent standard across all findings:

  - **MUST-FIX-BEFORE-2.0.0** — the mistake is locked in by the release. Public API shape that
    cannot change until a 3.0.0, wheel or sdist contents that break a fresh `pip install`, a
    release gate that will fail the push, or content that would be pushed and cannot be
    cleanly unpushed.
  - **SHOULD-FIX** — real and worth fixing before the deadline, but correctable in a 2.0.1
    without breaking anyone. Most docs inaccuracies land here.
  - **OPTIONAL** — cosmetic or housekeeping. Nothing is lost by deferring past the release.

Rank by lock-in, not by how ugly the problem is. A hideous typo in a guide is OPTIONAL; a quietly
wrong `__all__` export is MUST-FIX.

Document structure:

  1. **Header** — date, HEAD sha (`git rev-parse --short HEAD`), unpushed commit count
     (`git log --oneline @{u}..HEAD 2>/dev/null | wc -l`, falling back to a stated 663 if no
     upstream is configured), and a one-paragraph statement of why the release cut makes this
     ranking matter.
  2. **The line** — a short "if you only fix N things" list naming the MUST-FIX items by title,
     so the user can draw a line through it immediately. Put this near the top, not the bottom.
  3. **MUST-FIX-BEFORE-2.0.0** — full findings, ordered by fix cost ascending so cheap wins come
     first.
  4. **SHOULD-FIX** — full findings.
  5. **OPTIONAL** — may be compressed to one line each.
  6. **UNVERIFIED** — every item that could not be settled, each with the exact check that would
     settle it. Do not silently drop these into another bucket.
  7. **Scope and method** — what was inspected, what was deliberately not inspected (the
     auto-generated API reference, the full pytest suite, `03_cli_walkthrough.md`), and the
     commands actually run. This is what makes the audit's coverage auditable.
  8. **Total fix cost estimate** per rank tier.

Every finding keeps its file:line evidence and fix-cost estimate. Deduplicate findings that two
tasks reported (a deprecated call form appearing in both the API and docs fragments is one
finding with two evidence lines, not two findings).

Then verify no other repo file changed and commit:

```bash
git status --porcelain
git add .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md
git commit -m "docs(21): pre-2.0.0 release audit -- ranked findings"
```

If `git status --porcelain` shows ANY modified tracked file other than the audit document, STOP,
do not commit, and report which file changed and in which task — the read-only constraint was
violated and the run must be reviewed before anything is staged.
  </action>
  <verify>
    <automated>test -s .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md &amp;&amp; grep -q 'MUST-FIX-BEFORE-2.0.0' .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md &amp;&amp; grep -q 'SHOULD-FIX' .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md &amp;&amp; grep -q 'OPTIONAL' .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md &amp;&amp; grep -qE '\.(py|md|toml|yaml|rst|ipynb):[0-9]+' .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md &amp;&amp; [ "$(git status --porcelain | grep -vc '^?? ')" = "0" ] &amp;&amp; git log -1 --name-only --pretty=format: | grep -c . | grep -qx 1</automated>
  </verify>
  <done>
Audit document exists with all three rank tiers, an UNVERIFIED section, a scope-and-method
section, and file:line evidence throughout; the commit touches exactly one file; working tree has
no other modified tracked files.
  </done>
</task>

</tasks>

<verification>
Run after Task 5:

```bash
# 1. Exactly one file changed in the audit commit
git log -1 --name-only --pretty=format:
# Expect exactly: .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md

# 2. No source, docs, config, or packaging file was touched anywhere in this run
git status --porcelain
# Expect no lines starting with ' M', 'M ', ' D', or 'D '

# 3. All three known shims are addressed by name
grep -c 'initial_distances\|refractive_project_fast' \
  .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md

# 4. Every rank tier is present
grep -c 'MUST-FIX-BEFORE-2.0.0\|SHOULD-FIX\|OPTIONAL' \
  .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md
```
</verification>

<success_criteria>
- `21-PRE-RELEASE-AUDIT.md` exists, is committed, and is the only file in that commit.
- Zero tracked repo files modified outside the audit document.
- All three known deprecation shims labelled CLEAN or DEPENDENTS with dependents at file:line.
- Wheel and sdist contents listed from an actual build; the `datasets/data/manifest.json`
  question answered definitively.
- The sphinx `-W` gate reported LIVE, FIXED, or UNVERIFIED from an actual `sphinx-build` run.
- Every hand-crafted docs page appears in the coverage checklist.
- Every finding carries a rank, file:line evidence, and a fix-cost estimate.
- Uncertain items appear under UNVERIFIED with the check that would settle them, not buried in
  another tier.
- The full pytest suite was never run.
- No command was backgrounded.
</success_criteria>

<output>
Create `.planning/quick/260811-e7s-pre-2-0-0-release-audit/SUMMARY.md` when done, recording the
MUST-FIX count, the total estimated fix cost, and any scope that could not be completed.
</output>
