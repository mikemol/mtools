# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the pin census as a textfile: the series, the par sha, and the atomic write.

W979. ⚑ THE BEHIND PIN IS THE POSITIVE CONTROL: a 0 for the current pin and the absent series
without a par sha only mean something beside a series that does read 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import repin_cli, repin_metrics

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_OLD = "03749d56d55741840da13d86533e7e8d698e3be8"
_NEW = "6868dd2e0b7f4a9c1d2e3f405162738495a6b7c8"
_REPO = "https://github.com/mikemol/mtools.git"
_PIN = f'dependencies = ["mikemol-hooks @ git+{_REPO}@{{sha}}#subdirectory=hooks"]\n'
_WHEEL = (
    'mikemol-ledger = { path = "vendor/wheels/mikemol_ledger-0.1.0+gc3ca6d2-py3-none-any.whl" }\n'
)
_BEHIND = 'mikemol_repin_behind_par{repo="alpha",dist="hooks"} 1'
_PINS = 3
_CLOCK = 1_700_000_000


def _tree(tmp_path: Path) -> Path:
    for name, body in {
        "alpha": _PIN.format(sha=_OLD),
        "bravo": _PIN.format(sha=_NEW),
        "charlie": _WHEEL,
    }.items():
        (tmp_path / name).mkdir(parents=True)
        (tmp_path / name / "pyproject.toml").write_text(body, encoding="utf-8")
    return tmp_path


def _run(root: Path, out: Path, *extra: str) -> list[str]:
    assert repin_cli.main(["--root", str(root), "--metrics", str(out), *extra]) == 0
    return out.read_text(encoding="utf-8").splitlines()


def test_a_pin_behind_par_reads_one_and_a_current_one_reads_zero(tmp_path: Path) -> None:
    """The control: alpha differs from the par sha, bravo holds it; a wheel is vendored."""
    out = tmp_path / "pins.prom"
    lines = _run(_tree(tmp_path / "tree"), out, "--sha", _NEW)
    assert _BEHIND in lines
    assert 'mikemol_repin_behind_par{repo="bravo",dist="hooks"} 0' in lines
    assert 'mikemol_repin_vendored{repo="charlie",dist="ledger"} 1' in lines
    assert not any(line.startswith('mikemol_repin_behind_par{repo="charlie"') for line in lines)
    assert f'mikemol_repin_par_info{{sha="{_NEW}"}} 1' in lines
    assert f"mikemol_repin_pins {_PINS}" in lines


def test_the_pinned_sha_lives_on_its_own_info_series(tmp_path: Path) -> None:
    """The sha is a label of pin_info only, so a pin moving does not mint a new behind series."""
    out = tmp_path / "pins.prom"
    text = "\n".join(_run(_tree(tmp_path / "tree"), out, "--sha", _NEW))
    info = f'mikemol_repin_pin_info{{repo="alpha",dist="hooks",form="pep508",sha="{_OLD}"}} 1'
    assert info in text
    assert _OLD not in text.replace(info, "")


def test_without_a_par_sha_nothing_is_claimed_behind(tmp_path: Path) -> None:
    """No target means no behind series at all: a 0 would call a pin current against nothing."""
    out = tmp_path / "pins.prom"
    text = "\n".join(_run(_tree(tmp_path / "tree"), out))
    assert "mikemol_repin_behind_par" not in text
    assert "mikemol_repin_par_info" not in text
    assert "mikemol_repin_pin_info" in text


def test_the_par_sha_is_declared_once_in_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The env var stands in for --sha when metrics are asked for, and never makes --write legal."""
    monkeypatch.setenv(repin_cli.PAR_ENV, _NEW)
    out = tmp_path / "pins.prom"
    lines = _run(_tree(tmp_path / "tree"), out)
    assert _BEHIND in lines
    assert repin_cli.main(["--root", str(tmp_path / "tree"), "--write"]) == repin_cli.EXIT_USAGE


def test_a_malformed_par_in_the_environment_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A par that is not a full commit is a usage refusal and no file is written."""
    monkeypatch.setenv(repin_cli.PAR_ENV, "abc")
    out = tmp_path / "pins.prom"
    tree = _tree(tmp_path / "tree")
    assert repin_cli.main(["--root", str(tree), "--metrics", str(out)]) == repin_cli.EXIT_USAGE
    assert not out.exists()


def test_the_census_carries_the_time_it_was_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scan_time_seconds is the run's clock in whole unix seconds, not the file's mtime."""
    monkeypatch.setattr(repin_cli, "_NOW", lambda: _CLOCK + 0.9)
    lines = _run(_tree(tmp_path / "tree"), tmp_path / "pins.prom", "--sha", _NEW)
    assert f"mikemol_repin_scan_time_seconds {_CLOCK}" in lines


def test_a_render_without_a_clock_claims_no_scan_time() -> None:
    """The body is a pure function of its inputs: no clock given, no series."""
    assert "scan_time" not in repin_metrics.render([], "/r", None)
    assert f"scan_time_seconds {_CLOCK}" in repin_metrics.render([], "/r", None, _CLOCK)


def test_label_values_are_escaped() -> None:
    """Backslash, quote and newline cannot break out of a label."""
    row = repin_cli.Row('we"ird\\repo\n', "d", "pep508", _OLD, "DIFFERS")
    text = repin_metrics.render([row], "/r", _NEW)
    assert 'repo="we\\"ird\\\\repo\\n"' in text


def test_publish_leaves_no_temporary_file_and_replaces_the_old_text(tmp_path: Path) -> None:
    """The scraper sees the whole new file or the whole old one, and no sibling is left behind."""
    target = tmp_path / "pins.prom"
    target.write_text("old\n", encoding="utf-8")
    repin_metrics.publish(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"
    assert [p.name for p in tmp_path.iterdir()] == ["pins.prom"]
