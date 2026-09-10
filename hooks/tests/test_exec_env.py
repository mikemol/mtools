# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What a witness can reach, measured in BOTH execution modes rather than assumed in one.

⚑⚑⚑ THE PREMISE THIS FILE WAS FIRST WRITTEN ON IS FALSE, AND MEASURING IT IS WHY THE FILE EXISTS.
`.bazelrc` argues against `--remote_local_fallback` on two legs, and the second one read: *a local
sandbox shares this kernel and this `$HOME`; that is how a test here read the author's own venv
from inside a hermetic action.* An earlier draft of THIS file imported that sentence as an
established fact and built three arms on top of it.

⚑⚑ MEASURED, by a probe reporting through the FAILURE channel — the first attempt used `print`,
which pytest captures on a pass, so it returned nothing and read as agreement a second time:

    field                local sandbox     --config=remote
    hostname             cassian           buildbuddy-executor-654cd76d7f-lzb2n
    uid                  1000              0
    $HOME                /home/mikemol     /root
    $HOME exists         FALSE             True  (the executor's own)
    checkout reachable   FALSE             False

⚑ SO THE LOCAL SANDBOX DOES NOT MOUNT `$HOME`. `Path.home()` returns `/home/mikemol` because the
VARIABLE is set while the DIRECTORY is not — a name outliving its referent, which is exactly the
shape that makes a claim readable and wrong. The author's checkout is unreachable in BOTH modes.
`.bazelrc`'s conclusion survives on its other leg (colocated executor, identical cores, outside
the accounting); what was withdrawn there is the `$HOME` mechanism, as stale rather than false —
true of bare `linux-sandbox`, closed by `--experimental_use_hermetic_linux_sandbox`.

⚑⚑⚑ AND THE PRE-COMMIT GATE THEN CAUGHT THIS FILE COMMITTING THE SAME CLASS OF ERROR. The gate
runs pytest DIRECTLY — no bazel, no sandbox — where `$HOME` is the real home, the checkout IS
reachable and `TEST_TMPDIR` is unset. Three arms that are true statements about a bazel action
were written as UNCONDITIONAL claims, and all three failed. The environment guard has to come
FIRST in every arm that presupposes it, not last in one of them: an arm whose precondition is
checked after its conclusion is asserting something it has not established it can measure.

⚑ AND THE FIRST DRAFT COULD NOT HAVE CAUGHT ANY OF THIS, because its arms were tautologies:
`assert reachable in (True, False)` and `assert mode, mode` pass under every possible world. Three
arms, green in both modes, discriminating nothing. Each arm below can FAIL, and each was F-armed
by aiming its predicate at a true case (3 failed, for the right reason, control asserted first).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ⚑⚑ THE SUBJECT OF EVERY ARM HERE IS A BAZEL ACTION, so a run outside one is UNMEASURABLE rather
# than passing or failing. `TEST_TMPDIR` is bazel's own marker. Skipping with a stated reason is
# this suite's convention for "the instrument does not apply", and it is not the same as green:
# under `bazel test` — the run whose verdict counts — these arms execute.
_UNDER_BAZEL = bool(os.environ.get("TEST_TMPDIR"))
_NEEDS_ACTION = pytest.mark.skipif(
    not _UNDER_BAZEL,
    reason="not running inside a bazel action (TEST_TMPDIR unset); neither sandbox claim applies",
)


def test_the_witness_runs_under_bazel_and_names_its_own_interpreter() -> None:
    """⚑ THE INTERPRETER AND THE HARNESS ARE FACTS ABOUT THE ACTION, and nothing recorded them.

    A mutation grader's flip is attributable only if the environment is fixed. `sys.executable`
    names the per-target venv bazel stages (`_test_exec_env.venv/bin/python3` in both modes).

    ⚑ THIS ARM IS DELIBERATELY NOT SKIPPED: it holds under the gate's bare pytest too, and it is
    the positive control for the two below — a run where the interpreter were unreadable would be
    a broken probe rather than a strong sandbox, and would pass a bare non-existence assertion.
    """
    exe = Path(sys.executable)
    assert exe.is_file(), f"sys.executable does not name a file: {exe}"
    assert exe.name.startswith("python"), f"the running interpreter is not a python: {exe}"


@_NEEDS_ACTION
def test_a_witness_cannot_reach_the_authors_checkout_in_either_mode() -> None:
    """⚑⚑ THE STRONG CLAIM, MEASURED IN BOTH MODES AND SO ASSERTABLE WITHIN ANY ACTION.

    An earlier draft recorded this instead of asserting it, believing the local sandbox would make
    it True. Measured: False under the local sandbox AND under `--config=remote`. So the refusal
    costs nothing and buys the property — and if a future sandbox configuration starts sharing the
    tree, this arm reports it rather than a comment quietly going stale.
    """
    assert Path(sys.executable).is_file(), "the probe cannot read even its own interpreter"

    checkout = Path.home() / "github" / "mtools" / "hooks" / "src"
    assert not checkout.is_dir(), (
        f"a hermetic action reached the author's working tree at {checkout} — the escape "
        f"`.bazelrc` warns about is real in this mode, which it was not when measured"
    )


@_NEEDS_ACTION
def test_the_home_variable_is_set_to_a_directory_that_may_not_exist() -> None:
    """⚑⚑ THE NAMED MECHANISM, AS AN ARM: `$HOME` IS A VARIABLE, NOT A MOUNT.

    Inside a local-sandbox action `$HOME` is `/home/mikemol` and that directory DOES NOT EXIST;
    under remote it is `/root` and does. So "the sandbox shares `$HOME`" is false in the only sense
    that would matter — reachability — even though `Path.home()` answers plausibly in both.

    This arm refuses the conflation rather than either outcome: whatever `$HOME` names inside an
    action, it must not be the author's populated checkout root.
    """
    home = Path.home()
    assert str(home), "HOME resolves to nothing at all"
    assert not (home / "github" / "mtools" / ".git").is_dir(), (
        f"$HOME ({home}) is the author's own checkout root — the action is not isolated from it"
    )
