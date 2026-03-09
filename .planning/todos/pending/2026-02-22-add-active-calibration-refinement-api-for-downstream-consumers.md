---
created: 2026-02-22T20:34:58.004Z
title: Add active calibration refinement API for downstream consumers
area: api
files: []
---

## Problem

AquaCal currently runs calibration as a one-shot pipeline. There is no mechanism for downstream libraries (e.g., 3D pose estimation, stereo reconstruction) to feed observations back into the calibration system for iterative refinement. As real-world usage accumulates data from downstream analyses, the initial calibration could be improved — but there's no API to support this workflow.

## Solution

Design and implement flexible public functions/methods that external libraries can import to trigger calibration refinement based on their analysis results. Key considerations:

- **AquaCal does not generate downstream data** — it only consumes it. The API should accept generic observation types (e.g., reprojection residuals, 3D point correspondences, pose constraints).
- Define clear input contracts (dataclasses/protocols) so consumers know what to provide.
- Support incremental updates (refine existing calibration) rather than requiring full re-calibration.
- Consider both single-camera and multi-camera refinement scenarios.
- Entry points should be importable as `from aquacal import refine_calibration` or similar.
- Preserve the existing pipeline as the primary calibration path; refinement is an optional follow-up.
