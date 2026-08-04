"""Generate the frozen numerical anchor for plan 19.2-26.

Run this from a checkout that does NOT contain plan 19.2-26's counter edits, and commit
the resulting JSON before touching any source file. The commit ordering is the evidence
that the anchor predates the change it guards -- an anchor generated after the edit is
self-confirming and would pass against any change, including a wrong one (T-19.2-38).

Usage:
    python -m tests.fixtures.generate_discard_anchor
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import calibrate_synthetic

ANCHOR_PATH = Path(__file__).parent / "discard_anchor.json"

# Matches tests/unit/test_datasets_pipelines.py's established harness so the anchor
# exercises the same deterministic path the existing bit-identity tests use.
MINIMAL_KWARGS = dict(n_water=1.0, refine_intrinsics=False, seed=1)


_NOTE_PLACEHOLDER = (
    "PROVENANCE CHAIN MISSING -- no prior anchor was on disk when this file was "
    "generated. Record why this anchor was (re)generated, and the before/after "
    "values, before committing."
)


def _existing_note() -> str:
    """Return the note from the anchor already on disk, if there is one.

    Regenerating the anchor must not discard the hand-curated provenance chain.
    An earlier version of this script hardcoded a fixed note string, so every
    regeneration silently overwrote that chain -- it happened in plan 19.3-04 and
    again in 19.4-02, and both times the note had to be reconstructed by hand
    while two other files still pointed at it for values it no longer held.
    """
    if not ANCHOR_PATH.is_file():
        return _NOTE_PLACEHOLDER
    try:
        prior = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _NOTE_PLACEHOLDER
    note = prior.get("provenance", {}).get("note")
    return note if isinstance(note, str) and note.strip() else _NOTE_PLACEHOLDER


def compute_anchor() -> dict:
    """Calibrate the deterministic 'minimal' scenario and extract exact values."""
    scenario = create_scenario("minimal", seed=1)
    result, _ = calibrate_synthetic(scenario, **MINIMAL_KWARGS)

    cameras = {}
    for name in sorted(result.cameras):
        cam = result.cameras[name]
        cameras[name] = {
            "R": np.asarray(cam.extrinsics.R, dtype=float).tolist(),
            "t": np.asarray(cam.extrinsics.t, dtype=float).tolist(),
            "water_z": float(cam.water_z),
        }

    return {
        "provenance": {
            "sha": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "scenario": "minimal",
            "kwargs": {k: str(v) for k, v in MINIMAL_KWARGS.items()},
            # The note carries a hand-curated provenance chain -- one entry per
            # intentional regeneration, with the before/after values. Both
            # `tests/unit/test_discard_accounting.py::test_matches_frozen_anchor`
            # and this file's own history point readers here for those values,
            # so a hardcoded default would silently break those references.
            # Carry the existing note forward; the regenerating plan appends its
            # own entry by hand.
            "note": _existing_note(),
        },
        "reprojection_error_rms": float(result.diagnostics.reprojection_error_rms),
        "cameras": cameras,
    }


if __name__ == "__main__":
    anchor = compute_anchor()
    ANCHOR_PATH.write_text(json.dumps(anchor, indent=2, sort_keys=True) + "\n")
    print(f"wrote {ANCHOR_PATH}")
    print(f"  sha        : {anchor['provenance']['sha']}")
    print(f"  cameras    : {len(anchor['cameras'])}")
    print(f"  rms        : {anchor['reprojection_error_rms']!r}")
