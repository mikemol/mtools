# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The settings of `mikemol-vlog`: flags over the host's config file, and the stream pairs (W1179).

⚑ NOTHING HERE NAMES WHERE THE STORE IS. The config file (`~/.config/mikemol/vlog.toml`) supplies
`service`, `resolver` (an argv list with `{name}`), `spool_dir`, `max_lines` and `max_bytes`; a flag
overrides the file; with no service the lines are spooled and kept (`vlogship.drain_all`).

CONSUMED BY: `vlogcli`.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.hooks import vlogship

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

DEFAULT_MAX_LINES = 100_000
DEFAULT_MAX_BYTES = 64 << 20
CONFIG_PATH = Path("~/.config/mikemol/vlog.toml")


@dataclass(frozen=True)
class Flags:
    """The settings given on the command line; None means the flag was not given."""

    service: str | None = None
    resolver: Sequence[str] | None = None
    spool_dir: Path | None = None
    max_lines: int | None = None
    max_bytes: int | None = None


def state_home() -> Path:
    """Find the user's state directory.

    Returns:
        `$XDG_STATE_HOME`, else `~/.local/state`.

    """
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")


def read_toml(path: Path) -> dict[str, object]:
    """Read the host config file.

    Returns:
        its table, empty when the file is missing or unreadable.

    """
    try:
        return cast("dict[str, object]", tomllib.loads(path.expanduser().read_text("utf-8")))
    except (OSError, ValueError):
        return {}


def _number(table: Mapping[str, object], key: str, flag: int | None, default: int) -> int:
    """Pick a bound: the flag, else the file's value when it is a positive integer, else default.

    Returns:
        the bound.

    """
    value = table.get(key)
    from_file = value if isinstance(value, int) and value > 0 else None
    return flag or from_file or default


def build(table: Mapping[str, object], flags: Flags) -> vlogship.Config:
    """Merge the flags over the config table.

    Returns:
        the shipper config.

    """
    listed = table.get("resolver", [])
    from_file = [str(x) for x in listed] if isinstance(listed, list) else []
    named = table.get("service")
    where = table.get("spool_dir")
    spool = flags.spool_dir or Path(str(where) if where else state_home() / "mikemol" / "vlog")
    return vlogship.Config(
        spool.expanduser(),
        flags.service or (named if isinstance(named, str) else None),
        tuple(from_file if flags.resolver is None else flags.resolver),
        _number(table, "max_lines", flags.max_lines, DEFAULT_MAX_LINES),
        _number(table, "max_bytes", flags.max_bytes, DEFAULT_MAX_BYTES),
    )


def streams_of(pairs: Sequence[str]) -> dict[str, str] | None:
    """Read `--stream KEY=VALUE` pairs.

    Returns:
        the mapping, or None when a pair has no `=` or an empty key.

    """
    found: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            return None
        found[key] = value
    return found
