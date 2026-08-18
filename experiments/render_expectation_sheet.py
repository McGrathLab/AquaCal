"""Render `experiments/EXPECTATIONS.md`'s generated region from the manifest.

D-05 makes `experiments/suite_expectations.json` the single source of truth for
every stage, artifact, profile and row count the v2.1 full-suite re-run
produces. D-08 requires the hand-verification sheet to be RENDERED from it, with
a test that fails when the two drift apart -- not hand-maintained beside it.

This module is a **formatter, not a second source of truth**. It reads the
manifest through `experiments._expectations.load_expectations`, which is also
what validates it, and it owns exactly the text between

    <!-- BEGIN GENERATED -->
    <!-- END GENERATED -->

in `experiments/EXPECTATIONS.md`. Everything outside those markers is
hand-written prose -- the `--check` contract, the E2 qualification, the two
reading rules -- that a machine cannot derive and this module must never touch.

Usage::

    python -m experiments.render_expectation_sheet --check   # exit 1 if stale
    python -m experiments.render_expectation_sheet --write   # regenerate

`--write` is idempotent: a second run leaves the file byte-identical.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from experiments._expectations import load_expectations

#: The sheet this module owns a region of.
SHEET_PATH = Path(__file__).resolve().with_name("EXPECTATIONS.md")

#: The region delimiters. Exactly one pair may appear in the sheet.
BEGIN_MARKER = "<!-- BEGIN GENERATED -->"
END_MARKER = "<!-- END GENERATED -->"

#: Named once so the failure message and the docstring cannot drift apart.
REGENERATE_COMMAND = "python -m experiments.render_expectation_sheet --write"


def _format_hours(value: Any) -> str:
    """Render an `est_hours.value`, which is a scalar or a [low, high] pair."""
    if isinstance(value, list):
        low, high = value
        return f"{low:g}-{high:g}"
    return f"{value:g}"


def _escape(text: str) -> str:
    """Make a value safe inside a markdown table cell."""
    return text.replace("|", "\\|")


def _rows_cell(artifact: dict[str, Any]) -> str:
    """The `full`-profile row expectation, or why there is none."""
    expected = artifact["rows"].get("full")
    if expected is None:
        return "not pinned"
    return str(expected)


def _yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def _stage_table(manifest: dict[str, Any]) -> list[str]:
    lines = [
        "| # | Stage | Concurrency | Est. h | Profiles | Output directory |",
        "|---|---|---|---|---|---|",
    ]
    for index, stage in enumerate(manifest["stages"], start=1):
        lines.append(
            f"| {index} | `{stage['id']}` | {stage['concurrency']} | "
            f"{_format_hours(stage['est_hours']['value'])} | "
            f"{', '.join(stage['profiles'])} | `{stage['out_dir']}` |"
        )
    return lines


def _artifact_table(manifest: dict[str, Any]) -> list[str]:
    lines = [
        "| Artifact | Stage | Directory | Rows (`full`) | Conditional | "
        "Immutable | Shape-only columns |",
        "|---|---|---|---|---|---|---|",
    ]
    for artifact in manifest["artifacts"]:
        shape_only = artifact["shape_only_columns"]
        shape_cell = (
            ", ".join(f"`{column}`" for column in shape_only) if shape_only else "—"
        )
        lines.append(
            f"| `{artifact['name']}` | `{artifact['stage']}` | "
            f"`{artifact['dir']}` | {_rows_cell(artifact)} | "
            f"{_yes_no(artifact['conditional'])} | "
            f"{_yes_no(artifact['immutable'])} | {_escape(shape_cell)} |"
        )
    return lines


def render_sheet(manifest: dict[str, Any] | None = None) -> str:
    """Render the sheet's generated region.

    Args:
        manifest: A pre-loaded manifest, for tests. Defaults to the committed
            one, loaded (and validated) by `load_expectations`.

    Returns:
        The text that belongs between `BEGIN_MARKER` and `END_MARKER`,
        newline-terminated. Derived entirely from the manifest -- this function
        introduces no expectation of its own.
    """
    data = load_expectations() if manifest is None else manifest
    summary = data["wall_clock_summary"]

    full_artifacts = [a for a in data["artifacts"] if "full" in a["profiles"]]
    pinned = [a for a in full_artifacts if a["rows"].get("full") is not None]
    conditional = [a for a in data["artifacts"] if a["conditional"]]
    immutable = [a for a in data["artifacts"] if a["immutable"]]
    shape_only = [a for a in data["artifacts"] if a["shape_only_columns"]]

    lines: list[str] = [
        "",
        "*This region is generated from `experiments/suite_expectations.json`.*",
        f"*Do not edit it by hand — run `{REGENERATE_COMMAND}`.*",
        "",
        "### Shape of the run",
        "",
        f"- **{len(data['stages'])} stages**, "
        f"**{len(data['artifacts'])} declared artifacts** "
        f"({len(full_artifacts)} expected under the `full` profile, of which "
        f"{len(pinned)} pin a row count).",
        f"- **{len(conditional)} conditional** artifact(s): legitimately absent "
        "when the condition did not hold, and their absence is not evidence of "
        "an incomplete run.",
        f"- **{len(immutable)} immutable** artifact(s): the re-run must not "
        "change them.",
        f"- **{len(shape_only)} artifact(s) carry shape-only columns** — present "
        "and correctly counted proves nothing about their values. Those are the "
        "cells a hand-verifier actually has to read.",
        f"- Serial wall clock **{_format_hours(summary['serial_total_hours'])} h**; "
        "with the concurrency pool "
        f"**{_format_hours(summary['expected_total_with_concurrency_hours'])} h**. "
        f"Dominant stage `{summary['dominant_stage']}` at "
        f"{_format_hours(summary['dominant_stage_hours'])} h.",
        "",
        "### Stages, in execution order",
        "",
        *_stage_table(data),
        "",
        "### Every expected artifact",
        "",
        "`Rows (full)` is the exact data-row count the completeness gate asserts "
        "under the `full` profile; `not pinned` means the artifact is a JSON "
        "sidecar or otherwise has no table shape to assert. `Shape-only columns` "
        "are columns whose PRESENCE is checked and whose VALUES are not — read "
        "them by hand.",
        "",
        *_artifact_table(data),
        "",
    ]
    return "\n".join(lines) + "\n"


def split_sheet(text: str) -> tuple[str, str, str]:
    """Split the sheet into (head, generated region, tail).

    Args:
        text: The whole sheet.

    Returns:
        `(head, generated, tail)`, where `head` ends with the begin marker's
        line and `tail` starts with the end marker's line, so that
        `head + generated + tail == text`.

    Raises:
        ValueError: If the markers are missing, out of order, or not unique.
            A sheet with two generated regions is a sheet where half the
            expectations are silently unmaintained, which is worse than none.
    """
    if text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise ValueError(
            f"{SHEET_PATH.name} must contain exactly one "
            f"{BEGIN_MARKER} / {END_MARKER} pair; found "
            f"{text.count(BEGIN_MARKER)} and {text.count(END_MARKER)}."
        )
    begin = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = text.index(END_MARKER)
    if end < begin:
        raise ValueError(
            f"{SHEET_PATH.name}: {END_MARKER} appears before {BEGIN_MARKER}."
        )
    return text[:begin], text[begin:end], text[end:]


def replace_generated_region(text: str, generated: str) -> str:
    """Return `text` with its generated region replaced by `generated`."""
    head, _, tail = split_sheet(text)
    return head + generated + tail


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument list, defaulting to `sys.argv[1:]`.

    Returns:
        0 when the sheet is up to date (or was just written), 1 when `--check`
        found it stale. The stale message always names `REGENERATE_COMMAND`:
        a failure that does not say how to fix it costs more than no check.
    """
    parser = argparse.ArgumentParser(
        prog="python -m experiments.render_expectation_sheet",
        description=(
            "Render EXPECTATIONS.md's generated region from "
            "suite_expectations.json (D-08)."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed sheet is stale. Never writes.",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the sheet's generated region in place.",
    )
    args = parser.parse_args(argv)

    text = SHEET_PATH.read_text(encoding="utf-8")
    generated = render_sheet()
    updated = replace_generated_region(text, generated)

    if args.write:
        if updated == text:
            print(f"{SHEET_PATH.name}: already up to date.")
        else:
            SHEET_PATH.write_text(updated, encoding="utf-8")
            print(f"{SHEET_PATH.name}: regenerated from suite_expectations.json.")
        return 0

    # --check is the default: this module must never write unless asked.
    if updated == text:
        print(f"{SHEET_PATH.name}: up to date with suite_expectations.json.")
        return 0
    print(
        f"{SHEET_PATH.name} is STALE: its generated region no longer matches "
        f"experiments/suite_expectations.json. Regenerate it with:\n"
        f"    {REGENERATE_COMMAND}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
