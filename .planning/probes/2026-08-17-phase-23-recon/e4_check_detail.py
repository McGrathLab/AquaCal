"""Scratch: enumerate exactly which E4 columns mismatch under --check. Read-only."""

from pathlib import Path

import pandas as pd

import experiments.e4_benchmark_grid as m

out_dir = Path("experiments/results")
committed = pd.read_csv(out_dir / "benchmark_grid.csv")

cell_statuses = []
for n_cameras, n_frames in m.DECLARED_CELLS:
    cf = (
        out_dir
        / "e4_cells"
        / f"cameras_{n_cameras}_frames_{n_frames}"
        / "benchmark.json"
    )
    cell_statuses.append(
        {
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": "ok" if cf.exists() else "failed",
            "status_reason": "" if cf.exists() else "missing",
            "exit_code": None,
        }
    )

fresh = m.build_grid_dataframe(out_dir, cell_statuses, m.E2_BENCHMARK_PATH)

key = (
    m.GRID_KEY_COLUMNS[0]
    if isinstance(m.GRID_KEY_COLUMNS, (list, tuple))
    else "cell_key"
)
c, f = committed.set_index(key), fresh.set_index(key)
common = [i for i in c.index if i in f.index]
print(f"key={key}  committed={len(c)} fresh={len(f)} common={len(common)}")
print(f"committed-only: {[i for i in c.index if i not in f.index]}")
print(f"fresh-only:     {[i for i in f.index if i not in c.index]}")

cols = [col for col in c.columns if col in f.columns]
bad = {}
for col in cols:
    for r in common:
        a, b = c.loc[r, col], f.loc[r, col]
        if pd.isna(a) and pd.isna(b):
            continue
        try:
            if abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(a))):
                continue
        except (TypeError, ValueError):
            if str(a) == str(b):
                continue
        bad.setdefault(col, []).append((r, a, b))

print(f"\ncolumns compared: {len(cols)}")
print(f"MISMATCHING COLUMNS: {sorted(bad)}")
for col, items in sorted(bad.items()):
    print(f"\n### {col}  ({len(items)}/{len(common)} rows)")
    for r, a, b in items[:3]:
        print(f"   {r}: committed={a!r} fresh={b!r}")
