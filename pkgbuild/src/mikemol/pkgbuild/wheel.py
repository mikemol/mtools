# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the engine's WHEEL, the artifact a cell installs the engine FROM, and install it.

Ported from paperkit's `tools/wheel.py` (paperkit:W142). Behaviour is unchanged; the two
`# noqa` waivers of the original are replaced by structure (a typed lazy backend load and a
top-level `venv` import), and the entry point is a `main()` so it is a console script.

The wheel is built ONCE, here, through the DECLARED PEP 517 backend (setuptools, staged by
Bazel), and installed many times: a wheel is a zip, so for a stdlib-only project extracting it
IS a complete install. `install` copies real files into a private venv and claims the shared
name atomically; it needs nothing but the standard library.

Usage:  mikemol-wheel build <out.whl> <pyproject.toml>   (needs the DECLARED setuptools backend)
        mikemol-wheel install <venv-dir> <wheel> [dep-path ...]   (cell side; stdlib only)
"""

from __future__ import annotations

import importlib
import os
import pathlib
import shutil
import sys
import tempfile
import venv
import zipfile
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_ARGC_BUILD = 3
_ARGC_INSTALL_MIN = 3
_SITE_MARKER = "/site-packages/"


def _only(matches: list[pathlib.Path], what: str) -> pathlib.Path:
    """Return the ONE match, refusing zero or many.

    A glob that takes `next()` picks the first and discards the rest SILENTLY. A glob is a
    query, and its CARDINALITY is part of the answer.

    Returns:
        The single match.

    Raises:
        SystemExit: when there is not exactly one match.

    """
    if len(matches) != 1:
        msg = f"expected exactly one {what}, found {len(matches)}: {matches}"
        raise SystemExit(msg)
    return matches[0]


def build(out: str, pyproject: str) -> None:
    """Build the wheel from the project rooted at `pyproject`'s directory, into `out`.

    The build goes through the DECLARED backend, not a host `uv`: no host binary, no host
    cache, and an action the remote executor can run. The backend is loaded lazily because
    only this side needs it; `install` runs where setuptools is absent.

    ⚑ THE ONE PEP 517 HOOK IS TYPED BY A `cast` TO A CALLABLE, NOT BY A `Protocol` CLASS. A
    Protocol method body is a def-site nothing executes, so the mutation grid reported it
    SURVIVED (measured on this port's first run): a stub that no test can exercise.
    """
    build_wheel = cast(
        "Callable[[str], str]", importlib.import_module("setuptools.build_meta").build_wheel
    )
    root = pathlib.Path(pyproject).resolve().parent
    # setuptools REUSES `build/lib`, so a wheel built after `packages` shrank still carries
    # the package that was removed. Ours at both ends.
    shutil.rmtree(root / "build", ignore_errors=True)
    cwd = pathlib.Path.cwd()
    try:
        os.chdir(root)  # PEP 517 builds the project rooted at the CWD
        with tempfile.TemporaryDirectory() as td:
            name = build_wheel(td)
            shutil.copyfile(pathlib.Path(td) / name, out)
    finally:
        os.chdir(cwd)
        shutil.rmtree(root / "build", ignore_errors=True)


def install(venv_dir: str, wheel: str, *extra: str) -> str:
    """Create the venv and INSTALL the wheel into it: copies, not a pointer. Stdlib only.

    Build to a private path, then claim the shared name atomically: sandboxed cells share an
    execroot, so several run this concurrently and `clear=True` on the shared path raced. An
    already-built venv is REUSED, because the result is content-determined.

    Returns:
        The path of the venv's python.

    """
    vd = pathlib.Path(venv_dir).resolve()
    marker = vd / ".pk-complete"
    if not marker.exists():
        tmp = vd.with_name(f"{vd.name}.{os.getpid()}.tmp")
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        # --symlinks, NOT --copies: `--copies` copies the interpreter binary but NOT
        # libpython, and the venv dies loading shared libraries.
        venv.EnvBuilder(with_pip=False, symlinks=True, clear=True).create(tmp)
        _populate(tmp, wheel, extra)
        (tmp / ".pk-complete").write_text("")
        try:
            tmp.rename(vd)  # atomic when the name is free
        except OSError:
            # A peer won the race and the shared name now exists, complete. Its content
            # equals ours by construction, so DISCARD OURS rather than clobber a venv in use.
            shutil.rmtree(tmp, ignore_errors=True)
    return str(vd / "bin" / "python")


def _populate(vd: pathlib.Path, wheel: str, extra: tuple[str, ...]) -> None:
    """Extract the engine wheel and name the dep roots; split out so `install` builds privately."""
    sp = _only(sorted(vd.glob("lib/python*/site-packages")), "site-packages dir")
    with zipfile.ZipFile(wheel) as z:
        z.extractall(sp)

    # The deps are NOT wheels: they are already-extracted site-packages trees (rules_python's
    # `@hub//<pkg>:pkg`), so what the venv needs from them is their ROOT on its path, which a
    # .pth in site-packages names.
    roots: list[str] = []
    for d in extra:
        if _SITE_MARKER in d:
            r = d.split(_SITE_MARKER)[0] + "/site-packages"
            if r not in roots:
                roots.append(r)
    if roots:
        (sp / "_pydeps.pth").write_text(
            "\n".join(str(pathlib.Path(r).resolve()) for r in roots) + "\n",
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run `build` or `install` from the command line.

    Returns:
        0 on success.

    Raises:
        SystemExit: with the usage text when the arguments do not fit either command.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["build"] and len(args) == _ARGC_BUILD:
        build(args[1], args[2])
        return 0
    if args[:1] == ["install"] and len(args) >= _ARGC_INSTALL_MIN:
        sys.stdout.write(install(args[1], args[2], *args[3:]) + "\n")
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
