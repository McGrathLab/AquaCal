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
