# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R: a stack that leaves ONE consistent tree after changing only the sha is a repin (W2342).

The fixtures take the shapes of nemik's repin to 636e39b (cde95c66): pyproject.toml, MODULE.bazel
and uv.lock each naming the wheels, the checksum rows, and the wheels themselves under new names.
A wheel's value on either side is its BLOB id, never its text; `wheels` is every wheel HEAD holds.
"""

from __future__ import annotations

from mikemol.hooks import repin_admission

_OLD = "459a112"
_NEW = "636e39b"
_DIGEST_OLD = "a" * 64
_DIGEST_NEW = "b" * 64
_PYPROJECT = "pyproject.toml"
_MODULE = "MODULE.bazel"
_LOCK = "uv.lock"
_SUMS = "vendor/wheels/SHA256SUMS"
_README = "vendor/wheels/README.md"
_THIRD = 'name = "attrs"\nversion = "1.2.3"\n'
_OLD_BLOB = "blob-old"
_NEW_BLOB = "blob-new"
_CONVERGE_OLD = "0f8267e"
_PINS_DISAGREE = "different versions or shas"
_NOT_HELD = "which the tree does not hold after the stack"
type Texts = dict[str, str | None]


def _wheel(sha: str, dist: str = "hooks") -> str:
    return f"vendor/wheels/mikemol_{dist}-0.1.0+{sha}-py3-none-any.whl"


def _pyproject(sha: str, extra: str = "") -> str:
    head = "[project]\ndependencies = [\n]\n[tool.uv.sources]\n"
    return head + f'mikemol-hooks = {{ path = "{_wheel(sha)}" }}\n{extra}'


def _module(sha: str, prose: str) -> str:
    comment = f"# vendored at mtools {prose}\n"
    return comment + f'vendored_wheel(\n    wheel = "//:{_wheel(sha)}",\n)\n'


def _lock(sha: str, digest: str, third: str = _THIRD) -> str:
    package = f'[[package]]\nname = "mikemol-hooks"\nversion = "0.1.0+{sha}"\n'
    source = f'source = {{ path = "{_wheel(sha)}" }}\nwheels = [\n'
    name = f"mikemol_hooks-0.1.0+{sha}-py3-none-any.whl"
    row = f'    {{ filename = "{name}", hash = "sha256:{digest}" }},\n]\n'
    return f"[[package]]\n{third}\n" + package + source + row


def _sums(sha: str, digest: str) -> str:
    return f"{digest}  ./mikemol_hooks-0.1.0+{sha}-py3-none-any.whl\n"


def _texts(sha: str, digest: str, *, prose: str) -> Texts:
    return {
        _PYPROJECT: _pyproject(sha),
        _MODULE: _module(sha, prose),
        _LOCK: _lock(sha, digest),
        _SUMS: _sums(sha, digest),
    }


def _head() -> dict[str, str]:
    # Every wheel HEAD holds in the control repin: the hooks wheel at the old sha.
    return {_wheel(_OLD): _OLD_BLOB}


def _stack(
    new_texts: Texts | None = None, *, new_sha: str = _NEW, old_texts: Texts | None = None
) -> tuple[Texts, Texts]:
    old = old_texts or _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    new = new_texts or _texts(new_sha, _DIGEST_NEW, prose=new_sha)
    old[_wheel(_OLD)] = _OLD_BLOB
    new[_wheel(_OLD)] = None
    old[_wheel(new_sha)] = None
    new[_wheel(new_sha)] = _NEW_BLOB
    return old, new


def _admits(
    old: Texts, new: Texts, held: Texts | None = None, wheels: dict[str, str] | None = None
) -> str | None:
    return repin_admission.admits(old, new, held, _head() if wheels is None else wheels)


def test_a_repin_of_the_text_files_and_the_wheels_is_admitted() -> None:
    """The control: four text files change their sha, hash and prose only; a wheel is renamed."""
    old, new = _stack()
    assert _admits(old, new) is None


def test_the_g_spelling_of_the_sha_is_the_same_sha() -> None:
    """`+g<sha>` in the names and the text is admitted, as `+<sha>` is."""
    sha = "g" + _NEW
    new = _texts(sha, _DIGEST_NEW, prose=_NEW)
    old, new = _stack(new, new_sha=sha)
    assert _admits(old, new) is None


def test_one_stray_line_in_a_text_file_refuses_the_stack_and_names_the_file() -> None:
    """A new dependency in pyproject.toml is more than a sha."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_PYPROJECT] = _pyproject(_NEW, 'rich = "13"\n')
    old, new = _stack(new)
    reason = _admits(old, new)
    assert reason is not None
    assert _PYPROJECT in reason


def test_a_third_party_version_in_the_lock_is_not_a_repin() -> None:
    """Only the mikemol packages' versions move; `attrs` going to 1.2.4 refuses the stack."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, 'name = "attrs"\nversion = "1.2.4"\n')
    old, new = _stack(new)
    reason = _admits(old, new)
    assert reason is not None
    assert _LOCK in reason


def test_a_file_a_repin_does_not_own_refuses_the_stack() -> None:
    """A source file beside the repin is named and refused."""
    old, new = _stack()
    old["src/app.py"] = "x = 1\n"
    new["src/app.py"] = "x = 2\n"
    reason = _admits(old, new)
    assert reason is not None
    assert "src/app.py is not a repin-owned file" in reason


def test_two_shas_in_one_stack_refuse_it() -> None:
    """The lock at another sha than the pyproject is two repins, not one."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock("abc1234", _DIGEST_NEW)
    old, new = _stack(new)
    reason = _admits(old, new)
    assert reason is not None
    assert "every pin to one sha" in reason


def test_a_wheel_named_for_another_sha_refuses_the_stack() -> None:
    """The texts say 636e39b and an added wheel says abc1234: no text names it."""
    old, new = _stack()
    old[_wheel("abc1234")] = None
    new[_wheel("abc1234")] = _NEW_BLOB
    reason = _admits(old, new)
    assert reason is not None
    assert "is named by no file of the stack" in reason


def test_a_stack_that_moves_no_sha_is_not_a_repin() -> None:
    """A no-op, and a stray wheel beside it, pass nothing: no pin moved."""
    same = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    same[_wheel(_OLD)] = _OLD_BLOB
    assert _admits(same, dict(same)) is not None
    evil = dict(same)
    evil[_wheel("abc1234", "evil")] = _NEW_BLOB
    assert _admits(same, evil) is not None
    assert _admits({}, {}) is not None


def test_a_third_party_local_version_is_not_a_second_sha() -> None:
    """A package that is not mikemol's keeps its own `+local` version and counts for nothing."""
    local = 'name = "torchlike"\nversion = "2.0.1+deadbee"\n'
    old = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old[_LOCK] = _lock(_OLD, _DIGEST_OLD, local)
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, local)
    old, new = _stack(new, old_texts=old)
    assert _admits(old, new) is None


def test_a_third_party_local_version_that_changes_is_not_a_repin() -> None:
    """A package that is not mikemol's may not move its `+local` version beside a repin."""
    old = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old[_LOCK] = _lock(_OLD, _DIGEST_OLD, 'name = "torchlike"\nversion = "2.0.1+aaaaaaa"\n')
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, 'name = "torchlike"\nversion = "2.0.1+bbbbbbb"\n')
    old, new = _stack(new, old_texts=old)
    reason = _admits(old, new)
    assert reason is not None
    assert _LOCK in reason


def test_a_text_file_added_or_removed_is_not_a_repin() -> None:
    """The control: uv.lock created by the stack."""
    old, new = _stack()
    old[_LOCK] = None
    reason = _admits(old, new)
    assert reason is not None
    assert "added or removed" in reason


def test_a_dropped_trailing_newline_and_crlf_are_changes_beyond_the_sha() -> None:
    """Line terminators are bytes; the masked comparison keeps them."""
    for dropped in (True, False):
        new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
        body = str(new[_PYPROJECT])
        new[_PYPROJECT] = body.rstrip("\n") if dropped else body.replace("\n", "\r\n")
        old, new = _stack(new)
        assert _admits(old, new) is not None


def _converge_line(sha: str) -> str:
    return f'mikemol-converge = {{ path = "{_wheel(sha, "converge")}" }}\n'


def test_a_pin_held_at_an_older_sha_is_not_a_second_sha() -> None:
    """Nemik's real repin held converge at 0f8267e while the rest moved: one target sha."""
    held = _converge_line(_CONVERGE_OLD)
    old_texts = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old_texts[_PYPROJECT] = str(old_texts[_PYPROJECT]) + held
    new_texts = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new_texts[_PYPROJECT] = str(new_texts[_PYPROJECT]) + held
    old, new = _stack(new_texts, old_texts=old_texts)
    wheels = {**_head(), _wheel(_CONVERGE_OLD, "converge"): "blob-conv"}
    assert _admits(old, new, wheels=wheels) is None
    assert repin_admission.new_sha(old, new, None, wheels) == _NEW


def test_the_wheel_directory_readme_is_owned_but_never_a_pin() -> None:
    """X1: revendor may move the README's checksums, and its prose is not read as a pin."""
    old, new = _stack()
    row = "mikemol_hooks-0.1.0+{sha}-py3-none-any.whl sha256:{digest}\n"
    old[_README] = row.format(sha=_OLD, digest=_DIGEST_OLD)
    new[_README] = row.format(sha=_NEW, digest=_DIGEST_NEW)
    assert _admits(old, new) is None
    old, new = _stack()
    held: Texts = {_README: f"the wheel {_wheel(_OLD)} was here\n"}
    assert _admits(old, new, held) is None


def test_the_one_sha_every_changed_pin_moved_to_is_named_for_the_audit_trailer() -> None:
    """The landing writes it: a repin names its sha, anything else names none."""
    old, new = _stack()
    assert repin_admission.new_sha(old, new, None, _head()) == _NEW
    assert repin_admission.new_sha(old, dict(old), None, _head()) is None


def test_a_same_named_wheel_with_other_bytes_is_not_a_repin() -> None:
    """A repin never modifies an existing wheel path; the same name at another blob refuses."""
    old, new = _stack()
    old[_wheel(_NEW)] = "blob-a"
    new[_wheel(_NEW)] = "blob-b"
    reason = _admits(old, new)
    assert reason is not None
    assert "is an existing wheel with other bytes" in reason


def test_a_changed_digest_on_a_row_whose_sha_did_not_move_is_not_a_repin() -> None:
    """An untouched held wheel's checksum row changing is no part of a repin."""
    other = "  ./mikemol_other-0.1.0+9999999-py3-none-any.whl\n"
    old, new = _stack()
    old[_SUMS] = _sums(_OLD, _DIGEST_OLD) + "c" * 64 + other
    new[_SUMS] = _sums(_NEW, _DIGEST_NEW) + "d" * 64 + other
    reason = _admits(old, new)
    assert reason is not None
    assert "a digest on a pin whose sha did not move" in reason


def _two_pins(second: str, *, wheel: bool) -> tuple[Texts, Texts]:
    # A pyproject with two pins; hooks moves to the new sha, converge to `second`.
    old, new = _stack()
    old[_PYPROJECT] = str(old[_PYPROJECT]) + _converge_line(_CONVERGE_OLD)
    new[_PYPROJECT] = str(new[_PYPROJECT]) + _converge_line(second)
    if wheel:
        gone, came = _wheel(_CONVERGE_OLD, "converge"), _wheel(second, "converge")
        old[gone], new[gone] = "bc0", None
        old[came], new[came] = None, "bc1"
    return old, new


def _two_head() -> dict[str, str]:
    return {**_head(), _wheel(_CONVERGE_OLD, "converge"): "bc0"}


def test_two_pins_moving_to_two_shas_are_not_one_repin() -> None:
    """Hooks to 636e39b with converge to another sha is two repins, whatever HEAD holds."""
    old, new = _two_pins("5ba261f", wheel=True)
    reason = _admits(old, new, wheels=_two_head())
    assert reason is not None
    assert "every pin to one sha" in reason


def test_two_pins_catching_up_to_the_same_sha_are_one_repin() -> None:
    """Every changed pin moving to the one sha passes, however many pins moved."""
    old, new = _two_pins(_NEW, wheel=True)
    assert _admits(old, new, wheels=_two_head()) is None


def test_a_moved_pin_whose_wheel_the_tree_does_not_hold_is_not_a_repin() -> None:
    """Hooks and converge both move, only the hooks wheel arrives, converge's is nowhere."""
    old, new = _two_pins(_NEW, wheel=False)
    reason = _admits(old, new, wheels=_two_head())
    assert reason is not None
    assert "mikemol_converge" in reason
    assert _NOT_HELD in reason


def test_a_catch_up_to_a_wheel_head_already_holds_is_a_repin() -> None:
    """A pin moving to a wheel HEAD already has needs no wheel in the stack: existence rules."""
    old, new = _two_pins(_NEW, wheel=False)
    wheels = {**_two_head(), _wheel(_NEW, "converge"): "bc9"}
    assert _admits(old, new, wheels=wheels) is None


def test_a_text_naming_a_sha_no_wheel_carries_is_not_a_repin() -> None:
    """Pyproject alone, or a sha move that adds no wheel, names a wheel nobody holds."""
    old, new = _stack()
    del old[_wheel(_NEW)]
    del new[_wheel(_NEW)]
    reason = _admits(old, new)
    assert reason is not None
    assert _NOT_HELD in reason


def test_a_text_the_stack_forgot_leaves_the_pin_texts_disagreeing() -> None:
    """X2: the sums row and the wheel move, the pyproject is forgotten and names the old wheel."""
    old, new = _stack()
    for path in (_PYPROJECT, _MODULE, _LOCK):
        del old[path]
        del new[path]
    held: Texts = {
        _PYPROJECT: _pyproject(_OLD),
        _MODULE: _module(_OLD, _OLD),
        _LOCK: _lock(_OLD, _DIGEST_OLD),
    }
    reason = _admits(old, new, held)
    assert reason is not None
    assert "name hooks at 2 different versions or shas" in reason


def test_each_pin_text_forgotten_in_turn_is_a_disagreement() -> None:
    """X2: whichever pin text the stack leaves alone, the tree disagrees with itself."""
    for forgotten in (_PYPROJECT, _MODULE, _LOCK, _SUMS):
        old, new = _stack()
        held: Texts = {forgotten: old[forgotten]}
        del old[forgotten]
        del new[forgotten]
        reason = _admits(old, new, held)
        assert reason is not None
        assert _PINS_DISAGREE in reason


def test_deleting_a_wheel_a_pin_text_the_stack_leaves_alone_still_names_is_refused() -> None:
    """The stack deletes a held wheel and an untouched text still names it."""
    other = _wheel("9999999", "other")
    old, new = _stack()
    old[other] = "blob-held"
    new[other] = None
    del old[_SUMS]
    del new[_SUMS]
    sums = _sums(_NEW, _DIGEST_NEW)
    held: Texts = {_SUMS: sums + "c" * 64 + f"  ./{other.removeprefix('vendor/wheels/')}\n"}
    wheels = {**_head(), other: "blob-held"}
    assert _admits(old, new, {_SUMS: sums}, wheels) is None
    reason = _admits(old, new, held, wheels)
    assert reason is not None
    assert _NOT_HELD in reason


def test_an_added_wheel_with_the_target_sha_that_no_text_names_is_refused() -> None:
    """It carries the new sha, so only the named-by-no-file rule can refuse it."""
    old, new = _stack()
    stray = _wheel(_NEW, "other")
    old[stray], new[stray] = None, "blob-x"
    reason = _admits(old, new)
    assert reason is not None
    assert f"{stray} is named by no file of the stack" in reason


def test_a_sha_moved_only_on_a_lock_version_line_leaves_the_texts_disagreeing() -> None:
    """No moved line names a wheel; the other pin texts still pin hooks at the old sha."""
    old_lock = _lock(_OLD, _DIGEST_OLD)
    new_lock = old_lock.replace(f'version = "0.1.0+{_OLD}"', f'version = "0.1.0+{_NEW}"')
    assert new_lock != old_lock
    held: Texts = {_PYPROJECT: _pyproject(_OLD)}
    reason = _admits({_LOCK: old_lock}, {_LOCK: new_lock}, held)
    assert reason is not None
    assert "name hooks at 2 different versions or shas" in reason


def test_a_literal_s_where_the_new_line_has_a_sha_is_refused_not_an_error() -> None:
    """The masks are equal (the literal S, a sha token) but the token counts are 0 and 1."""
    old: Texts = {_PYPROJECT: 'x = "vendor/wheels/mikemol_hooks-0.1.0+S-py3-none-any.whl"\n'}
    new: Texts = {_PYPROJECT: f'x = "{_wheel(_NEW)}"\n'}
    reason = _admits(old, new)
    assert reason is not None
    assert "a digest on a pin whose sha did not move" in reason


def test_every_wheel_a_line_names_is_read_not_only_the_first() -> None:
    """Two wheels on one line move together; the second one's absence from the tree refuses."""
    both = '[tool]\npins = ["{hooks}", "{conv}"]\n'
    old, new = _stack()
    old[_PYPROJECT] = both.format(hooks=_wheel(_OLD), conv=_wheel(_CONVERGE_OLD, "converge"))
    new[_PYPROJECT] = both.format(hooks=_wheel(_NEW), conv=_wheel(_NEW, "converge"))
    reason = _admits(old, new, wheels=_two_head())
    assert reason is not None
    assert "mikemol_converge" in reason
    assert _NOT_HELD in reason


def test_a_comment_naming_the_old_wheel_in_a_pin_text_is_not_a_pin() -> None:
    """A comment line is prose and names no pin, so an unchanged one disagrees with nothing."""
    note = f"# the wheel was {_wheel(_OLD)} once\n"
    old, new = _stack()
    old[_PYPROJECT] = note + str(old[_PYPROJECT])
    new[_PYPROJECT] = note + str(new[_PYPROJECT])
    assert _admits(old, new) is None


def test_a_stack_that_moves_only_a_readme_token_moved_no_pin() -> None:
    """B1: the README is owned but is no pin text; its token moving alone is not a repin."""
    row = "mikemol_hooks-0.1.0+{sha}-py3-none-any.whl sha256:{digest}\n"
    old: Texts = {_README: row.format(sha=_OLD, digest=_DIGEST_OLD)}
    new: Texts = {_README: row.format(sha=_NEW, digest=_DIGEST_NEW)}
    reason = _admits(old, new)
    assert reason is not None
    assert "moves them to 0" in reason
    assert repin_admission.new_sha(old, new, None, _head()) is None


def test_a_sha_moved_on_a_version_line_that_no_named_wheel_carries_is_not_a_repin() -> None:
    """B1: no pin text names a wheel, so no wheel carries the new sha: refused by that rule."""
    package = 'name = "mikemol-hooks"\nversion = "0.1.0+{sha}"\n'
    old: Texts = {_LOCK: "[[package]]\n" + package.format(sha=_OLD)}
    new: Texts = {_LOCK: "[[package]]\n" + package.format(sha=_NEW)}
    reason = _admits(old, new)
    assert reason is not None
    assert f"no wheel a pin text names carries the new sha {_NEW}" in reason
