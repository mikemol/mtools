# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack touching a grid past half of its CPU budget is refused naming the unit, never a count."""

from pathlib import Path

from mikemol.hooks import commit_span, shardgate, stacksnap
from mikemol.hooks.stackfreeze import SNAP_ENV

_BUILD_300 = 'mutants_sharded(\n    name = "mutants",\n    shards = 80,\n    cpu_budget = 300,\n)\n'
_BUILD_900 = 'mutants_sharded(\n    name = "mutants",\n    shards = 36,\n    cpu_budget = 900,\n)\n'
_SAMPLE = '{"metric": {"__name__": "x", "target": "%s"}, "value": [1792570961, "%s"]}\n'
_CELL = '{"metric": {"__name__": "x", "target": "%s", "cell": "%s"}, "value": [1792570961, "%s"]}\n'
_STACK = '[{"waypoint": "W1", "subject": "s", "paths": ["hooks/src/a.py", "docs/x.txt"]}]'
_ENV = {commit_span.BIN_ENV: "/opt/mikemol-otlp", commit_span.ENDPOINTS_ENV: "/host/e.json"}
_HALF_OVER = 188.1
_SAMPLED = 2000.0
_BUILD_BEFORE = 1000.0
_BUILD_AFTER = 3000.0
_SHARD = "//hooks:mutants_19"
_FOUR_MODULES = {
    "src/a.py::f": 60.0,
    "src/a.py::g": 40.0,
    "src/b.py::h": 50.0,
    "src/c.py::i": 20.0,
    "src/d.py::j": 18.1,
}
_ONE_HUGE = {"src/a.py::big": 160.0, "src/b.py::x": 28.1}
_REGULAR = "100644"
_BLOB = "b" * 40
_FAILED = (1, "")


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
    cpu = _SAMPLE % (_SHARD, "188.1") + _SAMPLE % ("//hooks:mutants_2", "9") + "x\n"
    when = _SAMPLE % (_SHARD, "2000") + "{}\n"
    assert shardgate.readings(cpu, when) == {_SHARD: (_HALF_OVER, _SAMPLED)}


def test_the_cell_samples_group_by_shard_and_cell_and_skip_a_line_with_no_cell() -> None:
    """W2804: a cell line has the shard and the stable cell id; a shard-only line is no cell."""
    text = _CELL % (_SHARD, "src/a.py::f", "60") + _CELL % (_SHARD, "src/b.py::h", "50")
    text += _SAMPLE % (_SHARD, "188.1") + "junk\n"
    assert shardgate.cell_samples(text) == {_SHARD: {"src/a.py::f": 60.0, "src/b.py::h": 50.0}}


def test_a_shard_past_half_names_the_modules_and_their_cpu_and_no_shard_count() -> None:
    """W2804: 188.1 of 300 is 63%: the line lists the modules by summed CPU and the top cell."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    got = shardgate.findings(read, {"hooks"}, (_text, _old_build), {_SHARD: _FOUR_MODULES})
    assert len(got) == 1
    assert "//hooks:mutants_19 used 188 CPU s of 300 (63%)" in got[0]
    assert "its 5 cells span 4 module(s) (src/a.py 100 s, src/b.py 50 s," in got[0]
    assert "the heaviest cell is src/a.py::f at 60 s" in got[0]
    assert "set shards" not in got[0]
    assert "INDIVISIBLE" not in got[0]


def test_a_cell_alone_past_half_the_budget_is_named_indivisible() -> None:
    """A single 160 s cell of a 300 s budget cannot be helped by any decomposition of targets."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    got = shardgate.findings(read, {"hooks"}, (_text, _old_build), {_SHARD: _ONE_HUGE})
    assert "src/a.py::big alone used 160 CPU s: INDIVISIBLE, its source is what splits" in got[0]


def test_no_per_cell_reading_is_a_named_absence_and_still_no_count() -> None:
    """The first gate after the series exists has no cells: the line says so, never a guess."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    got = shardgate.findings(read, {"hooks"}, (_text, _old_build))
    assert "no per-cell reading of this shard is in the store" in got[0]
    assert "set shards" not in got[0]
    other = shardgate.findings(read, {"hooks"}, (_text, _old_build), {"//hooks:mutants_3": {}})
    assert "no per-cell reading of this shard is in the store" in other[0]


def test_a_reading_older_than_the_build_files_last_change_is_not_judged() -> None:
    """The reshard landed after that sample, so it describes a grid that is gone."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    assert not shardgate.findings(read, {"hooks"}, (_text, _new_build))


def test_a_build_file_with_no_known_change_time_still_judges_the_reading() -> None:
    """No git answer for the file is not a reason to wave the reading through."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    assert shardgate.findings(read, {"hooks"}, (_text, _unknown_build))


def test_a_shard_under_half_or_in_an_untouched_dist_is_not_named() -> None:
    """The controls: pathsforward's 315 of 900 is 35%, and an untouched dist is not judged."""
    read = {
        "//pathsforward:mutants_14": (314.8, _SAMPLED),
        _SHARD: (_HALF_OVER, _SAMPLED),
    }
    assert not shardgate.findings(read, {"pathsforward"}, (_text, _old_build))
    assert not shardgate.findings(read, {"fence"}, (_text, _old_build))


def test_a_dist_with_no_budget_or_no_build_file_is_not_judged() -> None:
    """No `cpu_budget` to compare with is not a verdict."""
    read = {_SHARD: (_HALF_OVER, _SAMPLED)}
    assert not shardgate.findings(read, {"hooks"}, (lambda _d: "", _old_build))
    assert not shardgate.findings(read, {"hooks"}, (lambda _d: None, _old_build))


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
    return 0, _SAMPLE % (_SHARD, "2000" if when else "188.1")


def test_a_stack_touching_the_slow_grid_is_refused_with_the_unit(tmp_path: Path) -> None:
    """The store answers a current past-half shard of hooks, and the stack changes a hooks file."""
    root, stack = _stack(tmp_path)
    said = shardgate.refusal(root, stack, _ENV, _store)
    assert said is not None
    assert "not to be raised" in said
    assert "no per-cell reading" in said
    assert "set shards" not in said


def _stack_of(tmp_path: Path, *paths: str) -> Path:
    listed = ", ".join(f'"{path}"' for path in paths)
    body = f'[{{"waypoint": "W1", "subject": "s", "paths": [{listed}]}}]'
    stack = tmp_path / "other-stack.json"
    stack.write_text(body, encoding="utf-8")
    return stack


def test_a_stack_that_carries_the_dists_build_file_is_the_repair_not_refused(
    tmp_path: Path,
) -> None:
    """The reading is of the committed grid and the shard count of the changed tree: not judged."""
    root, _ = _stack(tmp_path)
    repair = _stack_of(tmp_path, "hooks/src/a.py", "hooks/BUILD.bazel")
    assert shardgate.refusal(root, repair, _ENV, _store) is None


def test_another_dists_build_file_does_not_excuse_the_slow_grid(tmp_path: Path) -> None:
    """The control: carrying pathsforward's BUILD file leaves hooks judged, and refused."""
    root, _ = _stack(tmp_path)
    other = _stack_of(tmp_path, "hooks/src/a.py", "pathsforward/BUILD.bazel")
    said = shardgate.refusal(root, other, _ENV, _store)
    assert said is not None
    assert "hooks/BUILD.bazel" in said


def test_a_failed_store_query_refuses_nothing_even_when_it_printed_a_reading(
    tmp_path: Path,
) -> None:
    """W2811: a nonzero status is the answer, whatever the text says; the same text at 0 refuses."""
    root, stack = _stack(tmp_path)

    def failed(argv: list[str], cwd: Path) -> tuple[int, str]:
        status, text = _store(argv, cwd)
        return (status if argv[0] == "git" else 1), text

    assert shardgate.refusal(root, stack, _ENV, _store) is not None
    assert shardgate.refusal(root, stack, _ENV, failed) is None


def test_nothing_readable_refuses_nothing(tmp_path: Path) -> None:
    """A store that fails, no store at all and no stack all give no refusal."""
    root, stack = _stack(tmp_path)

    def failing(_argv: list[str], _cwd: Path) -> tuple[int, str]:
        return 1, ""

    assert shardgate.refusal(root, stack, _ENV, failing) is None
    assert shardgate.refusal(root, stack, {commit_span.BIN_ENV: "/opt/x"}, failing) is None
    assert shardgate.refusal(root, tmp_path / "absent.json", _ENV, failing) is None


def _build_with(shards: int | None) -> str:
    count = "" if shards is None else f"    shards = {shards},\n"
    return f'mutants_sharded(\n    name = "mutants",\n{count}    cpu_budget = 300,\n)\n'


def _frozen_env(tmp_path: Path, *paths: str) -> dict[str, str]:
    snap = tmp_path / "snapshot.json"
    stacksnap.dump(snap, [[stacksnap.Frozen(path, _REGULAR, _BLOB) for path in paths]])
    return {SNAP_ENV: str(snap)}


def _git_answering(old: str | None, new: str | None) -> shardgate.Run:
    # HEAD's BUILD text (`git show`) and the frozen blob's (`git cat-file blob`), or a failure.
    def run(argv: list[str], _cwd: Path) -> tuple[int, str]:
        if argv[:2] == ["git", "show"]:
            return _FAILED if old is None else (0, old)
        if argv[:3] == ["git", "cat-file", "blob"]:
            return _FAILED if new is None else (0, new)
        return _FAILED

    return run


def test_a_raise_of_shards_is_refused_even_when_the_stack_carries_the_build_file(
    tmp_path: Path,
) -> None:
    """W2804: 80 to 126 in hooks/BUILD.bazel is refused from the snapshot and git alone."""
    root, _ = _stack(tmp_path)
    stack = _stack_of(tmp_path, "hooks/BUILD.bazel")
    env = _frozen_env(tmp_path, "hooks/BUILD.bazel")
    run = _git_answering(_build_with(80), _build_with(126))
    said = shardgate.refusal(root, stack, env, run)
    assert said is not None
    assert "hooks/BUILD.bazel raises shards of mutants from 80 to 126" in said
    assert "a shards value is never raised" in said


def test_a_lower_a_deleted_an_unchanged_or_a_new_shards_value_is_admitted(
    tmp_path: Path,
) -> None:
    """The ratchet only refuses a rise: 80 to 40, no value at all, 80 to 80, no HEAD file."""
    root, _ = _stack(tmp_path)
    stack = _stack_of(tmp_path, "hooks/BUILD.bazel")
    env = _frozen_env(tmp_path, "hooks/BUILD.bazel")
    old = _build_with(80)
    lower = _git_answering(old, _build_with(40))
    deleted = _git_answering(old, _build_with(None))
    unchanged = _git_answering(old, old)
    new_file = _git_answering(None, _build_with(80))
    for run in (lower, deleted, unchanged, new_file):
        assert shardgate.refusal(root, stack, env, run) is None


def test_a_raise_names_the_dist_it_is_in_and_a_file_not_frozen_is_not_judged(
    tmp_path: Path,
) -> None:
    """Another dist's raise is named by that dist; a BUILD path with no frozen bytes is skipped."""
    root, _ = _stack(tmp_path)
    stack = _stack_of(tmp_path, "pathsforward/BUILD.bazel", "fence/BUILD.bazel")
    env = _frozen_env(tmp_path, "pathsforward/BUILD.bazel")
    run = _git_answering(_build_with(36), _build_with(48))
    said = shardgate.refusal(root, stack, env, run)
    assert said is not None
    assert "pathsforward/BUILD.bazel raises shards of mutants from 36 to 48" in said
    assert "fence" not in said


def _build_of(counts: dict[str, int]) -> str:
    # One sharded rule per name, in the order given, with a comment that must never be read.
    rules = [
        f'mutants_sharded(\n    # shards = 999 in a comment is prose\n    name = "{name}",\n'
        f'    shards = {count},\n    srcs = glob(["a(b)"]),\n)\n'
        for name, count in counts.items()
    ]
    return "".join(rules)


def _judged(tmp_path: Path, path: str, old: str | None, new: str | None) -> str | None:
    stack = _stack_of(tmp_path, path)
    return shardgate.refusal(tmp_path, stack, _frozen_env(tmp_path, path), _git_answering(old, new))


def test_a_raise_in_a_nested_build_file_is_refused_too(tmp_path: Path) -> None:
    """W2804 (github-82): the ratchet is on `shards =` anywhere, so a site package is judged."""
    said = _judged(tmp_path, "hooks/sites/x/BUILD.bazel", _build_with(1), _build_with(9))
    assert said is not None
    assert "hooks/sites/x/BUILD.bazel raises shards of mutants from 1 to 9" in said


def test_a_raise_in_the_second_of_two_targets_is_refused_naming_it(tmp_path: Path) -> None:
    """The first match is only one value: audiostruct's BUILD holds two sharded rules."""
    old = _build_of({"mutants": 34, "mutants_gpu": 4})
    new = _build_of({"mutants": 34, "mutants_gpu": 9})
    said = _judged(tmp_path, "audiostruct/BUILD.bazel", old, new)
    assert said is not None
    assert "shards of mutants_gpu from 4 to 9" in said
    assert "shards of mutants from" not in said


def test_a_lowering_of_one_target_does_not_excuse_a_raise_of_another(tmp_path: Path) -> None:
    """Paired by name: 34 to 20 in the first and 4 to 9 in the second still names the second."""
    old = _build_of({"mutants": 34, "mutants_gpu": 4})
    new = _build_of({"mutants": 20, "mutants_gpu": 9})
    said = _judged(tmp_path, "audiostruct/BUILD.bazel", old, new)
    assert said is not None
    assert "shards of mutants_gpu from 4 to 9" in said
    assert "shards of mutants from" not in said


def test_a_new_target_is_admitted_and_a_rename_carries_its_old_value(tmp_path: Path) -> None:
    """A new target has no prior value and a renamed one is its old value: a higher count raises."""
    old = _build_of({"mutants": 34})
    added = _build_of({"mutants": 34, "more": 50})
    assert _judged(tmp_path, "a/BUILD.bazel", old, added) is None
    assert _judged(tmp_path, "a/BUILD.bazel", old, _build_of({"renamed": 34})) is None
    said = _judged(tmp_path, "a/BUILD.bazel", old, _build_of({"renamed": 53}))
    assert said is not None
    assert "shards of renamed from 34 to 53" in said


def test_a_comment_or_a_string_is_never_read_as_a_shards_value(tmp_path: Path) -> None:
    """The comment `shards = 999` and the glob string with a parenthesis change nothing."""
    build = _build_of({"mutants": 7})
    assert shardgate.targets(build) == {"mutants": 7}
    assert _judged(tmp_path, "a/BUILD.bazel", build, build) is None


def _build_expr(expr: str, constant: int | None = None) -> str:
    bound = "" if constant is None else f"SHARDS = {constant}\n"
    return f'{bound}mutants_sharded(\n    name = "mutants",\n    shards = {expr},\n)\n'


def test_a_shards_bound_to_a_top_level_constant_is_judged_by_its_value(tmp_path: Path) -> None:
    """W2804 (github-82): `shards = SHARDS` with `SHARDS = 34` reads 34, a raise is named."""
    old, new = _build_expr("SHARDS", 34), _build_expr("SHARDS", 53)
    assert shardgate.targets(old) == {"mutants": 34}
    said = _judged(tmp_path, "a/BUILD.bazel", old, new)
    assert said is not None
    assert "shards of mutants from 34 to 53" in said
    assert _judged(tmp_path, "a/BUILD.bazel", old, old) is None
    assert _judged(tmp_path, "a/BUILD.bazel", _build_with(34), _build_expr("SHARDS", 20)) is None


def test_a_shards_that_cannot_be_read_is_refused_and_never_admitted(tmp_path: Path) -> None:
    """An expression, an unbound name and a call are unjudgeable: refused by target name."""
    unjudgeable = "shards of mutants is neither an int literal nor a top-level integer constant"
    for expr in ("2 * N", "UNBOUND", "len(X)"):
        said = _judged(tmp_path, "a/BUILD.bazel", _build_with(34), _build_expr(expr))
        assert said is not None
        assert unjudgeable in said
    assert shardgate.targets(_build_expr("2 * N")) == {}
    assert shardgate.parsed_targets(_build_expr("2 * N")) == {"mutants": None}


def test_a_new_target_carries_the_smallest_removed_value_not_the_largest(tmp_path: Path) -> None:
    """Two removed (34 and 10) and one added at 20 could raise the 10: refused, saying so."""
    old = _build_of({"a": 34, "b": 10})
    said = _judged(tmp_path, "a/BUILD.bazel", old, _build_of({"c": 20}))
    assert said is not None
    assert "shards of c from 10 to 20 (carries the smallest removed value)" in said
    assert _judged(tmp_path, "a/BUILD.bazel", old, _build_of({"c": 10})) is None
