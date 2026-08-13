"""Example dataset loading and management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aquacal.config.schema import CalibrationResult
from aquacal.datasets._manifest import get_dataset_info
from aquacal.datasets.download import download_and_extract


@dataclass
class ExampleDataset:
    """Example calibration dataset downloaded from Zenodo.

    Attributes:
        name: Dataset name (e.g., 'real-rig')
        type: Dataset type ('real')
        reference_calibration: Optional reference calibration result
        metadata: Additional metadata about the dataset
        cache_path: Path to cached dataset files
    """

    name: str
    type: str
    reference_calibration: CalibrationResult | None = None
    metadata: dict = field(default_factory=dict)
    cache_path: Path | None = None


def load_example(name: str) -> ExampleDataset:
    """Load an example calibration dataset.

    Downloads datasets from Zenodo on first use and caches them locally.

    Args:
        name: Dataset name. Available options:
            - 'real-rig': Real hardware calibration (Zenodo download)

    Returns:
        ExampleDataset with reference calibration and cache path

    Raises:
        ValueError: If dataset name is not recognized

    Note:
        The `'real-rig'` archive's `reference_outputs/` were produced under
        **OpenCV 4.13.0**. ChArUco corner detection is entirely OpenCV's
        (`cv2.aruco.CharucoDetector`), and it changes across minor versions:
        measured between 4.13.0 and 4.14.0, 1.95% fewer corner observations
        were detected and the reconstruction RMSE moved by +7.8%. So a re-run
        against this dataset reproduces the archived reference values on
        4.13.0 and can differ from them at the ~1-10% level on another minor
        version, with neither version's corner set being the correct one.
        `aquacal` pins `opencv-python==4.13.*` for that reason, and each run's
        own `benchmark.json` records the version it used under
        `environment.opencv_version`.

    Examples:
        >>> from aquacal.datasets import load_example
        >>> ds = load_example('real-rig')
        >>> print(ds.cache_path)
    """
    # Get dataset metadata from manifest
    dataset_info = get_dataset_info(name)

    # Download and extract (cached)
    _cache_path = download_and_extract(name, dataset_info)

    # Handle nested directory structure (Zenodo archives often have top-level folder)
    if (_cache_path / name).exists():
        actual_path = _cache_path / name
    else:
        actual_path = _cache_path

    # Load reference calibration if available
    reference_calibration = None
    ref_calib_file = actual_path / "reference_calibration.json"
    if ref_calib_file.exists():
        with open(ref_calib_file, encoding="utf-8") as f:
            ref_data = json.load(f)
        # TODO: Deserialize CalibrationResult from JSON
        # For now, just store the raw dict
        reference_calibration = ref_data

    # Read config for metadata
    import yaml

    config_file = actual_path / "config.yaml"
    if config_file.exists():
        with open(config_file, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        camera_names = config_data.get("cameras", [])
    else:
        camera_names = []

    return ExampleDataset(
        name=name,
        type=dataset_info["type"],
        reference_calibration=reference_calibration,
        metadata={
            "description": dataset_info["description"],
            "dataset_path": str(actual_path),
            "camera_names": camera_names,
            "has_reference_calibration": ref_calib_file.exists(),
        },
        cache_path=actual_path,
    )
