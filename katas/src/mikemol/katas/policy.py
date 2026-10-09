# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The host's policy values, read from a data file instead of written into code (W796, W878).

The host katas.py kept these as constants (`GH`, `SKIP_FLUSH`, `HOLDER`, the tool paths, the bazel
version, the standing nemik warnings). Constants in code under `.claude/` are what standing rule 16
refuses; constants in a tracked package would put the operator's rulings in a place that needs a
commit to change. So they are DATA: a TOML file in the user's config directory, read at start, whose
every required key is checked and named when absent.

⚑ NOTHING HERE HAS A DEFAULT THAT NAMES A MACHINE. A path or a holder that is not in the file is an
error naming the key, never a guess; only values that are safe to omit (an empty skip list, no cron
job file, the standing waypoint `W2`) have defaults.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

CONFIG_NAME = "katas.toml"
"""The policy file's name, under `<config dir>/mikemol/`."""

REQUIRED = (
    "root",
    "logs",
    "commit_tool",
    "pathsforward",
    "host_state",
    "holder",
    "nemik",
    "templates",
    "bazel_version",
)
"""The keys the file must carry."""

_STANDING = "W2"


class PolicyError(Exception):
    """The policy file is missing, unreadable, or carries a missing or ill-typed key."""


@dataclass(frozen=True)
class Policy:
    """Every host value the katas read: where things are, who holds the lock, what to skip."""

    root: Path
    logs: Path
    commit_tool: Path
    pathsforward: Path
    host_state: Path
    holder: str
    nemik: Path
    templates: Path
    bazel_version: str
    skip_flush: frozenset[str] = field(default_factory=frozenset)
    standing_warnings: tuple[str, ...] = ()
    job_file: Path | None = None
    standing_waypoint: str = _STANDING


def default_path(env: Mapping[str, str], home: Path) -> Path:
    """Locate the policy file: `$XDG_CONFIG_HOME/mikemol/katas.toml`, else under `~/.config`.

    Returns:
        the path (it may not exist).

    """
    base = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else home / ".config"
    return base / "mikemol" / CONFIG_NAME


def _table(path: Path) -> dict[str, object]:
    """Read the file as a table.

    Returns:
        the parsed keys.

    Raises:
        PolicyError: when the file cannot be read or is not TOML.

    """
    try:
        parsed = cast("object", tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        msg = f"{path}: {exc}"
        raise PolicyError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"{path}: not a table"
        raise PolicyError(msg)
    return cast("dict[str, object]", parsed)


def _text(table: Mapping[str, object], key: str) -> str:
    """Read a key that must be a non-empty string.

    Returns:
        the string.

    Raises:
        PolicyError: naming the key.

    """
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{key}: required, a non-empty string"
        raise PolicyError(msg)
    return value


def _strings(table: Mapping[str, object], key: str) -> tuple[str, ...]:
    """Read an optional key that must be a list of strings.

    Returns:
        the strings; empty when the key is absent.

    Raises:
        PolicyError: naming the key.

    """
    value = table.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{key}: a list of strings"
        raise PolicyError(msg)
    return tuple(cast("list[str]", value))


def load(path: Path) -> Policy:
    """Read and check the policy file.

    Returns:
        the policy.

    Raises:
        PolicyError: listing every required key that is absent, or naming the ill-typed one.

    """
    table = _table(path)
    absent = [key for key in REQUIRED if key not in table]
    if absent:
        msg = f"{path}: missing required key(s): {', '.join(absent)}"
        raise PolicyError(msg)
    job = table.get("job_file")
    return Policy(
        root=Path(_text(table, "root")),
        logs=Path(_text(table, "logs")),
        commit_tool=Path(_text(table, "commit_tool")),
        pathsforward=Path(_text(table, "pathsforward")),
        host_state=Path(_text(table, "host_state")),
        holder=_text(table, "holder"),
        nemik=Path(_text(table, "nemik")),
        templates=Path(_text(table, "templates")),
        bazel_version=_text(table, "bazel_version"),
        skip_flush=frozenset(_strings(table, "skip_flush")),
        standing_warnings=_strings(table, "standing_warnings"),
        job_file=Path(_text(table, "job_file")) if job is not None else None,
        standing_waypoint=str(table.get("standing_waypoint") or _STANDING),
    )
