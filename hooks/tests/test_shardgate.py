# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack touching a grid past half of its CPU budget is refused with the shard count (W1602)."""

from pathlib import Path

from mikemol.hooks import commit_span, shardgate

_BUILD_300 = 'mutants_sharded(\n    name = "mutants",\n    shards = 80,\n    cpu_budget = 300,\n)\n'
_BUILD_900 = 'mutants_sharded(\n    name = "mutants",\n    shards = 36,\n    cpu_budget = 900,\n)\n'
_SAMPLE = '{"metric": {"__name__": "x", "target": "%s"}, "value": [1792570961, "%s"]}\n'
_STACK = '[{"waypoint": "W1", "subject": "s", "paths": ["hooks/src/a.py", "docs/x.txt"]}]'
_ENV = {commit_span.BIN_ENV: "/opt/mikemol-otlp", commit_span.ENDPOINTS_ENV: "/host/e.json"}
_HALF_OVER = 188.1
_SHARDS_NOW = 80
_SLIGHTLY_OVER = 151.0
_SAMPLED = 2000.0
_BUILD_BEFORE = 1000.0
_BUILD_AFTER = 3000.0


def _text(dist: str) -> str | None:
    return {"hooks": _BUILD_300, "pathsforward": _BUILD_900}.get(dist)


def _old_build(_dist: str) -> float | None:
    return _BUILD_BEFORE


def _new_build(_dist: str) -> float | None:
    return _BUILD_AFTER


def _unknown_build(_dist: str) -> float | None:
    return None


def test_the_readings_join_the_cpu_samples_to_their_times_and_drop_a_target_with_no_time() -> None:
    """A sample line gives target and value; a target with no time is left out; junk is skipped."""
    cpu = _SAMPLE % ("//hooks:mutants_19", "188.1") + _SAMPLE % ("//hooks:mutants_2", "9") + "x\n"
    when = _SAMPLE % ("//hooks:mutants_19", "2000") + "{}\n"
    assert shardgate.readings(cpu, when) == {"//hooks:mutants_19": (_HALF_OVER, _SAMPLED)}


def test_a_shard_past_half_of_the_budget_names_the_dist_and_a_shard_count() -> None:
    """188.1 of 300 is 63%: with 80 shards, ceil(80 * 188.1 / (0.4 * 300)) = 126."""
    read = {"//hooks:mutants_19": (_HALF_OVER, _SAMPLED)}
    got = shardgate.findings(read, {"hooks"}, (_text, _old_build))
    assert len(got) == 1
    assert "//hooks:mutants_19 used 188 CPU s of 300 (63%)" in got[0]
    assert "set shards = 126 (now 80) in hooks/BUILD.bazel" in got[0]


def test_a_reading_older_than_the_build_files_last_change_is_not_judged() -> None:
    """The reshard landed after that sample, so it describes a grid that is gone."""
    read = {"//hooks:mutants_19": (_HALF_OVER, _SAMPLED)}
    assert not shardgate.findings(read, {"hooks"}, (_text, _new_build))


def test_a_build_file_with_no_known_change_time_still_judges_the_reading() -> None:
    """No git answer for the file is not a reason to wave the reading through."""
    read = {"//hooks:mutants_19": (_HALF_OVER, _SAMPLED)}
    assert shardgate.findings(read, {"hooks"}, (_text, _unknown_build))


def test_a_shard_under_half_or_in_an_untouched_dist_is_not_named() -> None:
    """The controls: pathsforward's 315 of 900 is 35%, and an untouched dist is not judged."""
    read = {
        "//pathsforward:mutants_14": (314.8, _SAMPLED),
        "//hooks:mutants_19": (_HALF_OVER, _SAMPLED),
    }
    assert not shardgate.findings(read, {"pathsforward"}, (_text, _old_build))
    assert not shardgate.findings(read, {"fence"}, (_text, _old_build))


def test_a_dist_with_no_budget_or_no_build_file_is_not_judged() -> None:
    """No `cpu_budget` to compare with is not a verdict."""
    read = {"//hooks:mutants_19": (_HALF_OVER, _SAMPLED)}
    assert not shardgate.findings(read, {"hooks"}, (lambda _d: "", _old_build))
    assert not shardgate.findings(read, {"hooks"}, (lambda _d: None, _old_build))


def test_the_proposal_is_always_at_least_one_more_shard() -> None:
    """A small overshoot still adds a shard to the 80 there are."""
    read = {"//hooks:mutants_1": (_SLIGHTLY_OVER, _SAMPLED)}
    got = shardgate.findings(read, {"hooks"}, (_text, _old_build))
    proposed = int(got[0].split("set shards = ")[1].split(" ")[0])
    assert proposed > _SHARDS_NOW


def _stack(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "BUILD.bazel").write_text(_BUILD_300, encoding="utf-8")
    stack = tmp_path / "stack.json"
    stack.write_text(_STACK, encoding="utf-8")
    return root, stack


def _store(argv: list[str], _cwd: Path) -> tuple[int, str]:
    # The store answers the value query and the time query; git answers the file's change time.
    if argv[0] == "git":
        return 0, f"{int(_BUILD_BEFORE)}\n"
    when = "tlast_over_time" in argv[-1]
    return 0, _SAMPLE % ("//hooks:mutants_19", "2000" if when else "188.1")


def test_a_stack_touching_the_slow_grid_is_refused_with_the_findings(tmp_path: Path) -> None:
    """The store answers a current past-half shard of hooks, and the stack changes a hooks file."""
    root, stack = _stack(tmp_path)
    said = shardgate.refusal(root, stack, _ENV, _store)
    assert said is not None
    assert "set shards = 126" in said


def test_nothing_readable_refuses_nothing(tmp_path: Path) -> None:
    """A store that fails, no store at all and no stack all give no refusal."""
    root, stack = _stack(tmp_path)

    def failing(_argv: list[str], _cwd: Path) -> tuple[int, str]:
        return 1, ""

    assert shardgate.refusal(root, stack, _ENV, failing) is None
    assert shardgate.refusal(root, stack, {commit_span.BIN_ENV: "/opt/x"}, failing) is None
    assert shardgate.refusal(root, tmp_path / "absent.json", _ENV, failing) is None
