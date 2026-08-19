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

import json
import os
import shutil
import subprocess
import sys
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
    dispatch_file: Path
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

    def dispatches(self) -> list[tuple[str, str]]:
        """`(stage, argv)` for every experiment invocation the driver BUILT.

        This is the one thing the marker file cannot give: the dry-run seam
        substitutes the WHOLE command, so the stub never sees the argv and a
        mistyped flag passes every other test in this file. The driver's
        `_record_dispatch` writes the argv it was about to launch, so these
        assertions read the REAL invocation lines rather than a mock.
        """
        if not self.dispatch_file.exists():
            return []
        rows = []
        for line in self.dispatch_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            stage, _, argv = line.partition("\t")
            rows.append((stage, argv))
        return rows

    def dispatch_snapshot(self) -> list[str]:
        """Every dispatched line as `stage\\targv`, sorted.

        Sorted because the pool's completion order is genuinely
        nondeterministic; the SET of invocation lines is the invariant, not
        the order they happened to land in.
        """
        return sorted(f"{stage}\t{argv}" for stage, argv in self.dispatches())


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
    sandbox_out: bool = True,
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
        sandbox_out: When False, `SUITE_OUT_DIR` is NOT set, so the driver
            resolves its own output tree. Needed only by the tests that assert
            WHICH tree it resolves (`experiments/results` normally,
            `experiments/results_smoke` under `--smoke`) -- a sandboxed
            `SUITE_OUT_DIR` overrides that resolution and would make those
            assertions vacuous. Safe because the seam is still set, so no
            stage body runs and nothing is written; the tests assert that.

    Returns:
        A `DriverRun` with the exit code, stdout and the parsed state TSV.
    """
    state_dir = sandbox / "state"
    out_dir = sandbox / "out"
    state_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = sandbox / "markers.tsv"
    dispatch = sandbox / "dispatch.tsv"

    env = dict(os.environ)
    # THE SEAM. Never absent from any invocation in this file: without it the
    # driver runs the real ~22-26 hour suite.
    env["RUN_EXPERIMENT_SUITE_DRY_RUN"] = "1"
    env["RUN_EXPERIMENT_SUITE_DRY_RUN_CMD"] = stub
    if sandbox_out:
        env["SUITE_OUT_DIR"] = out_dir.as_posix()
    else:
        env.pop("SUITE_OUT_DIR", None)
    env["SUITE_STATE_DIR"] = state_dir.as_posix()
    env["SUITE_MARKER"] = marker.as_posix()
    env["SUITE_DISPATCH_LOG"] = dispatch.as_posix()
    env.pop("SUITE_SERIAL", None)
    env.pop("SUITE_SMOKE", None)
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
        dispatch_file=dispatch,
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


def _was_skipped_as_complete(run: DriverRun, stage_id: str) -> bool:
    """Did the driver skip `stage_id` because it already had a completion line?

    Matched BY NAME, never by queue index. The index in `SKIP stage N (name)`
    is the position in the driver's own shortest-first execution order, which is
    NOT the manifest's listing order -- e5 is 9th in the manifest and 6th in the
    queue. A resume test's sharpest assertion is the NEGATIVE one ("it was not
    skipped"), and a negative assertion carrying the wrong number passes against
    every driver ever written. That vacuous-gate shape is one this project has
    already been bitten by, so the index is kept out of the predicate entirely.
    """
    needle = f"({stage_id}): already has a recorded completion line"
    return any(needle in line for line in run.stdout.splitlines())


def _write_state(sandbox: Path, lines: str) -> Path:
    """Plant a hand-crafted state file at the sha-derived dry-run path."""
    state_dir = sandbox / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"run_experiment_suite_state.{_frozen_sha()}.dryrun.tsv"
    state_file.write_text(lines, encoding="utf-8")
    return state_file


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
        _write_state(tmp_path, "e5\t6\tstart\t2026-08-18T00:00:00.000Z\t\n")

        run = run_driver(tmp_path)
        assert run.returncode == 0
        assert "e5" in run.stage_invocations(), (
            "e5 carried a start line with no completion line, so it must be "
            "re-run from scratch; it was not invoked at all"
        )
        assert not _was_skipped_as_complete(run, "e5"), (
            "e5 was SKIPPED although its state line was a start with no "
            "matching completion -- a died stage was treated as done"
        )

    def test_a_stage_that_completed_with_a_nonzero_exit_is_rerun(
        self, bash_available, tmp_path
    ):
        """D-22: a completion line is not enough -- the exit code decides.

        `state_complete` always writes the stage's exit code as column 5, and
        the frozen run's own state file already carries the proof line
        `reconstruction_bootstrap\t10\tcomplete\t...\t1`: a stage that RAN
        AND FAILED. Matching only on "complete" made the resume silently drop
        it. On a single-shot 15-16 h run that is the failure most likely to cost
        the whole night -- the end-of-run roll-up does catch the missing
        artifact, but only after everything else has finished.
        """
        _write_state(
            tmp_path,
            "e5\t6\tstart\t2026-08-18T00:00:00.000Z\t\n"
            "e5\t6\tcomplete\t2026-08-18T00:00:01.000Z\t1\n",
        )

        run = run_driver(tmp_path)
        assert run.returncode == 0
        assert "e5" in run.stage_invocations(), (
            "e5's completion line carried exit code 1 -- it ran and FAILED -- "
            "so it must be re-run; it was not invoked at all"
        )
        assert not _was_skipped_as_complete(run, "e5"), (
            "a stage that completed NON-ZERO was SKIPPED on resume. That is "
            "D-22: the resume dropped a stage that produced nothing"
        )

    def test_a_stage_that_completed_with_exit_zero_is_still_skipped(
        self, bash_available, tmp_path
    ):
        """The other half: reading column 5 must not make resume useless.

        Without this, `$5 == 0` could be "satisfied" by re-running everything.
        """
        _write_state(
            tmp_path,
            "e5\t6\tstart\t2026-08-18T00:00:00.000Z\t\n"
            "e5\t6\tcomplete\t2026-08-18T00:00:01.000Z\t0\n",
        )

        run = run_driver(tmp_path)
        assert run.returncode == 0
        assert _was_skipped_as_complete(run, "e5"), (
            "a cleanly completed stage was re-run; the resume path is the "
            f"recovery the driver is built around.\n{run.stdout[-3000:]}"
        )
        assert "e5" not in run.stage_invocations()


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


#: The line that opens the frameset probe's heredoc inside
#: `_preflight_frameset`. The probe is a Python program embedded in the driver,
#: and the WHOLE pre-flight stage is substituted under the dry-run seam
#: (`run_one_stage preflight` hits `_dry_run_stub` and returns before
#: `_preflight_frameset` is ever called), so `run_driver` structurally cannot
#: reach it. The tests below therefore lift the probe OUT of the driver source
#: and run it directly. The program under test is still exactly the one the
#: driver ships -- it is SLICED from the file on every call, never copied into
#: this one -- so it cannot drift from what an operator runs at 3 a.m.
_PROBE_HEREDOC_OPEN = 'SUITE_E2_RELEASE_CONFIG="${E2_RELEASE_CONFIG}"'


def _frameset_probe_source() -> str:
    """The frameset probe's Python body, sliced out of the driver."""
    lines = DRIVER_PATH.read_text(encoding="utf-8").splitlines()
    opens = [
        i
        for i, line in enumerate(lines)
        if _PROBE_HEREDOC_OPEN in line and line.rstrip().endswith("<<'PY'")
    ]
    assert len(opens) == 1, (
        "expected exactly one frameset-probe heredoc in the driver, found "
        f"{len(opens)}; the slice below would run the wrong program"
    )
    start = opens[0] + 1
    end = next(i for i in range(start, len(lines)) if lines[i] == "PY")
    return "\n".join(lines[start:end]) + "\n"


def run_frameset_probe(
    sandbox: Path,
    *,
    n_declared: int = 13,
    n_present: int = 13,
    kind: str = "dir",
    bytes_each: int = 400,
    floor: int = 1000,
) -> subprocess.CompletedProcess:
    """Run the driver's frameset probe against a synthetic frameset.

    The sandbox gets its own copy of `experiments/suite_expectations.json` with
    ONLY `preflight.frameset.cheap_check.min_total_bytes` lowered, and the probe
    runs with the sandbox as cwd so it reads that copy. The floor is moved in
    the MANIFEST, never in the probe: a test that needed the number written into
    the script would be testing a different program than the one that ships
    (FIX-06 is exactly that failure).

    Args:
        sandbox: A `tmp_path` to build the frameset and manifest copy in.
        n_declared: How many extrinsic paths the release config declares.
        n_present: How many of those actually exist on disk.
        kind: `"dir"` for an IMAGE set (D-08's real shape) or `"file"` for the
            video set the check was originally written against.
        bytes_each: Bytes held by each present path.
        floor: The `min_total_bytes` written into the sandbox manifest copy.

    Returns:
        The finished probe process; `returncode` is the driver's 0/2/3 contract.
    """
    sandbox.mkdir(parents=True, exist_ok=True)
    frames = sandbox / "frames"
    frames.mkdir(exist_ok=True)

    declared: dict[str, str] = {}
    for i in range(n_declared):
        name = f"cam{i:02d}"
        if kind == "dir":
            target = frames / name
            if i < n_present:
                target.mkdir()
                half = bytes_each // 2
                # TWO files per directory, so a byte sum that merely stat()ed
                # the directory itself could not accidentally agree.
                (target / "000000.png").write_bytes(b"\0" * half)
                (target / "000001.png").write_bytes(b"\0" * (bytes_each - half))
        else:
            target = frames / f"{name}.avi"
            if i < n_present:
                target.write_bytes(b"\0" * bytes_each)
        declared[name] = target.as_posix()

    config = sandbox / "release_config.yaml"
    config_lines = ["paths:", "  extrinsic_videos:"]
    config_lines += [f'    {k}: "{v}"' for k, v in declared.items()]
    config.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    manifest_dir = sandbox / "experiments"
    manifest_dir.mkdir(exist_ok=True)
    data = json.loads(
        (REPO_ROOT / "experiments" / "suite_expectations.json").read_text(
            encoding="utf-8"
        )
    )
    data["preflight"]["frameset"]["cheap_check"]["min_total_bytes"] = floor
    (manifest_dir / "suite_expectations.json").write_text(
        json.dumps(data), encoding="utf-8"
    )

    probe = sandbox / "_frameset_probe.py"
    probe.write_text(_frameset_probe_source(), encoding="utf-8")

    env = dict(os.environ)
    env["SUITE_E2_RELEASE_CONFIG"] = config.as_posix()
    return subprocess.run(
        [sys.executable, probe.as_posix()],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
        timeout=DRIVER_TIMEOUT_S,
    )


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


class TestFramesetPreflightIsPathKindAgnostic:
    """D-10: the pre-flight check must see an IMAGE set, not only videos.

    D-09: the probe built `present` with `p.is_file()`. The frozen run's target
    holds an image set (13 DIRECTORIES of frames), for which that predicate is
    False on every path -- so `present` came back empty, the probe exited 2 =
    ABSENT, and the driver refused with "use --skip-e2". Taking that advice
    would have made the whole 15-16 h re-run SYNTHETIC-ONLY. `detection.py`
    already auto-selects `ImageSet` for a directory, which is why this was a
    driver defect and not a library one.
    """

    def test_a_directory_frameset_passes(self, tmp_path):
        """The case D-09 broke: 13 image DIRECTORIES over the floor."""
        run = run_frameset_probe(tmp_path, kind="dir")
        assert run.returncode == 0, (
            "a 13-directory image set was not accepted by pre-flight; this is "
            f"D-09, and it costs E2 outright.\n{run.stdout}\n{run.stderr}"
        )
        assert "MATCH:" in run.stdout
        assert "13 present" in run.stdout

    def test_a_video_file_frameset_still_passes(self, tmp_path):
        """The original case must not regress: 13 video FILES over the floor."""
        run = run_frameset_probe(tmp_path, kind="file")
        assert run.returncode == 0, (
            f"the video-set case regressed.\n{run.stdout}\n{run.stderr}"
        )
        assert "MATCH:" in run.stdout

    @pytest.mark.parametrize("kind", ["dir", "file"])
    def test_an_entirely_missing_frameset_is_still_absent(self, tmp_path, kind):
        """ABSENT stays exit 2, for both path kinds. Its override is --skip-e2."""
        run = run_frameset_probe(tmp_path, n_present=0, kind=kind)
        assert run.returncode == 2, (
            "absence must stay exit 2; the driver's `case` maps 2 to the "
            f"--skip-e2 refusal.\n{run.stdout}\n{run.stderr}"
        )
        assert "ABSENT:" in run.stdout

    @pytest.mark.parametrize("kind", ["dir", "file"])
    def test_a_frameset_under_the_floor_is_still_a_mismatch(self, tmp_path, kind):
        """MISMATCH stays exit 3 -- a different mistake with a different flag."""
        run = run_frameset_probe(tmp_path, kind=kind, bytes_each=400, floor=10**7)
        assert run.returncode == 3, (
            "a frameset below the manifest's byte floor must stay exit 3, which "
            "is the branch that names --allow-frameset-mismatch.\n"
            f"{run.stdout}\n{run.stderr}"
        )
        assert "MISMATCH:" in run.stdout
        assert "RETIRED" in run.stdout, (
            "the mismatch report must still name what was probably found"
        )

    @pytest.mark.parametrize("kind", ["dir", "file"])
    def test_a_partially_present_frameset_is_a_mismatch(self, tmp_path, kind):
        """11 of 13 present is a MISMATCH (exit 3), not an ABSENCE.

        Exit 2 means NOTHING declared exists; a partial frameset is a wrong
        archive, and the two get different overrides on purpose.
        """
        run = run_frameset_probe(tmp_path, n_present=11, kind=kind)
        assert run.returncode == 3, f"{run.stdout}\n{run.stderr}"
        assert "found 11 present of 13 declared" in run.stdout

    def test_the_byte_floor_is_never_a_literal_in_the_driver(self):
        """FIX-06's rule: the expected numbers live in the manifest only."""
        source = DRIVER_PATH.read_text(encoding="utf-8")
        manifest = load_expectations()
        floor = manifest["preflight"]["frameset"]["cheap_check"]["min_total_bytes"]
        assert str(floor) not in source, (
            "the frameset byte floor was written into the shell script. That is "
            "exactly how the RETIRED archive's counts survived in a code "
            "comment while the manifest said something else (FIX-06)"
        )
        assert 'cheap["min_total_bytes"]' in source, (
            "the probe no longer reads the floor from the manifest by key"
        )

    def test_each_probe_exit_still_carries_its_own_override_flag(self):
        """P26-D-50: two mistakes, two flags -- asserted on the driver source.

        The Bash `case` branches on the probe's exit codes, so the numbers above
        are only meaningful if each branch still prints its own way out.
        """
        source = DRIVER_PATH.read_text(encoding="utf-8")
        absent = [
            line for line in source.splitlines() if "the E2 frameset is ABSENT" in line
        ]
        mismatch = [
            line
            for line in source.splitlines()
            if "does NOT match the manifest" in line
        ]
        assert absent and all("--skip-e2" in line for line in absent)
        assert mismatch and all(
            "--allow-frameset-mismatch" in line for line in mismatch
        )


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


# ---------------------------------------------------------------------------
# THE REDUCED-SCALE PASS (plan 26-11, D-33 form 1).
#
# Everything below still runs under the seam and still runs no experiment. What
# is new is WHAT is read: `_record_dispatch` writes the argv each stage was
# about to launch, so these assertions read the REAL invocation lines. That is
# the gap the seam leaves open by design -- it substitutes the whole command,
# so a mistyped flag passes every test above and then fails hours into a 22-31
# hour frozen run.
# ---------------------------------------------------------------------------

#: The full-scale dispatch list, frozen. THIS IS THE POINT OF THE SNAPSHOT: it
#: makes "plan 26-11 did not move the production path" CHECKABLE rather than
#: asserted. Adding `--smoke` routing touched every one of these lines, and the
#: only evidence that none of them changed is a literal recorded before the
#: change and compared after it.
#:
#: Captured with no `SUITE_OUT_DIR`, so the paths are the ones a production run
#: actually uses. Sorted: the pool's order is nondeterministic, the SET is the
#: invariant.
#:
#: `e4_repeat` and `e2_band` are ABSENT and that is correct, not an omission:
#: both build their invocations only AFTER the dry-run seam returns (e4_repeat
#: behind its destructive pre-run clear, e2_band behind the emitted per-seed
#: configs), so no dry run can observe them. They are the only two.
_FULL_SCALE_DISPATCH_SNAPSHOT = [
    "e1\tpython -u -m experiments.e1_refractive_comparison --force --out experiments/results",
    "e1_band\tpython -u -m experiments.e1_refractive_comparison --seeds 42,43,44,45 --out experiments/results",
    "e2_memory\tpython -u -m experiments.e2_real_rig --config experiments/results_e2_invocations/config_e2_memory.yaml --out experiments/results_e2_memory --force",
    "e2_production\tpython -u -m experiments.e2_real_rig --config experiments/results_e2_invocations/config_e2_classification.yaml --out experiments/results --force",
    "e2_timing\tpython -u -m experiments.e2_real_rig --config experiments/results_e2_invocations/config_e2_timing.yaml --out experiments/results_e2_timing --force",
    "e3\tpython -u -m experiments.e3_derived_quantities --check --baseline-dir experiments/pre_rerun_baseline/results --out experiments/results",
    "e3\tpython -u -m experiments.e3_derived_quantities --force --out experiments/results",
    "e4\tpython -u -m experiments.e4_benchmark_grid --force --out experiments/results",
    "e5\tpython -u -m experiments.e5_index_sensitivity --force --out experiments/results",
    "e5_band\tpython -u -m experiments.e5_index_sensitivity --seeds 42,43,44,45,46,47 --out experiments/results --force",
    "e6_band\tpython -u -m experiments.e6_generalization_sweep --seeds 42,43,44,45,46,47 --axes index,layout,cameras --out experiments/results --force",
    "e6_repeat1\tpython -u -m experiments.e6_generalization_sweep --force --out experiments/results",
    "e7\tpython -u -m experiments.e7_interface_ablation --force --out experiments/results",
    "e7_band\tpython -u -m experiments.e7_interface_ablation --seeds 42,43,44,45,46,47,48,49,50,51 --out experiments/results",
    "e7_focal_standoff\tpython -u -m experiments.e7_focal_standoff_analysis --out experiments/results",
    "fd_jacobian\tpython -u -m experiments.fd_jacobian_accuracy --out experiments/results --force",
    "reconstruction_bootstrap\tpython -u -m experiments.reconstruction_bootstrap --out experiments/results --force",
]

#: The stages whose experiment honors `--smoke` AND whose invocation the seam
#: can observe. Measured at the argparse level against the exact argv the
#: driver builds, never read off a docstring: `e7_interface_ablation` honors
#: the flag (`e7_interface_ablation.py:918`) although plan 26-11's own verified
#: list omitted it, and `e7_focal_standoff_analysis` accepts it from the shared
#: parent parser while doing nothing whatsoever with it.
_SMOKE_FLAGGED_STAGES = {
    "e1",
    "e1_band",
    "e2_memory",
    "e2_production",
    "e2_timing",
    "e3",
    "e4",
    "e5",
    "e5_band",
    "e6_band",
    "e6_repeat1",
    "e7",
    "e7_band",
    "fd_jacobian",
    "reconstruction_bootstrap",
}

#: Skipped under smoke, with a DECLARED REDUCTION line. Neither is a failure.
#: `e7_focal_standoff` does nothing with the flag and reads a hardcoded
#: `experiments/results` path; `e4_repeat`'s `--cell` and `--splice-repeat` are
#: both mutually exclusive with `--smoke` in e4's own parser.
_SMOKE_SKIPPED_STAGES = {"e7_focal_standoff", "e4_repeat"}


@pytest.fixture(scope="module")
def full_scale_run(bash_available, tmp_path_factory) -> DriverRun:
    """One dry run with NO smoke and NO out-dir sandbox.

    The out dir is deliberately not sandboxed: these assertions are about which
    tree the driver RESOLVES, and `SUITE_OUT_DIR` overrides that resolution.
    """
    return run_driver(tmp_path_factory.mktemp("fullscale"), sandbox_out=False)


@pytest.fixture(scope="module")
def smoke_run(bash_available, tmp_path_factory) -> DriverRun:
    return run_driver(
        tmp_path_factory.mktemp("smoke"), args=("--smoke",), sandbox_out=False
    )


class TestSmokeMode:
    """`--smoke`: every stage's REAL invocation line, executable in minutes.

    The pass this covers is NOT evidence about geometry, convergence, accuracy
    or any published number, and no test here pretends otherwise. 26-07's rule
    is unchanged: every acceptance and production run is at full scale, never
    substituted. What `--smoke` buys is that a mistyped flag or a broken import
    in one of twenty invocation lines surfaces in minutes instead of at hour 18.
    """

    def test_smoke_flags_exactly_the_supporting_stages(self, smoke_run):
        """Every observable dispatch carries the flag, and the set is exact.

        Both halves matter. "Every dispatch carries it" alone would pass on a
        driver that dispatched only one stage; "the set is exact" alone would
        pass on a driver that recorded the flag without passing it.
        """
        assert smoke_run.returncode == 0, smoke_run.stdout[-3000:]
        flagged = {
            stage for stage, argv in smoke_run.dispatches() if "--smoke" in argv.split()
        }
        unflagged = {
            stage
            for stage, argv in smoke_run.dispatches()
            if "--smoke" not in argv.split()
        }
        assert flagged == _SMOKE_FLAGGED_STAGES, (
            "the wrong stages carry --smoke. Missing: "
            f"{sorted(_SMOKE_FLAGGED_STAGES - flagged)}; unexpected: "
            f"{sorted(flagged - _SMOKE_FLAGGED_STAGES)}"
        )
        assert not unflagged, (
            f"stage(s) {sorted(unflagged)} dispatched WITHOUT --smoke inside a "
            "reduced-scale pass, so they would run at full scale -- the pass "
            "would take hours, which is the one thing it exists not to do"
        )

    def test_smoke_skips_the_two_stages_that_cannot_take_the_flag(self, smoke_run):
        """Skipped, declared, and NOT a failure -- all three.

        A test that only checked "did not run" would pass on a driver that
        crashed the stage, and one that only checked the exit code would pass
        on a driver that ran it at full scale.
        """
        dispatched = {stage for stage, _ in smoke_run.dispatches()}
        assert dispatched.isdisjoint(_SMOKE_SKIPPED_STAGES), (
            f"{sorted(dispatched & _SMOKE_SKIPPED_STAGES)} dispatched under "
            "--smoke. e7_focal_standoff would re-analyse the PRODUCTION tree's "
            "band (it reads a hardcoded experiments/results path), and "
            "e4_repeat's --cell/--splice-repeat are refused outright by e4's "
            "own parser"
        )
        for stage in sorted(_SMOKE_SKIPPED_STAGES):
            assert f"{stage}: SKIPPED under --smoke" in smoke_run.stdout, (
                f"{stage} was skipped SILENTLY. A silent skip is exactly the "
                "F-001 shape: a run that looks green while something never "
                f"ran.\n{smoke_run.stdout[-3000:]}"
            )
        assert smoke_run.returncode == 0, (
            "a declared reduction is an announced omission, not a failure; the "
            f"run exited {smoke_run.returncode}"
        )

    def test_smoke_never_names_the_production_out_dir(self, smoke_run):
        """The distinct out dir is MANDATORY, not tidiness (research SP-7).

        Every experiment's `--smoke` path branches on
        `args.out == parser.get_default("out")` and that default IS
        `experiments/results` (`_io.py:64`), so passing it is indistinguishable
        from passing nothing: E3/E4/E5/E6/E7 would each take their
        TemporaryDirectory branch and the whole pass would write nothing while
        exiting 0.

        Compared token-by-token, never by substring: `experiments/results_smoke`
        and `experiments/results_e2_timing` both CONTAIN `experiments/results`,
        so a substring check would be satisfied by the very bug it must catch.
        """
        offenders = []
        for stage, argv in smoke_run.dispatches():
            tokens = argv.split()
            for flag in ("--out", "--band-dir", "--invocation-dir"):
                if flag in tokens:
                    value = tokens[tokens.index(flag) + 1]
                    if value == "experiments/results":
                        offenders.append(f"{stage}: {flag} {value}")
        assert not offenders, (
            "a reduced-scale pass pointed at the PRODUCTION output tree: "
            + "; ".join(offenders)
        )
        out_values = {
            argv.split()[argv.split().index("--out") + 1]
            for _, argv in smoke_run.dispatches()
            if "--out" in argv.split()
        }
        assert "experiments/results_smoke" in out_values, (
            "no stage was pointed at experiments/results_smoke, so the forced "
            f"out dir did not take effect: {sorted(out_values)}"
        )

    def test_smoke_moves_every_sibling_out_dir_too(self, smoke_run):
        """`run_stage_e2_band` OPENS with `rm -rf "${OUT_DIR_E2_BAND}"`.

        Left at its production value, a rehearsal's first act would DELETE
        `experiments/results_e2_band` -- three 48-87 minute calibrations. That
        is the sharpest reason the sibling trees move with `OUT_DIR`, and not a
        tidiness point. `e4_repeat` has the same shape and is skipped anyway; it
        is re-pointed regardless, so the skip is not the only thing standing
        between a rehearsal and a destroyed production tree.
        """
        production_siblings = {
            "experiments/results_e2_band",
            "experiments/results_e2_timing",
            "experiments/results_e2_memory",
            "experiments/results_e2_invocations",
            "experiments/results_e4_repeat",
        }
        offenders = []
        for stage, argv in smoke_run.dispatches():
            for token in argv.split():
                for sibling in production_siblings:
                    if token == sibling or token.startswith(sibling + "/"):
                        offenders.append(f"{stage}: {token}")
        assert not offenders, (
            "a reduced-scale pass named a PRODUCTION sibling tree: "
            + "; ".join(sorted(set(offenders)))
        )

    def test_smoke_banner_says_the_pass_is_not_evidence(self, smoke_run):
        """D-14: loud, at launch AND in the terminal summary.

        The wording is load-bearing, not decoration. 26-07 built the driver so
        acceptance and production runs are never substituted, and this plan adds
        a substituted path next to it; the only thing keeping the two
        distinguishable at 7 a.m. is a banner that says so in both places.
        """
        assert smoke_run.stdout.count("DECLARED REDUCTION") >= 2, (
            "the reduced-scale declaration must appear at launch AND in the "
            "terminal summary; one line at the top of an overnight log is not "
            "a declaration"
        )
        for phrase in (
            "REDUCED-SCALE PASS",
            "NOTHING THIS RUN PRODUCES IS EVIDENCE",
            "EVERY ACCEPTANCE AND PRODUCTION",
            "INVOCATION LINE",
        ):
            assert phrase in smoke_run.stdout, (
                f"the launch banner does not say {phrase!r}. A reduced-scale "
                "run that does not announce what it is NOT is a number waiting "
                f"to be quoted.\n{smoke_run.stdout[-4000:]}"
            )

    def test_smoke_completes_every_stage_and_exits_zero(self, smoke_run, manifest):
        """A reduced-scale pass is still a whole-queue pass.

        Every stage records a start and a completion line, including the two
        that are skipped: a declared omission is a completed stage with nothing
        dispatched, not a hole in the state file.
        """
        expected = {stage["id"] for stage in manifest["stages"]}
        completed = set(smoke_run.completions())
        assert completed == expected, (
            "a reduced-scale pass must still traverse EVERY stage. Missing: "
            f"{sorted(expected - completed)}; unexpected: "
            f"{sorted(completed - expected)}\n{smoke_run.stdout[-3000:]}"
        )
        assert smoke_run.returncode == 0, smoke_run.stdout[-3000:]

    def test_smoke_does_not_write_the_real_state_file_either(self, smoke_run):
        """The 19.5 separation is not weakened by the new path."""
        assert not smoke_run.real_state_file.exists()

    def test_the_env_var_is_equivalent_to_the_smoke_flag(
        self, bash_available, tmp_path
    ):
        """`SUITE_SMOKE=1` == `--smoke`, for symmetry with SUITE_SERIAL.

        Asserted on the dispatched argv rather than on a log line, so a driver
        that merely PRINTS that smoke is active cannot pass.
        """
        run = run_driver(tmp_path, extra_env={"SUITE_SMOKE": "1"}, sandbox_out=False)
        assert run.returncode == 0, run.stdout[-3000:]
        flagged = {
            stage for stage, argv in run.dispatches() if "--smoke" in argv.split()
        }
        assert flagged == _SMOKE_FLAGGED_STAGES, (
            "SUITE_SMOKE=1 did not select the same stage set as --smoke: "
            f"{sorted(flagged)}"
        )


class TestSmokeAndProfileStaySeparable:
    """`--profile` selects the completeness gate's expectations. That is ALL.

    `--smoke` selects the SCALE the stages run at. The two were conflated in
    plan 26-10's launch line, which asked for a `--smoke` acceptance pass and
    would have started the full-scale 22-31 hour production suite while grading
    it against smoke expectations. Keeping them separable is the fix.
    """

    def test_profile_defaults_to_full_without_smoke(self, full_scale_run):
        assert "Profile: full." in full_scale_run.stdout, (
            f"the profile default moved off 'full'\n{full_scale_run.stdout[:2000]}"
        )

    def test_smoke_defaults_the_profile_to_smoke(self, smoke_run):
        assert "Profile: smoke." in smoke_run.stdout, (
            f"--smoke did not default the profile\n{smoke_run.stdout[:2000]}"
        )

    def test_an_explicit_profile_beats_the_smoke_default(
        self, bash_available, tmp_path
    ):
        """`--profile full --smoke` is honored.

        A reduced-scale run graded against the FULL expectation set is a
        legitimate thing to ask for -- it is how you see everything a smoke pass
        cannot produce. It must not be silently rewritten.
        """
        run = run_driver(tmp_path, args=("--profile", "full", "--smoke"))
        assert run.returncode == 0, run.stdout[-3000:]
        assert "Profile: full." in run.stdout, (
            "--smoke overrode an EXPLICIT --profile full; the two concepts are "
            f"not separable any more\n{run.stdout[:2000]}"
        )
        flagged = {
            stage for stage, argv in run.dispatches() if "--smoke" in argv.split()
        }
        assert flagged, "--profile full suppressed the reduced-scale flag routing"


class TestFullScalePathDidNotMove:
    """The regression rail for "production is exactly what it was".

    Plan 26-11 rewrote every stage's invocation line to interpolate one helper.
    The claim that none of them changed is worth nothing as an assertion; this
    is the snapshot that makes it checkable.
    """

    def test_no_stage_receives_the_smoke_flag_without_it(self, full_scale_run):
        offenders = [
            f"{stage}: {argv}"
            for stage, argv in full_scale_run.dispatches()
            if "--smoke" in argv.split()
        ]
        assert not offenders, (
            "a stage dispatched --smoke in a FULL-SCALE run. That is a "
            "substituted production run, which is the one thing 26-07's design "
            "forbids: " + "; ".join(offenders)
        )

    def test_the_full_scale_out_dir_is_still_experiments_results(self, full_scale_run):
        out_values = {
            argv.split()[argv.split().index("--out") + 1]
            for _, argv in full_scale_run.dispatches()
            if "--out" in argv.split()
        }
        assert "experiments/results" in out_values, (
            "no stage was pointed at experiments/results in a full-scale run; "
            f"the production out dir moved: {sorted(out_values)}"
        )
        assert "experiments/results_smoke" not in out_values, (
            "a FULL-SCALE run wrote into the reduced-scale tree"
        )

    def test_the_full_scale_dispatch_list_matches_the_frozen_snapshot(
        self, full_scale_run
    ):
        """The literal, line for line.

        If this fails and the change was intended, update the snapshot IN THE
        SAME COMMIT as the driver change and say why in the message -- the
        snapshot's only value is that it is not edited casually.
        """
        assert full_scale_run.dispatch_snapshot() == _FULL_SCALE_DISPATCH_SNAPSHOT, (
            "the full-scale dispatched command list changed.\nexpected:\n  "
            + "\n  ".join(_FULL_SCALE_DISPATCH_SNAPSHOT)
            + "\nactual:\n  "
            + "\n  ".join(full_scale_run.dispatch_snapshot())
        )

    def test_the_snapshot_covers_every_stage_that_can_be_observed(
        self, full_scale_run, manifest
    ):
        """Guard against a snapshot that passes because it captured nothing.

        A frozen list is worthless if the mechanism that fills it silently stops
        working, so the covered set is checked against the manifest rather than
        against itself. `preflight` and `prelaunch_probe` invoke no experiment;
        `e4_repeat` and `e2_band` build their invocations only after the seam
        returns.
        """
        covered = {line.split("\t", 1)[0] for line in _FULL_SCALE_DISPATCH_SNAPSHOT}
        expected = {stage["id"] for stage in manifest["stages"]} - {
            "preflight",
            "prelaunch_probe",
            "e4_repeat",
            "e2_band",
        }
        assert covered == expected, (
            f"snapshot coverage drifted. Missing: {sorted(expected - covered)}; "
            f"unexpected: {sorted(covered - expected)}"
        )
        assert full_scale_run.dispatch_snapshot(), (
            "the dispatch recorder captured nothing at all, so the snapshot "
            "test above passed vacuously"
        )


class TestPortableInterpreterResolution:
    """D-12 as SUPERSEDED by D-29: the conda-env-by-name rung is gone.

    D-12 asked for a three-rung chain whose middle rung discovered a conda env
    named `AquaCal` on either platform. Plan 27-01 measured the Linux run
    machine and the author deleted that rung outright (D-29): the env there is
    lowercase `aquacal`, and case-fixing it would have pointed the fallback at
    exactly the environment D-26 excludes -- OpenCV **4.14.0**, the version
    `pyproject.toml` pins against for a measured reason. Auto-discovery by name
    is the defect; the case was incidental.
    """

    def test_the_resolution_is_logged_on_success_not_only_on_failure(self, pooled_run):
        """A run against the wrong interpreter must be visible in the log.

        Before D-29 the only interpreter output was a stderr WARNING on the
        degrade path, so a successful resolve to the WRONG environment left no
        trace at all.
        """
        assert "INTERPRETERS:" in pooled_run.stdout, (
            "the driver never printed which interpreter it resolved.\n"
            f"{pooled_run.stdout[:3000]}"
        )
        assert "rung:" in pooled_run.stdout, (
            "the resolution line does not name WHICH rung won"
        )
        assert "PRELAUNCH_GATE_PYTHON" in pooled_run.stdout, (
            "the resolution line must name the override, so an operator on a "
            "machine where the fallback is wrong knows what to set"
        )

    def test_the_resolution_line_names_both_interpreters(self, pooled_run):
        """D-30: the gate interpreter is NOT the stage interpreter.

        `GATE_PYTHON` writes the run manifest; every stage runs bare
        `python -u -m experiments.<mod>`. Recording only one of them lets the
        manifest describe an interpreter that computed nothing.
        """
        line = next(
            line for line in pooled_run.stdout.splitlines() if "INTERPRETERS:" in line
        )
        assert "gate=" in line and "stage=" in line, line

    def test_no_conda_environment_is_discovered_by_name(self):
        """D-29, asserted on the driver SOURCE.

        The deleted rung is named in a comment on purpose -- the reason it went
        is worth more than the rung was -- so this looks for it as CODE.
        """
        source = DRIVER_PATH.read_text(encoding="utf-8")
        code = [
            line
            for line in source.splitlines()
            if not line.lstrip().startswith("#") and "envs/" in line
        ]
        assert not code, (
            "the driver resolves an interpreter by conda environment NAME "
            "again. D-29 deleted that rung because the name it would find on "
            f"the run machine carries the excluded OpenCV 4.14.0: {code}"
        )

    def test_the_stage_interpreter_variable_matches_the_stage_call_sites(self):
        """`SUITE_STAGE_PYTHON` must describe the interpreter stages ACTUALLY use.

        A variable naming an interpreter no stage runs would be a provenance
        record of nothing -- the D-30 defect in a new place.
        """
        source = DRIVER_PATH.read_text(encoding="utf-8")
        assert 'STAGE_PYTHON="python"' in source
        assert "export SUITE_STAGE_PYTHON=" in source
        call_sites = [
            line.strip()
            for line in source.splitlines()
            if "-u -m experiments." in line and not line.lstrip().startswith("#")
        ]
        assert call_sites, "no stage call site was found at all"
        offenders = [
            line for line in call_sites if "python -u -m experiments." not in line
        ]
        assert not offenders, (
            "a stage runs something other than bare `python -u -m`, so "
            f"SUITE_STAGE_PYTHON no longer describes it: {offenders}"
        )


class TestTheE2ReleaseConfigDefaultIsInRepo:
    """D-11/D-12: the exact E2 inputs live INSIDE the frozen sha.

    The default used to be an absolute path on the Windows planning box, which
    put the inputs of the run that produces the manuscript's Section 3 numbers
    outside the artifact describing them -- the F-001 shape.
    """

    def test_the_default_is_the_committed_linux_config(self, bash_available, tmp_path):
        run = run_driver(tmp_path, args=("--skip-e2",))
        assert "experiments/configs/e2_release_linux.yaml" in run.stdout, (
            f"the driver did not resolve the in-repo default.\n{run.stdout[:3000]}"
        )
        assert "in-repo default" in run.stdout

    def test_the_committed_config_actually_exists(self):
        assert (
            REPO_ROOT / "experiments" / "configs" / "e2_release_linux.yaml"
        ).is_file(), (
            "the driver's E2_RELEASE_CONFIG default points at a file that is "
            "not in the repository"
        )

    def test_the_override_still_wins(self, bash_available, tmp_path):
        """D-12's escape hatch: the Git Bash box is where defects get diagnosed.

        The committed default's paths are the LINUX target's, so a local E2 run
        needs this variable. It must not have been narrowed into a flag.
        """
        sentinel = (tmp_path / "somewhere_else.yaml").as_posix()
        run = run_driver(
            tmp_path,
            args=("--skip-e2",),
            extra_env={"SUITE_E2_RELEASE_CONFIG": sentinel},
        )
        assert sentinel in run.stdout, (
            "SUITE_E2_RELEASE_CONFIG did not repoint the release config.\n"
            f"{run.stdout[:3000]}"
        )
        assert "SUITE_E2_RELEASE_CONFIG override" in run.stdout

    def test_no_windows_literal_survives_as_a_default(self):
        """The Desktop path stays reachable, but only through the variable."""
        source = DRIVER_PATH.read_text(encoding="utf-8")
        code = [
            line
            for line in source.splitlines()
            if not line.lstrip().startswith("#") and "Desktop/Aqua" in line
        ]
        assert not code, f"a Windows literal is still reachable as code: {code}"

    def test_preflight_still_names_exactly_five_overrides(self, manifest):
        """D-12, still binding: no fourth refusal and no sixth flag.

        Phase 26 § D cut three pre-flight refusals; this phase adds none.
        """
        overrides = manifest["preflight"]["overrides"]
        assert len(overrides) == 5, sorted(overrides)
