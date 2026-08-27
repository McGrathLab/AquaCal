"""FIX-06's regression guard: stale provenance strings stay corrected.

This file's subject is **source text**, not runtime behavior. It exists because a
previous pass at this class of defect corrected `experiments/e2_real_rig.py`'s
`--config` help text and left an identical stale claim sitting in a code comment
on the explicit-config branch a few hundred lines away -- a partial fix that reads
as complete from either site alone. The tests here assert that BOTH sites carry
the corrected claim together, not just one.

This file necessarily **contains** the stale strings itself -- the tests assert on
them and the supersession header quotes them for context. Any grep-based gate
elsewhere must therefore be scoped by filename, never run repo-wide, or it will
match this file after a perfect fix (see the plan's grep-hygiene note).

**There is a SECOND file with the same property**, added by phase 29.1 plan 03:
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-STALE-STRING-AUDIT.md`. That
audit quotes every retired claim in its Pass B table, because quoting the claim is
how it records what was corrected. It is therefore likewise **never scanned** by
anything here, and no gate for this defect class may walk `.planning/`. Between the
two of them, a repo-wide grep for any sentence below returns two guaranteed hits
that are not defects.
"""

from __future__ import annotations

import pathlib

import pytest

# Anchored to the repository root via this file's own location, not the process
# working directory -- resolving relative to cwd can silently vanish a gate just
# because pytest was invoked from elsewhere (WR-06).
# tests/unit/test_stale_provenance_strings.py -> parents[2] == repo root.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

E2_SOURCE = REPO_ROOT / "experiments" / "e2_real_rig.py"
E1_SOURCE = REPO_ROOT / "experiments" / "e1_refractive_comparison.py"
SYNTHETIC_SOURCE = REPO_ROOT / "src" / "aquacal" / "datasets" / "synthetic.py"

# Phase 29.1 plan 03: the four boundary files the bounded sweep corrected, plus the
# two twin sites outside the boundary that carried the identical claim. Each is a
# NAMED constant for the reason this module exists: a tree walk would match this
# file and the audit document, both of which quote every sentence below.
E4_SOURCE = REPO_ROOT / "experiments" / "e4_benchmark_grid.py"
E6_SOURCE = REPO_ROOT / "experiments" / "e6_generalization_sweep.py"
DRIVER_SOURCE = REPO_ROOT / "experiments" / "run_experiment_suite.sh"
EXPECTATIONS_SOURCE = REPO_ROOT / "experiments" / "_expectations.py"
GATES_SOURCE = REPO_ROOT / "experiments" / "check_rerun_gates.py"
FRAMESET_DOC = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "19.1-experiment-suite-consolidation"
    / "19.1-E2-FRAMESET-PROVENANCE.md"
)

# Sentence fragments unique to the defect -- chosen so the corrected site-4
# comment's deliberate retention of the "1,817" figures, now under an explicit
# RETIRED-record attribution, does not trip these assertions.
RETIRED_CLAIM_SENTENCES = (
    "frame-subsampled extraction of the capture that produced them",
    "The PUBLISHED Zenodo archive is a",
    "release diagnostics.json: 0.8786 px, quoted as 0.88)",
)

# D-08/D-10's claim-sentence gate for E1's band. These are the PRE-RULING-A1
# clauses, taken verbatim from
# `.planning/todos/pending/2026-08-20-e1-band-scope-string-still-claims-ten-
# seeds-after-ruling-A1-cut-it-to-four.md`, as they appeared in the source --
# each fragment fits inside ONE source line, because the strings they came from
# were implicitly concatenated across lines and a whole sentence would never
# match the file text.
#
# Ruling A1 cut E1's band from ten seeds to four on 2026-08-15; these clauses
# survived it and shipped in the 2026-08-20 production run's
# `e1_seed_band_provenance.json`, authorising a ten-seed, 640/960-row domain
# that was never executed. The `scope` field is now DERIVED at write time, so
# a regression here means someone re-froze a measurement into a literal.
E1_PRE_RULING_A1_CLAIMS = (
    "seeds, detection noise from 0.25 px to 1.2 px",
    "the four-level ten-seed",
    "band establishing it (640/960 rows) is executed in Phase",
    "WILL BE quoted over",
    "STATED DOMAIN (BAND-01, D-14).",
    "eight test depths 1.10-2.50 m",
    "verified in Phase 29 (D-21)",
)


def _read(path: pathlib.Path) -> str:
    """Read a target file's text, skipping cleanly if it is genuinely absent.

    Args:
        path: File to read.

    Returns:
        The file's text content, decoded as UTF-8.
    """
    if not path.is_file():
        pytest.skip(f"target file not found: {path}")
    return path.read_text(encoding="utf-8")


class TestE2RealRigStrings:
    """Source-text assertions on `experiments/e2_real_rig.py`."""

    @pytest.mark.parametrize("sentence", RETIRED_CLAIM_SENTENCES)
    def test_stale_archive_claims_are_gone(self, sentence: str) -> None:
        """Each retired claim sentence must be entirely absent from the source."""
        source = _read(E2_SOURCE)
        assert sentence not in source, (
            f"stale provenance claim regressed in {E2_SOURCE}: {sentence!r}"
        )

    def test_both_archive_sites_were_corrected(self) -> None:
        """Sites 1 and 4 carry the same claim; a count of 1 means one was fixed
        and the other left -- the specific defect FIX-06 was reopened to close.
        """
        source = _read(E2_SOURCE)
        for token in ("21889922", "18645385", "262 usable frames", "7762"):
            assert source.count(token) >= 2, (
                f"expected {token!r} at both corrected sites (>=2 occurrences), "
                f"found {source.count(token)}"
            )

    def test_provenance_string_hardcodes_no_live_value(self) -> None:
        """The mean_per_camera_reprojection_px string names its derivation and
        marks the release comparison superseded, never swapping one frozen
        number (0.8786) for another (0.8240) -- that would reproduce the defect
        one run later.
        """
        source = _read(E2_SOURCE)
        assert "0.8240" not in source
        assert "SUPERSEDED as a description of this field" in source

    def test_data_01a_label_is_retired(self) -> None:
        """DATA-01a labelled the claim that no longer describes the archive."""
        source = _read(E2_SOURCE)
        assert "DATA-01a" not in source


class TestSyntheticWaterZDescription:
    """Source-text assertions on `src/aquacal/datasets/synthetic.py`."""

    def test_real_rig_standoff_appositive_is_gone(self) -> None:
        """The stale 'the real-rig standoff, ~1.031 m' appositive is corrected."""
        source = _read(SYNTHETIC_SOURCE)
        assert "the real-rig standoff, ~1.031 m" not in source

    def test_rig_true_geometry_is_named(self) -> None:
        """The docstring now names the rig's own estimated water_z."""
        source = _read(SYNTHETIC_SOURCE)
        assert "1.0738404" in source

    def test_constant_itself_is_unchanged(self) -> None:
        """WATER_Z must not be reconciled toward the rig's true value after a
        future reader reads the corrected docstring -- the defect was the
        description, not the constant.
        """
        source = _read(SYNTHETIC_SOURCE)
        assert "WATER_Z: float = 1.031" in source


class TestFramesetProvenanceSupersession:
    """Source-text assertions on the superseded provenance document."""

    def test_header_is_first_and_complete(self) -> None:
        """The supersession header opens the file and names both record ids
        plus the repointing commit.
        """
        source = _read(FRAMESET_DOC)
        assert source.startswith("> **SUPERSEDED")
        rule_index = source.find("\n---\n")
        assert rule_index != -1, "expected a bare '---' rule ending the header"
        header = source[:rule_index]
        assert "21889922" in header
        assert "18645385" in header
        assert "25655f7" in header

    def test_historical_body_is_preserved(self) -> None:
        """The document is correct as a description of the retired record; a
        version with the subsampling figures scrubbed has destroyed the
        provenance trail and must fail here. This asserts preservation, not
        correction.
        """
        source = _read(FRAMESET_DOC)
        rule_index = source.find("\n---\n")
        assert rule_index != -1, "expected a bare '---' rule ending the header"
        body = source[rule_index:]
        assert "# E2 frameset provenance" in body
        assert "60 usable" in body


class TestE1BandScopeIsDerived:
    """Source-text assertions on `experiments/e1_refractive_comparison.py`.

    The subject is the `scope` field of `e1_seed_band_provenance.json` and the
    module docstring's STATED DOMAIN paragraph, which carried the same
    pre-ruling-A1 claim. Both are source text here, and both are checked
    together for the reason this module exists at all: correcting one site and
    leaving its twin reads as complete from either site alone.

    Like the rest of this module, **this class necessarily contains the stale
    clauses itself** -- `E1_PRE_RULING_A1_CLAIMS` quotes them. Any grep-based
    gate elsewhere must therefore stay scoped by filename and never run
    repo-wide, or it matches this file after a perfect fix.
    """

    @pytest.mark.parametrize("clause", E1_PRE_RULING_A1_CLAIMS)
    def test_pre_ruling_a1_claims_are_gone(self, clause: str) -> None:
        """Each pre-A1 clause must be entirely absent from the source."""
        source = _read(E1_SOURCE)
        assert clause not in source, (
            f"pre-ruling-A1 band claim regressed in {E1_SOURCE}: {clause!r}"
        )

    def test_scope_is_derived_not_a_literal(self) -> None:
        """The positive half. Absence alone would also be satisfied by deleting
        the field; these assert it is COMPUTED from the run that wrote it.
        """
        source = _read(E1_SOURCE)
        assert "MEASURED DOMAIN (BAND-01, D-08)" in source
        assert "{len(seeds)} seed(s) {list(seeds)}" in source
        assert "{len(band_df)} rows of exp1_band.csv" in source
        assert "{len(parameter_band_df)} rows of " in source
        assert "swept_noise_levels" in source
        assert "swept_depths" in source

    def test_ruling_a1_is_cited_by_name(self) -> None:
        """A stable cross-reference is a citation, not a recomputed value, and
        it is the only place a reader learns why the seed axis is that size.
        """
        source = _read(E1_SOURCE)
        assert "RULING A1" in source
        assert "run_stage_e1_band" in source

    def test_module_docstring_points_at_the_derived_field(self) -> None:
        """The docstring's STATED DOMAIN paragraph names the axes and defers to
        the sidecar for the values, rather than quoting a count that goes stale
        the next time the grid is resized.
        """
        source = _read(E1_SOURCE)
        docstring = source[: source.index('"""', 3)]
        assert "ruling A1" in docstring
        assert "e1_seed_band_provenance.json" in docstring
        assert "DERIVES from the run" in docstring

    def test_retired_claim_is_named_rather_than_scrubbed(self) -> None:
        """The docstring keeps the retired ten-seed/640/960 figures under an
        explicit "the version that did" attribution -- the same retention this
        module already pins for e2_real_rig.py's site 4. A version with them
        scrubbed has destroyed the trail that explains the correction.
        """
        source = _read(E1_SOURCE)
        docstring = source[: source.index('"""', 3)]
        assert "ten seeds," in docstring
        assert "640/960 rows, from the pre-A1 plan" in docstring


# ---------------------------------------------------------------------------
# Phase 29.1 plan 03 -- the bounded stale-string sweep (SC-4, D-09/D-10).
#
# Every sentence below was corrected because it annotated a value the 2026-08-20
# production run RECOMPUTES, while carrying no attribution. The full boundary,
# the enumeration command and the per-site classification are in
# `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-STALE-STRING-AUDIT.md`.
#
# Each fragment fits inside ONE source line: the surrounding text is wrapped
# comment or docstring prose, so a whole sentence would never match the file.
# ---------------------------------------------------------------------------

# `experiments/e1_refractive_comparison.py`. Five sites, all of them ruling A1's
# ten-seed band surviving in arithmetic and cross-references rather than in the
# provenance prose plan 29.1-02 already corrected.
E1_PRE_A1_ROW_COUNT_CLAIMS = (
    "x 2 models = 160 rows at production scale",
    "regenerable artifact behind MF-08's 97-178x",
    "committed 160/240-row baseline",
    "it writes a 640-row file in which",
    "960 rows collapse onto 240 distinct keys",
    "from 160 to 640 rows (10 seeds x 4 levels",
    "from 240 to 960",
)

# `experiments/e4_benchmark_grid.py`. The seed-invariance claim MF-24 refuted.
# NOTE the shape of this fragment: the corrected text deliberately says "It does
# NOT report the same count", so a gate on the bare phrase "report the same
# count" would fail against a perfect fix. The verb form is load-bearing.
E4_SEED_INVARIANCE_CLAIM = "re-run reports the same count"

# `experiments/e6_generalization_sweep.py`. Two docstrings stating MF-12's
# pre-Phase-28 digits as present-tense facts about a field the run recomputes.
E6_PRE_RUN_DECOMPOSITION_CLAIMS = (
    "is -18.8547 mm, and the camera Z position error",
    "On the committed seed-43, layout=line row this reads",
    "-18.8547 - (-18.4955) == -0.3592",
)

# `experiments/run_experiment_suite.sh`, in ruling A1's own comment block.
DRIVER_PRE_A1_CLAIMS = (
    "and that matters: the headline 97-178x",
    "ratio band and all sixteen ledger numbers backed by exp1_band.csv live at",
)

# The two twin sites OUTSIDE the sweep's boundary, corrected because leaving a
# twin of a corrected claim is the partial-fix shape this whole module exists to
# catch (see `test_both_archive_sites_were_corrected`).
EXPECTATIONS_TWIN_CLAIM = "E1's band is 160/240 rows"
GATES_TWIN_CLAIMS = (
    "explicitly declines to read it as a verdict: at 0.268% of 73,975",
    "verdict at 0.268% of 73,975 observations (pipeline.py:1288)",
)


class TestBoundedStaleStringSweep:
    """Source-text assertions on the four boundary files plan 03 corrected.

    Every assertion is scoped to a NAMED file constant. None walks the tree,
    because this module and the audit document under `.planning/` both contain
    the sentences below by necessity -- see the module docstring.

    Absence assertions alone would also be satisfied by deleting the prose, so
    each file also gets a POSITIVE assertion that the replacement states what is
    true and names where the live value comes from.
    """

    @pytest.mark.parametrize("clause", E1_PRE_A1_ROW_COUNT_CLAIMS)
    def test_e1_pre_a1_row_counts_are_gone(self, clause: str) -> None:
        """No pre-ruling-A1 row count survives in E1's source."""
        source = _read(E1_SOURCE)
        assert clause not in source, (
            f"pre-ruling-A1 row count regressed in {E1_SOURCE}: {clause!r}"
        )

    def test_e1_defers_row_counts_to_the_derived_sidecar(self) -> None:
        """The positive half for E1: the shape claims now name their axes and
        point at the field that derives the counts, instead of freezing a
        product of a seed list that ruling A1 already resized.
        """
        source = _read(E1_SOURCE)
        assert "one row per seed x noise level x test_depth x model" in source
        assert "`e1_seed_band_provenance.json` states the counts it emitted" in source
        assert "is seeds x levels x `len(TEST_DEPTHS)` x models" in source
        assert "once per NOISE_LEVELS entry" in source

    def test_e1_names_the_ten_seed_sweep_as_the_owner_of_its_own_numbers(
        self,
    ) -> None:
        """The published 97-178x band and the "2 of 10 seeds" finding are the
        TEN-seed sweep's. E1's four-seed band cannot regenerate them, and the
        docstring must say so rather than claiming it can -- the correction is
        attribution, not deletion, so the figures stay under an explicit owner.
        """
        source = _read(E1_SOURCE)
        assert "What it does NOT regenerate is" in source
        assert "TEN-seed `seed_sweep_19_3/` sweep's own numbers" in source
        assert "n=10" in source

    def test_e4_does_not_claim_the_guard_count_is_seed_invariant(self) -> None:
        """The highest-severity row of the audit. MF-24 measured 198/210/183
        over seeds 42/43/44 and 194 under OpenCV 4.14, so a re-run does NOT
        report the same count -- and the anchor row's permanent-status argument
        rested on the claim that it does.
        """
        source = _read(E4_SOURCE)
        assert E4_SEED_INVARIANCE_CLAIM not in source, (
            f"seed-invariance claim regressed in {E4_SOURCE}: "
            f"{E4_SEED_INVARIANCE_CLAIM!r}"
        )

    def test_e4_attributes_the_guard_rate_and_states_the_spread(self) -> None:
        """The positive half for E4: the rate keeps its numbers, now under the
        record they were measured on, and the seed spread is stated so the next
        reader cannot re-derive the retired invariance claim.
        """
        source = _read(E4_SOURCE)
        assert "committed 2026-08-20 record (seed 42, OpenCV 4.13.0.92)" in source
        assert "MF-24" in source
        assert "198, 210 and 183 flagged observations for seeds 42, 43 and 44" in source
        assert "194 under OpenCV 4.14" in source
        assert "It does NOT report the same count" in source

    @pytest.mark.parametrize("clause", E6_PRE_RUN_DECOMPOSITION_CLAIMS)
    def test_e6_pre_run_decomposition_claims_are_gone(self, clause: str) -> None:
        """No pre-Phase-28 digit is stated as a present-tense fact about a
        field E6 recomputes.
        """
        source = _read(E6_SOURCE)
        assert clause not in source, (
            f"pre-run decomposition claim regressed in {E6_SOURCE}: {clause!r}"
        )

    def test_e6_keeps_mf12s_figures_under_an_explicit_attribution(self) -> None:
        """Retained, not scrubbed -- the same retention this module already pins
        for `e2_real_rig.py`'s site 4 and for E1's pre-A1 docstring figures. A
        version with MF-12's digits deleted has destroyed the trail that
        explains the correction, and must fail here.
        """
        source = _read(E6_SOURCE)
        assert "-18.8547" in source
        assert "-18.4955" in source
        assert "MF-12's OWN MEASUREMENT" in source
        assert "was measured on, the signed water_z mean was" in source

    def test_e6_points_the_reader_at_the_recomputed_artifact(self) -> None:
        """The positive half for E6: the checkable identity now names the file
        to check it against, so the check survives the next run.
        """
        source = _read(E6_SOURCE)
        assert "generalization_sweep_per_camera_band.csv" in source
        assert "The DECOMPOSITION is the finding, not the" in source
        assert "the identity holds to" in source

    @pytest.mark.parametrize("clause", DRIVER_PRE_A1_CLAIMS)
    def test_driver_pre_a1_claims_are_gone(self, clause: str) -> None:
        """Ruling A1's own comment block must not claim the four-seed band
        backs a ten-seed published spread.
        """
        source = _read(DRIVER_SOURCE)
        assert clause not in source, (
            f"pre-ruling-A1 claim regressed in {DRIVER_SOURCE}: {clause!r}"
        )

    def test_driver_attributes_the_published_band_to_the_ten_seed_sweep(
        self,
    ) -> None:
        """The positive half for the driver, and the clause that must survive:
        0.5 px still has to stay in `NOISE_LEVELS`, for the reason it always
        did. Only the ownership of the 97-178x band changes.
        """
        source = _read(DRIVER_SOURCE)
        assert "every ledger number" in source
        assert "backed by exp1_band.csv lives at 0.5 px" in source
        assert "TEN-seed seed_sweep_19_3/ sweep's own" in source
        assert "cannot" in source and "reproduce an n=10 band" in source

    def test_expectations_helper_twin_was_corrected_too(self) -> None:
        """`experiments/_expectations.py` is OUTSIDE the sweep's boundary and
        carried `e1_refractive_comparison.py:213`'s claim verbatim. Correcting
        one and leaving the other is exactly the partial fix FIX-06 was reopened
        to close, so the twin is pinned here with its in-boundary original.
        """
        source = _read(EXPECTATIONS_SOURCE)
        assert EXPECTATIONS_TWIN_CLAIM not in source, (
            f"stale band shape regressed in {EXPECTATIONS_SOURCE}: "
            f"{EXPECTATIONS_TWIN_CLAIM!r}"
        )
        assert "Row counts live in `suite_expectations.json`" in source

    @pytest.mark.parametrize("clause", GATES_TWIN_CLAIMS)
    def test_gate_twin_no_longer_states_the_rate_unattributed(
        self, clause: str
    ) -> None:
        """`experiments/check_rerun_gates.py` is outside the boundary too, and
        one of its two sites is worse than a comment: it is the message the gate
        PRINTS into every roll-up, so an unattributed frozen rate was emitted as
        live output on each run.
        """
        source = _read(GATES_SOURCE)
        assert clause not in source, (
            f"unattributed guard rate regressed in {GATES_SOURCE}: {clause!r}"
        )

    def test_gate_twin_attributes_the_rate_and_drops_it_from_the_message(
        self,
    ) -> None:
        """The positive half for the gate. The docstring keeps the figures under
        the record they came from; the runtime message drops them entirely,
        because it already prints each exempt row's OWN count -- which is the
        derivation remedy in its strongest form.
        """
        source = _read(GATES_SOURCE)
        assert "record (seed 42, OpenCV 4.13.0.92)" in source
        assert "MF-24 measured 198/210/183 for" in source
        assert "verdict below pipeline.py:1288's 1% threshold" in source
