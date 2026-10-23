# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find opa and hold it to the pinned version (W1845, from luthen's checks/opa_pin.py, W1326).

A check that finds opa with a plain lookup trusts whatever version answered, and a different opa is
a different checker; the plan verdict that gates an apply is only as good as the policy engine that
judged it. This holds the binary to the config's pin: `opa version` must read it.

⚑ THE PIN IS THE CONSUMER'S, not a constant here: luthen pins 1.20.2, and `PlanConfig.opa_pin`
carries whatever a repo pins. mtools' own `pathsforward.opa_eval.resolve` does the same check for
the queue's Rego witnesses with the same kind of number; that is a second witness of the rule, not a
dependency, because waldo imports nothing from a sibling dist.

⚑ NOT FOUND, NOT RUNNING, AMBIGUOUS AND WRONG ARE ALL None: no case admits an opa it could not read
the version of. `opa version` printing two `Version:` lines is ambiguous and refused.
"""

from pathlib import Path

from mikemol.waldo.plantools import Tools

VERSION_LABEL = "Version: "


def parse_version(code: int, said: str) -> str | None:
    """Read the version out of `opa version` output.

    Returns:
        the version, or None when the command failed or the output is ambiguous.

    """
    if code != 0:
        return None
    versions = [
        line.removeprefix(VERSION_LABEL)
        for line in said.splitlines()
        if line.startswith(VERSION_LABEL)
    ]
    return versions[0] if len(versions) == 1 else None


def version_of(tools: Tools, binary: Path) -> str | None:
    """Ask a binary for its version.

    Returns:
        the version it reports, or None when it does not run.

    """
    done = tools.run(binary, "version")
    return parse_version(done.returncode, done.stdout)


def pinned_opa(tools: Tools, pin: str) -> Path | None:
    """Find opa and accept it only at the pinned version.

    Returns:
        the binary when it is the pinned version, None when absent or any other.

    """
    found = tools.find("opa")
    if found is None or version_of(tools, found) != pin:
        return None
    return found
