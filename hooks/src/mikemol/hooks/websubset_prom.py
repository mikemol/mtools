# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Codon idiom census as a Prometheus textfile, so the burn-down is a series (mtools:W1350).

⚑ A MEASUREMENT IS A SERIES, NOT A SPOT READING (operator direction relayed by github-8f): the tree
census says how many modules each refused idiom blocks today; written as a node-exporter textfile on
every run, the same rows plot as the burn-down and each rewrite shows as a step. The house shape is
`repin_metrics`: gauges, a `scan_time_seconds` that is a parameter (never read here, so the body is
a pure function of its inputs), and an atomic write.

    mikemol_codon_idiom_modules{repo,target,rule}   modules the rule blocks
    mikemol_codon_idiom_sites{repo,target,rule}     sites of the rule in all of them
    mikemol_codon_modules{repo,target}              modules read
    mikemol_codon_clean_modules{repo,target}        modules with no finding under the target

⚑ A RULE WITH NO FINDING IS ABSENT, NOT ZERO, unless it was seen before: a series that drops out of
the textfile reads as stale, so every rule of the target is written for every repo, 0 included. That
is what makes the last module leaving a rule show as a step to 0 and not as a vanished line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import websubset

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.hooks.websubset_tree import TreeCensus

PREFIX = "mikemol_codon"
_ESCAPES = (("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"))
_HELP = {
    "modules": "src modules read",
    "clean_modules": "src modules with no finding under the target",
    "idiom_modules": "modules the rule blocks",
    "idiom_sites": "sites of the rule across all modules",
}


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


def render(counted: Sequence[tuple[str, TreeCensus]], scanned: int | None = None) -> str:
    """Render the censuses, one per repo, as the textfile body.

    Returns:
        the exposition text, ending in a newline; `scan_time_seconds` is left out when `scanned`
        is None.

    """
    out: list[str] = []
    if scanned is not None:
        out += _header("scan_time_seconds", "unix time the census was taken")
        out.append(f"{PREFIX}_scan_time_seconds {scanned}")
    families: dict[str, list[str]] = {name: [] for name in _HELP}
    for repo, found in counted:
        base = {"repo": repo, "target": found.target}
        families["modules"].append(_series("modules", base, found.total))
        families["clean_modules"].append(_series("clean_modules", base, found.clean))
        for rule in sorted(websubset.RULES[found.target]):
            modules, sites = _reach(found, rule)
            labels = {**base, "rule": rule}
            families["idiom_modules"].append(_series("idiom_modules", labels, modules))
            families["idiom_sites"].append(_series("idiom_sites", labels, sites))
    for name, help_text in _HELP.items():
        out += _header(name, help_text)
        out += families[name]
    return "\n".join(out) + "\n"


def _reach(found: TreeCensus, rule: str) -> tuple[int, int]:
    """Read one rule's modules and sites from a census.

    Returns:
        (modules, sites), both 0 for a rule with no finding.

    """
    for count in found.rules:
        if count.rule == rule:
            return count.modules, count.sites
    return 0, 0


def publish(path: Path, text: str) -> None:
    """Write the textfile atomically, so a scraper never reads half of one.

    The text goes to a sibling temporary file and is renamed over `path`.
    """
    scratch = path.with_name(f".{path.name}.tmp")
    scratch.write_text(text, encoding="utf-8")
    scratch.replace(path)
