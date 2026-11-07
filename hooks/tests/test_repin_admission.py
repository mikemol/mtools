# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Clause R: a stack that changes only the vendored sha is a repin, anything else is not (W2311).

The fixtures take the shapes of nemik's repin to 636e39b (cde95c66): pyproject.toml, MODULE.bazel
and uv.lock each naming the wheels, the checksum rows, and the wheels themselves under new names.
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
_THIRD = 'name = "attrs"\nversion = "1.2.3"\n'


def _wheel(sha: str) -> str:
    return f"vendor/wheels/mikemol_hooks-0.1.0+{sha}-py3-none-any.whl"


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


def _texts(sha: str, digest: str, *, prose: str) -> dict[str, str | None]:
    return {
        _PYPROJECT: _pyproject(sha),
        _MODULE: _module(sha, prose),
        _LOCK: _lock(sha, digest),
        _SUMS: _sums(sha, digest),
    }


def _stack(
    new_texts: dict[str, str | None] | None = None,
    *,
    new_sha: str = _NEW,
    old_texts: dict[str, str | None] | None = None,
) -> tuple[dict[str, str | None], dict[str, str | None]]:
    old = old_texts or _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    new = new_texts or _texts(new_sha, _DIGEST_NEW, prose=new_sha)
    old[_wheel(_OLD)] = ""
    new[_wheel(_OLD)] = None
    old[_wheel(new_sha)] = None
    new[_wheel(new_sha)] = ""
    return old, new


def test_a_repin_of_the_text_files_and_the_wheels_is_admitted() -> None:
    """The control: four text files change their sha, hash and prose only; a wheel is renamed."""
    old, new = _stack()
    assert repin_admission.admits(old, new) is None


def test_the_g_spelling_of_the_sha_is_the_same_sha() -> None:
    """`+g<sha>` in the names and the text is admitted, as `+<sha>` is."""
    sha = "g" + _NEW
    new = _texts(sha, _DIGEST_NEW, prose=_NEW)
    old, new = _stack(new, new_sha=sha)
    assert repin_admission.admits(old, new) is None


def test_one_stray_line_in_a_text_file_refuses_the_stack_and_names_the_file() -> None:
    """A new dependency in pyproject.toml is more than a sha."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_PYPROJECT] = _pyproject(_NEW, 'rich = "13"\n')
    old, new = _stack(new)
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert _PYPROJECT in reason


def test_a_third_party_version_in_the_lock_is_not_a_repin() -> None:
    """Only the mikemol packages' versions move; `attrs` going to 1.2.4 refuses the stack."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, 'name = "attrs"\nversion = "1.2.4"\n')
    old, new = _stack(new)
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert _LOCK in reason


def test_a_file_a_repin_does_not_own_refuses_the_stack() -> None:
    """A source file beside the repin is named and refused."""
    old, new = _stack()
    old["src/app.py"] = "x = 1\n"
    new["src/app.py"] = "x = 2\n"
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "src/app.py is not a repin-owned file" in reason


def test_two_shas_in_one_stack_refuse_it() -> None:
    """The lock at another sha than the pyproject is two repins, not one."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock("abc1234", _DIGEST_NEW)
    old, new = _stack(new)
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "every pin to one sha" in reason


def test_a_wheel_named_for_another_sha_refuses_the_stack() -> None:
    """The texts say 636e39b and an added wheel says abc1234."""
    old, new = _stack()
    old[_wheel("abc1234")] = None
    new[_wheel("abc1234")] = ""
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "carries a sha other than the one the pins moved to" in reason


def test_a_stack_that_names_no_sha_is_not_a_repin() -> None:
    """Texts that change nothing a repin changes name no sha, and a repin names one."""
    same: dict[str, str | None] = {_PYPROJECT: "[project]\n"}
    assert repin_admission.admits(same, dict(same)) is not None


def test_a_third_party_local_version_is_not_a_second_sha() -> None:
    """A package that is not mikemol's keeps its own `+local` version and counts for nothing."""
    local = 'name = "torchlike"\nversion = "2.0.1+deadbee"\n'
    old = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old[_LOCK] = _lock(_OLD, _DIGEST_OLD, local)
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, local)
    old, new = _stack(new, old_texts=old)
    assert repin_admission.admits(old, new) is None


def test_a_text_file_added_or_removed_and_an_empty_stack_are_not_repins() -> None:
    """The controls: nothing changed, and uv.lock created by the stack."""
    assert repin_admission.admits({}, {}) is not None
    old, new = _stack()
    old[_LOCK] = None
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "added or removed" in reason


def test_a_third_party_local_version_that_changes_is_not_a_repin() -> None:
    """A package that is not mikemol's may not move its `+local` version beside a repin."""
    before = 'name = "torchlike"\nversion = "2.0.1+aaaaaaa"\n'
    after = 'name = "torchlike"\nversion = "2.0.1+bbbbbbb"\n'
    old = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old[_LOCK] = _lock(_OLD, _DIGEST_OLD, before)
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock(_NEW, _DIGEST_NEW, after)
    old, new = _stack(new, old_texts=old)
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert _LOCK in reason


def test_a_stack_that_moves_no_sha_is_not_a_repin() -> None:
    """B2: a no-op, a same-named wheel with other bytes and a stray wheel pass nothing."""
    texts = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    same = dict(texts)
    same[_wheel(_OLD)] = ""
    assert repin_admission.admits(same, dict(same)) is not None
    evil = dict(same)
    evil["vendor/wheels/mikemol_evil-0.1.0+abc1234-py3-none-any.whl"] = ""
    reason = repin_admission.admits(same, {**evil})
    assert reason is not None


def test_an_added_wheel_no_new_text_names_is_refused() -> None:
    """B2: a new sha on a wheel nothing references is not part of the repin."""
    old, new = _stack()
    new["vendor/wheels/mikemol_evil-0.1.0+abc1234-py3-none-any.whl"] = ""
    old["vendor/wheels/mikemol_evil-0.1.0+abc1234-py3-none-any.whl"] = None
    reason = repin_admission.admits(old, new)
    assert reason is not None


def test_a_dropped_trailing_newline_and_crlf_are_changes_beyond_the_sha() -> None:
    """B2: line terminators are bytes; the masked comparison keeps them."""
    for dropped in (True, False):
        new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
        body = str(new[_PYPROJECT])
        new[_PYPROJECT] = body.rstrip("\n") if dropped else body.replace("\n", "\r\n")
        old, new = _stack(new)
        assert repin_admission.admits(old, new) is not None


def test_a_pin_held_at_an_older_sha_is_not_a_second_sha() -> None:
    """B1: nemik's real repin held converge at 0f8267e while the rest moved; one new sha."""
    wheel = "vendor/wheels/mikemol_converge-0.1.0+0f8267e-py3-none-any.whl"
    held = f'mikemol-converge = {{ path = "{wheel}" }}\n'
    old_texts = _texts(_OLD, _DIGEST_OLD, prose=_OLD)
    old_texts[_PYPROJECT] = str(old_texts[_PYPROJECT]) + held
    new_texts = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new_texts[_PYPROJECT] = str(new_texts[_PYPROJECT]) + held
    old, new = _stack(new_texts, old_texts=old_texts)
    assert repin_admission.admits(old, new) is None
    assert repin_admission.new_sha(old, new) == _NEW


def test_the_wheel_directory_readme_is_a_repin_owned_file() -> None:
    """B1: revendor writes checksums into vendor/wheels/README.md; it moves with the sha."""
    old, new = _stack()
    row = "mikemol_hooks-0.1.0+{sha}-py3-none-any.whl sha256:{digest}\n"
    old["vendor/wheels/README.md"] = row.format(sha=_OLD, digest=_DIGEST_OLD)
    new["vendor/wheels/README.md"] = row.format(sha=_NEW, digest=_DIGEST_NEW)
    assert repin_admission.admits(old, new) is None


def test_the_one_new_sha_is_named_for_the_audit_trailer() -> None:
    """The landing writes it: a repin names its sha, anything else names none."""
    old, new = _stack()
    assert repin_admission.new_sha(old, new) == _NEW
    assert repin_admission.new_sha(old, dict(old)) is None


_OTHER = "9999999"
_ROW_OTHER = "  ./mikemol_other-0.1.0+9999999-py3-none-any.whl\n"


def _other_wheel() -> str:
    return f"vendor/wheels/mikemol_other-0.1.0+{_OTHER}-py3-none-any.whl"


def test_a_same_named_wheel_with_other_bytes_is_not_a_repin() -> None:
    """D1: a repin never modifies an existing wheel path; the same name at another blob refuses."""
    old, new = _stack()
    old[_wheel(_NEW)] = "blob-a"
    new[_wheel(_NEW)] = "blob-b"
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "is an existing wheel with other bytes" in reason


def test_a_changed_digest_on_a_row_whose_sha_did_not_move_is_not_a_repin() -> None:
    """D1: an untouched held wheel's checksum row changing is no part of a repin."""
    old, new = _stack()
    old[_SUMS] = _sums(_OLD, _DIGEST_OLD) + "c" * 64 + _ROW_OTHER
    new[_SUMS] = _sums(_NEW, _DIGEST_NEW) + "d" * 64 + _ROW_OTHER
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "a digest on a pin whose sha did not move" in reason


def _two_pins(second: str) -> tuple[dict[str, str | None], dict[str, str | None]]:
    # A pyproject with two pins; the first moves to the new sha, the second to `second`.
    other_old = "vendor/wheels/mikemol_converge-0.1.0+0f8267e-py3-none-any.whl"
    other_new = f"vendor/wheels/mikemol_converge-0.1.0+{second}-py3-none-any.whl"
    head = "[tool.uv.sources]\n"
    first_old = f'mikemol-hooks = {{ path = "{_wheel(_OLD)}" }}\n'
    first_new = f'mikemol-hooks = {{ path = "{_wheel(_NEW)}" }}\n'
    old, new = _stack()
    old[_PYPROJECT] = head + first_old + f'mikemol-converge = {{ path = "{other_old}" }}\n'
    new[_PYPROJECT] = head + first_new + f'mikemol-converge = {{ path = "{other_new}" }}\n'
    return old, new


def test_two_pins_moving_to_two_shas_are_not_one_repin() -> None:
    """D2: hooks to 636e39b with converge to another sha is two repins, whatever HEAD holds."""
    old, new = _two_pins("5ba261f")
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "every pin to one sha" in reason


def test_two_pins_catching_up_to_the_same_sha_are_one_repin() -> None:
    """D2: every changed pin moving to the one sha passes, however many pins moved."""
    old, new = _two_pins(_NEW)
    assert repin_admission.admits(old, new) is None


def test_a_text_naming_a_sha_no_wheel_carries_is_not_a_repin() -> None:
    """D3: pyproject alone, or a sha move that adds no wheel, names a wheel nobody supplies."""
    old, new = _stack()
    del old[_wheel(_NEW)]
    del new[_wheel(_NEW)]
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert f"no wheel of the stack carries the new sha {_NEW}" in reason


def test_deleting_a_wheel_a_new_text_still_names_is_not_a_repin() -> None:
    """D3: the stack deletes a held wheel and a text it ships still names that wheel."""
    old, new = _stack()
    old[_other_wheel()] = "blob-held"
    new[_other_wheel()] = None
    old[_SUMS] = _sums(_OLD, _DIGEST_OLD) + "c" * 64 + _ROW_OTHER
    new[_SUMS] = _sums(_NEW, _DIGEST_NEW) + "c" * 64 + _ROW_OTHER
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "is deleted but a text of the stack still names it" in reason
