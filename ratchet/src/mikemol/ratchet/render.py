# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Render a ratchet verdict: how a census, its paydown, its moves and its growth READ.

Moved from substrate's `substrate/ratchet_render.py` (N-a row 4); its suite is ported to
`tests/test_render.py`.

⚑ THIS MODULE OWNS EVERY STRING A GATE PRINTS, AND NOTHING HERE TOUCHES A FILE: a renderer that
could also write would let a `--list` or `--quiet` run bank a baseline as a side effect of
formatting. `core` owns what is TRUE; this owns how it reads.

⚑⚑ TWO THINGS DID NOT TRAVEL AS WRITTEN (the letter's §3):
- `MINT_BYPASS` named `SUBSTRATE_RATCHET_WRITE=1`, an ambient switch this package does not have
  (`core`'s `write` is a REQUIRED argument). The default now describes the package's own model,
  and `Report.mint_bypass` lets a caller that still has an env switch supply its own wording.
- `list_pointer` offered the `--list` hint only when `sys.argv[0]` ended in `.py`, so a gate run as
  an INSTALLED CONSOLE SCRIPT silently lost it. A bare `argv[0]` cannot tell a console script from
  a non-CLI caller such as pytest (both are extensionless names), so the gate DECLARES its program
  name as `Report.prog`; inference from argv stays conservative (`.py` only), and a non-CLI
  caller still gets no pointer rather than a wrong one.
`emit` also takes an optional stream (stdout by default).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import TextIO

# How many lost keys a failed round-trip names before truncating.
LOST_SHOWN = 5

# ⚑ Named rather than inline: two adjacent strings meant as two list elements silently become one.
MINT_ROUTE = "  The baseline is MINTED BY THE COMMIT PATH, which is the promotion gate:  git commit"
MINT_BYPASS = (
    "  Calling the write path by hand (write=True) outside that route BYPASSES the gate and\n"
    "  banks a census against a tree nothing has approved — the `--no-verify` shape. "
    "Enumerate first:  --list"
)


@dataclass(frozen=True, slots=True)
class Report:
    """How a ratchet run renders its keys and its census.

    ⚑⚑ `render` is the per-KEY lift and `summary` the per-CENSUS one. `prog` is the gate's own
    program name, for the `--list` pointer; `mint_bypass` overrides the default bypass warning.
    """

    noun: str = "entries"
    render: Callable[[str], str] | None = None
    summary: str | None = None
    refuse_hint: str | None = None
    quiet: bool = False
    list_keys: bool = False
    prog: str | None = None
    mint_bypass: str | None = None


DEFAULT = Report()


@dataclass(frozen=True, slots=True)
class Voice:
    """Who is speaking and how: the pair every message in this module needs."""

    label: str
    report: Report

    @property
    def noun(self) -> str:
        """Name the census's unit, as this gate names it.

        Returns:
            the report's noun.

        """
        return self.report.noun


def renderer(voice: Voice) -> Callable[[str], str]:
    """Build a TOTAL key renderer, falling back to the bare key.

    ⚑ A PAID-DOWN key is by definition absent from the current census, so a renderer indexing a
    dict built from it raises exactly on the branch reporting PROGRESS. This wrapper stops a gate
    making its own good news crash.

    Returns:
        a renderer that never raises and never renders a key as blank.

    """
    custom = voice.report.render

    def _render(key: str) -> str:
        if custom is None:
            return key
        try:
            return custom(key) or key
        except (KeyError, IndexError, AttributeError, TypeError, ValueError):
            return key

    return _render


def emit(lines: Iterable[str], stream: TextIO | None = None) -> None:
    """Write a gate's message as ONE ordered narrative, to one stream.

    ⚑ Splitting a verdict from its findings across stdout/stderr lets them flush independently.
    """
    (stream or sys.stdout).write("\n".join(lines) + "\n")


def list_pointer(count: int, noun: str, prog: str | None = None) -> str:
    """Name the enumeration mode for a population of `count`.

    ⚑ The program is the gate's DECLARED name when it gives one; otherwise it is read from
    `sys.argv[0]` only when that is a `.py` script. A non-CLI caller gets no pointer rather than
    a fabricated one.

    Returns:
        the pointer line, or "" for an empty census or an unknown program.

    """
    if not count:
        return ""
    name = prog
    if name is None:
        argv0 = sys.argv[0] if sys.argv and sys.argv[0] else ""
        name = Path(argv0).name if argv0.endswith(".py") else ""
    if not name:
        return ""
    return f"\n  ↳ {name} --list   enumerates the {count} — WHICH {noun}, not how many."


def census_listing(keys: set[str], voice: Voice) -> list[str]:
    """Render the whole census, one key per line, ending with its count.

    Returns:
        the lines.

    """
    render = renderer(voice)
    tail = f" ({voice.report.summary})" if voice.report.summary else ""
    total = f"{voice.label}: {len(keys)} {voice.noun} in the current census{tail}"
    return [*(f"    {render(k)}" for k in sorted(keys)), total]


def moved_lines(moved: set[tuple[str, str]], voice: Voice) -> list[str]:
    """Render relocations: same debt, new home, neither paydown nor growth.

    Returns:
        the lines; none for no moves, or under quiet.

    """
    if not moved or voice.report.quiet:
        return []
    render = renderer(voice)
    head = (
        f"{voice.label}: {len(moved)} {voice.noun} RELOCATED (same debt, new home — "
        f"not paydown, not growth):"
    )
    return [head, *(f"    ~ {render(src)}\n      -> {render(dst)}" for src, dst in sorted(moved))]


def paid_lines(
    paid: set[str], sizes: tuple[int, int], voice: Voice, *, verb: str, dry: bool
) -> list[str]:
    """Render paydown, given the (before, after) baseline sizes, whether or not keys were added.

    Returns:
        the lines; none for no paydown.

    """
    if not paid:
        return []
    render = renderer(voice)
    before, after = sizes
    lines = []
    if dry:
        lines.append(f"{voice.label}: [--dry-run] previewing the write; nothing recorded")
    lines.append(
        f"{voice.label}: baseline {verb} {before} -> {after} ({len(paid)} {voice.noun} paid down)"
    )
    lines.extend(f"    - {render(k)}" for k in sorted(paid))
    return lines


def added_lines(added: set[str], paid_count: int, voice: Voice) -> list[str]:
    """Render growth: the refusal, and any paydown it blocks.

    Returns:
        the lines; none for no growth. Quiet never silences a refusal.

    """
    if not added:
        return []
    render = renderer(voice)
    head = (
        f"{voice.label}: BROKEN — {len(added)} NEW {voice.noun} (this census is "
        f"DEBT; it may only be PAID DOWN, not grown):"
    )
    lines = [head, *(f"    + {render(k)}" for k in sorted(added))]
    if paid_count:
        lines.append(
            f"  ⚑ {paid_count} genuine paydown(s) above CANNOT record while any "
            f"NEW key is present — clear the additions and they land."
        )
    if voice.report.refuse_hint:
        lines.append(f"  {voice.report.refuse_hint}")
    return lines


def frozen_line(count: int, voice: Voice) -> str:
    """Render the at-baseline case, naming the mode that enumerates it.

    Returns:
        the line, with the `--list` pointer when the program is known.

    """
    pointer = list_pointer(count, voice.noun, voice.report.prog)
    return f"{voice.label}: at baseline {count} {voice.noun} (frozen){pointer}"


def no_baseline_lines(count: int, path: str, voice: Voice) -> list[str]:
    """Render the would-record case for a baseline that does not exist yet.

    ⚑ Name the ROUTE, not the mechanism: a wrong baseline in a paydown-only ratchet is debt that
    can never legitimately be paid.

    Returns:
        the lines: the head, the mint route, and the bypass warning.

    """
    head = f"{voice.label}: no baseline at {path} — would record {count} {voice.noun}"
    return [head, MINT_ROUTE, voice.report.mint_bypass or MINT_BYPASS]


def roundtrip_failure(
    lost: set[str], gained: set[str], sizes: tuple[int, int], voice: Voice
) -> list[str]:
    """Render a baseline that did not read back as written, given (wrote, read) sizes.

    ⚑⚑ A write succeeding is not a read agreeing.

    Returns:
        the lines, naming lost and spurious counts and the first lost keys.

    """
    render = renderer(voice)
    wrote, read = sizes
    head = (
        f"{voice.label}: ⚑ BASELINE DID NOT ROUND-TRIP — wrote {wrote}, read back "
        f"{read} ({len(lost)} lost, {len(gained)} spurious)"
    )
    return [head, *(f"    lost: {render(k)}" for k in sorted(lost)[:LOST_SHOWN])]


def recorded_line(count: int, read_back: int, path: str, voice: Voice) -> str:
    """Render a verified baseline mint.

    Returns:
        the line, stating what was read back.

    """
    return (
        f"{voice.label}: baseline recorded = {count} {voice.noun} -> "
        f"{Path(path).name} ({read_back} keys read back, verified)"
    )
