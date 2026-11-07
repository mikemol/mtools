# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The submit refusal reads the stack file and the named pace file (W1920).

⚑ THE CONTROLS: a stack that lowers nothing is refused, one of queue files alone and one that
touches the owed ratchet are admitted, and a stack file that cannot be read refuses nothing.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import admission, ratchet_pace, runproc, stacksnap
from mikemol.hooks.stackfreeze import SNAP_ENV
from mikemol.hooks.stackrun import Item

if TYPE_CHECKING:
    from pathlib import Path

_RATCHET = "corpus/exit-baseline.txt"


def _repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Build a repository `r` owing one payable ratchet, its pace file named in an env map.

    Returns:
        the repository root and the environment naming the pace file.

    """
    root = tmp_path / "r"
    (root / ".claude").mkdir(parents=True)
    (root / "corpus").mkdir()
    (root / _RATCHET).write_text("a 1\nb 2\n", encoding="utf-8")
    (root / ".claude" / "paths-forward.json").write_text('{"waypoints": []}', encoding="utf-8")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "repo": "r",
        "ratchet": _RATCHET,
        "state": "behind",
        "observed": "0",
        "required": "1",
    }
    head = f'{{"as_of": "{stamp}", "window": "10"}}'
    pace = tmp_path / "pace.json"
    pace.write_text(f"{head}\n{json.dumps(row)}\n", encoding="utf-8")
    return root, {ratchet_pace.ENV: str(pace)}


def _stack(tmp_path: Path, *paths: str) -> Path:
    path = tmp_path / "stack.json"
    entry: dict[str, object] = {"waypoint": "W1", "subject": "s", "paths": list(paths)}
    entries: list[dict[str, object]] = [entry]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_a_stack_that_lowers_nothing_is_refused_and_one_touching_the_ratchet_is_not(
    tmp_path: Path,
) -> None:
    """The stack file's paths are what is judged, against the pace file the env names."""
    root, env = _repo(tmp_path)
    plain = _stack(tmp_path, "hooks/x.py")
    assert ratchet_pace.refusal(root, plain, env) is not None
    paying = _stack(tmp_path, "hooks/x.py", _RATCHET)
    assert ratchet_pace.refusal(root, paying, env) is None


def test_queue_only_and_an_unreadable_stack_file_refuse_nothing(tmp_path: Path) -> None:
    """Queue-state commits are admitted; a missing or torn stack file cannot be judged."""
    root, env = _repo(tmp_path)
    queue = _stack(tmp_path, ".claude/paths-forward.json", ".claude/paths-forward.ledger")
    assert ratchet_pace.refusal(root, queue, env) is None
    assert ratchet_pace.refusal(root, tmp_path / "absent.json", env) is None


_BLOB = "d" * 40
_OTHER = "e" * 40
_MODE = "100644"


def _admitted_stack(tmp_path: Path, blob: str) -> tuple[Path, dict[str, str]]:
    """Write a one-entry stack of hooks/x.py for W1 and its frozen snapshot at `blob`.

    Returns:
        the stack file and the environment naming the snapshot.

    """
    stack = _stack(tmp_path, "hooks/x.py")
    snap = tmp_path / "snapshot.json"
    stacksnap.dump(snap, [[stacksnap.Frozen("hooks/x.py", _MODE, blob)]])
    return stack, {SNAP_ENV: str(snap)}


def test_a_pinned_row_admits_exactly_its_change_on_the_frozen_snapshot(tmp_path: Path) -> None:
    """The control: the row's blob admits; another blob, no row, and no snapshot all refuse."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB}, review="r")
    stack, snap_env = _admitted_stack(tmp_path, _BLOB)
    assert ratchet_pace.refusal(root, stack, {**env, **snap_env}, [row]) is None
    assert ratchet_pace.refusal(root, stack, {**env, **snap_env}) is not None
    assert ratchet_pace.refusal(root, stack, env, [row]) is not None
    other, other_env = _admitted_stack(tmp_path, _OTHER)
    assert ratchet_pace.refusal(root, other, {**env, **other_env}, [row]) is not None


def test_an_unreadable_snapshot_never_admits(tmp_path: Path) -> None:
    """A snapshot the env names that is not there or not a snapshot is no admission."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB}, review="r")
    stack = _stack(tmp_path, "hooks/x.py")
    absent = {**env, SNAP_ENV: str(tmp_path / "absent.json")}
    assert ratchet_pace.refusal(root, stack, absent, [row]) is not None
    torn = tmp_path / "torn.json"
    torn.write_text("{", encoding="utf-8")
    assert ratchet_pace.refusal(root, stack, {**env, SNAP_ENV: str(torn)}, [row]) is not None


def test_the_rows_are_asked_only_for_a_stack_that_would_be_refused(tmp_path: Path) -> None:
    """A paydown or a queue-state stack is admitted without consulting a row."""
    root, _env = _repo(tmp_path)
    pace = tmp_path / "pace.json"
    asked: list[bool] = []

    def spy() -> bool:
        asked.append(True)
        return False

    now = datetime.now(UTC)
    assert ratchet_pace.stack_reason(root, [_RATCHET], now, pace, spy) is None
    queue = [".claude/paths-forward.json"]
    assert ratchet_pace.stack_reason(root, queue, now, pace, spy) is None
    assert not asked
    assert ratchet_pace.stack_reason(root, ["hooks/x.py"], now, pace, spy) is not None
    assert asked == [True]


def _landing(path: str, blob: str) -> list[Item]:
    """Make the one item being landed: W1 taking `path` frozen at `blob`.

    Returns:
        the items, as the landing paths hold them.

    """
    return [Item("W1", "s", "", (path,), (stacksnap.Frozen(path, _MODE, blob),))]


def test_the_trailer_names_the_row_only_when_the_pace_needed_it_and_the_row_matches(
    tmp_path: Path,
) -> None:
    """W2312: needed and matched gives the id; a paydown, another blob and no row give None."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB}, review="r")
    now = datetime.now(UTC)
    assert (
        ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _BLOB), env, [row], now) == "r/W1"
    )
    assert (
        ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _OTHER), env, [row], now) is None
    )
    assert ratchet_pace.admitted_ident(root, _landing("hooks/x.py", _BLOB), env, [], now) is None


def test_a_stack_the_pace_would_admit_anyway_never_spends_a_row(tmp_path: Path) -> None:
    """A paydown and a queue-state stack answer None even when a row matches them exactly."""
    root, env = _repo(tmp_path)
    now = datetime.now(UTC)
    paying = admission.Row(repo="r", card="W1", blobs={_RATCHET: _BLOB}, review="r")
    assert ratchet_pace.admitted_ident(root, _landing(_RATCHET, _BLOB), env, [paying], now) is None
    queue = admission.Row(
        repo="r", card="W1", blobs={".claude/paths-forward.json": _BLOB}, review="r"
    )
    landing = _landing(".claude/paths-forward.json", _BLOB)
    assert ratchet_pace.admitted_ident(root, landing, env, [queue], now) is None


def test_an_item_that_was_not_frozen_is_never_admitted(tmp_path: Path) -> None:
    """No frozen files means no blobs to match: a row cannot admit what it cannot read."""
    root, env = _repo(tmp_path)
    row = admission.Row(repo="r", card="W1", blobs={"hooks/x.py": _BLOB}, review="r")
    unfrozen = [Item("W1", "s", "", ("hooks/x.py",))]
    assert ratchet_pace.admitted_ident(root, unfrozen, env, [row], datetime.now(UTC)) is None


_BIRTH_FILE = "codon-edges-baseline.json"
_RECORD = "bde02714-1533-475a-b934-d2ce58024a15:104181"


def _git(root: Path, *args: str, text: str | None = None) -> str:
    done = runproc.run(["git", "-C", str(root), *args], stdin_text=text)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _entry(record: str, ratchet: str = _BIRTH_FILE) -> str:
    row: dict[str, object] = {
        "ratchet": ratchet,
        "old": 0,
        "new": 3,
        "reason": "birth",
        "warrant": record,
    }
    body: dict[str, object] = {"rebaselines": [row]}
    return json.dumps(body)


def _birth(root: Path, record: str) -> tuple[admission.Row, list[stacksnap.Frozen]]:
    """Make a git repo with one commit, a birth row, and the stack's frozen files.

    Returns:
        the row and the frozen files, the rebaselines blob really stored in the repository.

    """
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "first")
    stored = _git(root, "hash-object", "-w", "--stdin", text=_entry(record))
    files = [
        stacksnap.Frozen(_BIRTH_FILE, _MODE, _BLOB),
        stacksnap.Frozen("rebaselines.json", _MODE, stored),
    ]
    row = admission.Row(
        repo="r",
        review="r",
        card="W1",
        blobs={_BIRTH_FILE: _BLOB, "rebaselines.json": stored},
        kind=admission.BIRTH,
        ratchet=_BIRTH_FILE,
        old=0,
        new=3,
        record=_RECORD,
    )
    return row, files


def test_a_birth_row_admits_only_when_its_accident_checks_pass(tmp_path: Path) -> None:
    """The control, then each accident: another record, and a ratchet file already at HEAD."""
    root, env = _repo(tmp_path)
    row, files = _birth(root, _RECORD)
    landing = [Item("W1", "s", "", (_BIRTH_FILE, "rebaselines.json"), tuple(files))]
    now = datetime.now(UTC)
    assert ratchet_pace.admitted_ident(root, landing, env, [row], now) == "r/W1"
    wrong = _git(root, "hash-object", "-w", "--stdin", text=_entry(_RECORD.replace("1041", "9999")))
    tampered = [files[0], stacksnap.Frozen("rebaselines.json", _MODE, wrong)]
    swapped = admission.Row(
        repo="r",
        review="r",
        card="W1",
        blobs={_BIRTH_FILE: _BLOB, "rebaselines.json": wrong},
        kind=admission.BIRTH,
        ratchet=_BIRTH_FILE,
        old=0,
        new=3,
        record=_RECORD,
    )
    other = [Item("W1", "s", "", (_BIRTH_FILE, "rebaselines.json"), tuple(tampered))]
    assert ratchet_pace.admitted_ident(root, other, env, [swapped], now) is None
    (root / _BIRTH_FILE).write_text("{}", encoding="utf-8")
    _git(root, "add", _BIRTH_FILE)
    _git(root, "commit", "-q", "-m", "second")
    assert ratchet_pace.admitted_ident(root, landing, env, [row], now) is None


def test_a_birth_row_is_judged_at_submit_too_and_never_admitted_without_git(
    tmp_path: Path,
) -> None:
    """The submit refusal asks the accident checks; a root git cannot read admits nothing."""
    root, env = _repo(tmp_path)
    row, files = _birth(root, _RECORD)
    paths = (_BIRTH_FILE, "rebaselines.json")
    stack = _stack(tmp_path, *paths)
    snap = tmp_path / "snapshot.json"
    stacksnap.dump(snap, [files])
    submit_env = {**env, SNAP_ENV: str(snap)}
    assert ratchet_pace.refusal(root, stack, submit_env, [row]) is None
    (root / _BIRTH_FILE).write_text("{}", encoding="utf-8")
    _git(root, "add", _BIRTH_FILE)
    _git(root, "commit", "-q", "-m", "second")
    assert ratchet_pace.refusal(root, stack, submit_env, [row]) is not None
    bare = tmp_path / "bare" / "r"
    (bare / ".claude").mkdir(parents=True)
    (bare / ".claude" / "paths-forward.json").write_text('{"waypoints": []}', encoding="utf-8")
    landing = [Item("W1", "s", "", paths, tuple(files))]
    assert ratchet_pace.admitted_ident(bare, landing, env, [row], datetime.now(UTC)) is None


def test_the_landing_refuses_a_stack_the_pace_still_refuses_unless_a_row_clears_it(
    tmp_path: Path,
) -> None:
    """B1: no row refuses; a paydown does not; a birth whose file a peer landed does."""
    root, env = _repo(tmp_path)
    now = datetime.now(UTC)
    plain = [Item("W1", "s", "", ("hooks/x.py",))]
    assert ratchet_pace.landing_refusal(root, plain, env, [], now) is not None
    paying = [Item("W1", "s", "", ("hooks/x.py", _RATCHET))]
    assert ratchet_pace.landing_refusal(root, paying, env, [], now) is None
    row, files = _birth(root, _RECORD)
    paths = (_BIRTH_FILE, "rebaselines.json")
    landing = [Item("W1", "s", "", paths, tuple(files))]
    assert ratchet_pace.landing_refusal(root, landing, env, [row], now) is None
    (root / _BIRTH_FILE).write_text("{}", encoding="utf-8")
    _git(root, "add", _BIRTH_FILE)
    _git(root, "commit", "-q", "-m", "a peer lands the ratchet file")
    said = ratchet_pace.landing_refusal(root, landing, env, [row], now)
    assert said is not None
    assert f"the birth row {row.ident()} did not clear: " in said
    assert said.rsplit("did not clear: ", 1)[1]


def test_a_group_needs_an_admission_exactly_when_the_pace_refuses_it(tmp_path: Path) -> None:
    """B1: the train ends its round before a group the pace refuses; a paydown needs none."""
    root, env = _repo(tmp_path)
    now = datetime.now(UTC)
    plain = [Item("W1", "s", "", ("hooks/x.py",))]
    assert ratchet_pace.needs_admission(root, plain, env, now)
    paying = [Item("W1", "s", "", ("hooks/x.py", _RATCHET))]
    assert not ratchet_pace.needs_admission(root, paying, env, now)


def _birth_at(
    root: Path, *, ratchet: str, tracked: str | None = None, commit: bool = True
) -> tuple[admission.Row, list[Item]]:
    """Make a git repo, optionally with a tracked file, and a birth of `ratchet` over it.

    Returns:
        the row and the landing items.

    """
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    if tracked is not None:
        target = root / tracked
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}", encoding="utf-8")
        _git(root, "add", "--", tracked)
    if commit:
        _git(root, "commit", "-q", "-m", "first", "--allow-empty")
    stored = _git(root, "hash-object", "-w", "--stdin", text=_entry(_RECORD, ratchet))
    files = (
        stacksnap.Frozen(ratchet, _MODE, _BLOB),
        stacksnap.Frozen("rebaselines.json", _MODE, stored),
    )
    row = admission.Row(
        repo="r",
        card="W1",
        blobs={ratchet: _BLOB, "rebaselines.json": stored},
        review="r",
        kind=admission.BIRTH,
        ratchet=ratchet,
        old=0,
        new=3,
        record=_RECORD,
    )
    return row, [Item("W1", "s", "", (ratchet, "rebaselines.json"), files)]


def test_a_head_git_cannot_list_refuses_even_when_the_rebaselines_blob_is_readable(
    tmp_path: Path,
) -> None:
    """B2: an unborn HEAD fails ls-tree while the blob reads; it must not read as an empty HEAD."""
    root, env = _repo(tmp_path)
    row, landing = _birth_at(root, ratchet=_BIRTH_FILE, commit=False)
    assert ratchet_pace.landing_refusal(root, landing, env, [row]) is not None


def test_a_nested_ratchet_already_at_head_and_a_non_utf8_name_both_refuse(tmp_path: Path) -> None:
    """N2 and N8: -r reaches a nested file; a name that is not UTF-8 refuses instead of raising."""
    nested = "sub/dir/baseline.json"
    root, env = _repo(tmp_path)
    row, landing = _birth_at(root, ratchet=nested, tracked=nested)
    assert ratchet_pace.landing_refusal(root, landing, env, [row]) is not None
    odd = tmp_path / "odd" / "r"
    (odd / ".claude").mkdir(parents=True)
    (odd / ".claude" / "paths-forward.json").write_text('{"waypoints": []}', encoding="utf-8")
    row2, landing2 = _birth_at(odd, ratchet=_BIRTH_FILE)
    (odd / os.fsdecode(b"\xff.txt")).write_text("x", encoding="utf-8")
    _git(odd, "add", "-A")
    _git(odd, "commit", "-q", "-m", "odd name")
    assert ratchet_pace.landing_refusal(odd, landing2, env, [row2]) is not None


_OLD_SHA = "459a112"
_NEW_SHA = "636e39b"


def _pyproject(sha: str, extra: str = "") -> str:
    row = f'mikemol-fence = {{ path = "vendor/wheels/mikemol_fence-0.1.0+{sha}-py3-none-any.whl" }}'
    return f"[tool.uv.sources]\n{row}\n{extra}"


def _wheel(sha: str) -> str:
    return f"vendor/wheels/mikemol_fence-0.1.0+{sha}-py3-none-any.whl"


def _repin_repo(root: Path) -> None:
    """Commit a repo vendoring one wheel at the old sha."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "vendor" / "wheels").mkdir(parents=True)
    (root / "pyproject.toml").write_text(_pyproject(_OLD_SHA), encoding="utf-8")
    (root / _wheel(_OLD_SHA)).write_bytes(b"old wheel")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "vendor the wheel")


def _repin_items(root: Path, pyproject: str, wheel_sha: str = _NEW_SHA) -> list[Item]:
    """Item for a stack that renames the wheel and rewrites pyproject.toml.

    Returns:
        the one item, its files frozen with blobs really stored in the repository.

    """
    toml = _git(root, "hash-object", "-w", "--stdin", text=pyproject)
    wheel = _git(root, "hash-object", "-w", "--stdin", text="new wheel")
    files = (
        stacksnap.Frozen("pyproject.toml", _MODE, toml),
        stacksnap.Frozen(_wheel(wheel_sha), _MODE, wheel),
        stacksnap.Frozen(_wheel(_OLD_SHA), _MODE, ""),
    )
    return [Item("W1", "s", "", tuple(f.path for f in files), files)]


def test_a_repin_is_admitted_by_clause_r_and_a_stray_line_or_a_second_sha_is_not(
    tmp_path: Path,
) -> None:
    """W2329: only the vendored sha changes in the text files; anything else keeps the refusal."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    now = datetime.now(UTC)
    clean = _repin_items(root, _pyproject(_NEW_SHA))
    assert ratchet_pace.landing_refusal(root, clean, env, [], now) is None
    stray = _repin_items(root, _pyproject(_NEW_SHA, 'rich = "13"\n'))
    assert ratchet_pace.landing_refusal(root, stray, env, [], now) is not None
    split = _repin_items(root, _pyproject(_NEW_SHA), wheel_sha="abc1234")
    assert ratchet_pace.landing_refusal(root, split, env, [], now) is not None


def test_the_submit_refusal_admits_a_repin_the_same_way(tmp_path: Path) -> None:
    """The submit asks clause R too, on the frozen snapshot, and still refuses a stray line."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    for text, refused in ((_pyproject(_NEW_SHA), False), (_pyproject(_NEW_SHA, "x = 1\n"), True)):
        item = _repin_items(root, text)[0]
        stack = _stack(tmp_path, *item.paths)
        snap = tmp_path / "snapshot.json"
        stacksnap.dump(snap, [list(item.files or ())])
        reason = ratchet_pace.refusal(root, stack, {**env, SNAP_ENV: str(snap)}, [])
        assert (reason is not None) is refused


def test_a_repin_names_its_sha_in_the_audit_trailer_and_a_source_file_beside_it_is_refused(
    tmp_path: Path,
) -> None:
    """Clause R leaves its mark; a tracked source file in the stack is not repin-owned."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    now = datetime.now(UTC)
    clean = _repin_items(root, _pyproject(_NEW_SHA))
    assert ratchet_pace.admitted_ident(root, clean, env, [], now) == f"r/repin-{_NEW_SHA}"
    src = _git(root, "hash-object", "-w", "--stdin", text="x = 2\n")
    extra = stacksnap.Frozen("src/app.py", _MODE, src)
    files = (*(clean[0].files or ()), extra)
    beside = [Item("W1", "s", "", (*clean[0].paths, "src/app.py"), files)]
    assert ratchet_pace.landing_refusal(root, beside, env, [], now) is not None
    assert ratchet_pace.admitted_ident(root, beside, env, [], now) is None


def test_a_stack_that_moves_no_sha_does_not_get_past_the_pace(tmp_path: Path) -> None:
    """B2 end to end: the HEAD pyproject, unchanged, is not a repin and is refused."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    now = datetime.now(UTC)
    noop = _repin_items(root, _pyproject(_OLD_SHA), wheel_sha=_OLD_SHA)
    assert ratchet_pace.landing_refusal(root, noop, env, [], now) is not None


def test_an_earlier_entry_at_other_bytes_is_not_hidden_by_a_later_clean_one(
    tmp_path: Path,
) -> None:
    """A path frozen twice at different blobs is no repin: the later would hide the earlier."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    now = datetime.now(UTC)
    clean = _repin_items(root, _pyproject(_NEW_SHA))[0]
    stray = _repin_items(root, _pyproject(_NEW_SHA, 'rich = "13"\n'))[0]
    first = next(f for f in stray.files or () if f.path == "pyproject.toml")
    files = (first, *(clean.files or ()))
    twice = [Item("W1", "s", "", clean.paths, files)]
    assert ratchet_pace.landing_refusal(root, twice, env, [], now) is not None


def test_a_link_or_a_flipped_execute_bit_in_a_repin_stack_is_refused(tmp_path: Path) -> None:
    """N2: only a regular file with the mode HEAD gave it belongs to a repin."""
    root, env = _repo(tmp_path)
    _repin_repo(root)
    now = datetime.now(UTC)
    clean = _repin_items(root, _pyproject(_NEW_SHA))[0]
    assert ratchet_pace.landing_refusal(root, [clean], env, [], now) is None
    for mode in ("120000", "100755"):
        files = tuple(
            stacksnap.Frozen(f.path, mode, f.blob) if f.path == "pyproject.toml" else f
            for f in clean.files or ()
        )
        odd = [Item("W1", "s", "", clean.paths, files)]
        assert ratchet_pace.landing_refusal(root, odd, env, [], now) is not None
