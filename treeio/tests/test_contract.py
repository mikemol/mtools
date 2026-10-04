# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `contract`: the stated-intent contract, its refusals, and the entry-point forms."""

from __future__ import annotations

import contextvars
import functools
import os
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.treeio.ambient import AmbientConflictError
from mikemol.treeio.context import INTENT, SNAPSHOT_STATE
from mikemol.treeio.contract import (
    NEAR_MISS_SPELLINGS,
    cli_main,
    guard,
    require_at_entry,
    require_explicit_mutation,
    snapshot_once,
)
from mikemol.treeio.errors import AmbientVocabError, MutationContractError
from mikemol.treeio.gitrun import git
from mikemol.treeio.proc import capture

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_REFUSED = 2
_SHA_LEN = 40
_UNSET = "SUBSTRATE_EXPLICIT_MUTATION"


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, in a genuinely fresh context.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def _isolate(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Give git a fixed identity and no inherited repository; leave the switch at its default."""
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.delenv(_UNSET, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(root.parent))
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def _repo(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `root` a repository with one commit, and stand the process in it."""
    _isolate(monkeypatch, root)
    git(root, "init", "-q")
    (root / "a.txt").write_text("one", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "c")
    monkeypatch.chdir(root)


def _refusal(fn: Callable[[], object]) -> str:
    """Run `fn` and report the contract refusal it raised.

    Returns:
        The refusal text, or NO RAISE when nothing was raised.

    """
    try:
        fn()
    except MutationContractError as e:
        return str(e)
    return "NO RAISE"


def _near_miss_refusal(spelling: str) -> str:
    """Report the refusal for an invocation that stated only a near-miss spelling.

    Returns:
        The refusal text.

    """
    return _refusal(lambda: require_explicit_mutation("t", ["t", spelling]))


def _child(code: str, *, strict: str | None = None) -> tuple[int, str, str]:
    """Run a snippet in a fresh interpreter at the real default of the off-switch.

    Returns:
        The exit status, stdout and stderr of the child.

    """
    env = {k: v for k, v in os.environ.items() if k != _UNSET}
    # The child finds this package where the parent did, with no path edited in either process.
    env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    if strict is not None:
        env[_UNSET] = strict
    done = capture([sys.executable, "-c", code], env=env)
    return done.returncode, done.stdout, done.stderr


def test_apply_alone_satisfies_the_contract_and_becomes_the_ambient_intent() -> None:
    """The statement is read once from argv and every frame below asks the context."""

    def run() -> tuple[str | None, str | None, str | None]:
        verdict = require_explicit_mutation("selftest", ["t", "--apply"])
        return verdict, INTENT.get(), INTENT.origin()

    assert _fresh(run) == (None, "apply", "argv at selftest (--apply)")


def test_dry_run_alone_satisfies_the_contract_and_becomes_the_ambient_intent() -> None:
    """The other flag binds the other value."""

    def run() -> tuple[str | None, str | None, str | None]:
        verdict = require_explicit_mutation("selftest", ["t", "--dry-run"])
        return verdict, INTENT.get(), INTENT.origin()

    assert _fresh(run) == (None, "dry-run", "argv at selftest (--dry-run)")


def test_an_argv_statement_does_not_rebind_an_intent_that_is_already_ambient() -> None:
    """The first binding wins: a later statement in a nested frame leaves the ambient alone."""

    def run() -> tuple[str | None, str | None, str | None]:
        require_explicit_mutation("entry", ["t", "--apply"])
        again = require_explicit_mutation("nested", ["t", "--dry-run"])
        return again, INTENT.get(), INTENT.origin()

    assert _fresh(run) == (None, "apply", "argv at entry (--apply)")


def test_both_flags_are_refused_even_when_the_switch_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two contradictory statements have no safe reading, so the off-switch does not help."""
    monkeypatch.setenv(_UNSET, "0")
    message = _fresh(
        lambda: _refusal(lambda: require_explicit_mutation("t", ["t", "--apply", "--dry-run"]))
    )
    assert message == (
        "⚑ t: BOTH --apply and --dry-run given — they are mutually exclusive. "
        "Refusing rather than picking one."
    )


def test_neither_flag_is_refused_at_the_default_and_the_refusal_is_not_an_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bare invocation refuses, states the two words, and cannot be swallowed by a handler."""
    monkeypatch.delenv(_UNSET, raising=False)

    def bare() -> BaseException | None:
        try:
            require_explicit_mutation("tool", ["t"])
        except MutationContractError as e:
            return e
        return None

    caught = _fresh(bare)
    assert caught is not None
    assert not isinstance(caught, Exception)
    assert str(caught) == (
        "⚑ tool: neither --apply nor --dry-run was given.\n"
        "  A mutating tool must not GUESS: default-dry silently does nothing when you "
        "meant to write,\n  default-apply silently writes when you meant to look. State one."
    )


def test_the_off_switch_downgrades_to_an_advisory_that_says_it_is_unarmed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the switch at 0 the run proceeds, and every such run announces itself."""
    monkeypatch.setenv(_UNSET, "0")
    assert _fresh(lambda: require_explicit_mutation("tool", ["t"])) == "advisory"
    err = capsys.readouterr().err
    assert err.startswith("⚑ tool: neither --apply nor --dry-run was given.")
    assert "⚑ RUNNING UNARMED: SUBSTRATE_EXPLICIT_MUTATION=0 downgraded this REFUSAL" in err
    assert err.endswith("having been stated.\n")


def test_any_other_switch_value_is_still_armed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the exact value 0 disarms the contract: one, empty and words all refuse."""
    for value in ("1", "", "off"):
        monkeypatch.setenv(_UNSET, value)
        message = _fresh(lambda: _refusal(lambda: require_explicit_mutation("t", ["t"])))
        assert message.startswith("⚑ t: neither --apply nor --dry-run was given.")


def test_a_longer_flag_containing_apply_does_not_satisfy_the_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reading apply-all as consent is the substring defect: it refuses and names the successor."""
    monkeypatch.delenv(_UNSET, raising=False)
    message = _fresh(lambda: _refusal(lambda: require_explicit_mutation("t", ["t", "--apply-all"])))
    assert "      --apply-all  →  --apply\n" in message
    assert message.count("NEAR MISS") == 1


def test_a_near_miss_is_refused_with_the_exact_substitution_and_never_blessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every recorded near miss is refused, the refusal leads with the substitution, all listed."""
    monkeypatch.delenv(_UNSET, raising=False)
    for wrong, right in NEAR_MISS_SPELLINGS.items():
        message = _fresh(functools.partial(_near_miss_refusal, wrong))
        assert f"      {wrong}  →  {right}\n" in message
    both = _fresh(
        lambda: _refusal(lambda: require_explicit_mutation("t", ["t", "--dry", "--force"]))
    )
    assert "      --dry  →  --dry-run\n      --force  →  --apply\n" in both
    assert both.endswith("`--apply` and `--dry-run`; there is no third.")
    assert (
        "⚑ you typed a NEAR MISS — this tool does not accept it as a statement of intent:" in both
    )


def test_a_stated_intent_satisfies_the_contract_without_touching_argv() -> None:
    """A fixture says in code what it does: both values pass and bind, argv is not read."""

    def run(intent: str) -> tuple[str | None, str | None]:
        return require_explicit_mutation("t", ["t"], intent=intent), INTENT.get()

    assert _fresh(lambda: run("apply")) == (None, "apply")
    assert _fresh(lambda: run("dry-run")) == (None, "dry-run")


def test_an_unrecognised_intent_refuses_and_a_disagreeing_one_conflicts() -> None:
    """The escape is at least as strict as the contract it bypasses, and the ambient value wins."""

    def vocab() -> str:
        try:
            require_explicit_mutation("t", ["t"], intent="maybe")
        except AmbientVocabError as e:
            return str(e)
        return "NO RAISE"

    def conflict() -> str:
        require_explicit_mutation("entry", ["t", "--dry-run"])
        try:
            require_explicit_mutation("fixture", ["t"], intent="apply")
        except AmbientConflictError as e:
            return str(e)
        return "NO RAISE"

    assert "intent='maybe' is not one of 'apply' / 'dry-run'" in _fresh(vocab)
    assert "bound:    'dry-run'  by argv at entry (--dry-run)" in _fresh(conflict)


def test_argv_defaults_to_the_process_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no argv given the contract reads the process's own."""
    monkeypatch.setattr(sys, "argv", ["tool", "--dry-run"])
    assert _fresh(lambda: require_explicit_mutation("t")) is None
    monkeypatch.delenv(_UNSET, raising=False)
    monkeypatch.setattr(sys, "argv", ["tool"])
    assert _fresh(lambda: _refusal(lambda: require_explicit_mutation("t"))) != "NO RAISE"


def test_guard_checks_the_contract_snapshots_and_announces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The one call a writer makes: it states intent, returns the sha, and says how to recover."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    sha = _fresh(lambda: guard("tool target", ["a.txt"], intent="apply", root=tmp_path))
    assert sha is not None
    assert len(sha) == _SHA_LEN
    assert capsys.readouterr().out == (
        f"snapshot {sha[:12]} [tool target] — recover any file with:\n"
        f"    git checkout {sha[:12]} -- <path>\n"
    )


def test_guard_with_no_repository_warns_that_edits_are_unrecoverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing net is announced, not hidden, and the caller gets None."""
    _isolate(monkeypatch, tmp_path)
    assert _fresh(lambda: guard("tool", [], intent="apply", root=tmp_path)) is None
    assert capsys.readouterr().out == (
        "⚠ tool: NO SNAPSHOT (not a git worktree?) — edits are unrecoverable\n"
    )


def test_guard_refuses_before_snapshotting_when_the_contract_is_not_met(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refusal comes first: nothing is snapshotted and the journal is never created."""
    _repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["tool"])
    message = _fresh(lambda: _refusal(lambda: guard("tool", ["a.txt"], root=tmp_path)))
    assert message.startswith("⚑ tool: neither --apply nor --dry-run was given.")
    assert not (tmp_path / "scratch").exists()


def test_a_best_effort_handler_around_guard_does_not_swallow_a_refusal() -> None:
    """The exact caller shape of the measured call sites: the refusal passes through it."""
    code = (
        "from mikemol.treeio.contract import guard\n"
        "from mikemol.treeio.errors import MutationContractError\n"
        "try:\n"
        "    try:\n"
        "        guard('probe', [], intent='maybe')\n"
        "    except Exception as x:\n"
        "        print('SWALLOWED', type(x).__name__)\n"
        "except SystemExit:\n"
        "    print('EXITED')\n"
        "except MutationContractError as x:\n"
        "    print('PASSED-THROUGH', type(x).__name__)\n"
    )
    assert _child(code) == (0, "PASSED-THROUGH AmbientVocabError\n", "")


def test_the_library_frame_raises_and_never_exits_in_a_fresh_interpreter() -> None:
    """At the real default the library arm raises a refusal that is not an Exception."""
    template = (
        "from mikemol.treeio.contract import require_explicit_mutation\n"
        "from mikemol.treeio.errors import MutationContractError\n"
        "try:\n"
        "    require_explicit_mutation('t', {argv!r}, intent={intent!r})\n"
        "    print('NO RAISE')\n"
        "except SystemExit:\n"
        "    print('EXITED')\n"
        "except MutationContractError as x:\n"
        "    print('RAISED', not isinstance(x, Exception))\n"
    )
    for argv, intent in ((["t"], None), (["t"], "maybe"), (["t", "--apply", "--dry-run"], None)):
        status, out, _ = _child(template.format(argv=argv, intent=intent))
        assert (status, out) == (0, "RAISED True\n")


def test_the_command_line_boundary_renders_a_refusal_as_exit_two_in_a_fresh_interpreter() -> None:
    """Through the boundary an unstated intent is exit 2 and the stderr names both words."""
    code = (
        "import sys\n"
        "from mikemol.treeio.contract import cli_main, require_explicit_mutation\n"
        "sys.exit(cli_main(lambda: require_explicit_mutation('t', {argv!r})) or 0)\n"
    )
    status, _, err = _child(code.format(argv=["t"]))
    assert status == _REFUSED
    assert "--apply" in err
    assert "--dry-run" in err
    near_status, _, near_err = _child(code.format(argv=["t", "--dry"]), strict="1")
    assert near_status == _REFUSED
    assert "--dry  →  --dry-run" in near_err


def test_an_unrecognised_intent_through_the_boundary_names_the_vocabulary_it_wanted() -> None:
    """The vocabulary refusal is exit 2 at the boundary and still names what it wanted."""
    code = (
        "import sys\n"
        "from mikemol.treeio.contract import cli_main, require_explicit_mutation\n"
        "sys.exit(cli_main(lambda: require_explicit_mutation('t', ['t'], intent='maybe')) or 0)\n"
    )
    status, _, err = _child(code)
    assert status == _REFUSED
    assert "'apply' / 'dry-run'" in err
    assert "REFUSES rather than passing" in err


def test_snapshot_once_snapshots_once_but_copies_every_untracked_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The latch's bug dissolved: one sha for the run, and the later file is still copied."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "one.py").write_text("1", encoding="utf-8")
    (tmp_path / "two.py").write_text("2", encoding="utf-8")

    def twice() -> tuple[str | None, str | None]:
        return (
            snapshot_once("t", ["one.py"], intent="apply", root=tmp_path),
            snapshot_once("t", ["two.py"], intent="apply", root=tmp_path),
        )

    first, second = _fresh(twice)
    assert first is not None
    assert second == first
    store = tmp_path / "scratch" / ".edit-snapshots"
    assert sorted(p.name for p in store.iterdir()) == ["one.py", "two.py"]
    journal = (tmp_path / "scratch" / "edit_snapshot.journal.tsv").read_text(encoding="utf-8")
    assert [ln for ln in journal.splitlines() if not ln.startswith("#")] == [
        f"{first}\tt\t1\tone.py"
    ]
    assert capsys.readouterr().out.count("recover any file with:") == 1


def test_snapshot_once_checks_the_contract_before_it_snapshots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consolidating the helpers must not delete the stated-intent check from the writers."""
    _repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["tool"])
    message = _fresh(lambda: _refusal(lambda: snapshot_once("tool", ["a.txt"], root=tmp_path)))
    assert message.startswith("⚑ tool: neither --apply nor --dry-run was given.")
    assert not (tmp_path / "scratch").exists()


def test_snapshot_once_without_a_repository_returns_none_and_does_not_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No snapshot is available, which is said once, and a second call stays quiet."""
    _isolate(monkeypatch, tmp_path)

    def twice() -> tuple[str | None, str | None, str | None]:
        first = snapshot_once("t", [], intent="apply", root=tmp_path)
        second = snapshot_once("t", [], intent="apply", root=tmp_path)
        state = SNAPSHOT_STATE.get()
        assert state is not None
        return first, second, state.sha

    assert _fresh(twice) == (None, None, "")
    assert capsys.readouterr().out.count("NO SNAPSHOT") == 1


def test_entry_with_apply_snapshots_in_the_same_act(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Stating apply IS the snapshot: the binding the whole entry form turns on."""
    _repo(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    assert _fresh(lambda: require_at_entry("tool", ["t", "--apply"], paths=["a.txt"])) is None
    assert "recover any file with:" in capsys.readouterr().out
    assert (tmp_path / "scratch" / "edit_snapshot.journal.tsv").exists()


def test_entry_with_dry_run_takes_no_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A stated dry-run writes nothing, so there is nothing to snapshot and the log stays useful."""
    _repo(tmp_path, monkeypatch)
    assert _fresh(lambda: require_at_entry("tool", ["t", "--dry-run"], paths=["a.txt"])) is None
    assert not capsys.readouterr().out
    assert not (tmp_path / "scratch").exists()


def test_entry_selftest_carve_out_is_a_distinct_verdict_and_an_intent_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A selftest passes without a flag and says so; an explicit intent overrides the carve-out."""
    _repo(tmp_path, monkeypatch)
    assert _fresh(lambda: require_at_entry("tool", ["t", "--selftest"])) == "selftest"
    assert not capsys.readouterr().out
    assert (
        _fresh(lambda: require_at_entry("tool", ["t", "--selftest"], intent="apply", paths=[]))
        is None
    )
    assert "recover any file with:" in capsys.readouterr().out


def test_entry_for_a_store_tool_says_a_snapshot_is_not_applicable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file copy cannot capture a store write, so the notice says so instead of claiming one."""
    _repo(tmp_path, monkeypatch)
    assert _fresh(lambda: require_at_entry("tool", ["t", "--apply"], store=True)) is None
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.startswith("   ⚑ tool: snapshot NOT APPLICABLE")
    assert "there is no snapshot to recover from." in captured.err
    assert not (tmp_path / "scratch").exists()


def _exit_of(fn: Callable[[], object]) -> object:
    """Run `fn` and report the status it exited with.

    Returns:
        The SystemExit code, or NO EXIT when it returned.

    """
    try:
        fn()
    except SystemExit as e:
        return e.code
    return "NO EXIT"


def test_a_bare_entry_renders_the_refusal_and_exits_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The entry point owns the pid, so it renders the message and exits 2 instead of raising."""
    monkeypatch.delenv(_UNSET, raising=False)
    assert _fresh(lambda: _exit_of(lambda: require_at_entry("tool", ["t"]))) == _REFUSED
    err = capsys.readouterr().err
    assert err.startswith("⚑ tool: neither --apply nor --dry-run was given.")
    assert "--apply" in err
    assert "--dry-run" in err


def test_a_near_miss_at_entry_exits_two_and_names_its_successor(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal at the entry point carries the substitution table, not a bare no."""
    monkeypatch.delenv(_UNSET, raising=False)
    assert _fresh(lambda: _exit_of(lambda: require_at_entry("tool", ["t", "--force"]))) == _REFUSED
    assert "--force  →  --apply" in capsys.readouterr().err


def test_an_advisory_at_entry_is_returned_as_the_verdict(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Under the off-switch the run goes on, and the caller can see it was unarmed."""
    monkeypatch.setenv(_UNSET, "0")
    assert _fresh(lambda: require_at_entry("tool", ["t"])) == "advisory"
    assert "RUNNING UNARMED" in capsys.readouterr().err


def test_entry_defaults_its_argv_to_the_process_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no argv given the entry form reads the process's own."""
    monkeypatch.setattr(sys, "argv", ["tool", "--dry-run"])
    assert _fresh(lambda: require_at_entry("tool")) is None
    monkeypatch.setattr(sys, "argv", ["tool", "--selftest"])
    assert _fresh(lambda: require_at_entry("tool")) == "selftest"


def test_cli_main_returns_what_the_tool_returns() -> None:
    """A tool that succeeds passes its status through, including None."""
    assert cli_main(lambda: 0) == 0
    assert cli_main(lambda: 7) == len(("a", "b", "c", "d", "e", "f", "g"))
    assert cli_main(lambda: None) is None


def test_cli_main_renders_a_contract_refusal_as_exit_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Only this package's own stated refusals become a message and a status."""

    def refuses() -> int:
        msg = "stated refusal"
        raise AmbientVocabError(msg)

    assert cli_main(refuses) == _REFUSED
    assert capsys.readouterr().err == "stated refusal\n"


def test_cli_main_lets_a_genuine_bug_surface_as_a_traceback() -> None:
    """It catches the contract family and not Exception, so a defect in the body is not hidden."""

    def buggy() -> int:
        msg = "a bug in the tool"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="a bug in the tool"):
        cli_main(buggy)
