# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The no-chaining gate: what it refuses, what it must not refuse, and what it says.

⚑ TWO-ARMED THROUGHOUT. Every rule gets a case that FIRES and a case that PASSES, because a
one-armed test passes a broken-shut gate: a hook that refuses everything satisfies every
fires_on case ever written. The false-positive block is not politeness — it is the arm that
makes the refusals mean something.

⚑ ACTION PER TEST. One assertion of one claim per function, so a failure names the claim rather
than a group.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import cmdparse, no_chaining

if TYPE_CHECKING:
    import pytest


# --- the composition operators -------------------------------------------------------------

def test_a_pipe_fires() -> None:
    """A pipe is refused: the tool should have the mode that produces this directly."""
    assert no_chaining.analyze("scripts/buildtime.py --top | tail -5")


def test_and_and_fires() -> None:
    """`&&` is refused: two questions that want one mode."""
    assert no_chaining.analyze("make -C agda -j && echo done")


def test_semicolon_fires() -> None:
    """`;` is refused: run the calls separately."""
    assert no_chaining.analyze("cd agda; make")


def test_or_or_fires() -> None:
    """`||` is refused: a shell fallback over an error string is judgement-in-turn."""
    assert no_chaining.analyze("make || echo failed")


def test_pipe_ampersand_fires() -> None:
    """`|&` is refused — the operator the origin's private copy LACKED.

    ⚑ shlex with `punctuation_chars=True` emits `|&` as ONE token, so a hand-written literal
    that listed `|` and `&` separately did not cover it: `make |& grep foo` was ALLOWED while
    `make | grep foo` was denied. Three confirmations agreed with the gap (a stale comment, an
    `--explain` that was right for the wrong reason, and a green selftest proving the arms the
    hook HAD) before anyone ran the tokenizer.
    """
    assert no_chaining.analyze("make |& grep foo x.py")


def test_background_ampersand_fires() -> None:
    """`&` is refused: use run_in_background, not shell control flow."""
    assert no_chaining.analyze("long_job.py &")


def test_operator_coverage_is_derived_not_restated() -> None:
    """Every operator the shared tokenizer knows is covered here, BY CONSTRUCTION.

    ⚑ THIS IS THE ARM THAT RETIRES THE `|&` CLASS RATHER THAN PATCHING ONE INSTANCE. A
    hand-written literal beside the authority is the two-bodies shape; an operator added to
    `cmdparse.OPERATORS` is covered here without an edit, and this case fails if that ever
    stops being true.
    """
    assert set(no_chaining.OPERATORS) >= cmdparse.OPERATORS


# --- shell control flow --------------------------------------------------------------------

def test_a_for_loop_fires() -> None:
    """`for` in command position is refused: the iteration belongs in a program."""
    assert no_chaining.analyze("for f in *.py; do wc -l $f; done")


def test_a_case_dispatch_fires() -> None:
    """`case` is refused: the classic judgement-not-in-code shape."""
    assert no_chaining.analyze("case $x in a) echo 1;; esac")


def test_an_until_loop_fires() -> None:
    """`until` is refused: same as `for`, the loop belongs to the tool."""
    assert no_chaining.analyze("until test -e f; do sleep 1; done")


# --- `cd`, and the message that must route ---------------------------------------------------

def test_a_bare_cd_fires_on_its_own() -> None:
    """`cd` alone is refused: it mutates state every later command inherits."""
    assert no_chaining.analyze("cd agda")


def test_the_cd_message_names_env_dash_c() -> None:
    """The refusal names `env -C` — the one-call form that replaces it.

    ⚑ A REFUSAL THAT ONLY BLOCKS IS HALF A GATE. The `&&` verdict was already correct on
    `cd x && make`, but its text ("two questions that want one mode") is useless there. The
    caller acts on the message.
    """
    assert "env -C" in no_chaining.refusal(no_chaining.analyze("cd agda && make -j"))


def test_the_cd_message_says_why() -> None:
    """The refusal explains the mechanism: the directory is an INPUT, not ambient state."""
    assert "ambient effect" in no_chaining.refusal(no_chaining.analyze("cd agda && make -j"))


def test_the_recommended_env_dash_c_form_passes() -> None:
    """The replacement this hook recommends must itself pass.

    ⚑ Otherwise the advice routes into a second refusal, and the gate blocks without routing.
    """
    assert not no_chaining.analyze("env -C agda make -j")


# --- the inline interpreter -------------------------------------------------------------------

def test_python_dash_c_fires() -> None:
    """`python3 -c` is refused: the program dies with the turn."""
    assert no_chaining.analyze('python3 -c "import ast; print(1)"')


def test_a_wrapper_does_not_hide_an_inline_script() -> None:
    """`timeout 300 python3 -c` is refused: the interpreter is seen anywhere, not just first."""
    assert no_chaining.analyze('timeout 300 python3 -c "print(1)"')


def test_an_env_prefix_does_not_hide_an_inline_script() -> None:
    """`PYTHONPATH=x python3 -c` is refused: an env prefix is not command position."""
    assert no_chaining.analyze('PYTHONPATH=scratch python3 -c "print(1)"')


def test_a_stdin_script_fires() -> None:
    """`python3 - < prog.py` is refused: the program arrives on stdin."""
    assert no_chaining.analyze("python3 - < prog.py")


def test_a_heredoc_into_an_interpreter_fires() -> None:
    """`python3 <<PY` is refused: the redirection is the only tell, and it is enough."""
    assert no_chaining.analyze("python3 <<PY\nprint(1)\nPY")


def test_perl_dash_e_fires() -> None:
    """`perl -e` is refused: the rule is about inline programs, not about Python."""
    assert no_chaining.analyze('perl -e "print 1"')


# --- the false positives: each CONTAINS a banned character and composes nothing ---------------

def test_a_quoted_pipe_in_a_regex_is_data() -> None:
    """`grep -nE 'foo|bar'` passes: a `|` inside quotes is data, not an operator."""
    assert not no_chaining.analyze("grep -nE 'foo|bar' notes.md")


def test_a_semicolon_inside_an_awk_body_is_data() -> None:
    """`awk '{print; n++}'` passes: the `;` belongs to awk's language, not to bash."""
    assert not no_chaining.analyze("awk '{print; n++}' data.tsv")


def test_for_inside_a_filename_is_not_a_keyword() -> None:
    """`format_for_each.py` passes: `for` is a keyword only in command position."""
    assert not no_chaining.analyze("python3 scripts/format_for_each.py")


def test_for_as_an_argument_is_not_a_keyword() -> None:
    """`grep -w for notes.md` passes: an argument is not command position."""
    assert not no_chaining.analyze("grep -w for notes.md")


def test_cd_as_an_argument_is_not_a_chdir() -> None:
    """`grep -w cd notes.md` passes: the same command-position guard covers `cd`."""
    assert not no_chaining.analyze("grep -w cd notes.md")


def test_a_plain_single_call_passes() -> None:
    """One tool call with flags is exactly the behaviour the rule WANTS."""
    assert not no_chaining.analyze("scripts/worklist_gate.py --order")


def test_running_a_real_script_passes() -> None:
    """`python3 scripts/x.py` passes: invoking a COMMITTED tool is the point.

    ⚑ If this fires, the hook has inverted its own purpose — it would refuse the very move it
    tells refused callers to make.
    """
    assert not no_chaining.analyze("python3 scripts/worklist_gate.py --order")


def test_python_dash_m_on_a_real_module_passes() -> None:
    """`python3 -m json.tool` passes: `-m` names a committed module, unlike `-c`."""
    assert not no_chaining.analyze("python3 -m json.tool data.json")


def test_a_bare_repl_is_not_a_script() -> None:
    """`python3` alone passes: with no args it is a REPL, not an inline program."""
    assert not no_chaining.analyze("python3")


def test_an_interpreter_named_as_an_argument_passes() -> None:
    """`grep -rn python3 notes.md` passes: the word is data here."""
    assert not no_chaining.analyze("grep -rn python3 notes.md")


def test_an_unparseable_command_is_allowed_through() -> None:
    """An unbalanced quote is bash's verdict, not ours — never break a session on a parse error."""
    assert not no_chaining.analyze("echo 'unterminated")


# --- heredoc bodies are data ------------------------------------------------------------------

def test_prose_in_a_heredoc_body_is_not_composition() -> None:
    """A commit message DESCRIBING shell is not shell.

    ⚑ THE FIRST MEASURED FALSE POSITIVE AFTER ARMING, in the origin tree. Claude Code ships no
    commit tool, so every multi-line message goes through `git commit -F - <<EOF` — and a
    message that merely NAMED the operators the hook had just caught was refused. The hook
    blocked a single tool call because of the content of its own argument.
    """
    assert not no_chaining.analyze("git commit -F - <<EOF\nfixed a ; b and c | d and e || f\nEOF")


def test_a_quoted_heredoc_tag_is_handled() -> None:
    """`<<'EOF'` is a heredoc too: the quoting of the tag does not change the body's status."""
    assert not no_chaining.analyze("cat > f <<'EOF'\na | b\nEOF")


def test_an_operator_after_a_heredoc_still_fires() -> None:
    """The strip must not overreach: shell AFTER the terminator is still shell."""
    assert no_chaining.analyze("git commit -F - <<EOF\nmsg\nEOF\necho done | wc -l")


# --- the refusal text and the deny envelope ----------------------------------------------------

def test_the_refusal_names_the_offending_token() -> None:
    """The message names `|`, so the caller knows which token to remove."""
    assert "`|`" in no_chaining.refusal(no_chaining.analyze("make | tail -5"))


def test_the_refusal_says_a_missing_mode_is_the_work() -> None:
    """The message routes: no mode is WORK, not grounds for a composition."""
    assert "add the" in no_chaining.refusal(no_chaining.analyze("make | tail -5"))


def test_the_refusal_names_the_discarded_exit_status() -> None:
    """The message names the rc-swallowing mechanism, not only the judgement one.

    ⚑ THIS SENTENCE IS HERE BECAUSE OF A MEASURED INCIDENT IN THIS REPO (2026-09-06). A peer's
    tool was reported as exiting 0 on a `ModuleNotFoundError` traceback; it exits 1, and the
    `| tail -1` in the probe meant `$?` was TAIL's status. The generic "judgement in the turn"
    text would not have named that, and it is the failure a reader is most likely to be in the
    middle of committing when this hook fires.
    """
    assert "TAIL's rc" in no_chaining.refusal(no_chaining.analyze("make | tail -5"))


def test_the_deny_envelope_names_the_event() -> None:
    """The envelope carries `PreToolUse` — the harness reads an empty stdout as ALLOW."""
    assert "PreToolUse" in no_chaining.deny_payload("x")


def test_the_deny_envelope_carries_the_decision() -> None:
    """The envelope carries `"deny"`, or the gate is silently inert."""
    assert '"deny"' in no_chaining.deny_payload("x")


def test_the_deny_envelope_carries_the_reason() -> None:
    """The envelope carries the reason text, so the refusal reaches the caller."""
    assert "no-chaining" in no_chaining.deny_payload(
        no_chaining.refusal(no_chaining.analyze("make | tail -5")))


# --- the payload reader: a hook that mis-reads its input judges the wrong thing -----------------

def test_a_well_formed_payload_yields_its_command() -> None:
    """The reader extracts the command from a well-formed PreToolUse payload."""
    assert no_chaining.command_of({"tool_input": {"command": "a | b"}}) == "a | b"


def test_a_non_string_command_yields_no_command() -> None:
    """A non-string `command` is rejected by a runtime check, not asserted away."""
    assert not no_chaining.command_of({"tool_input": {"command": 7}})


def test_a_non_mapping_payload_yields_no_command() -> None:
    """A payload that is not a mapping yields nothing rather than raising."""
    assert not no_chaining.command_of(["nope"])


def test_a_payload_with_no_tool_input_yields_no_command() -> None:
    """A payload missing `tool_input` yields nothing rather than raising."""
    assert not no_chaining.command_of({})


def test_a_non_mapping_tool_input_yields_no_command() -> None:
    """A `tool_input` that is not a mapping yields nothing rather than raising."""
    assert not no_chaining.command_of({"tool_input": "nope"})


# --- arming ------------------------------------------------------------------------------------

def test_the_shared_switch_arms_the_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    """`STRUCT_HOOK_BLOCK=1` arms this hook along with its sibling."""
    monkeypatch.delenv("NOCHAIN_HOOK_BLOCK", raising=False)
    monkeypatch.setenv("STRUCT_HOOK_BLOCK", "1")
    assert no_chaining.armed()


def test_an_explicit_off_beats_the_shared_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """`NOCHAIN_HOOK_BLOCK=0` stands this hook down while the shared switch is on.

    ⚑ Reading the two as a bare `or` makes staging one hook ahead of the other impossible.
    """
    monkeypatch.setenv("STRUCT_HOOK_BLOCK", "1")
    monkeypatch.setenv("NOCHAIN_HOOK_BLOCK", "0")
    assert not no_chaining.armed()


def test_unset_switches_leave_the_hook_unarmed(monkeypatch: pytest.MonkeyPatch) -> None:
    """With neither switch set the hook advises rather than denies."""
    monkeypatch.delenv("STRUCT_HOOK_BLOCK", raising=False)
    monkeypatch.delenv("NOCHAIN_HOOK_BLOCK", raising=False)
    assert not no_chaining.armed()


# --- end to end, through the real entry point --------------------------------------------------

def _run(payload: str, *, block: str) -> subprocess.CompletedProcess[str]:
    """Drive the module's `main()` in a subprocess with a synthetic PreToolUse payload.

    ⚑ THE PROBE RUNS THE HOOK RATHER THAN READING ITS CONFIG. A gate that reports what its
    config says is the green-over-nothing failure at the harness layer.
    """
    env = dict(os.environ, STRUCT_HOOK_BLOCK=block)
    env.pop("NOCHAIN_HOOK_BLOCK", None)
    return subprocess.run(
        [sys.executable, "-m", "mikemol.hooks.no_chaining"],
        input=payload, capture_output=True, text=True, env=env, check=False,
    )


def test_end_to_end_armed_a_pipe_is_denied() -> None:
    """ARMED: a piped command produces a deny decision on stdout."""
    out = _run('{"tool_input": {"command": "make | tail -5"}}', block="1")
    assert '"deny"' in out.stdout


def test_end_to_end_armed_a_single_call_is_not_denied() -> None:
    """ARMED: a single tool call produces NO decision — the not-deny arm.

    ⚑ WITHOUT THIS CASE A BROKEN-SHUT GATE PASSES THE WHOLE SUITE. Denying everything satisfies
    every deny arm; only this one can tell an armed gate from a jammed one.
    """
    out = _run('{"tool_input": {"command": "scripts/x.py --order"}}', block="1")
    assert not out.stdout.strip()


def test_end_to_end_a_malformed_payload_exits_zero() -> None:
    """Garbage on stdin exits 0: never break the session on a parse failure."""
    assert _run("not json at all", block="1").returncode == 0


def test_end_to_end_a_malformed_payload_denies_nothing() -> None:
    """Garbage on stdin denies nothing — a separate claim from the exit code.

    ⚑ SPLIT FROM THE ARM ABOVE BECAUSE `and` HIDES WHICH HALF FAILED, and the two halves fail
    for different reasons: a nonzero rc is a crashed hook, a stray deny is a hook judging a
    payload it could not read. ruff's PT018 named this, which is the action-per-test rule
    arriving from the linter rather than from review.
    """
    assert not _run("not json at all", block="1").stdout.strip()
