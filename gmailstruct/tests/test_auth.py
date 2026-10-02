# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""auth.decrypt: the token reaches memory only, and no failure carries it into a traceback."""

from __future__ import annotations

import traceback
from pathlib import Path

import pytest

from mikemol.gmailstruct.auth import DecryptError, Runner, decrypt

# ⚑ SYNTHETIC: a planted token, so a test can look for it where it must not be.
_TOKEN = "1//planted-refresh-token-0f2a"
_CIPHER = Path("/nonexistent/refresh.age")
_IDENTITY = Path("/nonexistent/yubikey-identity.txt")


class _Fake:
    """A runner that records each argv and answers with a fixed result."""

    def __init__(self, status: int, out: bytes, err: bytes = b"") -> None:
        self.calls: list[list[str]] = []
        self.result = (status, out, err)

    def __call__(self, argv: list[str]) -> tuple[int, bytes, bytes]:
        self.calls.append(argv)
        return self.result


def _decrypt(fake: Runner) -> str:
    return decrypt(_CIPHER, _IDENTITY, fake)


def _rendered(err: BaseException) -> str:
    return "".join(traceback.format_exception(err))


def test_token_is_returned_from_ages_stdout() -> None:
    """The positive control: age's stdout, stripped, is the token, asked for with this argv."""
    fake = _Fake(0, (_TOKEN + "\n").encode())
    assert _decrypt(fake) == _TOKEN
    assert fake.calls == [["age", "--decrypt", "--identity", str(_IDENTITY), str(_CIPHER)]]


def test_failed_decrypt_names_the_file_and_never_the_output() -> None:
    """A failing age is an error naming the file; its stdout, even a token, is in no traceback."""
    fake = _Fake(1, _TOKEN.encode(), b"age: error: no identity matched")
    with pytest.raises(DecryptError) as caught:
        _decrypt(fake)
    assert str(_CIPHER) in str(caught.value)
    assert _TOKEN not in _rendered(caught.value)


def test_failed_decrypt_quotes_ages_own_error() -> None:
    """The error quotes age's stderr (W382); a failed decrypt made no plaintext to leak."""
    fake = _Fake(1, b"", b"age: error: no identity matched\n")
    with pytest.raises(DecryptError, match=r"\(exit 1\): age: error: no identity matched$"):
        _decrypt(fake)


def test_failed_decrypt_with_stderr_on_the_terminal_says_where_the_cause_went() -> None:
    """A runner that let stderr through returns none; the error points at the terminal."""
    with pytest.raises(DecryptError, match="age's own message is printed above"):
        _decrypt(_Fake(1, b"", b""))


def test_empty_output_is_an_error_not_an_empty_token() -> None:
    """An age run succeeding with nothing on stdout is refused, never returned as a blank token."""
    with pytest.raises(DecryptError, match="to nothing"):
        _decrypt(_Fake(0, b"  \n"))


def test_non_utf8_output_is_an_error_carrying_none_of_it() -> None:
    """Undecodable plaintext is refused, and the error chain does not carry the bytes."""
    with pytest.raises(DecryptError) as caught:
        _decrypt(_Fake(0, b"\xff\xfe" + _TOKEN.encode()))
    assert caught.value.__cause__ is None
    assert _TOKEN not in _rendered(caught.value)


def test_decrypt_writes_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The token reaches memory only: decrypting leaves the working directory empty."""
    monkeypatch.chdir(tmp_path)
    _decrypt(_Fake(0, _TOKEN.encode()))
    assert not list(tmp_path.iterdir())
