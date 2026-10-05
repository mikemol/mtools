# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the module split: a pure plan, a write that must be asked for, nothing swallowed.

Arms marked `ORIGIN` transcribe the origin's selftest block for `--split`; arms marked `AUTHORED`
are this port's own (the plan/apply separation and the refusals the origin did not have to state).
Every arm builds a synthetic tree under `tmp_path` and goes through the public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import split

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pycodemod.splitscope import Statement

_BOUND = 12
_PAIR = 2
_SHADOW = "TABLE = {}\ndef f():\n    TABLE = 1\n    return TABLE\ndef g():\n    return TABLE\n"

_ORDER = (
    "R = {'a': {}}\n"
    "def fill():\n"
    "    return 1\n"
    "R['a']['k'] = fill()\n"
    "R['a'] = {k: v for k, v in R['a'].items() if v}\n"
)

_FILE_USES = (
    "from pathlib import Path\n"
    "def near():\n"
    "    return (Path(__file__).resolve().parent / 'x.bib').read_text()\n"
    "def own():\n"
    "    return Path(__file__).read_text()\n"
    "def neither():\n"
    "    return Path(__file__).resolve().parent\n"
)

_COMMENTED = (
    '"""mod doc."""\n'
    "import os\n"
    "\n"
    "\n"
    "# ⚑ WHY a exists\n"
    "def a():\n"
    "    return os.sep  # trailing\n"
    "\n"
    "\n"
    "def b():\n"
    "    return a()\n"
    "\n"
    "\n"
    "T = {'k': b}\n"
)

_FAN_IN = "def f():\n    return T\nT = {'k': f}\ndef g():\n    return T\n"

_BACKWARDS = "A = [1]\ndef f():\n    return B\nB = f\nA.append(B)\ndef h():\n    return A\n"

_SIX_DEFS = "".join(f"def d{k}():\n    return {k}\n" for k in range(6))

_LICENCED = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# Copyright (c) 2026 Mike Mol\n"
    "def a():\n"
    "    return 1\n"
    "def b():\n"
    "    return a()\n"
)

_HEAD = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Mike Mol\n"


def _write(root: Path, name: str, text: str) -> str:
    path = root / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _by_name(p: split.Plan) -> dict[str, Statement]:
    return {t.name: t for t in p.statements}


def _tree(root: Path) -> dict[str, str]:
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(root.iterdir())}


def _small(max_lines: int) -> split.Options:
    return split.Options(max_lines=max_lines)


def _too_long(p: split.Plan, bound: int) -> list[str]:
    return [n for n, c in p.files.items() if len(c.split("\n")) > bound]


# ── ORIGIN arms ───────────────────────────────────────────────────────────────────────────────


def test_a_shadowing_local_is_not_a_module_level_dependency(tmp_path: Path) -> None:
    """ORIGIN: a local that shadows a module-level name is not a dependency on it."""
    stm = _by_name(split.plan(_write(tmp_path, "sc.py", _SHADOW)))
    assert "TABLE" not in stm["f"].free
    assert "TABLE" in stm["g"].free


def test_impure_statements_keep_their_source_order(tmp_path: Path) -> None:
    """ORIGIN: two impure statements reading one name stay in source order through the sort."""
    p = split.plan(_write(tmp_path, "so.py", _ORDER), _small(200))
    assert [t.is_pure for t in p.statements] == [True, True, False, False]
    flat = [i for part in p.parts for i in part.ids]
    assert flat.index(2) < flat.index(3)


def test_file_as_a_location_is_not_a_hazard_but_as_source_is(tmp_path: Path) -> None:
    """ORIGIN: reading a sibling through __file__.parent is safe; reading its own text is not."""
    stm = _by_name(split.plan(_write(tmp_path, "fh.py", _FILE_USES)))
    assert (stm["near"].reads_file, stm["near"].reads_source) == (True, False)
    assert (stm["own"].reads_file, stm["own"].reads_source) == (True, True)
    assert (stm["neither"].reads_file, stm["neither"].reads_source) == (True, False)


def test_a_bounded_split_is_lossless_and_keeps_every_comment(tmp_path: Path) -> None:
    """ORIGIN: every part is under the bound, nothing is lost, comments and docstring survive."""
    p = split.plan(_write(tmp_path, "ls.py", _COMMENTED), _small(_BOUND))
    assert p.refusal is None
    assert len(p.parts) > 1
    assert _too_long(p, _BOUND) == []
    assert split.verify(p)[0]
    joined = "".join(p.files.values())
    assert "# ⚑ WHY a exists" in joined
    assert "return os.sep  # trailing" in joined
    assert "mod doc." in p.files["ls.py"]
    assert "mod doc." not in p.files["ls_00.py"]


def test_the_entry_module_imports_every_part(tmp_path: Path) -> None:
    """ORIGIN: every part is imported, so a part's module-level effects still run."""
    p = split.plan(_write(tmp_path, "ls.py", _COMMENTED), _small(_BOUND))
    entry = p.files["ls.py"]
    assert [part.file for part in p.parts if part.file.removesuffix(".py") not in entry] == []


def test_a_cycle_through_a_def_is_colocated_not_refused(tmp_path: Path) -> None:
    """ORIGIN: a fan-in table whose def reads it at call time splits; the cycle shares one part."""
    p = split.plan(_write(tmp_path, "cy.py", _FAN_IN), _small(200))
    assert p.refusal is None
    homes = dict(p.moves)
    assert homes["f"] == homes["T"]


def test_a_backwards_dependency_through_a_def_is_not_a_cycle_by_itself(tmp_path: Path) -> None:
    """ORIGIN: a data dependency that runs through a def does not refuse the split."""
    assert split.plan(_write(tmp_path, "cy2.py", _BACKWARDS), _small(200)).refusal is None


def test_an_unsplittable_statement_is_refused_on_budget_and_named(tmp_path: Path) -> None:
    """ORIGIN: one body over the bound is a refusal that names the part holding the statement."""
    big = "def big():\n" + "".join(f"    x{k} = {k}\n" for k in range(40))
    p = split.plan(_write(tmp_path, "bg.py", big), _small(20))
    assert p.refusal is not None
    assert p.refusal.kind == "budget"
    assert p.refusal.names == ("bg_00.py",)
    assert not p.files


def test_a_definition_bound_cuts_what_the_line_bound_cannot_see(tmp_path: Path) -> None:
    """ORIGIN: six tiny defs are one part under a line bound alone and three under max_defs=2."""
    path = _write(tmp_path, "md.py", _SIX_DEFS)
    lines_only = split.plan(path, _small(500))
    bounded = split.plan(path, split.Options(max_lines=500, max_defs=_PAIR))
    assert len(lines_only.parts) == 1
    assert bounded.refusal is None
    assert [len(part.names) for part in bounded.parts] == [2, 2, 2]
    assert split.verify(bounded)[0]
    assert len(split.plan(path, split.Options(max_lines=500, max_defs=None)).parts) == 1


def test_a_generous_definition_bound_does_not_disable_the_line_bound(tmp_path: Path) -> None:
    """ORIGIN: the line bound still cuts when max_defs is generous; neither subsumes the other."""
    body = "".join(
        f"def e{k}():\n" + "".join(f"    y{j} = {j}\n" for j in range(30)) for k in range(3)
    )
    p = split.plan(_write(tmp_path, "ml.py", body), split.Options(max_lines=40, max_defs=99))
    assert p.refusal is None
    assert len(p.parts) > _PAIR


# ── AUTHORED arms ─────────────────────────────────────────────────────────────────────────────


def test_plan_writes_nothing(tmp_path: Path) -> None:
    """AUTHORED: planning leaves the directory byte-for-byte as it was."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    before = _tree(tmp_path)
    p = split.plan(path, _small(_BOUND))
    assert p.applicable
    assert _tree(tmp_path) == before


def test_apply_refuses_without_the_explicit_operand(tmp_path: Path) -> None:
    """AUTHORED: no write operand raises and touches nothing, whatever the environment says."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    before = _tree(tmp_path)
    p = split.plan(path, _small(_BOUND))
    with pytest.raises(split.ChoiceError):
        split.apply(p)
    assert _tree(tmp_path) == before


def test_a_dry_run_reports_every_file_and_writes_none(tmp_path: Path) -> None:
    """AUTHORED: write=False names the files it would write, entry last, and changes nothing."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    before = _tree(tmp_path)
    rows = split.apply(split.plan(path, _small(_BOUND)), write=False)
    assert [r.name for r in rows][-1] == "ls.py"
    assert not any(r.written for r in rows)
    assert _tree(tmp_path) == before


def test_apply_writes_the_parts_and_the_rewritten_entry(tmp_path: Path) -> None:
    """AUTHORED: write=True lands every planned file exactly as planned, with no temp file left."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    p = split.plan(path, _small(_BOUND))
    rows = split.apply(p, write=True)
    assert all(r.written for r in rows)
    assert _tree(tmp_path) == dict(p.files)


def test_apply_is_idempotent_on_a_second_run(tmp_path: Path) -> None:
    """AUTHORED: re-planning the split module moves nothing, and applying that plan is a no-op."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    split.apply(split.plan(path, _small(_BOUND)), write=True)
    after_first = _tree(tmp_path)
    again = split.plan(path, _small(_BOUND))
    assert again.refusal is None
    assert not again.files
    assert split.apply(again, write=True) == ()
    assert _tree(tmp_path) == after_first


def test_a_name_that_cannot_move_is_refused_with_the_reason(tmp_path: Path) -> None:
    """AUTHORED: a kept name referenced by a part-bound name refuses and names both."""
    text = "def helper():\n    return 1\ndef user():\n    return helper()\n"
    path = _write(tmp_path, "kp.py", text)
    p = split.plan(path, split.Options(keep=frozenset({"helper"})))
    assert p.refusal is not None
    assert p.refusal.kind == "entry-dep"
    assert p.refusal.names == ("helper", "user")
    assert not p.applicable
    with pytest.raises(split.RefusedError, match="entry-dep"):
        split.apply(p, write=True)


def test_an_unparseable_file_is_a_skip_and_cannot_be_applied(tmp_path: Path) -> None:
    """AUTHORED: a syntax error is returned as a Skip, never raised and never swallowed."""
    path = _write(tmp_path, "bad.py", "def (:\n")
    p = split.plan(path)
    assert [(s.path, s.why) for s in p.skipped] == [(path, "unparseable")]
    assert not p.files
    with pytest.raises(split.RefusedError, match="skipped"):
        split.apply(p, write=False)


def test_a_missing_file_is_a_skip(tmp_path: Path) -> None:
    """AUTHORED: an unreadable path is a Skip with the reason, not an exception."""
    p = split.plan(str(tmp_path / "absent.py"))
    assert [s.why for s in p.skipped] == ["unreadable"]


def test_two_statements_on_one_line_are_refused(tmp_path: Path) -> None:
    """AUTHORED: a `;`-joined line cannot be sliced byte-exactly, so the plan refuses it."""
    p = split.plan(_write(tmp_path, "sc.py", "a = 1; b = 2\ndef f():\n    return a\n"))
    assert p.refusal is not None
    assert p.refusal.kind == "joined-line"


def test_a_module_that_declares_all_is_refused(tmp_path: Path) -> None:
    """AUTHORED: an existing `__all__` would need merging by hand, so no plan is made."""
    p = split.plan(_write(tmp_path, "al.py", "__all__ = ['f']\ndef f():\n    return 1\n"))
    assert p.refusal is not None
    assert p.refusal.kind == "all-declared"


def test_the_licence_header_stays_on_the_entry_and_opens_every_part(tmp_path: Path) -> None:
    """AUTHORED: SPDX and copyright lines travel to each part; the entry keeps its own block."""
    p = split.plan(_write(tmp_path, "lc.py", _LICENCED), split.Options(max_defs=1))
    assert len(p.parts) == _PAIR
    assert all(code.startswith(_HEAD) for code in p.files.values())


def test_no_suppression_comment_is_emitted(tmp_path: Path) -> None:
    """AUTHORED: the generated files declare their re-exports in `__all__`, with no noqa."""
    p = split.plan(_write(tmp_path, "ls.py", _COMMENTED), _small(_BOUND))
    assert "noqa" not in "".join(p.files.values())
    assert '"a",' in p.files["ls.py"]


def test_a_caller_of_a_moved_private_name_is_owed(tmp_path: Path) -> None:
    """AUTHORED: an importer of a private name the entry no longer re-exports is listed as owed."""
    path = _write(tmp_path, "lib.py", "def _hidden():\n    return 1\ndef shown():\n    return 2\n")
    caller = _write(tmp_path, "use.py", "from lib import _hidden, shown\n")
    p = split.plan(path, split.Options(max_defs=1), callers=[caller])
    assert [(o.path, o.name, o.file) for o in p.owed] == [(caller, "_hidden", "lib_00.py")]
    assert not p.skipped


_LIB = "def _hidden():\n    return 1\ndef shown():\n    return 2\n"


def _owed_by(tmp_path: Path, caller_text: str) -> list[tuple[int, str, str]]:
    path = _write(tmp_path, "lib.py", _LIB)
    caller = _write(tmp_path, "use.py", caller_text)
    p = split.plan(path, split.Options(max_defs=1), callers=[caller])
    return [(o.line, o.name, o.file) for o in p.owed]


def test_a_caller_reaching_a_moved_private_name_by_attribute_is_owed(tmp_path: Path) -> None:
    """AUTHORED: `import lib` then `lib._hidden` is owed an edit, as `from lib import` is."""
    assert _owed_by(tmp_path, "import lib\nx = lib._hidden()\n") == [(2, "_hidden", "lib_00.py")]


def test_a_caller_reaching_a_moved_private_name_through_an_alias_is_owed(tmp_path: Path) -> None:
    """AUTHORED: `import lib as L` then `L._hidden` is owed, and the alias is not the stem."""
    got = _owed_by(tmp_path, "import lib as L\nx = L._hidden()\ny = lib._hidden()\n")
    assert got == [(2, "_hidden", "lib_00.py")]


def test_a_caller_importing_the_stem_from_a_package_is_owed_by_attribute(tmp_path: Path) -> None:
    """AUTHORED: `from pkg import lib` binds the module, so `lib._hidden` is owed too."""
    got = _owed_by(tmp_path, "from pkg import lib as m\nx = m._hidden()\n")
    assert got == [(2, "_hidden", "lib_00.py")]


def test_an_attribute_the_entry_still_exports_or_another_module_owns_is_not_owed(
    tmp_path: Path,
) -> None:
    """AUTHORED: a public name, an unmoved name, or another module's attribute is never owed."""
    text = "import lib\nimport other\na = lib.shown()\nb = lib.nowhere\nc = other._hidden\n"
    assert _owed_by(tmp_path, text) == []


def test_an_unreadable_caller_is_skipped_not_dropped(tmp_path: Path) -> None:
    """AUTHORED: a caller that cannot be parsed comes back as a Skip on the plan."""
    path = _write(tmp_path, "lib.py", "def a():\n    return 1\ndef b():\n    return 2\n")
    caller = _write(tmp_path, "use.py", "from (:\n")
    p = split.plan(path, split.Options(max_defs=1), callers=[caller])
    assert [s.path for s in p.skipped] == [caller]
    assert not p.applicable


def test_apply_refuses_a_plan_whose_file_changed_since(tmp_path: Path) -> None:
    """AUTHORED: editing the module between plan and apply is refused, and nothing is written."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    p = split.plan(path, _small(_BOUND))
    (tmp_path / "ls.py").write_text(_COMMENTED + "# edited\n", encoding="utf-8")
    before = _tree(tmp_path)
    with pytest.raises(split.RefusedError, match="changed since"):
        split.apply(p, write=True)
    assert _tree(tmp_path) == before


def test_apply_never_overwrites_a_different_sibling(tmp_path: Path) -> None:
    """AUTHORED: a sibling already there with other content is refused before any write."""
    path = _write(tmp_path, "ls.py", _COMMENTED)
    _write(tmp_path, "ls_00.py", "mine = 1\n")
    p = split.plan(path, _small(_BOUND))
    before = _tree(tmp_path)
    with pytest.raises(split.ExistsError):
        split.apply(p, write=True)
    assert _tree(tmp_path) == before


def test_a_lambda_needs_its_default_and_its_body_names_but_not_its_parameters(
    tmp_path: Path,
) -> None:
    """AUTHORED: a lambda's default is read where it is written and its body reads from outside."""
    src = "D = 1\nX = 2\nh = lambda a, b=D: a + b + X\n"
    stm = _by_name(split.plan(_write(tmp_path, "lm.py", src)))
    assert stm["h"].free == frozenset({"D", "X"})
    assert stm["h"].binds == frozenset({"h"})


def test_a_class_needs_its_decorators_bases_keywords_and_body_names_but_not_its_own(
    tmp_path: Path,
) -> None:
    """AUTHORED: a class reads its decorator, bases, keyword values and body from outside itself."""
    src = (
        "Base = object\nMeta = type\ndeco = lambda c: c\nY = 1\nZ = 2\n"
        "@deco\n"
        "class C(Base, metaclass=Meta):\n"
        "    x = Y\n"
        "    def f(self):\n"
        "        return Z\n"
    )
    stm = _by_name(split.plan(_write(tmp_path, "cl.py", src)))
    assert stm["C"].free == frozenset({"deco", "Base", "Meta", "Y", "Z"})
    assert stm["C"].binds == frozenset({"C"})
