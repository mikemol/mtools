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
    assert "src/app.py" in reason


def test_two_shas_in_one_stack_refuse_it() -> None:
    """The lock at another sha than the pyproject is two repins, not one."""
    new = _texts(_NEW, _DIGEST_NEW, prose=_NEW)
    new[_LOCK] = _lock("abc1234", _DIGEST_NEW)
    old, new = _stack(new)
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "exactly one sha" in reason


def test_a_wheel_named_for_another_sha_refuses_the_stack() -> None:
    """The texts say 636e39b and an added wheel says abc1234."""
    old, new = _stack()
    old[_wheel("abc1234")] = None
    new[_wheel("abc1234")] = ""
    reason = repin_admission.admits(old, new)
    assert reason is not None
    assert "exactly one sha" in reason


def test_a_stack_that_names_no_sha_is_not_a_repin() -> None:
    """Texts that change nothing a repin changes name no sha, and a repin names one."""
    same: dict[str, str | None] = {_PYPROJECT: "[project]\n"}
    assert repin_admission.admits(same, dict(same)) is not None


def test_a_third_party_local_version_is_not_a_second_sha() -> None:
    """A package that is not mikemol's keeps its own `+local` version and counts for nothing."""
    local = 'name = "torchlike"\nversion = "2.0+deadbee"\n'
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
