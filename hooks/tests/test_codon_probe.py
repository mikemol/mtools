# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the Codon probe: the pin is read, the bytes are verified, nothing leaks (W1461).

⚑ THE CONTROL IS THE VERIFIED FETCH: a tarball that hashes to the pin is unpacked, cached and found
again without a second download; a tarball that does not, and one that tries to leave its directory,
unpack nothing. No test touches the network: the opener and the compiler are seams.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import codon_probe

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_TOP = "codon-deploy-linux-x86_64"
_URL = "https://example.invalid/codon.tgz"
_MODULE = f"""\
http_archive(
    name = "ruff",
    sha256 = "{"a" * 64}",
    url = "https://example.invalid/ruff.tgz",
)

http_archive(
    name = "codon",
    build_file_content = \"\"\"exports_files(["bin/codon"])\"\"\",
    sha256 = "{"b" * 64}",
    strip_prefix = "{_TOP}",
    url = "{_URL}",
)
"""
_BIN = b"#!/bin/sh\necho compiled\n"
_BAD_EXIT = 7


def _archive(member: str = f"{_TOP}/bin/codon") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(member)
        info.size = len(_BIN)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(_BIN))
    return buffer.getvalue()


def _pin(data: bytes) -> codon_probe.Pin:
    return codon_probe.Pin(_URL, hashlib.sha256(data).hexdigest(), _TOP)


def test_the_pin_is_read_from_the_codon_block_not_another_archive() -> None:
    """The control: the ruff block precedes it in the text, and its fields are not taken."""
    assert codon_probe.read_pin(_MODULE) == codon_probe.Pin(_URL, "b" * 64, _TOP)


@pytest.mark.parametrize(
    "text",
    [
        "",
        _MODULE.replace('name = "codon"', 'name = "other"'),
        _MODULE.replace(f'strip_prefix = "{_TOP}",', ""),
        _MODULE.replace(_URL, _URL.replace("https", "http")),
    ],
)
def test_a_missing_block_field_or_a_plain_http_url_is_refused(text: str) -> None:
    """No codon block, no strip prefix and a non-https URL each raise PinError."""
    with pytest.raises(codon_probe.PinError):
        codon_probe.read_pin(text)


def test_a_verified_download_is_unpacked_cached_and_not_fetched_twice(tmp_path: Path) -> None:
    """The bytes hash to the pin: bin/codon appears under the sha256, and a second call is free."""
    data = _archive()
    calls: list[str] = []

    def opener(url: str) -> bytes:
        calls.append(url)
        return data

    first = codon_probe.fetch(_pin(data), tmp_path, opener)
    assert first.read_bytes() == _BIN
    assert first.parent.parent.name == _pin(data).sha256
    assert codon_probe.fetch(_pin(data), tmp_path, opener) == first
    assert len(calls) == 1


def test_bytes_that_do_not_hash_to_the_pin_unpack_nothing(tmp_path: Path) -> None:
    """The positive control for the check: wrong bytes raise and leave the cache empty."""
    pin = codon_probe.Pin(_URL, "c" * 64, _TOP)
    with pytest.raises(codon_probe.PinError, match="nothing unpacked"):
        codon_probe.fetch(pin, tmp_path, lambda _url: _archive())
    assert list(tmp_path.iterdir()) == []


def test_an_archive_that_leaves_its_directory_is_refused_and_writes_nothing_outside(
    tmp_path: Path,
) -> None:
    """A `..` member passes the hash (the pin is of those bytes) but not the extraction filter."""
    data = _archive("../evil")
    cache = tmp_path / "cache"
    with pytest.raises(codon_probe.PinError):
        codon_probe.fetch(_pin(data), cache, lambda _url: data)
    assert not (tmp_path / "evil").exists()
    assert not (cache / _pin(data).sha256).exists()


def _tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    mtools = tmp_path / "mtools"
    mtools.mkdir()
    (mtools / "MODULE.bazel").write_text(_MODULE, encoding="utf-8")
    probe = tmp_path / "probe.py"
    probe.write_text("print(1)\n", encoding="utf-8")
    return mtools, tmp_path / "cache", probe


def test_main_runs_the_cached_compiler_on_the_file_and_passes_its_status_through(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The compiler's output and exit code are the tool's own."""
    mtools, cache, probe = _tree(tmp_path)
    binary = cache / codon_probe.read_pin(_MODULE).sha256 / "bin" / "codon"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(_BIN)
    seen: list[Sequence[str]] = []

    def runner(argv: Sequence[str]) -> tuple[int, str]:
        seen.append(argv)
        return _BAD_EXIT, "error: nope\n"

    argv = [str(probe), "--mtools", str(mtools), "--cache", str(cache)]
    assert codon_probe.main(argv, lambda _url: _archive(), runner) == _BAD_EXIT
    assert seen == [[str(binary), "run", str(probe)]]
    assert capsys.readouterr().out == "error: nope\n"


def test_main_refuses_a_download_that_is_not_the_pinned_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The pin in MODULE.bazel is `b`*64, so any archive hashes wrong and the tool refuses."""
    mtools, cache, probe = _tree(tmp_path)
    argv = [str(probe), "--mtools", str(mtools), "--cache", str(cache)]
    assert codon_probe.main(argv, lambda _url: _archive()) == codon_probe.EXIT_REFUSED
    assert "nothing unpacked" in capsys.readouterr().err


def test_main_without_exactly_one_existing_file_is_a_usage_error(tmp_path: Path) -> None:
    """No file, two files and a missing file are each exit 2."""
    present = tmp_path / "a.py"
    present.write_text("", encoding="utf-8")
    assert codon_probe.main([]) == codon_probe.EXIT_USAGE
    assert codon_probe.main([str(present), str(present)]) == codon_probe.EXIT_USAGE
    assert codon_probe.main([str(tmp_path / "missing.py")]) == codon_probe.EXIT_USAGE
