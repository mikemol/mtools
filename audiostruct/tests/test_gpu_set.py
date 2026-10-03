# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witness for the hand-listed GPU set: every wheel torch's cuda-toolkit extras require is staged.

rules_python stages `cuda-toolkit` without its extras, so `//audiostruct:gpu_set` names those
wheels by hand (W271). This reads the requirement from the installed metadata itself, torch's
`cuda-toolkit[...]` line and cuda-toolkit's per-extra `Requires-Dist`, and checks each named
wheel is a distribution in this process. Under bazel that is the staged set, so a torch move that
adds an extra, or a wheel dropped from the list, is a red rather than an OSError at first import.
"""

from __future__ import annotations

import re
from importlib import metadata

from packaging.requirements import Requirement


def _norm(name: str) -> str:
    """Return a distribution name in PEP 503 form.

    Returns:
        the lowercased name with each run of -_. as one hyphen.

    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _cuda_toolkit_requirement() -> Requirement:
    """Return torch's own requirement on cuda-toolkit, extras included.

    Returns:
        the parsed requirement.

    """
    found = [
        req
        for req in map(Requirement, metadata.requires("torch") or [])
        if _norm(req.name) == "cuda-toolkit"
    ]
    assert len(found) == 1, found
    return found[0]


def _wheels_for(extras: set[str]) -> set[str]:
    """Return the distributions cuda-toolkit requires for the given extras on this platform.

    Returns:
        the required distribution names, normalized.

    """
    wheels: set[str] = set()
    for req in map(Requirement, metadata.requires("cuda-toolkit") or []):
        if req.marker is None or any(req.marker.evaluate({"extra": e}) for e in extras):
            wheels.add(_norm(req.name))
    return wheels


def test_every_wheel_torch_cuda_extras_require_is_staged() -> None:
    """Each wheel torch's cuda-toolkit extras require is an installed distribution here.

    ⚑⚑ THE LIST IN BUILD.bazel IS HAND-WRITTEN (W271, W519): rules_python drops the extras, so
    the eleven wheels were copied from torch 2.14's Requires-Dist. When torch's pin moves this
    reads the new requirement, so an extra the list lacks fails here, named, instead of torch's
    import failing on a missing libcuda*.so. F-armed by deleting `nvidia_curand` from gpu_set.
    An empty extras set or an empty wheel set would make the check vacuous, so both must be held.
    """
    toolkit = _cuda_toolkit_requirement()
    wanted = _wheels_for(set(toolkit.extras))
    present = {_norm(d.metadata["Name"]) for d in metadata.distributions()}
    assert toolkit.extras
    assert wanted
    assert sorted(wanted - present) == []
