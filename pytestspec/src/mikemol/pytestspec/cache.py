# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A content-addressed cache of implementation results (W228), opted into with `--result-cache`.

⚑⚑ THE KEY IS THE CONFTEST'S CLAIM, NOT THE PLUGIN'S GUESS. Only the code that knows an
implementation can say everything it reads: a fixture and its operands are rarely all of it (the
W206 origin reads a whole default corpus, and one callee shells out to git). So nothing is cached
unless a `pytest_spec_cache_key` hookimpl names a key, and a hookimpl that returns None declares
that case uncacheable. The plugin's own hookimpl always returns None.

⚑ ONE KEY OR NONE. When two hookimpls name different keys for the same case, no key is sound,
so the case is not cached.

⚑ AN ENTRY NAMES ITS OWN KEY. The file is addressed by a hash of (impl, key), and a load checks
the stored impl and key against the asked-for ones, so a collision or a hand-copied file is a
miss, never a wrong hit. A result that JSON cannot hold is not stored; the case still runs.
"""

import hashlib
import json
from pathlib import Path
from typing import cast

import pluggy
import pytest

from mikemol.pytestspec.spec import Case

hookspec = pluggy.HookspecMarker("pytest")


@hookspec
def pytest_spec_cache_key(impl: str, case: Case) -> str | None:
    """Name the key that covers everything `impl` reads when it runs on `case`.

    Returns:
        the key, or None when the result must not be cached. The plugin registers this function
        as its own hookimpl, so a session with no conftest key caches nothing.

    """
    del impl, case
    return None


def key_for(config: pytest.Config, impl: str, case: Case) -> str | None:
    """Ask every hookimpl for the case's key.

    Returns:
        the one key they name, or None when none names one or two name different ones.

    """
    answers = cast("list[object]", config.hook.pytest_spec_cache_key(impl=impl, case=case))
    keys = {answer for answer in answers if isinstance(answer, str)}
    return keys.pop() if len(keys) == 1 else None


def entry(root: Path, impl: str, key: str) -> Path:
    """Locate the entry for (impl, key) under the cache root.

    Returns:
        the path its result is stored at, whether or not it exists.

    """
    digest = hashlib.sha256(f"{impl}\0{key}".encode()).hexdigest()
    return root / f"{digest}.json"


def load(root: Path, impl: str, key: str) -> tuple[bool, object]:
    """Read a stored result, if one was stored under exactly this impl and key.

    Returns:
        (True, result) on a hit; (False, None) when absent, unreadable, or stored for another key.

    """
    try:
        stored = cast("object", json.loads(entry(root, impl, key).read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return False, None
    if not isinstance(stored, dict):
        return False, None
    fields = cast("dict[str, object]", stored)
    if fields.get("impl") != impl or fields.get("key") != key or "result" not in fields:
        return False, None
    return True, fields["result"]


def store(root: Path, impl: str, key: str, result: object) -> bool:
    """Write a result under (impl, key), atomically.

    Returns:
        True when stored; False when JSON cannot hold the result, which is then left uncached.

    """
    payload: dict[str, object] = {"impl": impl, "key": key, "result": result}
    try:
        text = json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        return False
    target = entry(root, impl, key)
    root.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(target)
    return True
