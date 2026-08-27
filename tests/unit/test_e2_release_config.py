"""The committed E2 release config (D-11).

Until Phase 27 the exact inputs of the run that produces the manuscript's
Section 3 numbers lived at an absolute Windows path OUTSIDE the repository --
provenance stored beside the artifact instead of inside it, which is the F-001
shape. `experiments/configs/e2_release_linux.yaml` closes that, and this file is
what makes the closure enforceable rather than asserted.

Two of these tests are structural (13 + 13 declared paths, the frame_step /
max_calibration_frames signature). The important one is not: it RUNS
`emit_invocation_configs` against the committed config, because the three
questions the config had to answer -- does the release-tree write refusal fire
from `experiments/configs/`, does the variant builder need a base `internals`
block, is `paths.output_dir` present -- are all answered by the emitter's
behaviour and none of them by reading the file.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

yaml = pytest.importorskip("yaml")

from experiments.e2_real_rig import (  # noqa: E402  (after the yaml guard)
    E2_INVOCATION_VARIANTS,
    emit_invocation_configs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "experiments" / "configs" / "e2_release_linux.yaml"

#: The frameset signature pre-flight asserts, as `suite_expectations.json`
#: records it: "13 x 262 extrinsic frames at frame_step: 1 /
#: max_calibration_frames: 200". Only the two config-side halves are checked
#: here; the frame counts are the frameset's, not the config's.
EXPECTED_N_CAMERAS = 13
EXPECTED_FRAME_STEP = 1
EXPECTED_MAX_CALIBRATION_FRAMES = 200


@pytest.fixture(scope="module")
def config() -> dict:
    assert CONFIG_PATH.is_file(), (
        f"{CONFIG_PATH} does not exist. D-11 requires the E2 release config to "
        "live INSIDE the frozen sha; the driver's E2_RELEASE_CONFIG default "
        "points at it"
    )
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


class TestTheConfigParsesAndCarriesTheSignature:
    def test_it_declares_thirteen_extrinsic_and_thirteen_intrinsic_paths(self, config):
        """12 main cameras + 1 auxiliary, which is `n_extrinsic_videos: 13`."""
        paths = config["paths"]
        assert len(paths["extrinsic_videos"]) == EXPECTED_N_CAMERAS
        assert len(paths["intrinsic_videos"]) == EXPECTED_N_CAMERAS
        assert set(paths["extrinsic_videos"]) == set(paths["intrinsic_videos"]), (
            "the two path maps name different cameras"
        )

    def test_the_camera_lists_and_the_path_maps_agree(self, config):
        declared = set(config["cameras"]) | set(config["auxiliary_cameras"])
        assert declared == set(config["paths"]["extrinsic_videos"]), (
            "a camera is named in `cameras`/`auxiliary_cameras` with no "
            "extrinsic path, or vice versa"
        )

    def test_frame_step_is_one_over_already_subsampled_images(self, config):
        """NOT a discrepancy with the retired Desktop config's `frame_step: 30`.

        These frames are already subsampled at every 30th video frame, so 1 over
        the images equals 30 over the source video. 27-01 dissolved D-11's
        flagged discrepancy this way.
        """
        assert config["detection"]["frame_step"] == EXPECTED_FRAME_STEP

    def test_max_calibration_frames_matches_the_asserted_signature(self, config):
        assert (
            config["optimization"]["max_calibration_frames"]
            == EXPECTED_MAX_CALIBRATION_FRAMES
        )

    def test_a_top_level_paths_output_dir_line_exists(self, config):
        """`build_internals_variant_config` RAISES without one."""
        assert config["paths"].get("output_dir")

    def test_every_declared_path_is_absolute(self, config):
        """The probe resolves against the DRIVER'S CWD, not the config's dir.

        Under D-01/D-05 the driver runs from the frozen clone and the image set
        lives elsewhere, so a relative path here makes `_preflight_frameset`
        report ABSENT and the calibration fail on its first read.

        Absoluteness is judged with `PurePosixPath`, DELIBERATELY: this config
        describes the Linux run machine, and `pathlib.Path("/home/...")` on
        Windows is a drive-less `WindowsPath` whose `.is_absolute()` is False.
        Judging it with the running platform's flavour would make this test
        assert the opposite thing depending on where it ran.
        """
        paths = config["paths"]
        declared = list(paths["extrinsic_videos"].values()) + list(
            paths["intrinsic_videos"].values()
        )
        relative = [p for p in declared if not PurePosixPath(p).is_absolute()]
        assert not relative, f"these declared paths are not absolute: {relative}"

    def test_the_config_carries_no_base_internals_block(self, config):
        """D-11 decision 3, asserted rather than assumed.

        The three variants set `log_all_observation_depths` and
        `benchmark_memory` themselves; a base block would be a fourth place for
        them to disagree.
        """
        assert "internals" not in config


class TestTheInvocationEmitterAcceptsIt:
    """The question the file itself cannot answer.

    `emit_invocation_configs` refuses when its target resolves to, or inside,
    the source config's own directory (T-19.5-07-01 / T-26-17). Placing the
    config at `experiments/configs/` rather than `experiments/` is what keeps
    the default target (`experiments/results_e2_invocations`) a SIBLING rather
    than a CHILD -- and the only honest way to check that is to run the emitter.
    """

    def test_it_emits_three_variants_without_raising(self, tmp_path):
        written = emit_invocation_configs(CONFIG_PATH, tmp_path)
        assert [p.name for p in written] == [
            spec["filename"] for spec in E2_INVOCATION_VARIANTS
        ]
        for path in written:
            assert path.is_file()

    def test_the_default_invocation_dir_is_not_inside_the_config_dir(self):
        """The refusal's own predicate, evaluated on the SHIPPED default.

        `E2_INVOCATION_DIR` defaults to `experiments/results_e2_invocations` in
        the driver. If the config's directory were an ancestor of it, every real
        run would die in the emitter rather than in a test.
        """
        source_dir = CONFIG_PATH.parent.resolve()
        target = (REPO_ROOT / "experiments" / "results_e2_invocations").resolve()
        assert target != source_dir
        assert source_dir not in target.parents

    def test_only_the_classification_variant_logs_observation_depths(self, tmp_path):
        """D-16: the ~11 MB sidecar rides the classification run ONLY."""
        written = emit_invocation_configs(CONFIG_PATH, tmp_path)
        by_name = {
            spec["name"]: path
            for spec, path in zip(E2_INVOCATION_VARIANTS, written, strict=True)
        }
        loaded = {
            name: yaml.safe_load(path.read_text(encoding="utf-8"))
            for name, path in by_name.items()
        }
        assert loaded["classification"]["internals"]["log_all_observation_depths"]
        assert not loaded["timing"]["internals"]["log_all_observation_depths"]
        assert not loaded["memory"]["internals"]["log_all_observation_depths"]

    def test_timing_and_memory_never_share_an_invocation(self, tmp_path):
        """D-15: one run cannot honestly produce both numbers."""
        written = emit_invocation_configs(CONFIG_PATH, tmp_path)
        for path in written:
            internals = yaml.safe_load(path.read_text(encoding="utf-8"))["internals"]
            assert not (
                internals["benchmark_memory"]
                and internals["log_all_observation_depths"]
            ), f"{path.name} carries both perturbing internals keys"

    def test_each_variant_keeps_the_signature_and_the_declared_paths(self, tmp_path):
        """The variants differ in output_dir and two internals keys, nothing else."""
        written = emit_invocation_configs(CONFIG_PATH, tmp_path)
        source = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        for path in written:
            variant = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert variant["detection"]["frame_step"] == EXPECTED_FRAME_STEP
            assert (
                variant["optimization"]["max_calibration_frames"]
                == EXPECTED_MAX_CALIBRATION_FRAMES
            )
            assert (
                variant["paths"]["extrinsic_videos"]
                == source["paths"]["extrinsic_videos"]
            )
            assert variant["paths"]["output_dir"] != source["paths"]["output_dir"]
