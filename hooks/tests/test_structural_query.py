# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases for `mikemol.hooks.structural_query` — when it refuses, and what it says.

⚑⚑ A HOOK'S TESTS MUST EXERCISE THE REFUSAL AND THE PASS. A hook that refuses nothing and a hook
that refuses everything are both broken, and only the pair distinguishes them: every fires-on case
below passes against a `verdict` that returns True unconditionally, and every passes case against
one that returns False. Neither half is a test of this gate on its own.

⚑ THE TABLE IS SUPPLIED EXPLICITLY, NEVER READ FROM WHATEVER REPO THE SUITE RUNS IN. A test whose
subject is "which repo's table did you read" cannot itself depend on an ambient answer to that —
and a suite that silently read the checkout's own table would go green in this repo and prove
nothing about an adopting one.

⚑ THE MESSAGE CASES EXIST BECAUSE NOTHING CHECKED THE MESSAGE FOR AN ARC. Every case asked whether
the hook FIRES; the text was built inline in `main` and unreachable without a subprocess. A
refusal that names an unrunnable tool and stops is a gate that blocks without routing — measured,
in a borrowing checkout where the reader had no move left.
"""

from __future__ import annotations

import io
import json

import pytest

from mikemol.hooks import payload, routing_table, structural_query

# The claims table every verdict case is rendered against, named so no case depends on ambient
# state. `.log` and `.tsv` are DELIBERATELY ABSENT — they are what an unclaimed artifact looks
# like, and the passes cases below rest on their absence.
_CLAIMS: dict[str, tuple[str, str]] = {
    ".py": ("python source", "pycodemod.py"),
    ".md": ("markdown", "mdstruct.py"),
    ".agda": ("agda source", "agdastruct.py"),
}


def _fires(cmd: str) -> bool:
    """Report whether the gate refuses `cmd` against the fixed table.

    Returns:
        whether the gate refuses `cmd` against the fixed table.

    """
    return structural_query.verdict(cmd, _CLAIMS)[0]


def _stdin(text: str) -> io.StringIO:
    """Return a stand-in for `sys.stdin` delivering `text`.

    Returns:
        a stand-in for `sys.stdin` delivering `text`.

    """
    return io.StringIO(text)


def _payload_json(command: str) -> str:
    """Render a PreToolUse payload carrying `command`, typed at every level.

    ⚑ NAMED LOCALS, NOT A NESTED LITERAL AT THE CALL SITE. An inner `{...}` written inline is
    inferred on its own as `dict[Any, Any]` — the call site gives it nothing to check against —
    and the strict bar refuses it. The same construct in the hook itself cost six wrong
    attributions before a checker rendered the line.

    Returns:
        the a PreToolUse payload carrying `command`, typed at every level.

    """
    tool_input: dict[str, object] = {"command": command}
    envelope: dict[str, object] = {"tool_input": tool_input}
    return json.dumps(envelope)


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        ("a bare grep over .py", "grep -n 'def foo' scratch/tool.py"),
        ("a piped grep over .py", "cat x | grep -n foo scratch/a.py"),
        ("⚑ a timeout prefix", "timeout 180 grep -c __main__ scratch/seal_defs.py"),
        ("an env prefix", "env grep foo scratch/a.py"),
        ("a VAR= prefix", "PYTHONPATH=. grep foo scratch/a.py"),
        ("an absolute path to grep", "/usr/bin/grep foo scratch/a.py"),
        ("stacked wrappers", "timeout 60 env grep foo scratch/a.py"),
        ("head, a widened tool", "head -50 scratch/tool.py"),
        ("wc, a widened tool", "wc -l scratch/tool.py"),
        ("cat over .agda", "cat agda/Foo.agda"),
        ("⚑ a .py in ANOTHER repo", "grep foo /home/mikemol/github/otherrepo/x.py"),
    ],
)
def test_the_gate_refuses_a_textual_query_over_a_claimed_artifact(label: str, cmd: str) -> None:
    """⚑ EACH WRAPPER SHAPE HERE RAN SUCCESSFULLY AGAINST THE PREDECESSOR.

    It tested only `toks[0]`, and a `timeout` prefix is the ordinary invocation shape — so the
    gate was open for nearly every real command. The last case is the one that killed a
    location-based predicate: the claim is the ARTIFACT KIND, not the checkout it lives in.
    """
    assert _fires(cmd) is True, label


@pytest.mark.parametrize(
    ("label", "cmd"),
    [
        ("ls locates, it does not query structure", "ls -la scratch/tool.py"),
        ("find locates too", "find . -name '*.py'"),
        ("pgrep reads no file", "pgrep -af make"),
        ("an unclaimed .log", "grep -c Error /tmp/build.log"),
        ("an unclaimed .tsv", "wc -l scratch/.agda-times.tsv"),
        ("⚑ a directory named pkg.py/", "grep foo pkg.py/notes.txt"),
        ("a flag that looks like a path", "grep --include=x.py foo notes.txt"),
    ],
)
def test_the_gate_allows_what_it_must_not_refuse(label: str, cmd: str) -> None:
    """⚑ THE HALF THAT MAKES THE REFUSALS ABOVE MEAN ANYTHING.

    Without these, every case in this file passes against a gate that refuses every command — and
    a gate that refuses everything is not a strict gate, it is a broken one that gets disabled
    within a day. `pkg.py/` is the case that forced matching the argument WORD rather than testing
    `".py" in seg`.
    """
    assert _fires(cmd) is False, label


def test_an_unclaimed_suffix_becomes_claimed_when_a_row_declares_it() -> None:
    """⚑ THE GATE IS TAUGHT BY THE TABLE, NOT BY AN EDIT HERE — asserted, not assumed.

    The `.log` pass above could mean "logs are exempt" or "no row claims .log today". Only running
    the same command against a table that DOES claim it distinguishes a data-driven gate from a
    hardcoded exemption, and the whole design rests on it being the former.
    """
    with_log = {**_CLAIMS, ".log": ("build log", "buildlog.py")}
    assert structural_query.verdict("grep -c Error /tmp/build.log", with_log)[0] is True


def test_no_claims_at_all_refuses_nothing() -> None:
    """⚑ AND THAT IS THE DANGEROUS STATE, PINNED SO IT IS VISIBLE RATHER THAN DISCOVERED.

    An adopting repo with no routing table gets a gate that allows everything. The behaviour is
    correct — inventing claims for a repo that declared none applies a bar nobody chose — but it
    means "the hook is installed" and "the hook is refusing" are independent facts.
    """
    assert structural_query.verdict("grep -n foo x.py", {})[0] is False


def test_the_reasons_name_the_argument_and_its_owner() -> None:
    """The verdict carries WHAT was hit, not just THAT something was."""
    _hit, reasons = structural_query.verdict("wc -l scratch/tool.py", _CLAIMS)
    assert reasons == [("wc", [("scratch/tool.py", ".py", ("python source", "pycodemod.py"))])]


def _read_message() -> str:
    """Return the refusal text for a plain read of a claimed artifact.

    Returns:
        refusal text for a plain read of a claimed artifact.

    """
    return structural_query.refusal(structural_query.verdict("wc -l scratch/tool.py", _CLAIMS)[1])


def test_the_refusal_names_the_owning_tool() -> None:
    """A refusal that only denies leaves the author with no next move."""
    assert "pycodemod.py" in _read_message()


def test_the_refusal_offers_read_when_the_owning_tool_is_unavailable() -> None:
    """⚑ MEASURED IN A BORROWING CHECKOUT WHERE THE NAMED TOOL COULD NOT RUN.

    The message named the one route the reader could not take and stopped. `Read` is the answer
    and needs SAYING — it is not a shell command, so a reader thinking in Bash calls will not
    reach for it.
    """
    msg = _read_message()
    assert "Read" in msg
    assert "not a shell command" in msg


def test_a_shell_append_to_a_claimed_artifact_still_fires() -> None:
    """⚑ THE VERDICT DOES NOT SOFTEN FOR A WRITE.

    Operator ruling, 2026-08-19: *"don't support redirection, support editing"* / *"appendation
    causes files to grow out of control."* An earlier "fix" exempted `>>` from the argument list;
    that was the wrong repair, and the damage was measured — a staging block appended to and never
    drained grew past the budget of the reader that loads it every session.
    """
    assert _fires("cat >> scratch/tool.py") is True


def test_the_write_branch_routes_the_writer_to_the_owning_tool() -> None:
    """A blocked WRITER told to use `Read` gets useless advice, which reads as a bug in the gate."""
    cmd = "cat >> scratch/tool.py"
    msg = structural_query.refusal(structural_query.verdict(cmd, _CLAIMS)[1], cmd)
    assert "WRITES TOO" in msg
    assert "pycodemod.py" in msg
    assert "missing mode" in msg


def test_a_plain_read_does_not_get_the_write_advice() -> None:
    """⚑ THE POSITIVE CONTROL FOR THE WRITE BRANCH.

    Without this, the write cases pass against a `refusal` that appends the write paragraph
    unconditionally — and a reader pointed at an editor is the same category error one direction
    over.
    """
    assert "WRITES TOO" not in _read_message()


def test_the_deny_envelope_is_what_the_harness_reads() -> None:
    """⚑ AN EMPTY STDOUT IS READ AS *ALLOW*, so a malformed envelope is a silently-inert gate."""
    rendered: object = json.loads(structural_query.deny_payload("because"))
    decision: dict[str, str] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "because",
    }
    expected: dict[str, dict[str, str]] = {"hookSpecificOutput": decision}
    assert rendered == expected


def test_a_well_formed_payload_yields_its_command() -> None:
    """The hook reads the harness's shape, or renders a verdict about something that never ran."""
    parsed: object = json.loads(_payload_json("grep foo x.py"))
    assert structural_query.command_of(parsed) == "grep foo x.py"


def _bad_payloads() -> list[tuple[str, object]]:
    """Return the malformed payload shapes, each built through a typed local.

    Returns:
        malformed payload shapes, each built through a typed local.

    """
    non_mapping: list[str] = ["nope"]
    no_tool_input: dict[str, object] = {}
    bad_tool_input: dict[str, object] = {"tool_input": "nope"}
    numeric_command: dict[str, object] = {"command": 7}
    bad_command: dict[str, object] = {"tool_input": numeric_command}
    return [
        ("a non-mapping payload", non_mapping),
        ("a payload with no tool_input", no_tool_input),
        ("a non-mapping tool_input", bad_tool_input),
        ("a non-string command", bad_command),
    ]


@pytest.mark.parametrize(("label", "value"), _bad_payloads())
def test_a_malformed_payload_yields_no_command(label: str, value: object) -> None:
    """⚑ EVERY REJECTED SHAPE GETS A CASE — the payload is untrusted JSON, not a contract."""
    assert structural_query.command_of(value) == "", label


def test_a_command_free_payload_lets_the_call_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑ THE HOOK NEVER BREAKS A SESSION ON INPUT IT CANNOT READ.

    `main` returns 0 for a payload carrying nothing to judge, which is the same exit as a clean
    verdict — deliberately, because the alternative is a gate that fails the session over the
    harness changing a field name.
    """
    monkeypatch.setattr("sys.stdin", _stdin('{"tool_input": {}}'))
    assert structural_query.main() == 0


def test_unparseable_stdin_lets_the_call_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed JSON is tolerated; a bug in the hook's own logic is not — the excepts are named."""
    monkeypatch.setattr("sys.stdin", _stdin("{not json"))
    assert structural_query.main() == 0


def _fixed_claims() -> dict[str, tuple[str, str]]:
    """Return the test table, as a stand-in for the repo-derived reader.

    Returns:
        test table, as a stand-in for the repo-derived reader.

    """
    return _CLAIMS


def test_an_armed_hook_writes_a_deny_envelope_to_stdout(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ ARMED MEANS THE HARNESS SEES A DENY, NOT MERELY THAT A MESSAGE WAS PRINTED.

    An advisory hook writes to stderr, which the harness ignores; only the stdout envelope refuses
    the call. A hook that reports itself armed while writing to stderr detects every violation and
    refuses none.
    """
    monkeypatch.setenv(payload.SHARED_SWITCH, "1")
    monkeypatch.delenv(payload.OWN_SWITCH, raising=False)
    monkeypatch.setattr(routing_table, "claims", _fixed_claims)
    monkeypatch.setattr("sys.stdin", _stdin(_payload_json("wc -l scratch/tool.py")))
    assert structural_query.main() == 0
    assert '"deny"' in capsys.readouterr().out


def test_an_advisory_hook_writes_to_stderr_and_leaves_stdout_empty(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ THE POSITIVE CONTROL FOR ARMING, AT THE LEVEL THE HARNESS ACTUALLY READS.

    Without this the armed case passes against a hook that always denies — which is the failure
    mode the advisory default exists to avoid, since a guard whose first act is to break a working
    session trains people to disable it.
    """
    monkeypatch.delenv(payload.SHARED_SWITCH, raising=False)
    monkeypatch.delenv(payload.OWN_SWITCH, raising=False)
    monkeypatch.setattr(routing_table, "claims", _fixed_claims)
    monkeypatch.setattr("sys.stdin", _stdin(_payload_json("wc -l scratch/tool.py")))
    assert structural_query.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "structural-query" in captured.err


@pytest.mark.parametrize("tool", ["perl", "less", "more", "jq", "column"])
def test_a_pager_or_filter_reading_a_claimed_artifact_is_refused(tool: str) -> None:
    """⚑⚑ Each of these read a claimed artifact textually and PASSED, measured.

    A roster that decides what is blocked is a roster whose omissions are silent permissions —
    and unlike this repository's four enumerated populations, this one cannot be derived from a
    filesystem or a config. There is no query that yields "tool names", so it grows by
    measurement rather than by enumeration.
    """
    # ⚑ THE TABLE IS PASSED, NOT DISCOVERED. `verdict()` falls back to `routing_table.claims()`,
    # which reads the repo's SKILL.md relative to the CWD — so a test relying on the default
    # asserts against an EMPTY table under pytest and passes nothing to the gate. The first cut
    # did exactly that: five arms failed while the same commands blocked correctly from a shell.
    assert structural_query.verdict(f"{tool} notes.md", _CLAIMS)[0], (
        f"{tool} reads a claimed artifact textually and must be refused")


def test_the_interpreter_is_not_listed_because_it_is_the_prescribed_route() -> None:
    """⚑⚑⚑ A known opening, recorded so it is not mistaken for an oversight.

    `python3 -m mikemol.mdstruct.cli spans f.md` is the route this hook PRESCRIBES, so listing
    the interpreter would refuse the answer alongside the question. ⚑ An interpreter is not a
    tool, it is a way to be any tool, and no name-based roster can separate the two.

    ⚑ A reader meeting the roster cannot otherwise tell whether `python3` was considered and
    excluded or simply forgotten — and those warrant different responses: the first is a
    boundary, the second is a bug.
    """
    assert not structural_query.verdict(
        "python3 -m mikemol.mdstruct.cli spans notes.md", _CLAIMS)[0], (
        "the owning tool's own invocation must not be refused")


def test_a_command_that_touches_without_reading_is_permitted() -> None:
    """⚑ The P-arm for the denylist's SHAPE, and it is why an allowlist was rejected.

    Eight commands touch a claimed artifact without reading it textually — `git add`, `rm`,
    `cp`, `mv`, `ls`, `chmod`, `git diff`, the owning tool. An allowlist would have to enumerate
    every one of those plus whatever a future workflow reaches for; that population is unbounded
    and its omissions REFUSE legitimate work, where a denylist's omissions merely fail to catch
    one. Both are hand-written; only one fails safe.
    """
    for cmd in ("git add notes.md", "rm notes.md", "cp notes.md other.md", "chmod 644 notes.md"):
        assert not structural_query.verdict(cmd, _CLAIMS)[0], (
            f"{cmd} does not read the file and must be permitted")


@pytest.mark.parametrize("tool", ["hexdump", "vim", "sdiff", "col", "base64", "ed"])
def test_a_reader_or_editor_found_on_the_host_is_refused(tool: str) -> None:
    """⚑⚑ A second pass, measured against tools ACTUALLY INSTALLED rather than imagined.

    Twenty-six more were present on the host and absent from the roster. ⚑ Enumerating what a
    machine has is not the same as enumerating what could exist — but it is a real population,
    where a list written from memory is a guess about one.
    """
    assert structural_query.verdict(f"{tool} notes.md", _CLAIMS)[0], (
        f"{tool} reads a claimed artifact as text and must be refused")


@pytest.mark.parametrize(
    ("tool", "why"),
    [
        ("pandoc", "mdstruct's own backend — blocking it blocks the prescribed route"),
        ("tee", "consumes stdin and WRITES the named path; it never reads it"),
        ("xargs", "consumes stdin; the named path is not opened"),
    ],
)
def test_a_non_reader_on_the_host_is_permitted(tool: str, why: str) -> None:
    """⚑⚑⚑ The roster encodes READS A CLAIMED ARTIFACT AS TEXT, not "processes text".

    Getting that wrong costs something in both directions, and they are not symmetric: an
    omission fails to catch one command, while an over-inclusion REFUSES one that was never the
    problem. ⚑ A denylist entry firing on a non-reader is the allowlist's failure mode arriving
    by the back door.
    """
    assert not structural_query.verdict(f"{tool} notes.md", _CLAIMS)[0], f"{tool}: {why}"
