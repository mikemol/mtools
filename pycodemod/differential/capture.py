# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Capture each origin check's fixture text and operands by profiling the mode entry points (W128).

Run from the substrate root under substrate's venv: `python capture.py OUT.jsonl`. For every call
from _pycodemod_selftest.py's body into a function defined in pycodemod.py or a _pycodemod_*.py
module (other than the selftest itself), record the callee name, its arguments, and the text of
every file argument that exists. Each check is then attributed:
  fresh  - at least one mode call happened since the previous check
  sticky - no new call; the check reads the result of the last one
  none   - no mode call has happened yet
Writes a JSONL row per check to argv[1] and the class counts to stderr. Its output is
`captured.jsonl`, which `gen_cases.py` turns into the case files.
"""

import json
import os
import runpy
import sys
import tempfile
from pathlib import Path
from types import CodeType, FrameType
from typing import TypedDict, cast

SELF = "_pycodemod_selftest.py"
MAX = 4000
# ⚑ A CHECK'S OWN TEMP TREE IS THE ONLY FIXTURE, and the root is READ from tempfile, not spelled:
# the selftest makes its trees with tempfile, so this interpreter's tempdir is where they are.
TMPROOT = str(Path(tempfile.gettempdir()).resolve()) + "/"
DIRCAP = 200  # files per directory operand; a hit is visible as exactly 200 keys
PATHLEN = 512  # a longer string is a value, not a path
CO_VARARGS = 0x04
CO_VARKEYWORDS = 0x08


class Call(TypedDict):
    """One mode call: the callee, its operands (repr'd), and the files it read."""

    fn: str
    operands: dict[str, str]
    fixtures: dict[str, str]


checks: list[dict[str, object]] = []
pending: list[Call] = []
last: list[Call] = []


def _is_mode(fname: str) -> bool:
    base = Path(fname).name
    return base != SELF and (base == "pycodemod.py" or base.startswith("_pycodemod_"))


def _in_scope(caller: CodeType) -> bool:
    """Decide whether a call counts: made by the selftest body, or by a case module's _cases (W187).

    Returns:
        True for a call this capture records.

    """
    return caller.co_filename.endswith(SELF) or (
        caller.co_name == "_cases" and _is_mode(caller.co_filename)
    )


def _in_tmp(path: str | Path) -> bool:
    return str(Path(path).resolve()).startswith(TMPROOT)


def _paths(val: object) -> list[str]:
    """Collect every path-like argument (str or os.PathLike, alone or in a container) as a str.

    Returns:
        the path strings.

    """
    items: list[object] = list(val) if isinstance(val, (list, tuple, set, frozenset)) else [val]
    out: list[str] = []
    for item in items:
        text: object = (
            os.fspath(cast("os.PathLike[str]", item)) if isinstance(item, os.PathLike) else item
        )
        if isinstance(text, str) and len(text) < PATHLEN:
            out.append(text)
    return out


# ⚑⚑ A SYMLINK IS REFUSED, NEVER FOLLOWED (W193; operator ruling 2026-10-02: symlinks are
# inherently unsafe and unwanted). Reading through a link reads whatever it points at, inside the
# temp tree or not, and the harness never recreates one. The snapshot records this marker in place
# of any content or target, so a case whose fixture held a link is visible as such and is
# withheld by its spec rather than replayed without the link and passed vacuously (#110).
REFUSED = "@refused:symlink"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:MAX]


def _siblings(path: Path, out: dict[str, str]) -> None:
    """Record the .py files beside a file operand inside a check's temp tree (W405).

    aliases([aliasuser.py]) reads `target` as local only because target.py sits in the same temp
    dir; the capture once kept aliasuser.py alone. One level, capped like the directory walk.
    """
    for n, sib in enumerate(sorted(path.parent.glob("*.py"))):
        if n >= DIRCAP:
            break
        out.setdefault(str(sib), REFUSED if sib.is_symlink() else _read(sib))


def _tree(root: str, out: dict[str, str]) -> None:
    """Record every file under a directory operand as `<dir>//<relpath>`, capped at DIRCAP (W192).

    ⚑ Only a check's own temp tree is walked: v1 walked every directory operand before the cap
    applied, and an operand naming the substrate root (.venv and all) ran 30 CPU-minutes.

    ⚑ A link to a file or a directory is recorded as REFUSED and neither read nor descended.
    """
    n = 0
    base = Path(root)
    for dirpath, dirnames, filenames in os.walk(base):
        here = Path(dirpath)
        links = sorted(d for d in dirnames if (here / d).is_symlink())
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__" and d not in links)
        for name in sorted([*filenames, *links]):
            if n >= DIRCAP:
                break
            f = here / name
            key = f"{root}//{f.relative_to(base).as_posix()}"
            out[key] = REFUSED if f.is_symlink() else _read(f)
            n += 1


def snapshot(val: object) -> dict[str, str]:
    """Read every existing-file argument; a directory argument inside a temp tree is walked.

    Returns:
        {path or <dir>//<relpath>: text}.

    """
    out: dict[str, str] = {}
    for item in _paths(val):
        path = Path(item)
        if path.is_symlink():
            out[item] = REFUSED
        elif path.is_file():
            out[item] = _read(path)
            if _in_tmp(path.parent):
                _siblings(path, out)
        elif path.is_dir() and _in_tmp(path):
            _tree(item, out)
    return out


def _operands(frame: FrameType, code: CodeType) -> dict[str, object]:
    """Read a mode call's arguments by name, flattening one level of dict arguments.

    ⚑ W189: co_argcount counts positional parameters only, so `def py_files(*roots)` recorded NO
    operands; keyword-only, *args and **kwargs are counted too. A case that rebinds the
    module-global ROOT to a temp tree passes no operand at all, so ROOT is recorded as one.

    Returns:
        {name: value}.

    """
    n = code.co_argcount + code.co_kwonlyargcount
    n += bool(code.co_flags & CO_VARARGS) + bool(code.co_flags & CO_VARKEYWORDS)
    local = cast("dict[str, object]", frame.f_locals)
    args = {k: local[k] for k in code.co_varnames[:n] if k in local}
    for k, v in list(args.items()):
        if isinstance(v, dict):
            nested: dict[object, object] = dict(v)
            for kk, vv in nested.items():
                args[f"{k}.{kk}"] = vv
    root = cast("dict[str, object]", frame.f_globals).get("ROOT")
    if isinstance(root, str) and _in_tmp(root):
        args["<global ROOT>"] = root
    return args


def _record_call(frame: FrameType, code: CodeType) -> None:
    args = _operands(frame, code)
    fixtures: dict[str, str] = {}
    for v in args.values():
        fixtures.update(snapshot(v))
    pending.append(
        {
            "fn": f"{Path(code.co_filename).name}:{code.co_name}",
            "operands": {k: v if isinstance(v, str) else repr(v) for k, v in args.items()},
            "fixtures": fixtures,
        }
    )


def _record_check(frame: FrameType) -> None:
    calls: list[Call]
    if pending:
        cls, calls = "fresh", list(pending)
        last[:] = calls
        pending.clear()
    elif last:
        cls, calls = "sticky", list(last)
    else:
        cls, calls = "none", []
    back = frame.f_back
    checks.append(
        {
            "i": len(checks) + 1,
            "name": str(cast("dict[str, object]", frame.f_locals)["n"]),
            "line": back.f_lineno if back else 0,
            "class": cls,
            "calls": calls,
        }
    )


def _prof(frame: FrameType, event: str, _arg: object) -> None:
    code = frame.f_code
    back = frame.f_back
    if event == "call" and back is not None and _in_scope(back.f_code):
        if back.f_code.co_name != "check" and _is_mode(code.co_filename):
            _record_call(frame, code)
    elif event == "return" and code.co_name == "check" and code.co_filename.endswith(SELF):
        _record_check(frame)


def _has_fixture(check: dict[str, object]) -> bool:
    calls = check["calls"]
    if not isinstance(calls, list):
        return False
    return any(isinstance(c, dict) and c.get("fixtures") for c in calls)


def main(out: Path) -> int:
    """Run the origin selftest under the profiler and write one JSONL row per check.

    Returns:
        0; the selftest's own exit code is reported on stderr.

    """
    sys.path.insert(0, "scratch")
    sys.argv = ["scratch/pycodemod.py", "--selftest"]
    exit_code: object = None
    sys.setprofile(_prof)
    try:
        runpy.run_path("scratch/pycodemod.py", run_name="__main__")
    except SystemExit as exc:
        exit_code = exc.code
    finally:
        sys.setprofile(None)
    out.write_text("".join(json.dumps(c) + "\n" for c in checks), encoding="utf-8")
    counts: dict[str, int] = {}
    for c in checks:
        key = str(c["class"])
        counts[key] = counts.get(key, 0) + 1
    with_fixture = sum(1 for c in checks if _has_fixture(c))
    sys.stderr.write(
        f"checks {len(checks)} exit {exit_code} classes {counts} with_fixture_text {with_fixture}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
