# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The venv rule's claims, asserted against the artifact rather than against the Starlark.

⚑⚑⚑ THE DIRECTION: *"All projects in this repo should be constructing their .venv the same way --
as a build artifact. This should be a trivially-templatizable thing."* `//:venv.bzl` answers it and
every distribution calls it. These arms assert the properties that make the answer true, because a
rule that BUILDS is not the same claim as a rule that builds something that WORKS.

⚑⚑ AND THE FIRST DRAFT OF THE RULE BUILT A WELL-FORMED LINK TO NOTHING. `bin/python3` was computed
from `short_path`, where an EXTERNAL file's path begins `../` — so the common-prefix walk compared
a workspace-relative path against an escape sequence and produced a symlink that resolved into
`bazel-out/` and named no file. The target built green. Only running the interpreter caught it.
That is the same shape as the `sys.path` finding one layer down: a path that exists as a string
and not as a file, which is why these arms RUN things rather than inspecting them.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# ⚑⚑ THE ENVIRONMENT GUARD COMES FIRST, because these arms read a BUILT ARTIFACT under `bazel-bin`
# and the pre-commit gate runs bare pytest from the source tree. An arm that cannot reach its
# subject must SKIP with a stated reason, not fail — a red bar for an absent instrument teaches
# nothing and blocks the commits that would fix it.
# ⚑⚑⚑ NOT `Path(__file__).resolve()` — THAT IS THE ESCAPE `test_bar_fires` REFUSES, and it caught
# this file's first draft. `.resolve()` on `__file__` follows a runfiles symlink back OUT to the
# author's source tree, so an arm using it reads the live checkout from inside what is supposed to
# be a hermetic action. The AST witness that forbids it is right, and the repair is to derive the
# root from the WORKING DIRECTORY instead: these arms are about a built artifact under `bazel-bin`,
# which exists only in a developer checkout, and they skip everywhere else.
_REPO = Path.cwd()
if not (_REPO / "MODULE.bazel").is_file():
    # Under the gate, pytest runs from the distribution directory rather than the repo root.
    _REPO = _REPO.parent
_BAZEL_BIN = _REPO / "bazel-bin"
_NEEDS_BUILT_VENV = pytest.mark.skipif(
    not _BAZEL_BIN.is_dir(),
    reason="bazel-bin is absent; the venv artifact has not been built in this checkout",
)

# ⚑ THE POPULATION IS DERIVED, NOT TYPED. A hand-written list of four names is exactly the defect
# ⟐POLL-RUF201-POPULATION was — it went stale the tick a fifth distribution landed. Every directory
# with a `pyproject.toml` is a distribution, which is the same rule `blockers.sh` and
# `test_bar_fires` already use.
_DISTS = sorted(p.parent.name for p in _REPO.glob("*/pyproject.toml"))

# ⚑ TWO IS THE SMALLEST POPULATION THAT CAN TEST A TEMPLATE. One distribution cannot distinguish
# "the same everywhere" from "the only one there is", so the control below requires at least a
# pair — named rather than written inline, because the number IS the argument.
_MIN_DISTS_FOR_TEMPLATE = 2


def _venv_python(dist: str) -> Path:
    return _BAZEL_BIN / dist / ".venv" / "bin" / "python3"


@_NEEDS_BUILT_VENV
def test_the_repository_has_distributions_to_check() -> None:
    """⚑ THE POSITIVE CONTROL FOR EVERY DERIVED-POPULATION ARM BELOW.

    A glob that returns nothing makes each parametrised arm vacuous: zero cases, green suite, no
    measurement. This fails loudly instead.

    ⚑⚑ AND ITS FIRST DRAFT CARRIED THE COMMENT *"deliberately NOT skipped — it reads the source
    tree, which is present wherever pytest runs"*, WHICH IS FALSE AND THE SANDBOX SAID SO: inside a
    hermetic action there is no source tree, `_DISTS` is empty, and the arm failed with
    `no directory under /execroot/.../runfiles carries a pyproject.toml`. The sentence asserted a
    property of the environment that the environment denies. It carries the same guard as every
    other arm here, because it has the same subject: a developer checkout.
    """
    assert _DISTS, f"no directory under {_REPO} carries a pyproject.toml"
    assert len(_DISTS) >= _MIN_DISTS_FOR_TEMPLATE, (
        f"only {len(_DISTS)} distribution(s) found ({_DISTS}) — templatizability untested"
    )


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("dist", _DISTS)
def test_every_distribution_builds_a_venv(dist: str) -> None:
    """⚑⚑ THE TEMPLATIZABILITY CLAIM, AS AN ARM OVER THE DERIVED POPULATION.

    "Every project constructs its .venv the same way" is falsified by one distribution that does
    not. Adding a fifth distribution without its `venv_from_hub` call fails here rather than being
    noticed when someone tries to activate a venv that was never declared.
    """
    py = _venv_python(dist)
    assert py.is_symlink() or py.is_file(), (
        f"{dist} has no built venv interpreter at {py} — does its BUILD file call venv_from_hub?"
    )


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("dist", _DISTS)
def test_the_interpreter_link_is_relative(dist: str) -> None:
    """⚑⚑⚑ RELOCATABILITY, AND IT IS THE WHOLE BUILD-ARTIFACT PROPERTY.

    An artifact valid only at the path it was built at is host state with a build step in front of
    it. MEASURED: `pyvenv.cfg`'s `home` is INERT — rewriting it to `/nonexistent/nowhere` changed
    nothing — so the absolute-vs-relative `bin/python3` symlink is the real dependency, and an
    earlier probe that "confirmed" relocatability by editing `home` had measured nothing at all.
    """
    py = _venv_python(dist)
    assert py.is_symlink(), f"{dist}: bin/python3 is not a symlink, so it cannot be relative"
    target = str(py.readlink())
    assert not target.startswith("/"), (
        f"{dist}: bin/python3 points at an ABSOLUTE path ({target}) — the venv is pinned to this "
        f"host and is not relocatable"
    )


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("dist", _DISTS)
def test_the_built_interpreter_actually_runs(dist: str) -> None:
    """⚑⚑ A SYMLINK THAT RESOLVES TO NOTHING IS WELL-FORMED AND USELESS, AND THAT SHIPPED ONCE.

    The arm above checks the link is relative; this one checks it names a file that starts. Both
    are needed: the rule's first draft produced a relative link into the wrong tree, which passes
    the first arm and fails this one.
    """
    py = _venv_python(dist)
    proc = subprocess.run(
        [str(py), "-c", "import sys; print(sys.version.split()[0])"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, (
        f"{dist}: the built interpreter did not run (rc={proc.returncode}): "
        f"{proc.stderr.strip()[:300]}"
    )
    assert proc.stdout.strip().startswith("3."), f"{dist}: unexpected version {proc.stdout!r}"


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("dist", _DISTS)
def test_the_venv_imports_the_distributions_own_package(dist: str) -> None:
    """⚑⚑⚑ THE EDITABLE-INSTALL STEP, REPLACED BY A DECLARED INPUT.

    MEASURED: a venv built from `deps` alone runs pytest and dies on `ModuleNotFoundError: No
    module named 'mikemol'` — CORRECT, not a defect. A venv holds a project's DEPENDENCIES; the
    project itself arrives by an editable install, which is precisely the host-state step this rule
    exists to remove. So `srcs` names it, and this arm asserts the substitution worked.
    """
    py = _venv_python(dist)
    proc = subprocess.run(
        [str(py), "-c", f"import mikemol.{dist}"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, (
        f"{dist}: the venv cannot import its own package `mikemol.{dist}` — does its "
        f"venv_from_hub call pass srcs? {proc.stderr.strip().splitlines()[-1:]}"
    )


@_NEEDS_BUILT_VENV
def test_a_package_outside_the_declared_closure_does_not_import() -> None:
    """⚑⚑ THE F-ARM, AND THE OBVIOUS VERSION OF IT IS VACUOUS.

    Importing a DECLARED dependency to show the venv does not leak proves nothing — a pass is what
    a correct venv does. Measured, and corrected: the control must be a package the AMBIENT
    interpreter can import and the closure does not carry. `panflute` is mdstruct's dependency and
    is absent from hooks' closure, so hooks' venv must refuse it.

    ⚑ AND WHEN AN F-ARM FIRES, CHECK WHERE IT RESOLVED. An earlier run flagged `pip` as a leak
    until `__file__` showed the hermetic toolchain's own bundled copy rather than the host's.
    """
    py = _venv_python("hooks")
    if not py.is_symlink() and not py.is_file():
        pytest.skip("hooks venv is not built in this checkout")

    # ⚑ POSITIVE CONTROL FIRST: a declared package must import, or a refusal below means the
    # interpreter is broken rather than the closure being closed.
    ctrl = subprocess.run(
        [str(py), "-c", "import pytest"], capture_output=True, text=True, check=False,
    )
    assert ctrl.returncode == 0, (
        f"control failed: hooks' venv cannot import its declared pytest — "
        f"{ctrl.stderr.strip()[:200]}"
    )

    proc = subprocess.run(
        [str(py), "-c", "import panflute"], capture_output=True, text=True, check=False,
    )
    assert proc.returncode != 0, (
        "hooks' venv imported `panflute`, which is mdstruct's dependency and is not in hooks' "
        "declared closure — the venv is reaching outside what MODULE.bazel declares"
    )


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("dist", _DISTS)
def test_the_venv_runs_the_distributions_own_suite(dist: str) -> None:
    """⚑⚑⚑ THE END-TO-END CLAIM: this venv can do the job the host venv does.

    The three non-bazel consumers — `.githooks/pre-commit` (13 call sites), `preflight.sh` (7), and
    the interactive loop — all invoke `<dist>/.venv/bin/python3 -m pytest`. Collecting the suite is
    the cheapest arm that exercises interpreter, dependencies AND the distribution's own package
    together; running it would duplicate the suite this arm is inside.
    """
    py = _venv_python(dist)
    proc = subprocess.run(
        [str(py), "-m", "pytest", "tests/", "-q", "--no-header", "-p", "no:cacheprovider", "--co"],
        capture_output=True, text=True, check=False, cwd=str(_REPO / dist),
    )
    assert proc.returncode == 0, (
        f"{dist}: the built venv could not collect the distribution's suite "
        f"(rc={proc.returncode}): {proc.stdout.strip()[-400:]}"
    )
    assert "tests collected" in proc.stdout, (
        f"{dist}: pytest reported no collection line — {proc.stdout.strip()[-200:]}"
    )
