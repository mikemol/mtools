# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""opa is accepted only at the pinned version, and no unreadable case admits it (W1845).

⚑ EVERY WAY OF NOT KNOWING THE VERSION IS A REFUSAL: absent, failing to run, printing no version,
printing two, and printing another one all give None.
"""

from pathlib import Path

from mikemol.waldo import planopa

_OPA = Path("/usr/bin/opa")
_PIN = "1.20.2"


class _Done:
    def __init__(self, code: int, out: str) -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = ""


class _Fake:
    # A Tools: finds opa when told to, answers every run with a fixed reply and records the calls.
    def __init__(self, found: Path | None, code: int, out: str) -> None:
        self._found = found
        self._reply = _Done(code, out)
        self.calls: list[tuple[Path, tuple[str, ...], Path | None, str | None]] = []

    def find(self, name: str) -> Path | None:
        return self._found if name == "opa" else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool, args, cwd, stdin_text))
        return self._reply

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        self.calls.append((tool, (*args, str(cpu_seconds)), cwd, None))
        return self._reply


def _says(version: str) -> str:
    return f"Version: {version}\nBuild Commit: abc\nGo Version: go1.22\n"


def test_the_version_is_the_one_labelled_line() -> None:
    """One 'Version:' line is read, a failure or an ambiguous output is None."""
    assert planopa.parse_version(0, _says(_PIN)) == _PIN
    assert planopa.parse_version(1, _says(_PIN)) is None
    assert planopa.parse_version(0, "no label here\n") is None
    assert planopa.parse_version(0, _says("1") + _says("2")) is None


def test_opa_at_the_pin_is_accepted_after_asking_it_for_its_version() -> None:
    """The control: the found binary at the pinned version is returned, having run `version`."""
    fake = _Fake(_OPA, 0, _says(_PIN))
    assert planopa.pinned_opa(fake, _PIN) == _OPA
    assert fake.calls == [(_OPA, ("version",), None, None)]


def test_opa_at_another_version_or_unreadable_or_absent_is_refused() -> None:
    """A different checker is not the pinned one, and a binary that cannot say is not admitted."""
    assert planopa.pinned_opa(_Fake(_OPA, 0, _says("1.20.3")), _PIN) is None
    assert planopa.pinned_opa(_Fake(_OPA, 2, ""), _PIN) is None
    assert planopa.pinned_opa(_Fake(None, 0, _says(_PIN)), _PIN) is None


def test_an_absent_opa_is_never_run() -> None:
    """Nothing to ask: a missing binary is refused before any child starts."""
    fake = _Fake(None, 0, _says(_PIN))
    assert planopa.pinned_opa(fake, _PIN) is None
    assert not fake.calls


def test_the_pin_is_the_callers_not_luthens() -> None:
    """A consumer pinning another number gets that number accepted and luthen's refused."""
    other = _Fake(_OPA, 0, _says("1.21.0"))
    assert planopa.pinned_opa(other, "1.21.0") == _OPA
    assert planopa.pinned_opa(other, _PIN) is None
