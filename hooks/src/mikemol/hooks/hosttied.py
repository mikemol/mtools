# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the hooks test modules that only make sense inside the mtools checkout (W1239, W1147).

A published sdist is unpacked on its own, with nothing beside it: no repository root, no
`.githooks/`, no `blockers.sh`. These modules test the checkout's own git hooks and the repository
scripts that live ABOVE this distribution, so from an sdist they fail on a missing file, which is a
fact about where they run and not a defect. They are skipped there, with the reason below, and
still run everywhere else: the gate, bazel's runfiles and the mutation sandbox.

⚑ THE TEST IS "THIS IS AN UNPACKED SDIST", NOT "THE REPOSITORY IS HERE": an sdist carries
`PKG-INFO` at its top, and a checkout, bazel's runfiles and the mutation sandbox do not. Two
markers that asked whether the repository was present were measured wrong: `MODULE.bazel` was
absent in the bazel sandbox (all 151 `test_bar_fires` tests skipped there), and `blockers.sh` was
absent in the mutation sandbox (three declared mutants survived because their tests skipped).
Either would have dropped tests from the gate; this one cannot, because it is true only of an sdist.

CONSUMED BY: `tests/conftest.py`, which skips these modules when the marker is present.
"""

REASON = (
    "tests the mtools checkout's own hooks and scripts above this distribution; not in an sdist"
)
SDIST_MARKER = "PKG-INFO"
HOST_TIED = frozenset(
    {
        "test_adopt_launcher",
        "test_bar_fires",
        "test_bin_launchers_argv",
        "test_commit_launcher",
        "test_commit_launcher_fence",
        "test_gate_suite",
        "test_gen_warrants_write",
        "test_githook_post_commit",
        "test_githook_pre_push",
        "test_hooks_preflight",
        "test_inbound_launcher_root",
        "test_no_verify",
        "test_pairing_sections",
        "test_post_commit_census",
        "test_precommit_build_failure",
        "test_privacy_audit",
        "test_privacy_shipped",
        "test_probe",
        "test_routing_table",
        "test_shell_pipefail_race",
        "test_standing_facts",
        "test_standing_stop_launcher",
        "test_warrant_crosscheck",
    }
)


def skip_reason(module: str, in_sdist: bool) -> str | None:
    """Say why a test module is skipped, if it is.

    Returns:
        the reason when the module is host-tied and this is an unpacked sdist, else None.

    """
    if in_sdist and module in HOST_TIED:
        return REASON
    return None
