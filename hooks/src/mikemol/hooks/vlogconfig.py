# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The settings of `mikemol-vlog`: flags over the host's config file, and the stream pairs (W1179).

⚑ NOTHING HERE NAMES WHERE THE STORE IS. The config file (`~/.config/mikemol/vlog.toml`) supplies
`service`, `resolver` (an argv list with `{name}`), `spool_dir`, `max_lines` and `max_bytes`; a flag
overrides the file; with no service the lines are spooled and kept (`vlogship.drain_all`).

⚑ A SOURCE'S LINE TIME IS DECLARED IN DATA (W1185): `[stamps.NAME]` holds a `pattern` with exactly
one capture group and a `form` (`iso` or `epoch`), and `--stamp NAME` picks it. A name that is not
declared, a pattern that does not compile, or one without exactly one group is refused by name, so
a typo cannot silently fall back to the ship time.

CONSUMED BY: `vlogcli`.
"""

import os
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.hooks import vlogrecord, vlogship

DEFAULT_MAX_LINES = 100_000
DEFAULT_MAX_BYTES = 64 << 20
CONFIG_PATH = Path("~/.config/mikemol/vlog.toml")
FORMS = ("iso", "epoch")
ON_FULL = ("drop-oldest", "hold")
DEFAULT_ON_FULL = "drop-oldest"


@dataclass(frozen=True)
class Flags:
    """The settings given on the command line; None means the flag was not given."""

    service: str | None = None
    resolver: Sequence[str] | None = None
    spool_dir: Path | None = None
    max_lines: int | None = None
    max_bytes: int | None = None
    source: str | None = None


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


def _share(entry: object, key: str) -> int | None:
    """Read one source's integer cap for `key`.

    Returns:
        the cap, or None when the entry is not a table or declares no integer for the key.

    """
    if not isinstance(entry, dict):
        return None
    value = cast("dict[str, object]", entry).get(key)
    return value if isinstance(value, int) else None


def oversubscribed(table: Mapping[str, object]) -> str | None:
    """Say whether the per-source caps add up to more than the spool total.

    ⚑ A CAP IS THAT SOURCE'S SHARE OF THE TOTAL (W1213, luthen's shape): `max_lines` and
    `max_bytes` in `[source.NAME]` are carved out of the top-level pair, each source in its own
    spool file. Caps that sum above the total could not all be honoured, so a typo that
    oversubscribes is refused BY NAME instead of silently exceeding the ceiling. A source with no
    cap of its own is not counted and keeps the whole total as its bound.

    Returns:
        the reason, or None when the caps fit.

    """
    group = table.get("source")
    declared = cast("dict[str, object]", group) if isinstance(group, dict) else {}
    for key, default in (("max_lines", DEFAULT_MAX_LINES), ("max_bytes", DEFAULT_MAX_BYTES)):
        total = _number(table, key, None, default)
        shares: dict[str, int] = {}
        for name, entry in declared.items():
            share = _share(entry, key)
            if share is not None:
                shares[name] = share
        if sum(shares.values()) > total:
            names = ", ".join(f"{name}={shares[name]}" for name in sorted(shares))
            return f"the {key} caps of [source.*] ({names}) add up to more than the total {total}"
    return None


def merged_table(table: Mapping[str, object], source: str | None) -> dict[str, object] | str:
    """Lay `[source.NAME]` over the top-level settings, so the ceiling is declared per source.

    ⚑ THE POLICY IS DATA, NOT A CODE DEFAULT (W1186, luthen's ask): a source names its own
    `max_lines`, `max_bytes` and `on_full` (`drop-oldest` or `hold`), the top level supplies the
    default for the rest, and a typo in any `on_full` is refused by name rather than read as the
    default. An undeclared source is refused with the declared ones listed, and caps that add up
    to more than the total are refused (`oversubscribed`).

    Returns:
        the merged table, or the reason the source or a policy cannot be used.

    """
    over = oversubscribed(table)
    if over is not None:
        return over
    merged = {k: v for k, v in table.items() if k != "source"}
    group = table.get("source")
    declared = cast("dict[str, object]", group) if isinstance(group, dict) else {}
    if source is not None:
        entry = declared.get(source)
        if not isinstance(entry, dict):
            known = ", ".join(sorted(declared)) or "none declared"
            return f"source {source!r} is not declared in [source] ({known})"
        merged.update(cast("dict[str, object]", entry))
    policy = merged.get("on_full", DEFAULT_ON_FULL)
    if policy not in ON_FULL:
        return f"on_full {policy!r} is not one of {' or '.join(ON_FULL)}"
    return merged


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
    policy = table.get("on_full")
    return vlogship.Config(
        spool.expanduser(),
        flags.service or (named if isinstance(named, str) else None),
        tuple(from_file if flags.resolver is None else flags.resolver),
        _number(table, "max_lines", flags.max_lines, DEFAULT_MAX_LINES),
        _number(table, "max_bytes", flags.max_bytes, DEFAULT_MAX_BYTES),
        policy if isinstance(policy, str) and policy in ON_FULL else DEFAULT_ON_FULL,
        flags.source,
    )


def stamp_named(table: Mapping[str, object], name: str) -> vlogrecord.LineStamp | str:
    """Read the stamp kind called `name` from `[stamps.NAME]`.

    Returns:
        the stamp, or the reason it cannot be used (undeclared, a bad pattern, not exactly one
        capture group, an unknown form).

    """
    group = table.get("stamps")
    declared = cast("dict[str, object]", group) if isinstance(group, dict) else {}
    entry = declared.get(name)
    if not isinstance(entry, dict):
        known = ", ".join(sorted(declared)) or "none declared"
        return f"stamp {name!r} is not declared in [stamps] ({known})"
    fields = cast("dict[str, object]", entry)
    pattern, form = fields.get("pattern"), fields.get("form", "iso")
    if not isinstance(pattern, str) or form not in FORMS:
        return f"stamp {name!r} needs a string pattern and a form of {' or '.join(FORMS)}"
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return f"stamp {name!r} pattern does not compile: {exc}"
    if compiled.groups != 1:
        return f"stamp {name!r} pattern needs exactly one capture group, has {compiled.groups}"
    return vlogrecord.LineStamp(compiled, str(form))


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
