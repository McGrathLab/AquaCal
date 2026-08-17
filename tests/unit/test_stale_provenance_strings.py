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
