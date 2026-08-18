"""Measure how much of the box a single AquaCal solve actually uses.

Question this answers: the full-suite driver runs stages strictly serially
(review H4), a rule written to protect timing measurements. Only E4, e4_repeat,
e2_timing and e2_memory are timing-sensitive; the accuracy stages (the seed
bands) are not. If one solve leaves most of a 32-core box idle, those stages
could run N-wide and cut the suite's wall clock far more than any grid cut.

Method: launch one E1 single-seed run (the cheapest solve in the suite, ~400 s
of solver time) as a subprocess, and sample the whole process tree's CPU
utilisation and RSS every 2 s.

Outputs, all under this probe's own directory:
  samples.csv  -- t_s, cores_busy, rss_gib, n_procs
  summary.json -- aggregates plus the derived concurrency headroom

Nothing is written to experiments/results/ -- the child gets --out into this
directory (D-03 pattern, Phase 25).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

PROBE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROBE_DIR.parents[2]
OUT_DIR = PROBE_DIR / "e1_out"
SAMPLE_INTERVAL_S = 2.0

# The box being characterised.
N_LOGICAL_CORES = psutil.cpu_count(logical=True)
TOTAL_RAM_GIB = psutil.virtual_memory().total / 1024**3

# The Linux target, for the headroom derivation (linux32gb_scope.json).
TARGET_CORES = 32
TARGET_RAM_GIB = 31.06


def tree_stats(root: psutil.Process) -> tuple[float, float, int]:
    """Return (cpu_percent_summed, rss_bytes_summed, n_procs) for a tree."""
    procs = [root]
    try:
        procs.extend(root.children(recursive=True))
    except psutil.Error:
        pass
    cpu = 0.0
    rss = 0.0
    alive = 0
    for p in procs:
        try:
            cpu += p.cpu_percent(interval=None)
            rss += p.memory_info().rss
            alive += 1
        except psutil.Error:
            continue
    return cpu, rss, alive


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "experiments.e1_refractive_comparison",
        "--force",
        "--out",
        str(OUT_DIR),
    ]
    print(f"[probe] box: {N_LOGICAL_CORES} logical cores, {TOTAL_RAM_GIB:.1f} GiB RAM")
    print(f"[probe] launching: {' '.join(cmd)}", flush=True)

    child_log = (PROBE_DIR / "e1_child.log").open("w", encoding="utf-8")
    started = time.time()
    proc = subprocess.Popen(
        cmd, cwd=REPO_ROOT, stdout=child_log, stderr=subprocess.STDOUT
    )
    root = psutil.Process(proc.pid)
    # Prime cpu_percent; the first call always returns 0.0.
    tree_stats(root)
    time.sleep(SAMPLE_INTERVAL_S)

    samples: list[tuple[float, float, float, int]] = []
    with (PROBE_DIR / "samples.csv").open("w", encoding="utf-8") as fh:
        fh.write("t_s,cores_busy,rss_gib,n_procs\n")
        while proc.poll() is None:
            cpu, rss, n = tree_stats(root)
            t = time.time() - started
            cores = cpu / 100.0
            gib = rss / 1024**3
            fh.write(f"{t:.1f},{cores:.3f},{gib:.3f},{n}\n")
            fh.flush()
            samples.append((t, cores, gib, n))
            time.sleep(SAMPLE_INTERVAL_S)

    child_log.close()
    elapsed = time.time() - started
    exit_code = proc.returncode

    # Ignore the first 30 s (imports, board detection setup) so the aggregate
    # describes the solve rather than the startup.
    solve = [s for s in samples if s[0] >= 30.0] or samples
    cores_series = sorted(s[1] for s in solve)
    rss_peak = max((s[2] for s in samples), default=0.0)

    def pct(series: list[float], q: float) -> float:
        if not series:
            return 0.0
        return series[min(len(series) - 1, int(q * (len(series) - 1)))]

    mean_cores = sum(cores_series) / len(cores_series) if cores_series else 0.0
    p50 = pct(cores_series, 0.50)
    p95 = pct(cores_series, 0.95)
    peak_cores = cores_series[-1] if cores_series else 0.0

    # Headroom on the Linux target: bounded by cores AND by memory.
    by_cores = TARGET_CORES / p95 if p95 > 0 else float("inf")
    by_mem = (TARGET_RAM_GIB * 0.85) / rss_peak if rss_peak > 0 else float("inf")

    summary = {
        "probe": "solver-concurrency",
        "date": "2026-08-18",
        "question": (
            "Does one AquaCal solve saturate the box? If not, the accuracy-only "
            "stages of the full-suite driver could run N-wide."
        ),
        "vehicle": "e1_refractive_comparison single-seed (both models)",
        "measured_on": {
            "logical_cores": N_LOGICAL_CORES,
            "ram_gib": round(TOTAL_RAM_GIB, 2),
            "python": sys.version.split()[0],
        },
        "child_exit_code": exit_code,
        "wall_clock_s": round(elapsed, 1),
        "n_samples": len(samples),
        "cores_busy": {
            "mean": round(mean_cores, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "peak": round(peak_cores, 2),
            "note": "excludes the first 30 s of startup",
        },
        "peak_rss_gib": round(rss_peak, 2),
        "concurrency_headroom_on_linux_target": {
            "target_cores": TARGET_CORES,
            "target_ram_gib": TARGET_RAM_GIB,
            "bounded_by_cores": round(by_cores, 1),
            "bounded_by_memory_at_85pct": round(by_mem, 1),
            "recommended_workers": max(1, int(min(by_cores, by_mem))),
            "caveat": (
                "E1 is the cheapest and smallest solve in the suite. E6/E7 band "
                "cells and E2 are larger; peak RSS especially does not transfer. "
                "Treat this as an upper bound on headroom, not a setting."
            ),
        },
    }
    (PROBE_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
