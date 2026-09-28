# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pytest11 entry point: which files this plugin claims as specs.

⚑ THE SHELL (W198) DECLARES ONLY THE CLAIM. Collection, the SpecItem and the verdict mapping
arrive in W199; the pinned opa evaluator in W200. Nothing is collected until then, so an
installed plugin changes no suite's population.
"""

from pathlib import Path

SPEC_SUFFIX = ".rego"
# ⚑ A `_test.rego` FILE IS OPA'S OWN UNIT TEST OF A SPEC, run by `opa test`; it is not a spec.
OPA_TEST_SUFFIX = "_test.rego"


def claims(path: Path) -> bool:
    """Decide whether `path` is a spec this plugin collects.

    Returns:
        True for a `.rego` file, False for opa's own `_test.rego` and for anything else.

    """
    return path.name.endswith(SPEC_SUFFIX) and not path.name.endswith(OPA_TEST_SUFFIX)
