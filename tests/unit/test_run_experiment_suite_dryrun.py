"""The suite driver's first automated test, ever.

`experiments/run_experiment_suite.sh` schedules a 22-26 hour run and until now
nothing tested it. The `RUN_EXPERIMENT_SUITE_DRY_RUN` seam existed and had only
ever been driven by hand, which is why the 19.3 defect it was built to catch --
a dry run leaving a state file that makes the next REAL launch a silent no-op --
was found by inspecting leftovers rather than by a test.

**EVERY invocation in this file runs under the dry-run seam.** No test here runs
an experiment, and none may: the real driver runs the full suite. The seam
substitutes `RUN_EXPERIMENT_SUITE_DRY_RUN_CMD` for every stage body and every
gate call, so a whole 20-stage queue completes in a couple of seconds. Every
`subprocess.run` carries an explicit `timeout=` so a driver that hangs fails the
test instead of hanging the suite.

What is actually being asserted, and why it is asserted THIS way
---------------------------------------------------------------
The concurrency constraints (D-52) are read off the state file's ISO stamps, not
off a mock, because the state file is the artifact an operator debugs a real run
from and a mock would prove only that the mock agrees with itself.

The ordering assertions run under the POOLED scheduler specifically. Serial mode
structurally cannot exhibit an overlap, so a serial-only assertion proves
nothing about the constraint. `e6_band` after `e6_repeat1` is the sharpest case:
`run_stage_e6_repeat1` does `rm -rf ${OUT_DIR}/e6_configs` and removes
`generalization_sweep.csv` / `e6_provenance.json` under the SHARED `OUT_DIR`
that `e6_band` also writes, so an overlap there is a real `rm -rf` collision
mid-band, not a bookkeeping error.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from experiments._expectations import load_expectations

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "experiments" / "run_experiment_suite.sh"

#: Every `subprocess.run` in this file passes this explicitly. A driver that
#: hangs must fail the test, never hang the suite -- the failure mode CLAUDE.md
#: warns about at length.
DRIVER_TIMEOUT_S = 120

#: The dry-run substitute for every stage body and every gate call. It records
#: one marker line per invocation so a test can assert WHICH stages ran without
#: any experiment running, then sleeps briefly -- but only for stage bodies, so
#: real overlap is observable at the state file's millisecond resolution while
#: the whole queue still finishes in seconds.
#:
#: `name`, `stage_name` and `invocation` are the driver's own locals, visible to
#: the stub through bash's dynamic scoping: `stage_name` is set only inside
#: `run_gate_check`, which is what distinguishes a gate call from a stage body.
_STUB = (
    'printf \'stub\\t%s\\t%s\\t%s\\n\' "${name:-}" "${stage_name:-}" '
    '"${invocation:-}" >>"${SUITE_MARKER}"; '
    'if [ -z "${stage_name:-}" ]; then sleep 0.08; fi'
)


def _candidate_bashes() -> list[str]:
    """Every plausible `bash`, most likely first.

    `subprocess` must NOT be handed a bare "bash" on Windows: CreateProcess
    searches System32 before PATH, so it finds WSL's `bash.exe`, which cannot
    see a `C:/...` path at all and fails with a bare "No such file or
    directory" naming a file that plainly exists. The driver is a Git Bash
    (MINGW64) script and CLAUDE.md pins the shell, so the interpreter is
    resolved explicitly here and verified to actually see the driver.
    """
    candidates = []
    override = os.environ.get("SUITE_TEST_BASH")
    if override:
        candidates.append(override)
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    candidates += [
        "C:/Program Files/Git/usr/bin/bash.exe",
        "C:/Program Files/Git/bin/bash.exe",
        "/usr/bin/bash",
        "/bin/bash",
    ]
    return [c for c in candidates if "system32" not in c.lower()]


def _resolve_bash() -> str:
    """The first candidate bash that can see the driver, or skip the module."""
    for candidate in _candidate_bashes():
        try:
            probe = subprocess.run(
                [candidate, "-c", f'test -f "{DRIVER_PATH.as_posix()}"'],
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return candidate
    pytest.skip(  # pragma: no cover - environment guard
        "no bash on this machine can see "
        f"{DRIVER_PATH.as_posix()}; the driver is a Git Bash (MINGW64) script"
    )


def _frozen_sha() -> str:
    """The short sha the driver derives its state-file path from."""
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=DRIVER_TIMEOUT_S,
    ).stdout.strip()


@dataclass(frozen=True)
class StageEvent:
    """One line of the driver's state TSV."""

    name: str
    index: int
    event: str
    when: datetime
    exit_code: str


@dataclass
class DriverRun:
    """The outcome of one dry-run driver invocation."""

    returncode: int
    stdout: str
    state_dir: Path
    out_dir: Path
    state_file: Path
    real_state_file: Path
    marker_file: Path
    events: list[StageEvent] = field(default_factory=list)

    def starts(self) -> dict[str, datetime]:
        return {e.name: e.when for e in self.events if e.event == "start"}

    def completions(self) -> dict[str, datetime]:
        return {e.name: e.when for e in self.events if e.event == "complete"}

    def intervals(self) -> dict[str, tuple[datetime, datetime]]:
        """`{stage: (start, complete)}` for every stage that did both."""
        starts, completions = self.starts(), self.completions()
        return {
            name: (starts[name], completions[name])
            for name in starts
            if name in completions
        }

    def marker_lines(self) -> list[tuple[str, str, str]]:
        """`(name, stage_name, invocation)` per stub invocation, in order."""
        if not self.marker_file.exists():
            return []
        rows = []
        for line in self.marker_file.read_text(encoding="utf-8").splitlines():
            if not line.startswith("stub\t"):
                continue
            parts = line.split("\t")
            parts += [""] * (4 - len(parts))
            rows.append((parts[1], parts[2], parts[3]))
        return rows

    def stage_invocations(self) -> list[str]:
        """The stage bodies that ran (gate calls have a non-empty stage_name)."""
        return [name for name, stage_name, _ in self.marker_lines() if not stage_name]

    def gate_invocations(self) -> list[str]:
        return [stage for _, stage, _ in self.marker_lines() if stage]


def _parse_iso(text: str) -> datetime:
    """Parse the driver's stamp, which is ISO-8601 with a trailing `Z`.

    Millisecond resolution matters here and is why the driver writes it: at
    whole-second resolution every stage of a dry run shares a stamp, and a tie
    cannot distinguish "ordered correctly" from "overlapped".
    """
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _parse_state(path: Path) -> list[StageEvent]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        assert len(parts) >= 4, f"malformed state line: {line!r}"
        events.append(
            StageEvent(
                name=parts[0],
                index=int(parts[1]),
                event=parts[2],
                when=_parse_iso(parts[3]),
                exit_code=parts[4] if len(parts) > 4 else "",
            )
        )
    return events


def run_driver(
    sandbox: Path,
    *,
    args: tuple[str, ...] = (),
    stub: str = _STUB,
    serial: bool = False,
    extra_env: dict[str, str] | None = None,
    timeout: int = DRIVER_TIMEOUT_S,
) -> DriverRun:
    """Invoke the driver ONCE, under the dry-run seam, fully sandboxed.

    The output tree and the state directory are both redirected into `sandbox`
    via the driver's `SUITE_OUT_DIR` / `SUITE_STATE_DIR` overrides, so nothing
    here can touch `experiments/results`.

    Args:
        sandbox: A directory (usually `tmp_path`) to redirect all state into.
        args: Driver CLI arguments.
        stub: The dry-run substitute command.
        serial: Force `SUITE_SERIAL=1`.
        extra_env: Additional environment for the driver.
        timeout: Explicit subprocess timeout, always passed.

    Returns:
        A `DriverRun` with the exit code, stdout and the parsed state TSV.
    """
    state_dir = sandbox / "state"
    out_dir = sandbox / "out"
    state_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = sandbox / "markers.tsv"

    env = dict(os.environ)
    # THE SEAM. Never absent from any invocation in this file: without it the
    # driver runs the real ~22-26 hour suite.
    env["RUN_EXPERIMENT_SUITE_DRY_RUN"] = "1"
    env["RUN_EXPERIMENT_SUITE_DRY_RUN_CMD"] = stub
    env["SUITE_OUT_DIR"] = out_dir.as_posix()
    env["SUITE_STATE_DIR"] = state_dir.as_posix()
    env["SUITE_MARKER"] = marker.as_posix()
    env.pop("SUITE_SERIAL", None)
    if serial:
        env["SUITE_SERIAL"] = "1"
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        [_resolve_bash(), DRIVER_PATH.as_posix(), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    sha = _frozen_sha()
    state_file = state_dir / f"run_experiment_suite_state.{sha}.dryrun.tsv"
    real_state_file = state_dir / f"run_experiment_suite_state.{sha}.tsv"
    return DriverRun(
        returncode=completed.returncode,
        stdout=completed.stdout + completed.stderr,
        state_dir=state_dir,
        out_dir=out_dir,
        state_file=state_file,
        real_state_file=real_state_file,
        marker_file=marker,
        events=_parse_state(state_file),
    )


@pytest.fixture(scope="module")
def bash_available() -> None:
    if not DRIVER_PATH.exists():  # pragma: no cover - environment guard
        pytest.skip(f"{DRIVER_PATH} does not exist")
    _resolve_bash()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_expectations()


@pytest.fixture(scope="module")
def pooled_run(bash_available, tmp_path_factory) -> DriverRun:
    """One clean POOLED dry run, shared by every ordering assertion.

    Module-scoped because the ordering tests all interrogate the SAME run: they
    are assertions about one schedule, and re-running the queue per test would
    both be slower and let two tests disagree about what happened.
    """
    return run_driver(tmp_path_factory.mktemp("pooled"))


@pytest.fixture(scope="module")
def serial_run(bash_available, tmp_path_factory) -> DriverRun:
    return run_driver(tmp_path_factory.mktemp("serial"), serial=True)


def _overlaps(a: tuple[datetime, datetime], b: tuple[datetime, datetime]) -> bool:
    """True when two [start, complete] intervals genuinely overlap.

    Touching endpoints are NOT an overlap: a stage that starts at the instant
    another completes is correctly sequenced.
    """
    return a[0] < b[1] and b[0] < a[1]


class TestFullDryRun:
    """The queue runs end to end, and leaves the right state behind."""

    def test_full_dry_run_completes_every_stage_and_exits_zero(
        self, pooled_run, manifest
    ):
        expected = {stage["id"] for stage in manifest["stages"]}
        completed = set(pooled_run.completions())
        assert completed == expected, (
            "a clean dry run must complete EVERY stage. Missing: "
            f"{sorted(expected - completed)}; unexpected: "
            f"{sorted(completed - expected)}\n{pooled_run.stdout[-3000:]}"
        )
        assert pooled_run.returncode == 0, (
            "a clean dry run has no stage failure, no gate FAIL and no roll-up "
            f"FAIL, so it must exit 0; got {pooled_run.returncode}\n"
            f"{pooled_run.stdout[-3000:]}"
        )

    def test_one_start_and_one_complete_per_stage(self, pooled_run, manifest):
        for stage in manifest["stages"]:
            name = stage["id"]
            starts = [
                e for e in pooled_run.events if e.name == name and e.event == "start"
            ]
            completes = [
                e for e in pooled_run.events if e.name == name and e.event == "complete"
            ]
            assert len(starts) == 1, f"{name}: expected 1 start line, got {len(starts)}"
            assert len(completes) == 1, (
                f"{name}: expected 1 complete line, got {len(completes)}"
            )

    def test_dry_run_does_not_write_the_real_state_file(self, pooled_run):
        """The 19.5 fix, asserted rather than remembered.

        A dry run "completes" every stage in about a second. If it wrote the
        REAL state file, automatic resume would skip every stage on the next
        launch: the suite would do nothing, produce nothing, and EXIT 0. That
        is what made a real 19.3 launch a silent no-op.
        """
        assert pooled_run.state_file.exists(), (
            f"the dry-run state file was not written at {pooled_run.state_file}"
        )
        assert not pooled_run.real_state_file.exists(), (
            f"a DRY RUN wrote the REAL state file at {pooled_run.real_state_file}. "
            "The next real launch would skip every stage and exit 0 with no "
            "artifacts"
        )

    def test_stage_order_is_consistent_with_every_depends_on_edge(
        self, pooled_run, manifest
    ):
        intervals = pooled_run.intervals()
        violations = []
        for stage in manifest["stages"]:
            name = stage["id"]
            if name not in intervals:
                continue
            for dep in stage["depends_on"]:
                if dep not in intervals:
                    continue
                if intervals[name][0] < intervals[dep][1]:
                    violations.append(
                        f"{name} started {intervals[name][0].isoformat()} before "
                        f"{dep} completed {intervals[dep][1].isoformat()}"
                    )
        assert not violations, (
            "the pooled scheduler violated a depends_on edge: " + "; ".join(violations)
        )


class TestNoExperimentEverRuns:
    """The seam is the safety property this whole file rests on."""

    def test_every_stage_ran_only_as_a_stub(self, pooled_run, manifest):
        """Every stage body reached the stub, and none ran an experiment.

        The stub records one marker line per stage body. If a stage had
        executed for real it would have produced artifacts in the sandboxed
        out dir instead -- so both halves are asserted.
        """
        stage_ids = {stage["id"] for stage in manifest["stages"]}
        invoked = set(pooled_run.stage_invocations())
        assert stage_ids <= invoked | {"preflight"}, (
            f"stage(s) {sorted(stage_ids - invoked)} never reached the dry-run "
            "stub, so they either did not run or ran for real"
        )
        produced = [
            p.name for p in pooled_run.out_dir.iterdir() if p.name != "markers.tsv"
        ]
        assert not produced, (
            f"a dry run produced files in the output tree: {produced}. No test "
            "in this file may run an experiment"
        )

    def test_the_seam_is_set_on_every_invocation(self, tmp_path):
        """A run WITHOUT the stub command still never executes an experiment.

        `RUN_EXPERIMENT_SUITE_DRY_RUN` alone is what suppresses every stage
        body; `_CMD` only chooses the substitute. Asserted separately so a
        future edit that makes the seam depend on `_CMD` is caught here rather
        than by a 22-hour run.
        """
        run = run_driver(tmp_path, stub="true")
        assert run.returncode == 0
        produced = [p.name for p in run.out_dir.iterdir()]
        assert not produced, (
            f"a dry run with the default stub produced {produced} in the output tree"
        )


class TestResume:
    """The two resume semantics, which are not interchangeable."""

    def test_a_completed_stage_is_skipped_on_the_next_run(
        self, bash_available, tmp_path
    ):
        first = run_driver(tmp_path)
        assert first.returncode == 0

        second = run_driver(tmp_path)
        assert second.returncode == 0
        assert "SKIP stage" in second.stdout, (
            "the second run re-ran everything instead of skipping stages with a "
            "recorded completion line"
        )
        assert second.stage_invocations() == first.stage_invocations(), (
            "the second run appended new stage invocations to the marker file, "
            "so a stage with a completion line was re-run"
        )

    def test_a_started_but_uncompleted_stage_is_rerun_from_scratch(
        self, bash_available, tmp_path
    ):
        """A start line with no completion line is NOT 'done'.

        A stage that started and then died must be re-run from scratch --
        treating it as complete is how a partial result set spanning two trees
        gets assembled, which the abort protocol exists to forbid.
        """
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        sha = _frozen_sha()
        state_file = state_dir / f"run_experiment_suite_state.{sha}.dryrun.tsv"
        state_file.write_text(
            "e5\t7\tstart\t2026-08-18T00:00:00.000Z\t\n", encoding="utf-8"
        )

        run = run_driver(tmp_path)
        assert run.returncode == 0
        assert "e5" in run.stage_invocations(), (
            "e5 carried a start line with no completion line, so it must be "
            "re-run from scratch; it was not invoked at all"
        )
        assert "SKIP stage 7 (e5)" not in run.stdout, (
            "e5 was SKIPPED although its state line was a start with no "
            "matching completion -- a died stage was treated as done"
        )


class TestStickyExit:
    """D-01: a gate FAIL never aborts the queue, and never exits 0 either."""

    def test_a_gate_fail_is_sticky_and_the_queue_still_finishes(
        self, bash_available, tmp_path, manifest
    ):
        """BOTH halves, because either alone would pass on an abort.

        A test that only checked the exit code would pass on a driver that
        aborted at the failing gate -- which is the behaviour D-01 forbids.
        """
        stub = _STUB + '; [ "${stage_name:-}" != "e5" ]'
        run = run_driver(tmp_path, stub=stub)

        expected = {stage["id"] for stage in manifest["stages"]}
        completed = set(run.completions())
        assert completed == expected, (
            "a gate FAIL aborted the queue. D-01: E1, E5, E6, E7, E2 and E4 are "
            "independent and their measurements are still wanted after one of "
            f"them fails a check. Missing: {sorted(expected - completed)}"
        )
        assert run.returncode != 0, (
            "the driver exited 0 despite a gate FAIL. That is F-001 exactly: a "
            "run that exits 0 and looks green while something was never "
            "produced"
        )
        assert "GATE FAIL: e5" in run.stdout, (
            "the terminal summary must NAME the failing stage; a non-zero exit "
            f"with no explanation is not actionable at 7 a.m.\n{run.stdout[-3000:]}"
        )
        assert "SUITE FAILED" in run.stdout


@pytest.fixture(scope="module")
def preflight_abort_run(bash_available, tmp_path_factory) -> DriverRun:
    """One run whose pre-flight stage fails, shared by the two D-03/D-50 tests."""
    stub = _STUB + '; [ "${name:-}" != "preflight" ]'
    return run_driver(tmp_path_factory.mktemp("preflight_abort"), stub=stub)


class TestPreflight:
    """D-03 aborts; D-50 always prints the way out."""

    def test_a_preflight_failure_aborts_before_stage_one(self, preflight_abort_run):
        run = preflight_abort_run
        assert run.returncode != 0
        ran = {e.name for e in run.events}
        assert ran == {"preflight"}, (
            "a pre-flight failure must abort BEFORE stage 1; these stages also "
            f"recorded state lines: {sorted(ran - {'preflight'})}"
        )
        assert "ABORTING THE QUEUE" in run.stdout

    def test_a_preflight_refusal_names_its_override_flag(self, preflight_abort_run):
        """D-50, the governing rule for every surviving refusal.

        A malformed check must cost one minute and one flag, never a night.
        """
        run = preflight_abort_run
        for flag in (
            "--skip-e2",
            "--allow-frameset-mismatch",
            "--allow-nonempty-out",
            "--allow-low-disk",
            "--allow-gate-precheck-failure",
        ):
            assert flag in run.stdout, (
                f"the pre-flight abort message does not name {flag}. Every "
                "refusal must print the exact override flag that bypasses it"
            )

    def test_skip_e2_declares_the_reduction_and_does_not_abort(
        self, bash_available, tmp_path, manifest
    ):
        """D-14: a *silent* skip must be impossible.

        "Loud" alone is a log line and nobody reads the log overnight, so the
        declaration is announced at LAUNCH and again in the terminal summary.
        """
        run = run_driver(tmp_path, args=("--skip-e2",))
        assert run.returncode == 0, "--skip-e2 declares an omission; it must not abort"
        assert "DECLARED REDUCTION" in run.stdout
        assert "--skip-e2" in run.stdout
        assert run.stdout.count("DECLARED REDUCTION") >= 2, (
            "the declaration must appear at launch AND in the terminal summary; "
            "one line at the top of an overnight log is not a declaration"
        )
        completed = set(run.completions())
        assert completed == {stage["id"] for stage in manifest["stages"]}


class TestConcurrencyConstraints:
    """D-52's three hard constraints, read off the state file's ISO stamps.

    Every assertion here runs under the POOLED scheduler. Serial mode cannot
    exhibit an overlap, so a serial-only assertion proves nothing.
    """

    def test_serial_mode_also_completes_every_stage(self, serial_run, manifest):
        """`SUITE_SERIAL=1` is the escape hatch; it must actually work."""
        assert serial_run.returncode == 0, serial_run.stdout[-3000:]
        assert set(serial_run.completions()) == {
            stage["id"] for stage in manifest["stages"]
        }

    def test_the_pool_really_did_overlap_something(self, pooled_run):
        """Guard on every other test in this class.

        If the pool never ran two stages at once, the overlap assertions below
        would pass vacuously and prove nothing about the scheduler.
        """
        intervals = pooled_run.intervals()
        overlapping = [
            (a, b)
            for a in intervals
            for b in intervals
            if a < b and _overlaps(intervals[a], intervals[b])
        ]
        assert overlapping, (
            "no two stages overlapped, so this run did not exercise the pool at "
            "all and every overlap assertion below is vacuous"
        )

    def test_e6_band_starts_only_after_e6_repeat1_completes_under_pooled_mode(
        self, pooled_run
    ):
        """D-52 constraint 1, and the sharpest ordering edge in the phase.

        `run_stage_e6_repeat1` does `rm -rf ${OUT_DIR}/e6_configs` and removes
        `generalization_sweep.csv` / `e6_provenance.json` under the SHARED
        `OUT_DIR` that `e6_band` also writes. An overlap is a real `rm -rf`
        collision mid-band, not a bookkeeping error -- and `e6_band` is 8.9 h,
        roughly 40% of the whole suite.
        """
        intervals = pooled_run.intervals()
        assert "e6_repeat1" in intervals and "e6_band" in intervals
        assert intervals["e6_band"][0] > intervals["e6_repeat1"][1], (
            f"e6_band started {intervals['e6_band'][0].isoformat()} but "
            f"e6_repeat1 only completed {intervals['e6_repeat1'][1].isoformat()}"
        )
        assert not _overlaps(intervals["e6_band"], intervals["e6_repeat1"]), (
            "e6_band and e6_repeat1 overlapped under the pooled scheduler"
        )

    def test_e4_starts_only_after_e2_production_completes_under_pooled_mode(
        self, pooled_run
    ):
        """Ordering constraint O4: a SILENT WRONG NUMBER, not a crash.

        `resolve_e2_benchmark_path` (`e4_benchmark_grid.py:298`) quietly drops
        the real-rig row when E2's `benchmark.json` is absent, and
        `benchmark_grid.csv` comes back with 9 rows instead of 10.
        """
        intervals = pooled_run.intervals()
        assert "e2_production" in intervals and "e4" in intervals
        assert intervals["e4"][0] > intervals["e2_production"][1], (
            f"e4 started {intervals['e4'][0].isoformat()} but e2_production only "
            f"completed {intervals['e2_production'][1].isoformat()}"
        )

    def test_e3_check_and_force_stay_atomic_under_pooled_mode(self, pooled_run):
        """E3's two invocations are ONE stage and the order is load-bearing.

        `--check` FIRST records the pre-regeneration state of all three tiers;
        `--force` SECOND regenerates the committed tier CSVs. Running `--force`
        first destroys the only evidence of what moved -- and no resume boundary
        may fall between them.
        """
        e3_invocations = [
            invocation
            for name, stage_name, invocation in pooled_run.marker_lines()
            if name == "e3" and not stage_name
        ]
        assert e3_invocations == ["--check", "--force"], (
            "e3's paired invocations must be exactly --check then --force, "
            f"inside one stage; got {e3_invocations}"
        )
        e3_events = [e for e in pooled_run.events if e.name == "e3"]
        assert [e.event for e in e3_events] == ["start", "complete"], (
            "e3 recorded more than one start/complete pair, so the pool split "
            f"an atomic stage: {[e.event for e in e3_events]}"
        )

    def test_no_serial_alone_stage_ever_shares_the_box(self, pooled_run, manifest):
        """Constraint 3, and its rationale is TIMING INTEGRITY (review H4).

        `e4`, `e4_repeat`, `e2_timing` and `e2_memory` report runtimes. A
        runtime measured while another calibration held the box is a
        measurement of the queue, not of the algorithm.
        """
        intervals = pooled_run.intervals()
        serial_alone = [
            stage["id"]
            for stage in manifest["stages"]
            if stage["concurrency"] == "serial_alone"
        ]
        assert serial_alone, "the manifest declares no serial_alone stage"
        violations = []
        for name in serial_alone:
            if name not in intervals:
                continue
            for other, span in intervals.items():
                if other == name:
                    continue
                if _overlaps(intervals[name], span):
                    violations.append(f"{other} overlapped serial_alone {name}")
        assert not violations, "; ".join(violations)

    def test_never_two_200_frame_class_stages_at_once(self, pooled_run, manifest):
        """Constraint 2: peak RSS tracks FRAME COUNT.

        30 frames < 1 GiB, 100 frames 2.7-3.5 GiB, 200 frames 9.3-11.3 GiB.
        Five 3.5 GiB stages plus one 200-frame stage is 27.8 of about 31 GiB.
        """
        intervals = pooled_run.intervals()
        heavy = [
            stage["id"]
            for stage in manifest["stages"]
            if str(stage["frame_class"]) == "200" and stage["id"] in intervals
        ]
        assert heavy, "the manifest declares no 200-frame-class stage"
        violations = [
            f"{a} overlapped {b}"
            for i, a in enumerate(heavy)
            for b in heavy[i + 1 :]
            if _overlaps(intervals[a], intervals[b])
        ]
        assert not violations, (
            "two 200-frame-class stages were in flight at once: "
            + "; ".join(violations)
        )

    def test_the_pool_never_exceeds_its_worker_count(self, pooled_run):
        """The pool is bounded to SUITE_WORKERS, whose default is 4 (D-52).

        Deliberately NOT the probe's `recommended_workers: 16`: E1 is the
        cheapest and smallest solve in the suite and its peak RSS does not
        transfer.
        """
        boundaries: list[tuple[datetime, int]] = []
        for start, end in pooled_run.intervals().values():
            boundaries.append((start, 1))
            boundaries.append((end, -1))
        boundaries.sort(key=lambda item: (item[0], item[1]))
        in_flight = peak = 0
        for _, delta in boundaries:
            in_flight += delta
            peak = max(peak, in_flight)
        assert peak <= 5, (
            f"{peak} stages were in flight at once; the pool is bounded to 4-5"
        )
