# Phase 17: Per-Camera Interface Ablation Mode - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an opt-in `shared_interface: bool = True` config flag that, when `False`, gives each
optimized camera its own `water_z` parameter through the entire optimizer stack —
`pack_params`, `unpack_params`, `build_jacobian_sparsity`, `build_bounds`,
`build_structural_column_groups`, and per-camera seeding from `initial_water_z`. The default
shared-interface path must stay bit-for-bit unchanged (IFACE-05). This is an analysis/ablation
tool for the WP6 experiment, **not** a recommended production setting.

The numerical mechanics (packing, sparsity, bounds, column grouping, bit-exactness, equal-seed
recovery) are locked by the ROADMAP success criteria and IFACE-01..05. This context covers the
**user-facing presentation** of the mode: how it announces itself, how per-camera results are
surfaced, how seeding edge cases behave, and where the flag is exposed.

Out of scope: per-camera tilt/interface-normal (only `water_z` becomes per-camera); changing
shared-mode numerics; the full new-feature documentation write-up (Phase 21).
</domain>

<decisions>
## Implementation Decisions

### Ablation framing & warnings (IFACE-01)
- When `shared_interface=False`, emit exactly **one WARNING log line** at pipeline start.
- The message **includes the reason**, not just the non-recommendation — e.g. per-camera
  interface mode is active for degeneracy/ablation analysis only; the shared-interface
  assumption underlies the paper's central claim; not recommended for production calibration.
- Repeat the "analysis/ablation only, not recommended" framing in the `CalibrationConfig`
  field docstring for `shared_interface`.
- Add a **short docs stub** wherever refractive options are described, flagging the mode
  exists and is ablation-only. The complete write-up (worked example, WP6 context) defers to
  Phase 21.

### Per-camera spread reporting
- Per-camera mode surfaces the N recovered `water_z` values beyond storing them on each
  `CameraCalibration.water_z`, via **both**:
  1. A **console summary line** with per-camera `water_z` min/max/mean/std.
  2. A small **JSON file** under `output_dir/internals/` containing the per-camera
     `{name: water_z}` dict (in **meters**) plus spread stats `{min, max, mean, std, range}`.
     JSON chosen to match existing calibration JSON artifacts and be sweep-readable.
- **Always written in per-camera mode** — not gated behind a Phase 16 save flag and not behind
  a new flag. If the ablation was requested, its headline number is always produced.
- Console summary is human-facing → display in **mm** (project convention); the JSON file is
  machine-facing → **meters**.
- **When** it reports (final solution only vs every BA stage) = **Claude's discretion**,
  aligned to however Phase 16's per-stage internals artifacts are structured.

### Seed handling (per-camera path only) (IFACE-04)
- `initial_water_z is None` → **default-fill 0.15m for all cameras, silently** (matches
  current no-surprise behavior; optimizer separates values from an equal start).
- **Partial dict** (some cameras missing) → fill missing with 0.15m and **warn**, listing which
  cameras were defaulted.
- **Unknown keys** → **warn** on any key matching no known camera (likely a typo), but
  **silently ignore** keys belonging to `auxiliary_cameras` (legitimately excluded from joint
  BA, so no `water_z` parameter).
- All new seed/validation logic applies **only to the per-camera path**. Shared mode's
  consumption of `initial_water_z` is **left untouched** to protect the IFACE-05 bit-unchanged
  guarantee.

### Config exposure
- The **YAML config loader** must accept `shared_interface` — **pass-through only**, no
  cross-field validation at load time (the per-camera path's own seed/key warnings cover the
  real edge cases; keep loader logic in one place).
- `aquacal init`-generated config includes a **commented-out line with an inline note**:
  `# shared_interface: true  # set false for per-camera water_z ablation (analysis only, not recommended)`
  — discoverable, self-describing, inert by default.
- **No CLI flag** (`--shared-interface`) — YAML config is sufficient for an analysis knob.

### Claude's Discretion
- Timing of spread reporting (final-only vs per-BA-stage), matched to Phase 16 conventions.
- Exact JSON schema/key names for the spread file, matched to existing `internals/` artifacts.
- Exact warning/log message wording (content requirements above are the constraints).
- Whether the single-camera-rig case (per-camera mode meaningless) warrants any handling —
  not required; no load-time cross-field validation was mandated.
</decisions>

<specifics>
## Specific Ideas

- The per-camera `water_z` spread (min/max/std) is "the ablation's whole point" — the number
  the WP6 experiment reads. It must be trivially visible (console) and trivially machine-read
  (JSON), without a gating flag standing between the user and it.
- Distinguish *mistake* from *intent* in seed validation: unknown camera name = warn (typo);
  auxiliary-camera key = silently ignore (valid config).
- Keep the loader "dumb" — one place owns the per-camera logic, not two.
</specifics>

<deferred>
## Deferred Ideas

- **Full new-feature documentation** for per-camera mode (worked example, WP6 interpretation
  guidance) — Phase 21 owns the doc pass. Phase 17 ships only a stub + docstring.
- **CLI override flag** (`--shared-interface` / `--per-camera-interface`) for
  `aquacal calibrate` — considered and declined; revisit only if YAML config proves
  insufficient.
- **Per-camera tilt / interface normal** — explicitly out of scope; only `water_z` becomes
  per-camera this phase.

</deferred>

---

*Phase: 17-per-camera-interface-ablation-mode*
*Context gathered: 2026-07-23*
