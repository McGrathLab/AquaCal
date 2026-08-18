"""Couple the suite driver's stage list to the expectation manifest.

The driver (`experiments/run_experiment_suite.sh`) and the manifest
(`experiments/suite_expectations.json`) each hold a list of stages. Nothing
stops them drifting, and drift in one direction is exactly the audit finding
that produced this phase: F-001 was an invocation that existed in the manifest
of things the paper cites and in NO driver, so a run exited 0 and looked green
while a band CSV was never produced at all.

So the coupling is asserted BIDIRECTIONALLY -- every declared stage has an
expectation entry, and every expectation has an owning stage -- in the shape of
`test_all_committed_csvs_have_a_named_record` /
`test_csv_to_record_has_no_stale_entries` in
`tests/unit/test_experiments_provenance.py`.

Every assertion here is TEXTUAL or over the manifest. This file never executes
the driver: running it would launch the ~22-26 hour experimental suite.
"""

import re
from pathlib import Path

import pytest

from experiments._expectations import load_expectations

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "experiments" / "run_experiment_suite.sh"

# `[^)]*` spans newlines inside a character class, so a multi-line array is
# matched without DOTALL. The array is the driver's single stage declaration.
_STAGES_ARRAY_RE = re.compile(r"STAGES=\(([^)]*)\)")
_STAGE_FUNC_RE = re.compile(r"^run_stage_([a-z0-9_]+)\(\)", re.MULTILINE)
_STATE_FILE_RE = re.compile(r'^\s*STATE_FILE="([^"]*)"', re.MULTILINE)


def _driver_text() -> str:
    """Return the driver's source, skipping the module if it is absent.

    Degrades to a skip rather than a collection error, matching the pattern the
    provenance tests use: a checkout that predates the driver should not turn
    the whole unit suite red.
    """
    if not DRIVER_PATH.exists():
        pytest.skip(f"{DRIVER_PATH} does not exist")
    return DRIVER_PATH.read_text(encoding="utf-8")


def _stage_array(text: str) -> list[str]:
    """Return the ids in the driver's `STAGES=(...)` array, in order."""
    match = _STAGES_ARRAY_RE.search(text)
    assert match is not None, (
        "no STAGES=(...) array found in the driver -- the stage list is the "
        "one declaration this whole test module is built on"
    )
    return match.group(1).split()


def _manifest_stages() -> list[dict]:
    return load_expectations()["stages"]


@pytest.fixture(scope="module")
def driver_text() -> str:
    return _driver_text()


@pytest.fixture(scope="module")
def stage_array(driver_text: str) -> list[str]:
    return _stage_array(driver_text)


@pytest.fixture(scope="module")
def stage_index(stage_array: list[str]) -> dict[str, int]:
    return {name: i for i, name in enumerate(stage_array)}


class TestStageManifestBijection:
    """The driver's stage list and the manifest name the same stages."""

    def test_every_driver_stage_has_a_manifest_entry(self, stage_array):
        known = {stage["id"] for stage in _manifest_stages()}
        unknown = [name for name in stage_array if name not in known]
        assert not unknown, (
            f"the driver declares stage(s) {unknown} with no entry in "
            "experiments/suite_expectations.json -- add them there, or the "
            "completeness gate has no expectation to check them against and "
            "the stage can produce nothing without anyone noticing"
        )

    def test_every_manifest_stage_has_an_owning_driver_stage(self, stage_array):
        declared = set(stage_array)
        orphans = [
            stage["id"] for stage in _manifest_stages() if stage["id"] not in declared
        ]
        assert not orphans, (
            f"manifest stage(s) {orphans} are in no driver -- this is the "
            "exact shape of F-001: an invocation the paper depends on that no "
            "driver ever runs, so the suite exits 0 while the artifact is "
            "never produced. Add a run_stage_<id> function and an entry in "
            "STAGES=(...)"
        )

    def test_every_declared_stage_has_a_function(self, driver_text, stage_array):
        defined = set(_STAGE_FUNC_RE.findall(driver_text))
        missing = [name for name in stage_array if name not in defined]
        assert not missing, (
            f"STAGES lists {missing} but no run_stage_<id> function is defined "
            "for them -- the driver dispatches by name, so these would abort "
            "as UNKNOWN STAGE at run time"
        )

    def test_no_unreferenced_stage_functions(self, driver_text, stage_array):
        defined = set(_STAGE_FUNC_RE.findall(driver_text))
        unreferenced = sorted(defined - set(stage_array))
        assert not unreferenced, (
            f"run_stage_ function(s) {unreferenced} are defined but absent "
            "from STAGES=(...), so they never run. A stage that exists and is "
            "never scheduled is the same silent gap as one that does not exist"
        )


def _assert_precedes(stage_index: dict[str, int], first: str, second: str, why: str):
    """Assert `first` is scheduled before `second`, naming the anchor on failure.

    Missing stages are reported as an assertion rather than a KeyError: a
    dropped stage should read as "this ordering constraint cannot hold", not as
    a broken test.
    """
    for name in (first, second):
        assert name in stage_index, (
            f"stage '{name}' is not in STAGES=(...), so the ordering "
            f"constraint '{first} before {second}' cannot hold. {why}"
        )
    assert stage_index[first] < stage_index[second], (
        f"{first} (index {stage_index[first]}) must precede {second} "
        f"(index {stage_index[second]}). {why}"
    )


class TestStageOrder:
    """The array order respects every declared dependency edge."""

    def test_order_is_topological_over_depends_on(self, stage_index):
        violations = []
        for stage in _manifest_stages():
            name = stage["id"]
            if name not in stage_index:
                continue
            for dep in stage["depends_on"]:
                if dep not in stage_index:
                    continue
                if stage_index[dep] >= stage_index[name]:
                    violations.append(
                        f"{dep} (index {stage_index[dep]}) must precede "
                        f"{name} (index {stage_index[name]})"
                    )
        assert not violations, (
            "STAGES=(...) is not a topological order of the manifest's "
            "depends_on edges: " + "; ".join(violations)
        )

    def test_order_e7_focal_standoff_after_e7_band(self, stage_index):
        _assert_precedes(
            stage_index,
            "e7_band",
            "e7_focal_standoff",
            "O1: e7_focal_standoff_analysis reads the hardcoded, cwd-relative "
            "Path('experiments/results')/interface_ablation_band.csv "
            "(e7_focal_standoff_analysis.py:389), which its docstring says is "
            "deliberately never the --out directory. E7's band must land first.",
        )

    def test_order_reconstruction_bootstrap_after_e2_production(self, stage_index):
        _assert_precedes(
            stage_index,
            "e2_production",
            "reconstruction_bootstrap",
            "O2: reconstruction_bootstrap reads "
            "experiments/results/reconstruction_errors.csv and the hard "
            "REAL_RIG_METRICS_PATH = "
            "Path('experiments/results/real_rig_metrics.json') "
            "(reconstruction_bootstrap.py:56), both written by e2_production.",
        )

    def test_order_e4_after_e2_production(self, stage_index):
        _assert_precedes(
            stage_index,
            "e2_production",
            "e4",
            "O4, and this one is a SILENT WRONG NUMBER rather than a crash: "
            "resolve_e2_benchmark_path (e4_benchmark_grid.py:298) quietly "
            "drops the real-rig row when E2's benchmark.json is absent, and "
            "benchmark_grid.csv comes back with 9 rows instead of 10.",
        )

    def test_order_e6_band_after_e6_repeat1(self, stage_index):
        _assert_precedes(
            stage_index,
            "e6_repeat1",
            "e6_band",
            "D-52 constraint 1: e6_repeat1 and e6_band must never overlap. "
            "e6_repeat1 wipes E6's artifacts under the shared out dir before "
            "running, which would destroy a band running concurrently.",
        )


class TestDriverSafetyRails:
    """The rails whose absence has already cost this project a run."""

    def test_e6_repeat2_is_not_a_stage(self, driver_text, stage_array):
        assert "e6_repeat2" not in stage_array, (
            "D-42 reverses D-09: e6_repeat2 is not part of the v2.1 suite"
        )
        assert "run_stage_e6_repeat2" not in driver_text, (
            "D-42: e6_repeat2 must not be defined as a stage function. Its "
            "ISOLATION TEMPLATE may stay as a comment -- that is the point of "
            "keeping it -- but a defined function invites re-adding it"
        )
        assert {stage["id"] for stage in _manifest_stages()}.isdisjoint(
            {"e6_repeat2"}
        ), "D-42: e6_repeat2 must not appear in the expectation manifest either"

    def test_gate_never_runs_under_a_bare_python(self, driver_text):
        offenders = [
            line.strip()
            for line in driver_text.splitlines()
            if "check_rerun_gates" in line
            and not line.strip().startswith("#")
            and re.search(r"(^|[^\w\"}/])python\s", line)
        ]
        assert not offenders, (
            "check_rerun_gates.py must be invoked through the pinned "
            f'"${{GATE_PYTHON}}", never a bare `python`: {offenders}. It '
            "imports pandas AND aquacal, and Git Bash's `python` is Anaconda "
            "base on the planning box -- this was a real rerun_19_3.sh defect, "
            "fixed in 19.4/19.5, and it turns a gate into a silent ImportError"
        )

    def test_dry_run_state_path_differs_from_the_real_one(self, driver_text):
        assignments = _STATE_FILE_RE.findall(driver_text)
        assert len(assignments) == 2, (
            "expected exactly two STATE_FILE assignments (the dry-run branch "
            f"and the real one), found {len(assignments)}: {assignments}"
        )
        assert len(set(assignments)) == 2, (
            "the dry-run and real STATE_FILE paths are IDENTICAL. A dry run "
            '"completes" every stage in about a second, so the state file it '
            "leaves makes the next REAL launch a silent no-op: every stage "
            "skipped, exit 0, no artifacts, and a queue that looks like it "
            "succeeded. Separate paths are the structural fix; remembering to "
            "delete the file is not"
        )
        assert any("dryrun" in path for path in assignments), (
            f"neither STATE_FILE path is marked as the dry-run one: {assignments}"
        )

    def test_state_path_embeds_the_frozen_sha(self, driver_text):
        assignments = _STATE_FILE_RE.findall(driver_text)
        assert all("${FROZEN_SHA}" in path for path in assignments), (
            "D-23 as halved by D-48: the state file path must embed the frozen "
            "short sha, so a state file written at another commit is "
            f"structurally unreachable rather than merely detected: {assignments}"
        )
        assert 'FROZEN_SHA="$(git rev-parse --short HEAD' in driver_text, (
            "FROZEN_SHA must be derived from git rev-parse --short HEAD"
        )

    def test_every_stage_routes_through_the_dry_run_seam(
        self, driver_text, stage_array
    ):
        bodies = re.findall(
            r"^run_stage_([a-z0-9_]+)\(\) \{(.*?)^\}", driver_text, re.S | re.M
        )
        missing = [name for name, body in bodies if "_dry_run_active" not in body]
        assert not missing, (
            f"stage function(s) {missing} do not consult _dry_run_active, so a "
            "dry run would execute them for real. Plan 26-08's dry-run tests "
            "depend on the seam being universal"
        )

    def test_no_stage_destroys_anything_before_the_dry_run_seam(self, driver_text):
        """A dry run must never delete an artifact.

        rerun_19_3.sh's e6_repeat1 ran its `rm -rf`/`rm -f` cleanup
        unconditionally and only THEN consulted the dry-run seam, so a
        control-flow rehearsal deleted committed files under the tracked
        experiments/results tree. rerun_19_4.sh fixed it. This asserts the fix
        did not regress when the stage was lifted.
        """
        bodies = re.findall(
            r"^run_stage_([a-z0-9_]+)\(\) \{(.*?)^\}", driver_text, re.S | re.M
        )
        offenders = []
        for name, body in bodies:
            code = [
                line for line in body.splitlines() if not line.strip().startswith("#")
            ]
            seam = next(
                (i for i, line in enumerate(code) if "_dry_run_active" in line),
                len(code),
            )
            head = "\n".join(code[:seam])
            if re.search(r"\brm\b|\bmkdir\b", head):
                offenders.append(name)
        assert not offenders, (
            f"stage function(s) {offenders} run a destructive command BEFORE "
            "checking _dry_run_active, so a dry run would delete real "
            "artifacts. Move the dry-run branch above the cleanup"
        )

    def test_every_experiment_invocation_is_unbuffered(self, driver_text):
        buffered = [
            line.strip()
            for line in driver_text.splitlines()
            if re.search(r"(^|[^\w-])python -m experiments\.", line)
            and not line.strip().startswith("#")
        ]
        assert not buffered, (
            f"these invocations lack the -u flag: {buffered}. Python "
            "block-buffers stdout to a pipe, so a detached run's log is empty "
            "whether it is progressing normally or hung on the first video -- "
            "the two are indistinguishable and a real stall stays invisible"
        )
