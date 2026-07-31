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
            "note": (
                "Generated BEFORE plan 19.2-26's counter edits. Regenerating this file "
                "from instrumented code destroys the guarantee it exists to provide."
            ),
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
