# Tutorials

Two fast, synthetic-only Jupyter notebooks demonstrating AquaCal's calibration pipeline, plus a
written command-line walkthrough that calibrates the published real-rig dataset from Zenodo.

Each tutorial is self-contained and can be run locally; the notebooks can also run on Google Colab.

## Tutorial 01: Calibrate Your Rig

End-to-end calibration from data loading to validated 3D results, using fast synthetic data.
Covers ChArUco detection, intrinsic/extrinsic initialization, joint refractive bundle adjustment,
and a built-in diagnostics section for interpreting reprojection errors, checking interface
distance recovery, and troubleshooting common issues.

**Start here** if you want to calibrate a synthetic underwater multi-camera rig.

## Tutorial 02: Why Refractive Calibration Matters

Controlled synthetic experiments that quantify what you gain from modeling Snell's law refraction. Compares refractive vs non-refractive calibration on the same data — showing how non-refractive models introduce systematic bias in focal length and camera position even when reprojection error looks acceptable.

**Start here** if you want to understand when the refractive model is essential and how to validate parameter recovery accuracy.

## Tutorial 03: Calibrate the Real Rig from the Command Line

A written, end-to-end command-line walkthrough that downloads the published real-rig dataset
from Zenodo and calibrates it entirely with `aquacal` CLI commands, reproducing the numbers
published in the AquaCal paper's Section 3. Reproduction requires the archive's
`config_paper.yaml`; the quickstart config deliberately does not reproduce them.

**Start here** if you want to reproduce the published results or drive AquaCal from the command
line.

:::{toctree}
:maxdepth: 1
:hidden:

01_full_pipeline
02_synthetic_validation
03_cli_walkthrough
:::
