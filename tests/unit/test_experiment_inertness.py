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

from pathlib import Path

from aquacal.datasets.synthetic import create_scenario

_EXPERIMENTS_DIR = Path(__file__).resolve().parents[2] / "experiments"

_E1_PATH = _EXPERIMENTS_DIR / "e1_refractive_comparison.py"
_E3_PATH = _EXPERIMENTS_DIR / "e3_derived_quantities.py"
_E5_PATH = _EXPERIMENTS_DIR / "e5_index_sensitivity.py"
_E7_PATH = _EXPERIMENTS_DIR / "e7_interface_ablation.py"


def _non_comment_lines(path: Path) -> list[str]:
    """Source lines with `#`-prefixed (post-strip) comment lines filtered
    out, so a docstring or comment MENTIONING the symbol cannot
    self-invalidate the gate -- only a real reference (import, call) counts.
    """
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#")
    ]


def _count_references(path: Path, symbol: str) -> int:
    """Count of `symbol` appearing in `path`'s non-comment source text.

    Intentionally coarse (substring count on non-comment lines, not an AST
    walk): the point is "does this experiment reference the symbol AT ALL
    in live code", not a precise call-site enumeration.
    """
    return sum(line.count(symbol) for line in _non_comment_lines(path))


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
