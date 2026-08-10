"""Deterministic every-Nth-frame AVI -> lossless PNG frame extractor.

This is a data-prep utility, not part of the `aquacal` public API. It is the
producer of the Zenodo `real-rig` archive frameset: it reads synchronized
per-camera `.avi` recordings and writes every Nth decoded frame as a lossless
PNG into per-camera output directories, in the layout `aquacal.io.images.
ImageSet` reads back (`<out-dir>/<camera>/frame%04d.png`, natsort-stable).

Not intended to be imported. Run it directly:

    python scripts/extract_frames.py --video-dir raw_videos/extrinsics \\
        --out-dir staged/extrinsic --step 30
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import cv2

from aquacal.io.video import VideoSet

logger = logging.getLogger(__name__)

_CAMERA_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
_PROGRESS_INTERVAL = 25

# Maximum PNG compression. PNG is lossless at every level, so this trades encode
# time for archive size only. The D-07 sizing decision (~1,205 KB/frame, ~4.0 GB
# for the extrinsic frameset) was computed at this level; OpenCV's default writes
# frames roughly 2x larger, which would push the archive past the size band
# 21-06's acceptance criteria assert.
_PNG_COMPRESSION = 9


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured `argparse.ArgumentParser` for this script.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video-dir",
        type=Path,
        required=True,
        help="Directory of *.avi files, one per camera.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Destination root; per-camera subdirectories are created under it.",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=30,
        help="Extract every Nth frame (default 30, matching the release run).",
    )
    parser.add_argument(
        "--cameras",
        type=str,
        default=None,
        help="Comma-separated subset of camera ids to extract. "
        "Default is every *.avi found in --video-dir.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N written frames per camera. Smoke-test aid only -- "
        "the production run must not pass it.",
    )
    parser.add_argument(
        "--allow-ragged",
        action="store_true",
        help="Allow per-camera written-frame counts to differ (intrinsic "
        "videos are not synchronized in length; extrinsic videos must match).",
    )
    return parser


def _camera_id_from_path(avi_path: Path) -> str:
    """Derive a camera id from an AVI filename stem.

    The camera id is the filename stem up to the first `-`, e.g.
    `e3v829d-20260210T104839-105301.avi` -> `e3v829d`.

    Args:
        avi_path: Path to a `.avi` file.

    Returns:
        Camera id string.
    """
    return avi_path.stem.split("-", 1)[0]


def _discover_video_paths(video_dir: Path, cameras: str | None) -> dict[str, str]:
    """Discover per-camera AVI paths under `video_dir`.

    Args:
        video_dir: Directory of `*.avi` files, one per camera.
        cameras: Optional comma-separated subset of camera ids to keep.

    Returns:
        Dict mapping camera id to `.avi` file path, sorted by camera id.

    Raises:
        ValueError: If a derived camera id fails validation, or a requested
            camera in `cameras` is not found.
    """
    avi_paths = sorted(video_dir.glob("*.avi"))
    video_paths: dict[str, str] = {}
    for avi_path in avi_paths:
        cam = _camera_id_from_path(avi_path)
        if not _CAMERA_ID_PATTERN.fullmatch(cam):
            raise ValueError(
                f"Derived camera id {cam!r} from {avi_path.name!r} contains "
                "characters outside [A-Za-z0-9_-]; refusing to use it as a "
                "directory name."
            )
        video_paths[cam] = str(avi_path)

    if cameras is not None:
        requested = [c.strip() for c in cameras.split(",") if c.strip()]
        missing = [c for c in requested if c not in video_paths]
        if missing:
            raise ValueError(f"Requested cameras not found in {video_dir}: {missing}")
        video_paths = {c: video_paths[c] for c in requested}

    return dict(sorted(video_paths.items()))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python scripts/extract_frames.py`.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]` via `argparse`).

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        video_paths = _discover_video_paths(args.video_dir, args.cameras)
    except ValueError as exc:
        logger.error("ERROR: %s", exc)
        return 1

    if not video_paths:
        logger.error("ERROR: no *.avi files found in %s", args.video_dir)
        return 1

    out_dir: Path = args.out_dir
    for cam in video_paths:
        (out_dir / cam).mkdir(parents=True, exist_ok=True)

    written: dict[str, int] = {cam: 0 for cam in video_paths}

    vs = VideoSet(video_paths)
    for _frame_idx, frames in vs.iterate_frames(step=args.step):
        for cam, frame in frames.items():
            if frame is None:
                continue
            if args.limit is not None and written[cam] >= args.limit:
                continue
            dest = out_dir / cam / f"frame{written[cam]:04d}.png"
            ok = cv2.imwrite(
                str(dest), frame, [cv2.IMWRITE_PNG_COMPRESSION, _PNG_COMPRESSION]
            )
            if not ok:
                logger.error("ERROR: failed to write frame to %s", dest)
                return 1
            written[cam] += 1
            if written[cam] % _PROGRESS_INTERVAL == 0:
                logger.info("%s: %d frames written so far", cam, written[cam])

        if args.limit is not None and all(
            written[cam] >= args.limit for cam in video_paths
        ):
            break

    for cam, count in written.items():
        if count == 0:
            logger.error(
                "ERROR: camera %s produced 0 frames -- is this the AquaCal conda env?",
                cam,
            )
            return 1

    counts = set(written.values())
    if len(counts) > 1 and not args.allow_ragged:
        for cam, count in written.items():
            logger.error("%s: %d frames written", cam, count)
        logger.error(
            "ERROR: per-camera written counts differ; pass --allow-ragged "
            "if this is expected (e.g. intrinsic videos of differing length)."
        )
        return 1

    total_bytes = 0
    for cam, count in written.items():
        logger.info("%s: wrote %d frames", cam, count)
        for i in range(count):
            total_bytes += (out_dir / cam / f"frame{i:04d}.png").stat().st_size

    logger.info(
        "TOTAL: %d cameras, %d frames, %d bytes",
        len(written),
        sum(written.values()),
        total_bytes,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
