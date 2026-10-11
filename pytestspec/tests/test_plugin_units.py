# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Unit witnesses for the plugin's file claim, data paths, differential counter and xdist merge.

W1012. ⚑ THESE WERE ONLY REACHED THROUGH A WHOLE PYTEST SESSION (one inner `-n 2` run for the
merge), so a declared defect in each could survive: a forwarded report counted twice, a worker
tally summed where a declaration is taken once, a missing data path accepted. A stand-in config
and plugin manager drive each branch directly.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

import pytest

from mikemol.pytestspec import outcomes, plugin
from mikemol.pytestspec.spec import DO_NOT_PORT, SpecDataError

_SPEC = "s.rego"
_NODE = "s.rego::case"
_WORKER_KEY = "pytestspec-tally"
_NO_KEYWORDS: Mapping[str, object] = {}
_TWO = 2
_THREE = 3
_FIVE = 5
_SEVEN = 7


class _Manager:
    """The plugin manager as `pytest_configure` uses it: it registers, and it knows xdist."""

    def __init__(self, *, xdist: bool) -> None:
        self.xdist = xdist
        self.registered: dict[str, object] = {}

    def hasplugin(self, name: str) -> bool:
        """Say whether a plugin is loaded.

        Returns:
            True only for xdist, and only when this session has it.

        """
        return self.xdist and name == "xdist"

    def register(self, obj: object, name: str) -> None:
        """Remember what was registered under a name."""
        self.registered[name] = obj


class _Config:
    """The parts of `pytest.Config` the plugin reads: options, ini, stash and the manager."""

    def __init__(
        self,
        *,
        options: dict[str, object] | None = None,
        ini: dict[str, object] | None = None,
        xdist: bool = False,
    ) -> None:
        self.options = options or {}
        self.ini = ini or {}
        self.stash = pytest.Stash()
        self.pluginmanager = _Manager(xdist=xdist)
        self.workeroutput: object = None

    def getoption(self, name: str) -> object:
        """Answer an option.

        Returns:
            the stored value, or None.

        """
        return self.options.get(name)

    def getini(self, name: str) -> object:
        """Answer an ini key.

        Returns:
            the stored value, or None.

        """
        return self.ini.get(name)


class _Counting(Protocol):
    """The differential counter's hooks."""

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Count one report."""

    def pytest_sessionfinish(self) -> None:
        """Hand a worker's tallies over."""

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print the differential lines."""


class _Merging(Protocol):
    """The xdist merge's hook."""

    def pytest_testnodedown(self, node: object) -> None:
        """Merge one worker."""


class _Writer:
    """A terminal reporter that keeps the lines written to it."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_line(self, line: str) -> None:
        """Keep a line."""
        self.lines.append(line)


@dataclass
class _Node:
    """An xdist worker node, carrying what the worker handed over."""

    workeroutput: object


class _Forwarded(pytest.TestReport):
    """A report an xdist worker forwarded: it carries the `node` it came from."""

    node = "gw0"


def _as(config: _Config) -> pytest.Config:
    """Type the stand-in as the real thing.

    Returns:
        the same object.

    """
    return cast("pytest.Config", config)


def _configured(*, xdist: bool = False, **options: object) -> _Config:
    """Build a config and run `pytest_configure` on it.

    Returns:
        the configured stand-in, with the plugin objects registered on its manager.

    """
    config = _Config(options=dict(options), xdist=xdist)
    plugin.pytest_configure(_as(config))
    return config


def _counting(config: _Config) -> _Counting:
    """Find the differential counter `pytest_configure` registered.

    Returns:
        it, typed by its hooks.

    """
    return cast("_Counting", config.pluginmanager.registered["pytestspec-differential"])


def _merging(config: _Config) -> _Merging:
    """Find the xdist merge `pytest_configure` registered.

    Returns:
        it, typed by its hook.

    """
    return cast("_Merging", config.pluginmanager.registered["pytestspec-xdist-merge"])


def _open(config: _Config, *specs: str) -> dict[str, dict[str, int]]:
    """Open an all-zero tally for each spec.

    Returns:
        the tallies, which the stash holds by reference.

    """
    tallies = {spec: dict.fromkeys(plugin.COLUMNS, 0) for spec in specs}
    config.stash[plugin.TALLY] = tallies
    return tallies


def _report(
    when: Literal["setup", "call", "teardown"],
    outcome: Literal["passed", "failed", "skipped"],
    props: list[tuple[str, object]] | None = None,
) -> pytest.TestReport:
    """Build a report for `_NODE`.

    Returns:
        the report.

    """
    where = (_SPEC, 0, "c")
    return pytest.TestReport(_NODE, where, _NO_KEYWORDS, outcome, None, when, user_properties=props)


# --- which files are specs ---------------------------------------------------------------------


def test_a_rego_file_is_a_spec() -> None:
    """A `.rego` file is collected as a spec."""
    assert plugin.claims(Path("a.rego"))


@pytest.mark.parametrize("name", ["a_test.rego", "a.py", "rego"])
def test_opas_own_test_files_and_other_files_are_not_specs(name: str) -> None:
    """A `_test.rego` is opa's unit test of a spec, and anything not `.rego` is not a spec."""
    assert not plugin.claims(Path(name))


# --- the declared data paths -------------------------------------------------------------------


def test_data_paths_are_the_declared_paths_and_skip_what_is_not_a_path(tmp_path: Path) -> None:
    """Only a Path entry of the ini list is a data path; a string entry is dropped."""
    config = _Config(ini={plugin.DATA_INI: [tmp_path, "text"]})
    assert plugin.data_paths(_as(config)) == (tmp_path,)


def test_no_declared_data_is_no_data_paths() -> None:
    """An ini key that is unset or not a list declares nothing."""
    assert plugin.data_paths(_as(_Config())) == ()
    assert plugin.data_paths(_as(_Config(ini={plugin.DATA_INI: "text"}))) == ()


def test_a_declared_path_that_does_not_exist_is_refused_and_named(tmp_path: Path) -> None:
    """A missing library is an error naming every missing path, not a silent skip."""
    config = _Config(ini={plugin.DATA_INI: [tmp_path / "x", tmp_path, tmp_path / "y"]})
    with pytest.raises(SpecDataError) as info:
        plugin.data_paths(_as(config))
    assert str(info.value).endswith(f"does not exist: {tmp_path / 'x'}, {tmp_path / 'y'}")


# --- registration ------------------------------------------------------------------------------


def test_the_differential_counter_is_always_registered_and_the_merge_only_under_xdist() -> None:
    """The xdist merge implements a hook only xdist declares, so it is registered only with it."""
    alone = _configured()
    assert sorted(alone.pluginmanager.registered) == ["pytestspec-differential"]
    both = _configured(xdist=True)
    assert sorted(both.pluginmanager.registered) == [
        "pytestspec-differential",
        "pytestspec-xdist-merge",
    ]


# --- the differential counter ------------------------------------------------------------------


def test_a_call_report_is_counted_under_the_column_it_recorded() -> None:
    """The call recorded its column; the report is counted there, once."""
    config = _configured()
    tallies = _open(config, _SPEC)
    props: list[tuple[str, object]] = [(plugin.OUTCOME, outcomes.REFUSED)]
    _counting(config).pytest_runtest_logreport(_report("call", "passed", props))
    assert tallies[_SPEC][outcomes.REFUSED] == 1
    assert sum(tallies[_SPEC].values()) == 1


def test_a_passing_setup_or_teardown_decides_nothing() -> None:
    """Only a call, or a phase that failed, is an outcome."""
    config = _configured()
    tallies = _open(config, _SPEC)
    _counting(config).pytest_runtest_logreport(_report("setup", "passed"))
    _counting(config).pytest_runtest_logreport(_report("teardown", "passed"))
    assert not any(tallies[_SPEC].values())


def test_a_failed_setup_is_unmeasured_whatever_it_carries() -> None:
    """A setup error never reached a verdict, so it ignores a column its properties name."""
    config = _configured()
    tallies = _open(config, _SPEC)
    props: list[tuple[str, object]] = [(plugin.OUTCOME, outcomes.ADMITTED)]
    _counting(config).pytest_runtest_logreport(_report("setup", "failed", props))
    assert tallies[_SPEC][outcomes.UNMEASURED_COLUMN] == 1
    assert tallies[_SPEC][outcomes.ADMITTED] == 0


@pytest.mark.parametrize("props", [None, [(plugin.OUTCOME, _FIVE)]])
def test_a_call_with_no_usable_column_is_unmeasured(props: list[tuple[str, object]] | None) -> None:
    """A call that recorded no column, or a column that is no string, measured nothing."""
    config = _configured()
    tallies = _open(config, _SPEC)
    _counting(config).pytest_runtest_logreport(_report("call", "failed", props))
    assert tallies[_SPEC][outcomes.UNMEASURED_COLUMN] == 1


def test_a_forwarded_report_is_not_counted_again() -> None:
    """The worker counted it and hands its tally over, so the controller does not."""
    config = _configured()
    tallies = _open(config, _SPEC)
    props: list[tuple[str, object]] = [(plugin.OUTCOME, outcomes.ADMITTED)]
    where = (_SPEC, 0, "c")
    forwarded = _Forwarded(
        _NODE, where, _NO_KEYWORDS, "passed", None, "call", user_properties=props
    )
    _counting(config).pytest_runtest_logreport(forwarded)
    assert not any(tallies[_SPEC].values())


def test_a_report_for_no_spec_is_ignored() -> None:
    """A node that is not under a spec with an open tally counts nowhere and does not raise."""
    config = _configured()
    tallies = _open(config, "other.rego")
    _counting(config).pytest_runtest_logreport(_report("call", "failed"))
    assert not any(tallies["other.rego"].values())


def test_a_worker_hands_over_a_copy_of_its_tallies() -> None:
    """The handed-over tally is a snapshot: later counting does not reach into it."""
    config = _configured()
    tallies = _open(config, _SPEC)
    tallies[_SPEC][outcomes.ADMITTED] = _THREE
    config.workeroutput = {}
    _counting(config).pytest_sessionfinish()
    tallies[_SPEC][outcomes.ADMITTED] = _SEVEN
    handed = cast("dict[str, dict[str, dict[str, int]]]", config.workeroutput)[_WORKER_KEY]
    assert handed[_SPEC][outcomes.ADMITTED] == _THREE


def test_a_session_that_is_no_worker_hands_nothing_over() -> None:
    """With no worker output to write into, finishing the session does nothing."""
    config = _configured()
    _open(config, _SPEC)
    config.workeroutput = ["not", "a", "dict"]
    _counting(config).pytest_sessionfinish()
    assert config.workeroutput == ["not", "a", "dict"]


def test_the_differential_line_is_one_row_per_spec_in_name_order() -> None:
    """Every column is printed, specs sorted, under the chosen implementation or as-written."""
    config = _configured(impl="port")
    _open(config, "b.rego", "a.rego")
    writer = _Writer()
    _counting(config).pytest_terminal_summary(cast("pytest.TerminalReporter", writer))
    zeros = " ".join(f"{column}=0" for column in plugin.COLUMNS)
    assert writer.lines == [
        f"pytestspec: a.rego impl=port {zeros}",
        f"pytestspec: b.rego impl=port {zeros}",
    ]
    bare = _configured()
    _open(bare, "a.rego")
    plain = _Writer()
    _counting(bare).pytest_terminal_summary(cast("pytest.TerminalReporter", plain))
    assert plain.lines == [f"pytestspec: a.rego impl=as-written {zeros}"]


# --- the xdist merge ---------------------------------------------------------------------------


def _worker(**counts: int) -> _Node:
    """Build a worker node whose output carries one spec's tally.

    Returns:
        the node.

    """
    return _Node({_WORKER_KEY: {_SPEC: dict(counts)}})


def test_declarations_are_taken_once_and_outcomes_are_summed_across_workers() -> None:
    """Each worker collected every declaration, but a case ran on one worker only."""
    config = _configured(xdist=True)
    merge = _merging(config)
    first = _worker(**{DO_NOT_PORT: 2, plugin.CACHED: 1, outcomes.ADMITTED: 3})
    second = _worker(**{DO_NOT_PORT: 2, plugin.CACHED: 4, outcomes.ADMITTED: 4})
    merge.pytest_testnodedown(first)
    merge.pytest_testnodedown(second)
    merged = config.stash[plugin.TALLY][_SPEC]
    assert merged[DO_NOT_PORT] == _TWO
    assert merged[plugin.CACHED] == _FIVE
    assert merged[outcomes.ADMITTED] == _SEVEN


def test_a_column_a_worker_did_not_report_adds_nothing() -> None:
    """A worker's tally may omit a column; the missing one counts as zero, not as an error."""
    config = _configured(xdist=True)
    _merging(config).pytest_testnodedown(_worker(**{outcomes.ADMITTED: 1}))
    merged = config.stash[plugin.TALLY][_SPEC]
    assert merged[outcomes.ADMITTED] == 1
    assert merged[DO_NOT_PORT] == 0


@pytest.mark.parametrize("output", [None, [1], {}, {_WORKER_KEY: "text"}])
def test_a_worker_that_handed_over_no_tally_merges_nothing(output: object) -> None:
    """No output, output that is no object, or a tally that is no object leaves the merge alone."""
    config = _configured(xdist=True)
    _merging(config).pytest_testnodedown(_Node(output))
    assert plugin.TALLY not in config.stash or not config.stash[plugin.TALLY]
