# 27-TARGET-FACTS — the Linux run machine, measured

**Measured:** 2026-08-19, over SSH from the Windows development box.
**Method:** seven read-only foreground `ssh` round trips (`uname`, `free`, `df`, `ls`, `find`,
`du -sb`, `python -V`). Nothing was written, installed, cloned or run on the target.

## Why this exists

Four Phase 27 plans were about to be written against assumptions about a machine nobody had
measured. This note turns those four assumptions into four measurements, **before** the freeze
window opens, so a number that has to change changes inside the frozen sha rather than after it.

| Reads this note | For |
|---|---|
| 27-02 / 27-08 | D-10's `min_total_bytes` floor — measured on the target, not assumed |
| 27-08 | D-11's committed Linux image-set config paths |
| 27-08 | D-12's `GATE_PYTHON` middle rung — what it actually resolves to here |
| 27-12 | D-15's `SUITE_WORKERS` 4–5 RSS confirmation |

Three of the four measurements came back **contradicting the assumption**. That is the point of
measuring first.

---

## Machine

The Linux run machine, referred to throughout as such. Hostname, username and key material are
deliberately absent (see the redaction note at the end).

| Fact | Measured | Floor / expectation | Verdict | Reason |
|---|---|---|---|---|
| OS | Ubuntu 22.04.4 LTS | — | — | matches D-25's amendment |
| Kernel | `6.8.0-136-generic` x86_64 | — | — | matches D-25 |
| CPU model | 13th Gen Intel Core i9-13900KF | — | — | first recorded here |
| Logical CPUs | **32** | — | — | matches D-25 |
| RAM total | **33,351,241,728 B** (31.06 GiB) | — | — | matches D-25's "31 GiB" |
| RAM available | 30,156,177,408 B (28.09 GiB) | — | — | at measurement time, idle |
| Swap | 34,359,734,272 B (32.0 GiB) | — | — | not previously recorded |
| Free disk at the clone parent (`$HOME` filesystem, `/dev/nvme0n1p2`) | **710,725,156,864 B** (662.0 GiB) | `preflight.free_space_floor_gib: 20` | **CLEARS** | 33× the floor; disk is not a constraint for this phase |
| `git` | 2.34.1 | — | — | sufficient for `clone --branch <tag>` and `describe --tags --long --dirty` |

**Cross-check against the 2026-08-19 Amendment (D-25):** every re-measured value agrees. The
amendment's "662 GB free" and this note's 710,725,156,864 B are the same number read in different
units (662.0 GiB = 710.7 GB); there is **no disagreement**. The CPU model and swap size are new
here.

---

## The E2 image set

**Root, as located on the target:** `$HOME/PycharmProjects/AquaCal/aquacal_data/real-rig/real-rig/`

It was found by probing, not supplied verbatim — the author authorised the probe and asked that the
path found be recorded here for confirmation at review. Its children are exactly the per-camera
`extrinsic/<cam>/` and `intrinsic/<cam>/` trees D-08 describes, plus four candidate configs, a
`reference_calibration.json`, a `reference_outputs/` directory and three prior `output*/` trees.

> **Confirm at review:** this root was inferred, not given. If the intended image set lives
> elsewhere, every byte figure below is measuring the wrong tree.

Frames are PNG (`frame0000.png`, `frame0001.png`, …).

### `extrinsic/` — 13 directories

`ls -1 extrinsic | wc -l` = **13**. Expected `cheap_check.n_extrinsic_videos` = **13**. **MATCH**
(12 main + 1 auxiliary `e3v8250`, exactly the rig composition).

| Camera | Files | Bytes (`du -sb`) |
|---|---:|---:|
| e3v8250 (auxiliary) | 262 | 268,100,250 |
| e3v829d | 262 | 321,735,536 |
| e3v82e0 | 262 | 286,818,850 |
| e3v82f9 | 262 | 290,598,441 |
| e3v831e | 262 | 287,939,216 |
| e3v832e | 262 | 296,805,933 |
| e3v8334 | 262 | 299,378,524 |
| e3v83e9 | 262 | 298,549,683 |
| e3v83eb | 262 | 296,622,486 |
| e3v83ee | 262 | 292,488,456 |
| e3v83ef | 262 | 274,884,390 |
| e3v83f0 | 262 | 285,536,679 |
| e3v83f1 | 262 | 299,638,445 |
| **Total (sum of the 13)** | **3,406** | **3,799,096,889** |

`du -sb` on the `extrinsic/` parent reports 3,799,100,985 — 4,096 B more, the parent directory's
own inode. **3,799,096,889 is the number D-10's recursive per-path sum will produce**, because the
probe sums the 13 declared paths and never sees the parent.

### `intrinsic/` — 13 directories

| Camera | Files | Bytes (`du -sb`) |
|---|---:|---:|
| e3v8250 (auxiliary, fisheye) | 116 | 111,749,211 |
| e3v829d | 50 | 50,415,984 |
| e3v82e0 | 41 | 39,923,518 |
| e3v82f9 | 34 | 32,406,783 |
| e3v831e | 34 | 32,334,996 |
| e3v832e | 44 | 44,088,565 |
| e3v8334 | 35 | 34,729,723 |
| e3v83e9 | 34 | 32,598,008 |
| e3v83eb | 38 | 37,666,662 |
| e3v83ee | 31 | 27,409,722 |
| e3v83ef | 37 | 32,495,121 |
| e3v83f0 | 33 | 32,103,941 |
| e3v83f1 | 34 | 33,633,466 |
| **Total (sum of the 13)** | **561** | **541,555,700** |

The intrinsic counts are **not uniform** (31–116 per camera). Nothing in the pre-flight reads them;
they are recorded so a future "is the intrinsic set complete?" question has a baseline rather than
a guess. **Do not derive an expectation from this table** — it is one measurement of one tree, and
D-10's prohibition on inventing frame-count expectations applies here for the same reason.

---

## Byte-floor finding

**The measured extrinsic total DOES NOT CLEAR the floor.**

| Quantity | Value |
|---|---:|
| Measured total over the 13 extrinsic directories | 3,799,096,889 B |
| `preflight.frameset.cheap_check.min_total_bytes` | 4,000,000,000 B |
| Shortfall | **200,903,111 B (5.02% short)** |

Verdict, in D-10's own words: **does not clear the floor; the floor must be re-derived from this
measurement (D-10 — the check's shape is fixed, the number may not be), which plan 27-08 does.**

Why this is a manifest number to re-derive and not a check to weaken — the evidence, so 27-08 does
not have to re-gather it:

- The floor's stated rationale is *"a crude discriminator, not an estimate … its ONLY job is to
  separate the two archives."* It is not an accuracy assertion, and lowering it costs nothing it
  was ever protecting.
- **4,000,000,000 was derived from "4.35 GB as published"** — the Zenodo record's *packaged*
  size. The on-disk expanded PNG tree is 3.80 GB decimal / 3.54 GiB. The floor was set against a
  number that does not describe the thing being summed. This is not a shortfall in the data; it is
  a unit/representation mismatch baked into the manifest on 2026-08-12.
- The frameset is **verified-signature-correct by every other observable**: 13 directories, 262
  files in each, all thirteen cameras present. There is no sign of the retired archive.
- The retired archive is ~4.3× subsampled — on the order of ~0.9 GB expanded. **Any floor between
  roughly 1.5e9 and 3.7e9 still separates the two archives**, which is the check's only job. The
  discriminating power lost by re-deriving is nil.

> **This does NOT authorise touching the check's shape.** D-10 is explicit: accept a file or a
> directory, sum recursively, keep both assertions, keep ABSENT (2) and MISMATCH (3) distinct, keep
> reading the numbers from `suite_expectations.json`. Only the literal `min_total_bytes` value is in
> question, and only 27-08 changes it — with `min_total_bytes_rationale` rewritten to say it was
> re-derived from an on-target measurement of the expanded tree, not from the packaged archive size.

### Two further findings for 27-08, surfaced by the same measurement

1. **The existing on-target config declares RELATIVE paths.**
   `config_paper_cv413.yaml` at the image-set root uses `extrinsic/e3v829d/` etc., with
   `output_dir: output_cv413`. The pre-flight probe does `pathlib.Path(p)` and then `p.exists()` —
   resolved against the **driver's cwd**, which under D-01/D-05 is the *frozen clone*, not the data
   root. A verbatim copy of this config into the repo would make the probe test
   `<clone>/extrinsic/e3v829d/`, which does not exist, and the driver would refuse with ABSENT.
   D-11's committed config must therefore use absolute target paths, or the probe must resolve
   relative paths against the config's own directory. **27-08 must decide which; it cannot copy the
   file unchanged.**

2. **That config is otherwise the D-11 config almost verbatim.** It already carries
   `detection.frame_step: 1`, `optimization.max_calibration_frames: 200`,
   `refine_intrinsics: true`, `refine_auxiliary_intrinsics: true`, the 12+1 camera split with
   `e3v8250` as both auxiliary and fisheye, and both board specs. Its header states the frames are
   *already* subsampled at every 30th video frame, so `frame_step: 1` over these images equals
   `frame_step: 30` over the source video — **which explains the Desktop config's `frame_step: 30`
   that D-11 flagged as a discrepancy.** The two configs are not in conflict; they address
   different input kinds. 27-08 should start from `config_paper_cv413.yaml`, not from scratch.

3. **Each extrinsic directory holds exactly 262 files, which equals the manifest's
   `usable_frames: 262`.** Recorded as an observation only. D-10 forbids turning it into an
   expectation and that prohibition stands — but the exact coincidence is worth an author's eye,
   because `usable_frames` is documented as *post-detection* and a raw file count should not
   normally equal it.

---

## Interpreter

`conda` is **not on the PATH** for a non-interactive `ssh host 'cmd'` — confirmed, exactly as D-28
records. `conda env list` is therefore unavailable remotely; envs were enumerated by listing
`~/anaconda3/envs` directly.

| Rung | Path probed | Result |
|---|---|---|
| env override | `SUITE_GATE_PYTHON` (or equivalent) | not set on the target; unmeasurable here |
| D-12 middle rung, as currently specified | `~/anaconda3/envs/**AquaCal**/bin/python` | **ABSENT** |
| the env that actually exists | `~/anaconda3/envs/**aquacal**/bin/python` | Python 3.11.15 |
| unrelated env | `~/anaconda3/envs/aquamvs/bin/python` | Python 3.12.13 |
| bare `python` | `command -v python` | **NOT FOUND — no `python` on the PATH at all** |
| bare `python3` | `/usr/bin/python3` | Python 3.10.12 |

**Two findings that bind D-12, both fatal to the chain as currently written:**

- **The env name is lowercase `aquacal`, and Linux filesystems are case-sensitive.** A middle rung
  spelled `AquaCal` resolves to nothing here. 27-08 must probe case-insensitively, glob
  `~/anaconda3/envs/*/bin/python`, or take the frozen env's path from an explicit variable.
- **The final fallback rung `python` does not exist.** Not "resolves to the wrong version" —
  absent. `GATE_PYTHON=python` would fail with *command not found*, which reads like a broken
  driver rather than an unresolved interpreter. If the chain is going to fall through, it must fall
  through to `python3`, and even then it lands on **3.10.12 — below `pyproject.toml`'s
  `requires-python = ">=3.11"`**, failing at import rather than at a clear version check (D-28).
  A loud resolution log is not sufficient on its own; the resolved interpreter's version should be
  asserted against the floor.

**D-26 and D-27 both re-confirmed, independently:**

- `~/anaconda3/envs/aquacal` holds `cv2 4.14.0`, numpy 2.4.6, scipy 1.17.1 — **4.14.0 is the exact
  version `opencv-python==4.13.*` exists to exclude.** 27-12 must build a new env.
- `site-packages/__editable__.aquacal-2.0.1.pth` contains the single line
  `$HOME/PycharmProjects/AquaCal/src` — a different checkout, at a different sha, on a different
  branch. Reusing this env would import unfrozen code while stamping the frozen sha.

**Clone target:** the author's chosen frozen-clone path is a fresh sibling of the form
`$HOME/aquacal-frozen-<tag>`. Both `$HOME/aquacal-frozen-rerun-freeze-01` and
`$HOME/aquacal-frozen` were checked and **neither exists**, so the clone lands on virgin ground.
It is deliberately **not** `$HOME/PycharmProjects/AquaCal` — D-27 records that checkout as the one
the existing env imports from at `27c80e7`, which is the silent-provenance failure this phase
exists to close.

---

## Headroom

Measured RSS classes from `.planning/probes/2026-08-18-solver-concurrency/`, against 31.06 GiB:

| Stage class | Measured RSS | 4 workers | 5 workers |
|---|---|---:|---:|
| 30 frames | < 1 GiB | < 4 GiB | < 5 GiB |
| 100 frames | 2.7–3.5 GiB | 10.8–14.0 GiB | 13.5–17.5 GiB |
| 200 frames | 9.3–11.3 GiB | — scheduler permits at most one — | — |

Worst realistic mix, one 200-frame stage plus the rest at the 100-frame ceiling:
11.3 + 3×3.5 = **21.8 GiB** at 4 workers, 11.3 + 4×3.5 = **25.3 GiB** at 5 workers, against
31.06 GiB total. **`SUITE_WORKERS` 4–5 holds**, with 5 the tighter of the two. 32 logical cores
against 4–5 processes each holding a measured median 0.99 cores means CPU is not the binding
resource; RAM is. 32 GiB of swap exists but is not headroom — a swapping solver is a stalled run.

**Do not re-tune this** (D-15). A short stage's RSS is a **floor**, not a setting, and the headroom
figure above is an **upper bound**. This is a confirmation that the existing 4–5 figure is still
sized correctly for the machine it will run on, and nothing more.

---

## What this note does NOT prove

**Nothing here proves the code runs on the target.** Every measurement above is `ls`, `du`, `df`
and `python -V`. No AquaCal code was imported, no environment was built, no repository was cloned.

- It does not prove the frozen sha imports on Linux.
- It does not prove the pre-flight passes — it proves the opposite for the byte floor, and 27-08
  has to act on that.
- It does not prove `GATE_PYTHON` resolves; it proves the currently-specified chain does not.
- It does not prove the E2 config's paths resolve from the driver's cwd; it raises the concern.

That is plan **27-12's** clean-clone verification, against the tag, in a fresh environment. It is
the only venue that can catch a Linux-only failure, and none of the above substitutes for it.

---

> **Pre-push flag** — for plan 27-11's audit, before 218 commits go public.
>
> The E2 image-set root and the frozen-clone path both live under the operator's home directory,
> whose name is a personal identifier. **Both are written here as `$HOME/…`, with the literal home
> directory deliberately elided**, so that no username appears in this file. Plan 27-11's audit
> should confirm that (a) no later plan re-expands `$HOME` into a committed artifact, and (b) the
> committed release config of D-11 does not embed the literal home path — which is a second, and
> better, reason for it to use paths resolved relative to the config or supplied by environment
> variable rather than absolute paths hard-coded into a public file.
>
> The machine's hostname, the SSH username and all key material are absent from this file by
> construction. The ssh-config **alias** `lab-pc` is used in prose because 27-CONTEXT.md § D-25
> already records it publicly and an alias is not a hostname.
