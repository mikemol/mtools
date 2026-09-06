# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The project a checker run belongs to — ambient to the analysis, not threaded through it.

⚑⚑⚑ A `ContextVar`, NOT A PARAMETER (operator, 2026-08-31: *"Contextvars; don't thread."*). The
governing project is a property of the RUN, not an argument each layer has an opinion about. A
first cut added `cwd=` to the subprocess caller and passed it down from the analyser — which
makes every intermediate signature carry a value it does not use, and obliges every future
caller to know about a decision that was already made upstream. That is the shape a
`ContextVar` exists to retire.

⚑⚑ AND THE ALTERNATIVE IS NOT A GLOBAL. A module-level variable would leak across concurrent
analyses and would have to be saved and restored by hand at every boundary; a `ContextVar`
scopes to the logical run, restores on `reset`, and is correct under threads and async without
either being designed for.

⚑ WHY THIS EXISTS AT ALL: A CONFIG'S RELATIVE PATHS RESOLVE AGAINST THE WORKING DIRECTORY, so
naming a config is not enough. MEASURED 2026-08-31 — a sibling repo declaring
`namespace-packages = ["src/mikemol"]` had it honoured when the checker ran FROM that repo and
IGNORED when the same file and the same `--config` were passed from elsewhere, so a lint rule
fired on a deliberate PEP 420 namespace and demanded the `__init__.py` whose absence is that
package's whole design. **Config, staging directory and working directory are one decision.**

⚑ UNSET MEANS THIS PROCESS'S DIRECTORY, which is what an in-repo edit always got implicitly.
Nothing changes until a caller has a better answer to bind.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# ⚑ THE DEFAULT IS `None`, MEANING "wherever this process already is". An explicit default of
# some repo's root would make the unbound case silently wrong for every other repo — the exact
# defect this module was written to remove.
_PROJECT: ContextVar[Path | None] = ContextVar("checker_project", default=None)


def project() -> Path | None:
    """Return the project a checker should run in, or None for this process's directory.

    Returns:
        project a checker should run in, or None for this process's directory.

    """
    return _PROJECT.get()


@contextmanager
def in_project(root: Path | None) -> Iterator[None]:
    """Bind the governing project for the duration of the block.

    ⚑ THE TOKEN IS RESET IN A `finally`, so an exception inside the analysis cannot leave a
    later run bound to an earlier one's project. A bare `set` without the reset is the
    hand-managed global this replaces, wearing a nicer API.
    """
    token = _PROJECT.set(root)
    try:
        yield
    finally:
        _PROJECT.reset(token)
