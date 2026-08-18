"""Source-level proof that E1, E3, E5 and E7 never reach
`generate_camera_array` on their production path (SC-3).

**This is the FIRST post-fix inertness evidence for this claim.** A prior
worktree (plan 19.4-05) ran `python -u -m experiments.e7_interface_ablation
--check` and got exit 0, but that worktree was based at `0c0d321`, which
does NOT contain the `generate_camera_array` fix (D-19.4-09, landed in
19.4-02). That earlier result proves E7's baseline is intact on UNFIXED
code -- it is NOT evidence of inertness under the fix, and must not be
cited as such. This plan's base (`a36a300`) DOES contain the fix; only
results produced from this base count.

**Corrected rationale (CONTEXT.md § CORRECTION, 2026-08-04).** An earlier
version of D-19.4-13 claimed E1 is inert because its `"ideal"` preset uses
`height_variation=0.0`. That is WRONG: E1's production `SCENARIO_NAME =
"realistic"` (`e1_refractive_comparison.py:89`), not `"ideal"`. The real,
stronger reason -- which also covers E7 -- is that `"realistic"` resolves
to `generate_real_rig_array()` (`synthetic.py:1141-1142`), which assigns
the frozen module-level `WATER_Z` to every camera and never calls
`generate_camera_array` at all. E1, E3, E5 and E7 are therefore ALL inert
for the same underlying reason: none of the four reaches
`generate_camera_array` in production. **E7 is in the inert set**, not the
re-measured set -- it moves from "re-measured, numbers change" to
"byte-inert, and the inertness is a gate": its committed
`interface_ablation.csv` must match exactly, and a `--check` failure here
is a real defect signal in the fix, never an expected move (blocking
anti-pattern 3 forbids relaxing `CHECK_RTOL` to paper over it).

This is a scenario-construction-layer claim only -- no full-solve
exact-equality test is written here (unlike
`tests/synthetic/test_guard_inertness.py`, which proved an INTERNAL
mid-solve recording change was inert). Source-text counting plus a
`create_scenario("realistic")` construction check is the appropriate,
cheaper proof for "the ground truth this experiment builds did not change".
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aquacal.datasets.synthetic import create_scenario

_EXPERIMENTS_DIR = Path(__file__).resolve().parents[2] / "experiments"

_E1_PATH = _EXPERIMENTS_DIR / "e1_refractive_comparison.py"
_E3_PATH = _EXPERIMENTS_DIR / "e3_derived_quantities.py"
_E5_PATH = _EXPERIMENTS_DIR / "e5_index_sensitivity.py"
_E7_PATH = _EXPERIMENTS_DIR / "e7_interface_ablation.py"


def _count_references(path: Path, symbol: str) -> int:
    """Count of real references to `symbol` in `path` -- imports, calls and
    attribute accesses in live code.

    Resolved via AST rather than substring matching. The original
    implementation stripped `#`-comment lines and counted substrings, which
    did not honour its own stated contract that "a docstring or comment
    MENTIONING the symbol cannot self-invalidate the gate": a docstring is an
    expression, not a `#` line, so it survived the filter. Plan 19.4-06 then
    added a paragraph to E1's module docstring correctly stating that E1
    "never reaches `generate_camera_array`", and the gate failed on the very
    sentence asserting the invariant it exists to check (caught by the
    post-merge integration gate; plans 04 and 06 each passed alone).

    An AST walk is strictly MORE precise than the substring count, not
    weaker: a genuine `from ... import generate_camera_array`, a call, or an
    attribute access is still counted, while prose is correctly ignored.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == symbol:
            count += 1
        elif isinstance(node, ast.Attribute) and node.attr == symbol:
            count += 1
        elif isinstance(node, ast.ImportFrom):
            count += sum(
                1 for alias in node.names if symbol in (alias.name, alias.asname)
            )
        elif isinstance(node, ast.Import):
            count += sum(
                1
                for alias in node.names
                if alias.name == symbol or alias.name.endswith(f".{symbol}")
            )
    return count


def test_e3_never_references_generate_camera_array():
    """E3 (derived quantities) never imports or calls generate_camera_array
    -- it derives from other experiments' already-written CSVs, not from
    its own scenario construction."""
    assert _count_references(_E3_PATH, "generate_camera_array") == 0


def test_e5_never_references_generate_camera_array():
    """E5 (index sensitivity) builds its own scenario via
    generate_real_rig_array() + generate_real_rig_trajectory(), never via
    generate_camera_array -- confirmed at the source-text level."""
    assert _count_references(_E5_PATH, "generate_camera_array") == 0


def test_e1_never_references_generate_camera_array():
    """E1 (refractive comparison) never references generate_camera_array in
    source text. Its production scenario is built entirely through
    create_scenario("realistic") -> generate_real_rig_array()."""
    assert _count_references(_E1_PATH, "generate_camera_array") == 0


def test_e7_never_references_generate_camera_array():
    """E7 (interface ablation) never references generate_camera_array in
    source text -- the same footing as E1/E3/E5, not a special case."""
    assert _count_references(_E7_PATH, "generate_camera_array") == 0


def test_e1_production_scenario_name_is_realistic():
    """E1's production SCENARIO_NAME resolves to "realistic", not "ideal" --
    the corrected rationale (CONTEXT.md § CORRECTION). The stale claim that
    E1 is inert because it runs "ideal" would be FALSIFIED by this
    assertion; it does not run "ideal" in production."""
    from experiments.e1_refractive_comparison import SCENARIO_NAME

    assert SCENARIO_NAME == "realistic"


def test_e7_production_scenario_name_is_realistic_not_smoke():
    """E7's production scenario_name is "realistic"; "minimal" appears only
    under --smoke. Confirmed directly against source text rather than
    importing E7's module (which has side effects at import time in some
    experiment scripts)."""
    source = _E7_PATH.read_text(encoding="utf-8")
    assert 'scenario_name = "minimal" if smoke else "realistic"' in source


def test_realistic_scenario_water_zs_is_one_shared_value():
    """create_scenario("realistic", seed=42) -- the production scenario for
    both E1 and E7 -- produces a water_zs dict with exactly ONE distinct
    value: proof that this path is a flat, shared interface with no
    per-camera jitter of any kind, i.e. it never touches
    generate_camera_array's (now-fixed) per-camera jitter mechanism at
    all."""
    scenario = create_scenario("realistic", seed=42)
    assert len(set(scenario.water_zs.values())) == 1


def test_realistic_scenario_water_zs_is_seed_invariant():
    """The "realistic" scenario's water_zs does not move with seed at all
    (unlike generate_camera_array's grid family) -- generate_real_rig_array
    assigns the frozen module-level WATER_Z unconditionally, independent of
    any seed argument."""
    scenario_a = create_scenario("realistic", seed=1)
    scenario_b = create_scenario("realistic", seed=999)
    assert scenario_a.water_zs == scenario_b.water_zs


def test_reference_counter_detects_a_real_reference():
    """Positive control: the counter must actually FIRE on live code.

    Without this, `_count_references` could silently degrade to returning 0
    for everything and every inertness assertion above would pass
    vacuously. E4 is the natural control -- it is one of the two grid-family
    experiments that genuinely imports and calls `generate_camera_array`,
    which is precisely why E4's numbers move under this phase's fix while
    E1/E3/E5/E7's do not.
    """
    e4_path = _EXPERIMENTS_DIR / "e4_benchmark_grid.py"
    assert _count_references(e4_path, "generate_camera_array") > 0


def test_reference_counter_ignores_prose_but_not_code(tmp_path):
    """The counter honours its own contract: prose mentioning the symbol is
    ignored, an import or call is not.

    This is the exact confusion that broke the gate once already -- E1's
    module docstring correctly states it "never reaches
    generate_camera_array", and a substring-based counter failed on that
    sentence.
    """
    prose_only = tmp_path / "prose_only.py"
    prose_only.write_text(
        '"""This module never calls generate_camera_array."""\n'
        "# generate_camera_array is not used here either\n"
        "X = 1\n",
        encoding="utf-8",
    )
    assert _count_references(prose_only, "generate_camera_array") == 0

    real_use = tmp_path / "real_use.py"
    real_use.write_text(
        "from aquacal.datasets.synthetic import generate_camera_array\n"
        "result = generate_camera_array(n_cameras=2)\n",
        encoding="utf-8",
    )
    assert _count_references(real_use, "generate_camera_array") > 0


def test_e1_header_states_the_accuracy_claim_stated_domain():
    """BAND-01/D-14: E1's module docstring records the domain over which its
    absolute-accuracy numbers may be quoted, beside the D-19.3-17 demotion
    note, together with the D-16 ill-conditioning caveat.

    Scoped to `_E1_PATH`'s parsed docstring, never to a repository-wide grep:
    the prose in THIS file (and in any plan or summary document) must be
    unable to satisfy or falsify the gate. `_count_references`'s own
    docstring records what happened the last time a source-text check here
    was allowed to see prose it did not mean to see.
    """
    tree = ast.parse(_E1_PATH.read_text(encoding="utf-8"), filename=str(_E1_PATH))
    docstring = ast.get_docstring(tree)
    assert docstring is not None

    # The noise range the domain is stated over.
    assert "0.25" in docstring
    assert "1.2" in docstring
    # The seed count and the geometry the domain is stated over.
    assert "ten seeds" in docstring
    assert "12-camera" in docstring
    # D-16: the caveat, paired with the converged-baseline finding.
    assert "ill-conditioned" in docstring.lower()
    assert "converged" in docstring.lower()
    # D-21: the establishing band is Phase 28 work, not a Phase 25 result.
    assert "Phase 28" in docstring
    # D-13: the anti-confusion note names the 0.5 px isolator.
    assert "normal_fixed" in docstring


# ---------------------------------------------------------------------------
# DEGEN-04 / D-04: the gate-scope rationale must exist at all three gate sites
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]

_GATE_RATIONALE_SITES = (
    _REPO_ROOT / "src" / "aquacal" / "calibration" / "_observability.py",
    _EXPERIMENTS_DIR / "e4_benchmark_grid.py",
    _EXPERIMENTS_DIR / "e6_generalization_sweep.py",
)


def _read(path: Path) -> str:
    """Read a target file's text, skipping cleanly if it is genuinely absent.

    Args:
        path: File to read.

    Returns:
        The file's text content, decoded as UTF-8.
    """
    if not path.is_file():
        pytest.skip(f"target file not found: {path}")
    return path.read_text(encoding="utf-8")


def test_gate_scope_rationale_present_at_all_three_sites():
    """DEGEN-04 / D-04: the authored-vs-given-geometry rationale for keeping the
    degeneracy gate synthetic-only, and the tripwire that would re-open the
    decision, are present at every site a code reader meets the gate.

    The decision itself has no verification criterion -- it is a policy call
    (25-RESEARCH.md). What is checkable, and what this pins, is that the
    reasoning exists beside the gate rather than only in a planning file.

    GREP-HYGIENE NOTE -- the failure mode deliberately avoided here. The
    original `_count_references` above stripped `#`-comment lines and counted
    substrings, so a *docstring* asserting an invariant survived the filter and
    failed the very gate that checked it (see that function's own docstring).
    The mitigation used here is scoping by FILENAME: this assertion reads only
    the three files in `_GATE_RATIONALE_SITES`, and this test module is not one
    of them. Nothing written in this docstring -- including the phrases quoted
    below -- can therefore either satisfy or falsify the assertion. The phrases
    are also required to be present rather than absent, so the polarity is the
    safe one: prose leaking into a scanned file could only ever make a missing
    rationale look present in a file that is supposed to carry it anyway.
    """
    for path in _GATE_RATIONALE_SITES:
        source = _read(path)
        # The decision and the reasoning that licenses it.
        assert "SYNTHETIC-ONLY" in source, f"{path.name} lacks the gate-scope decision"
        assert "authored" in source, f"{path.name} lacks the authored-geometry half"
        assert "given" in source, f"{path.name} lacks the given-geometry half"
        # The tripwire, and the sole source of the count it would be read from.
        assert "camera_model_failure" in source, f"{path.name} lacks the tripwire"
        assert "Phase 29" in source, f"{path.name} lacks the frozen-table reference"
        # The provenance of the evidence, marked provisional (D-02).
        assert "2026-08-17-degeneracy-classification" in source, (
            f"{path.name} does not cite the probe that settled the mechanism"
        )
        assert "D-04" in source, f"{path.name} does not name the decision"
