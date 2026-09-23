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
# ⚑ A symlinked directory is never a distribution: `bazel-mtools` mirrors the root, and once the
# root carried a pyproject.toml it matched this glob (measured, 5 phantom failures here).
_DISTS = sorted(p.parent.name for p in _REPO.glob("*/pyproject.toml") if not p.parent.is_symlink())

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
def test_the_interpreter_link_is_depth_independent(dist: str) -> None:
    """⚑⚑⚑ RELOCATABILITY, RE-MEASURED: THE LINK IS ABSOLUTE, BY OPERATOR RULING 2026-09-19.

    This arm used to assert the link was RELATIVE, on the reasoning that an absolute link pins the
    venv to one host. What it did not measure: a relative link pins the venv to one DEPTH. The same
    venv staged into a test's runfiles tree sits four directories from the runfiles root where
    `bazel-bin` sits six from the execroot, and the relative link dangled there —
    `//ratchet:mutants` refused on `-x bin/python3` with all 2,070 venv files staged. An absolute
    link into the toolchain resolves from `bazel-bin`, from any runfiles tree, and from a scratch
    copy four directories deeper run from `/` (measured). `pyvenv.cfg`'s `home` is `bin`, the
    venv's own directory, so no second coordinate is baked in.

    ⚑ Under a SANDBOX the link is not a link at all — bazel hardlinks the resolved interpreter —
    and the stdlib is found through `PYTHONHOME`, from the repo name written beside `pyvenv.cfg`.
    That file is asserted here too, because the checker reads it and a missing one is a silent
    fall-through to a dead interpreter.
    """
    py = _venv_python(dist)
    assert py.is_symlink(), f"{dist}: bin/python3 is not a symlink"
    target = str(py.readlink())
    assert target.startswith("/"), (
        f"{dist}: bin/python3 is RELATIVE ({target}) — valid at one depth only; it dangles "
        f"inside a runfiles tree (measured 2026-09-19, //ratchet:mutants)"
    )
    assert target.endswith("/bin/python3"), f"{dist}: the link names {target}, not an interpreter"
    note = py.parent.parent / "pythonhome.runfiles"
    assert note.is_file(), f"{dist}: {note} missing — the sandboxed arm has no PYTHONHOME to set"
    repo = note.read_text(encoding="utf-8").strip()
    assert repo, f"{dist}: pythonhome.runfiles is empty — no repo name for PYTHONHOME"
    assert "/" not in repo, f"{dist}: pythonhome.runfiles holds a path {repo!r}, not a repo name"
    assert f"/{repo}/bin/python3" in target, (
        f"{dist}: the note names {repo!r} but the link goes to {target} — two answers to one "
        f"question"
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


# ⚑ THE CONSOLE-SCRIPT POPULATION IS DERIVED FROM THE ARTIFACT, like `_DISTS` from the tree: every
# regular file in a built `bin/` that is not the interpreter link is an entry `venv.bzl` wrote.
_ENTRIES = sorted(
    f"{p.parent.parent.parent.name}/{p.name}"
    for p in _BAZEL_BIN.glob("*/.venv/bin/*")
    if p.name != "python3" and not p.is_symlink()
)

# ⚑ Bounded, because a direct run that reached the shell or the wrong interpreter must fail the arm,
# not hang it; the hooks read one JSON payload from stdin and exit well inside this.
_ENTRY_TIMEOUT_S = 60


@_NEEDS_BUILT_VENV
@pytest.mark.parametrize("depth", ["bazel-bin", "symlink-elsewhere"])
@pytest.mark.parametrize("entry", _ENTRIES)
def test_a_console_script_runs_directly_under_the_venvs_python(
    entry: str, depth: str, tmp_path: Path,
) -> None:
    """⚑⚑⚑ A DIRECT RUN OF A BUILT ENTRY REACHES PYTHON, NEVER THE SHELL PARSING PYTHON.

    MEASURED 2026-09-23 at HEAD: `bazel-bin/hooks/.venv/bin/mikemol-hook-no-chaining < payload`
    printed `line 4: import: command not found` and a syntax error on line 7, rc=2 — the entry had
    no shebang, so the kernel refused it and the shell ran it as a script. The launchers never
    noticed, because they name the interpreter themselves.

    ⚑⚑ THE POSITIVE WITNESS IS `PYTHONPROFILEIMPORTTIME`: only a CPython writes `import time:` to
    stderr, so its presence proves an interpreter ran the file; that the distribution's own package
    appears in it proves the entry got as far as its own import. `symlink-elsewhere` runs the entry
    through a link at another depth, which is what a runfiles tree presents.
    """
    dist, name = entry.split("/")
    script = _BAZEL_BIN / dist / ".venv" / "bin" / name
    if depth == "symlink-elsewhere":
        link = tmp_path / "deeper" / "bin" / name
        link.parent.mkdir(parents=True)
        link.symlink_to(script)
        script = link
    # ⚑ Through a SHELL, as a person types it: a bare `execve` of a shebang-less file raises
    # ENOEXEC, while a shell falls back to reading the file as shell — the failure actually seen.
    proc = subprocess.run(
        ["/bin/sh", "-c", 'exec "$0"', str(script)],
        input="{}", capture_output=True, text=True, check=False, timeout=_ENTRY_TIMEOUT_S,
        env={"PATH": "/usr/bin:/bin", "PYTHONPROFILEIMPORTTIME": "1"},
    )
    assert "command not found" not in proc.stderr, (
        f"{entry}: the SHELL ran the Python file — {proc.stderr.strip()[:300]}"
    )
    assert "import time:" in proc.stderr, (
        f"{entry}: no Python interpreter ran the entry (rc={proc.returncode}): "
        f"{proc.stderr.strip()[:300]}"
    )
    assert f"mikemol.{dist}" in proc.stderr, (
        f"{entry}: an interpreter ran, but never imported mikemol.{dist} from the venv"
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
