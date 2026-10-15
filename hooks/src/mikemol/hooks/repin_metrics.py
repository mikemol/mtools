# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A pin census as a Prometheus textfile, so fleet pin drift is a series (mtools:W979).

⚑ A SURVEY IS A ONE-OFF AND A SERIES IS A TREND. `mikemol-repin` prints which repo pins which sha;
that answers today. Written as a node-exporter style textfile on every run, the same rows become
series a luthen producer turns into `luthen_` metrics and a Grafana row can plot: how many pins are
behind the par sha, and for how long.

⚑ ONE SERIES PER PIN, THE SHA AS A LABEL ONLY WHERE IT IS INFORMATION. `behind_par` and `vendored`
carry just `repo` and `dist`, so a pin moving to a new sha does not mint a new series of those; the
pinned sha lives on its own `pin_info` series (value 1), the Prometheus idiom for a label that
changes. `par_info` names the sha the census was taken against and `scan_info` the root, so a
reading of 0 behind is never separated from what it was measured against.

⚑ WITHOUT A PAR SHA NOTHING IS CLAIMED BEHIND: a census with no target has status `-` on every
pin, and `behind_par` is then absent rather than 0, because 0 would say "current" about a sha nobody
named.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mikemol.hooks.repin_cli import Row

PREFIX = "mikemol_repin"
_ESCAPES = (("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"))
_VENDORED = "VENDORED"
_DIFFERS = "DIFFERS"
_UNKNOWN = "-"


def _label(value: str) -> str:
    """Escape a label value as the exposition format wants.

    Returns:
        the value with backslash, quote and newline escaped.

    """
    for raw, escaped in _ESCAPES:
        value = value.replace(raw, escaped)
    return value


def _series(name: str, labels: dict[str, str], value: int) -> str:
    inner = ",".join(f'{key}="{_label(text)}"' for key, text in labels.items())
    return f"{PREFIX}_{name}{{{inner}}} {value}"


def _header(name: str, help_text: str) -> list[str]:
    return [f"# HELP {PREFIX}_{name} {help_text}", f"# TYPE {PREFIX}_{name} gauge"]


def render(rows: Iterable[Row], root: str, par: str | None, scanned: int | None = None) -> str:
    """Render the census as the textfile body.

    ⚑ `scan_time_seconds` IS WHEN THE CENSUS WAS TAKEN, in unix seconds, so a dead census alerts
    off a series rather than the textfile's mtime (luthen-observability:W806, mtools:W987). It is a
    parameter, never read here, so the body is a pure function of its inputs.

    Returns:
        the exposition text, ending in a newline; `behind_par` is left out when `par` is None and
        `scan_time_seconds` when `scanned` is None.

    """
    census = list(rows)
    out = _header("pins", "pins found in the scan")
    out.append(f"{PREFIX}_pins {len(census)}")
    if scanned is not None:
        out += _header("scan_time_seconds", "unix time the census was taken")
        out.append(f"{PREFIX}_scan_time_seconds {scanned}")
    out += _header("scan_info", "the root the census read")
    out.append(_series("scan_info", {"root": root}, 1))
    if par is not None:
        out += _header("par_info", "the sha the census was measured against")
        out.append(_series("par_info", {"sha": par}, 1))
    out += _header("pin_info", "the sha each pin holds; the value is always 1")
    out += [
        _series("pin_info", {"repo": r.repo, "dist": r.dist, "form": r.form, "sha": r.pinned}, 1)
        for r in census
    ]
    out += _header("vendored", "1 when the pin is a vendored wheel, which a repin never rewrites")
    out += [
        _series("vendored", {"repo": r.repo, "dist": r.dist}, int(r.status == _VENDORED))
        for r in census
    ]
    if par is not None:
        out += _header(
            "behind_par",
            "1 when a git pin differs from the par sha or a vendored wheel lacks a must-have fix, "
            "else 0",
        )
        out += [
            _series("behind_par", {"repo": r.repo, "dist": r.dist}, value)
            for r in census
            if (value := _behind(r)) is not None
        ]
        out += _header("missing_fix", "1 for each must-have fix a vendored wheel's commit lacks")
        out += [
            _series("missing_fix", {"repo": r.repo, "dist": r.dist, "fix": fix[:12]}, 1)
            for r in census
            for fix in r.missing or ()
        ]
    return "\n".join(out) + "\n"


def _behind(row: Row) -> int | None:
    """Say whether a pin is behind: by ancestry for a measured wheel, by sha for a git pin.

    ⚑ A WHEEL NOT MEASURED, AND A PIN WITH NO TARGET, ARE NOT CLAIMED CURRENT: both are None, so no
    series says 0 about a commit nothing was compared with.

    Returns:
        1 or 0, or None when there is no measurement to report.

    """
    if row.missing is not None:
        return int(bool(row.missing))
    if row.status in {_VENDORED, _UNKNOWN}:
        return None
    return int(row.status == _DIFFERS)


def publish(path: Path, text: str) -> None:
    """Write the textfile atomically, so a scraper never reads half of one.

    The text goes to a sibling temporary file and is renamed over `path`.
    """
    scratch = path.with_name(f".{path.name}.tmp")
    scratch.write_text(text, encoding="utf-8")
    scratch.replace(path)
