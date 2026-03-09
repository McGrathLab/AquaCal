"""Synthetic and example datasets for AquaCal.

This module provides utilities for generating synthetic calibration data with
known ground truth, and loading example datasets for testing and validation.

Synthetic Data Generation
-------------------------
Use ``create_scenario()`` to create predefined test scenarios::

    from aquacal.datasets import create_scenario

    scenario = create_scenario('ideal')
    print(f"{len(scenario.intrinsics)} cameras")
    print(f"{len(scenario.board_poses)} frames")

Example Dataset Loading
------------------------
Use ``load_example()`` to load downloadable example datasets::

    from aquacal.datasets import load_example

    ds = load_example('real-rig')
    print(f"Cache path: {ds.cache_path}")

Cache Management
----------------
Downloaded datasets are cached in ``./aquacal_data/``::

    from aquacal.datasets import get_cache_info, clear_cache

    # Check cache status
    info = get_cache_info()
    print(f"Cached datasets: {info['cached_datasets']}")

    # Clear entire cache
    clear_cache()
"""

from aquacal.datasets._manifest import list_datasets
from aquacal.datasets.download import clear_cache, get_cache_info
from aquacal.datasets.loader import ExampleDataset, load_example
from aquacal.datasets.synthetic import (
    SyntheticScenario,
    create_scenario,
    generate_synthetic_detections,
)

__all__ = [
    "create_scenario",
    "generate_synthetic_detections",
    "SyntheticScenario",
    "load_example",
    "ExampleDataset",
    "list_datasets",
    "clear_cache",
    "get_cache_info",
]
