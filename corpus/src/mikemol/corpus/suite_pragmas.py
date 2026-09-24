# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read what a suite DECLARES about itself: the deps it needs and the tenant it wants.

Moved from substrate's `substrate/suite_pragmas.py` (N-a row 2); its suite is ported to
`tests/test_suite_pragmas.py`.

⚑⚑ THE DECLARATION LIVES IN THE SUITE, NEVER IN A ROSTER HERE: a `{path: deps}` map is current
only as of its last edit. A suite that needs numpy says so in one comment,
`# selftest-requires: numpy, scipy`, anywhere in the file.

⚑⚑ THE TENANT NAMES ARE THE CALLER'S. substrate admitted exactly `sandbox` and `live`, the two
its store authority names; that set is substrate's store policy (the same --live/--sandbox pair
its row-5 letter keeps out of shared code), so `tenant` takes the admitted names as an argument.
The rule itself travels unchanged: a tenant OUTSIDE the admitted set declares NOTHING, so a
misspelled `# selftest-tenant: sandbxo` never makes a runner invent a tenant from a typo.

⚑ AN ABSENT OR UNREADABLE DECLARATION IS NOT AN ERROR: a runner asks every discovered file, so
both readers return the empty answer and the failure surfaces when the suite is RUN.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

REQUIRES = re.compile(r"^#\s*selftest-requires:\s*(.+)$", re.MULTILINE)

# Any tenant word; whether it is ADMITTED is the caller's set, checked after the match.
TENANT = re.compile(r"^#\s*selftest-tenant:\s*(\S+)\s*$", re.MULTILINE)


def _source(path: str) -> str | None:
    """Read a suite's source.

    Returns:
        the source, or None when it cannot be read.

    """
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _captured(pattern: re.Pattern[str], src: str) -> str | None:
    """Return a pattern's first group, narrowed to `str` once, here.

    ⚑ `re.Match.group()` is typed `str | Any`; narrowing at this seam keeps both readers typed.

    Returns:
        the captured text, or None when the pattern did not match.

    """
    match = pattern.search(src)
    if match is None:
        return None
    got = match.group(1)
    return got if isinstance(got, str) else None


def requires(path: str) -> tuple[str, ...]:
    """Name the packages a suite declares it needs.

    Returns:
        the declared packages, trimmed; empty when none is declared or the file is unreadable.

    """
    src = _source(path)
    declared = None if src is None else _captured(REQUIRES, src)
    if declared is None:
        return ()
    return tuple(p.strip() for p in declared.split(",") if p.strip())


def tenant(path: str, *, admitted: Collection[str]) -> str | None:
    """Name the tenant FLAG a suite declares, when it names an admitted tenant.

    Returns:
        `--<tenant>` for a declared tenant in `admitted`; None for none, a typo, an unadmitted
        name, or an unreadable file.

    """
    src = _source(path)
    declared = None if src is None else _captured(TENANT, src)
    return f"--{declared}" if declared is not None and declared in admitted else None
