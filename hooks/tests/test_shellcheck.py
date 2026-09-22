# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The shell hook: which files are shell, what the linter says, and what an absent linter does.

⚑ PORTED FROM substrate's in-file selftest (letter 2026-09-22), one case per function. The trap
case is INVERTED into a pair: substrate's passed only because of an SC2329 waiver this package does
not inherit, so the pair asserts the waiver mechanism instead of one tree's waiver.

⚑ THE LINTER ARMS ARE MARKED AND SKIP WITH A REASON when no shellcheck is found — a skip is visible
in the run, a silent pass is not.
"""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import shellcheck

if TYPE_CHECKING:
    from pathlib import Path

_NO_LINTER = shellcheck.linter() is None
_needs_linter = pytest.mark.skipif(_NO_LINTER, reason="no shellcheck on PATH or at the mise shim")

_TRAP = (
    '#!/usr/bin/env bash\nset -uo pipefail\nT="$(mktemp)"\ncleanup() { rm -f "$T"; }\n'
    "trap cleanup EXIT\necho hi\nexit 0\n"
)


def _codes(found: list[shellcheck.Finding] | None) -> list[str]:
    """Return the rule codes of a verdict, failing loudly on UNKNOWN.

    Returns:
        the codes, in order.

    """
    assert found is not None, "the linter rendered no verdict"
    return [code for code, _line, _msg in found]


# --- which files are shell ---

def test_a_sh_path_is_bash() -> None:
    """A `.sh` path with no shebang is bash, the house default."""
    assert shellcheck.shell_dialect("x.sh", "echo hi") == "bash"


def test_a_bash_shebang_is_bash() -> None:
    """A `#!/bin/bash` shebang is bash whatever the name."""
    assert shellcheck.shell_dialect("configure", "#!/bin/bash\necho hi") == "bash"


def test_a_sh_shebang_is_sh() -> None:
    """A `#!/bin/sh` shebang is the sh dialect, not bash."""
    assert shellcheck.shell_dialect("x", "#!/bin/sh\necho hi") == "sh"


def test_an_env_style_shebang_is_read() -> None:
    """`#!/usr/bin/env bash` is read through `env`."""
    assert shellcheck.shell_dialect("x", "#!/usr/bin/env bash\necho hi") == "bash"


def test_a_python_shebang_in_a_sh_file_is_not_shell() -> None:
    """The shebang outranks the suffix: a `.sh` file that is really python is not linted."""
    assert shellcheck.shell_dialect("x.sh", "#!/usr/bin/env python3\nprint(1)") is None


def test_a_plain_python_file_is_not_shell() -> None:
    """A `.py` file with no shebang is not shell."""
    assert shellcheck.shell_dialect("x.py", "print(1)") is None


def test_zsh_is_not_lintable() -> None:
    """A zsh shebang is an answer — not shell shellcheck can read — not a miss."""
    assert shellcheck.shell_dialect("x.zsh", "#!/bin/zsh\necho hi") is None


def test_a_zsh_suffix_without_a_shebang_is_not_lintable() -> None:
    """A `.zsh` fragment is not defaulted to bash."""
    assert shellcheck.shell_dialect("x.zsh", "echo hi") is None


def test_a_byte_order_mark_does_not_hide_the_shebang() -> None:
    """A leading BOM is stripped before the shebang is read."""
    assert shellcheck.shell_dialect("x", "﻿#!/bin/sh\necho hi") == "sh"


def test_a_markdown_file_is_not_shell() -> None:
    """Markdown with a backticked command in it is not shell."""
    assert shellcheck.shell_dialect("README.md", "# notes\n`echo hi`") is None


def test_a_non_shell_file_is_not_linted() -> None:
    """A non-shell file is `[]` BEFORE the linter is looked for — no linter needed."""
    assert shellcheck.analyze_file("x.py", "import os\nprint(os.getcwd())") == []


# --- the tree's waivers ---

def _tree(tmp_path: Path, table: str) -> str:
    """Write a pyproject carrying `table` and return a shell path it governs.

    Returns:
        the path of a script under the fixture project.

    """
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "fixture"\n\n[tool.mikemol-hooks.shellcheck.exclude]\n{table}\n',
        encoding="utf-8",
    )
    return str(tmp_path / "run.sh")


def test_a_dated_warrant_waives_its_code(tmp_path: Path) -> None:
    """A code with a dated warrant longer than the minimum is in the governing set."""
    path = _tree(tmp_path, 'SC2016 = "single-quoted bash -c bodies, measured 4 sites 2026-09-22"')
    assert shellcheck.exclude_for(path) == frozenset({"SC2016"})


def test_an_undated_warrant_waives_nothing(tmp_path: Path) -> None:
    """A warrant naming no year is suppression, not relief: the code is not waived.

    ⚑ THE POSITIVE CONTROL SITS IN THE SAME FIXTURE: a dated sibling IS waived, so an empty
    reader cannot pass this arm.
    """
    path = _tree(
        tmp_path,
        'SC2016 = "single quotes are intended in the generated scripts here"\n'
        'SC2086 = "word splitting is the intent at these sites, measured 2026-09-22"',
    )
    waived = shellcheck.exclude_for(path)
    assert "SC2086" in waived
    assert "SC2016" not in waived


def test_a_short_warrant_waives_nothing(tmp_path: Path) -> None:
    """A dated warrant too short to say what was measured waives nothing."""
    path = _tree(
        tmp_path,
        'SC2016 = "ok 2026"\nSC2086 = "word splitting is the intent at these sites, measured 2026"',
    )
    waived = shellcheck.exclude_for(path)
    assert "SC2086" in waived
    assert "SC2016" not in waived


def test_a_list_of_bare_codes_waives_nothing(tmp_path: Path) -> None:
    """A list is not the table's shape; it waives nothing rather than everything it names."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n\n[tool.mikemol-hooks.shellcheck]\nexclude = ["SC2016"]\n',
        encoding="utf-8",
    )
    assert shellcheck.exclude_for(str(tmp_path / "run.sh")) == frozenset()


def test_no_governing_project_waives_nothing() -> None:
    """With no path there is no project, and the package set — empty — applies."""
    assert shellcheck.exclude_for("") == frozenset()


def test_an_unparseable_pyproject_waives_nothing(tmp_path: Path) -> None:
    """A pyproject that is not TOML yields the package set, not a crash."""
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    assert shellcheck.exclude_for(str(tmp_path / "run.sh")) == frozenset()


# --- the linter's output, narrowed ---

def test_a_json1_comment_becomes_a_finding() -> None:
    """A well-formed comment becomes (code, line, message)."""
    raw = {"comments": [{"code": 2086, "line": 3, "message": " Double quote. "}]}
    assert shellcheck.findings_of(raw) == [("SC2086", 3, "Double quote.")]


def test_a_waived_code_is_dropped_and_its_neighbour_kept() -> None:
    """The exclude set drops its codes and only its codes."""
    raw = {"comments": [{"code": 2086, "line": 1, "message": "a"},
                        {"code": 2016, "line": 2, "message": "b"}]}
    assert _codes(shellcheck.findings_of(raw, frozenset({"SC2016"}))) == ["SC2086"]


def test_a_non_mapping_output_yields_no_findings() -> None:
    """An output shape this hook does not read yields no findings, not a wrong verdict."""
    assert shellcheck.findings_of(["not", "a", "mapping"]) == []


def test_a_non_list_comments_field_yields_no_findings() -> None:
    """`comments` that is not a list yields no findings."""
    assert shellcheck.findings_of({"comments": "none"}) == []


def test_a_non_integer_line_reads_as_zero() -> None:
    """A malformed line number is 0 — visibly wrong rather than silently shifted."""
    assert shellcheck.findings_of({"comments": [{"code": 1, "line": "3"}]}) == [("SC1", 0, "")]


# --- what the edit will put on disk ---

def test_write_carries_the_whole_content() -> None:
    """A Write's content is the post-edit file, exactly."""
    got = shellcheck.post_edit_content("Write", {"file_path": "a.sh", "content": "echo 1"})
    assert got == ("a.sh", "echo 1")


def test_an_unreadable_edit_target_is_unknown() -> None:
    """An Edit whose target cannot be read yields None — unknown, not a guess."""
    tool_input: dict[str, object] = {
        "file_path": "/nonexistent/zz.sh", "old_string": "a", "new_string": "b"}
    assert shellcheck.post_edit_content("Edit", tool_input)[1] is None


def test_an_edit_replaces_the_first_occurrence_only(tmp_path: Path) -> None:
    """An Edit without `replace_all` applies once, as the harness does."""
    target = tmp_path / "a.sh"
    target.write_text("x x", encoding="utf-8")
    tool_input: dict[str, object] = {"file_path": str(target), "old_string": "x", "new_string": "y"}
    assert shellcheck.post_edit_content("Edit", tool_input)[1] == "y x"


def test_an_edit_with_replace_all_replaces_every_occurrence(tmp_path: Path) -> None:
    """`replace_all` applies the edit everywhere."""
    target = tmp_path / "a.sh"
    target.write_text("x x", encoding="utf-8")
    tool_input: dict[str, object] = {
        "file_path": str(target), "old_string": "x", "new_string": "y", "replace_all": True}
    assert shellcheck.post_edit_content("Edit", tool_input)[1] == "y y"


def test_another_tool_carries_no_content() -> None:
    """A tool that writes nothing this hook can reconstruct yields None."""
    assert shellcheck.post_edit_content("Read", {"file_path": "a.sh"})[1] is None


# --- the repair exemption ---

def test_installing_the_linter_is_a_repair() -> None:
    """`mise use -g shellcheck@latest` is the repair the refusal names."""
    assert shellcheck.is_repair("mise use -g shellcheck@latest")


def test_installing_something_else_is_not_a_repair() -> None:
    """The package manager alone is not exempt: `apt install jq` stays refused."""
    assert not shellcheck.is_repair("apt install jq")


# --- the real linter ---

@pytest.mark.needs_shellcheck
@_needs_linter
def test_an_unquoted_expansion_is_caught() -> None:
    """`[ $f = x ]` is a finding — the T-arm."""
    assert _codes(shellcheck.analyze_command("f=$1; [ $f = x ] && echo hi"))


@pytest.mark.needs_shellcheck
@_needs_linter
def test_clean_shell_passes() -> None:
    """`echo "hello"` is measured-clean — the F-arm, without which the hook could deny all."""
    assert shellcheck.analyze_command('echo "hello"') == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_clean_file_passes() -> None:
    """A clean bash file is measured-clean."""
    body = '#!/usr/bin/env bash\nset -euo pipefail\necho "hi"\n'
    assert shellcheck.analyze_file("x.sh", body) == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_trap_handler_before_an_exit_fires_with_no_waiver() -> None:
    """With an empty exclude set, SC2329 fires on a trap handler before `exit 0`.

    ⚑ INVERTED FROM THE ORIGIN, where this passed only because the origin waived SC2329.
    """
    assert "SC2329" in _codes(shellcheck.analyze_file("x.sh", _TRAP))


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_trap_handler_before_an_exit_passes_with_its_waiver() -> None:
    """With SC2329 waived, the same script is clean — the waiver reaches the linter's verdict."""
    assert shellcheck.analyze_file("x.sh", _TRAP, frozenset({"SC2329"})) == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_finding_on_the_first_line_reports_line_one() -> None:
    """The synthetic preamble is invisible: the operator's first line is line 1."""
    found = shellcheck.analyze_command("[ $x = y ]")
    assert found is not None
    assert {line for _code, line, _msg in found} == {1}


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_fragment_earns_no_missing_shebang_finding() -> None:
    """SC2148 is about the wrapper, never reported for a command fragment.

    ⚑ THE POSITIVE CONTROL IS IN THE SAME FUNCTION: the same fragment's defect IS reported, so
    an empty verdict cannot pass this arm.
    """
    codes = _codes(shellcheck.analyze_command("echo $x"))
    assert codes
    assert "SC2148" not in codes


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_commit_message_heredoc_body_is_data() -> None:
    """Prose with `$word` and backticks in a heredoc body is not linted as shell."""
    assert shellcheck.analyze_command("git commit -F - <<EOF\nfix $thing and `x`\nEOF") == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_neutralizing_does_not_unterminate_the_document() -> None:
    """Quoting the tag leaves the heredoc terminated: no SC1044/SC1072."""
    assert shellcheck.analyze_command("cat <<EOF\nhi\nEOF") == []


@pytest.mark.needs_shellcheck
@_needs_linter
def test_a_finding_after_a_heredoc_keeps_its_true_line() -> None:
    """Real shell after a heredoc still lints, on its own line — the body was quoted, not cut."""
    found = shellcheck.analyze_command("cat <<EOF\nprose $v\nEOF\n[ $x = y ]")
    assert found is not None
    assert [line for _code, line, _msg in found] == [4, 4]


@pytest.mark.needs_shellcheck
@_needs_linter
def test_an_already_quoted_heredoc_tag_is_left_alone() -> None:
    """A quoted tag is not re-quoted, and its body stays data."""
    assert shellcheck.analyze_command("cat <<'EOF'\nprose $v\nEOF") == []


# --- the hook, through main() ---

def _main(
    monkeypatch: pytest.MonkeyPatch, record: dict[str, object], *, own: str | None, shared: str
) -> None:
    """Run `main()` over one payload with the switches set as given."""
    if own is None:
        monkeypatch.delenv(shellcheck.OWN_SWITCH, raising=False)
    else:
        monkeypatch.setenv(shellcheck.OWN_SWITCH, own)
    monkeypatch.setenv("STRUCT_HOOK_BLOCK", shared)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(record)))
    assert shellcheck.main() == 0


def _absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Make the linter unfindable: an empty PATH and a shim that does not exist."""
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(shellcheck, "MISE_SHIM", tmp_path / "no-shim")


_BASH: dict[str, object] = {"tool_name": "Bash", "tool_input": {"command": "echo hi"}}


def test_an_armed_hook_with_no_linter_refuses_and_names_the_repair(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Armed with no linter: a deny naming the install — never a silent allow."""
    _absent(monkeypatch, tmp_path)
    _main(monkeypatch, _BASH, own="1", shared="0")
    out = capsys.readouterr().out
    assert '"deny"' in out
    assert "mise use -g shellcheck@latest" in out


def test_an_unarmed_hook_with_no_linter_advises_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Unarmed with no linter: nothing on stdout, the advisory on stderr."""
    _absent(monkeypatch, tmp_path)
    _main(monkeypatch, _BASH, own="0", shared="0")
    got = capsys.readouterr()
    assert not got.out
    assert "cannot render a verdict" in got.err


def test_an_armed_hook_with_no_linter_admits_the_install(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The install the refusal names is admitted, and says so — no deadlock."""
    _absent(monkeypatch, tmp_path)
    record: dict[str, object] = {
        "tool_name": "Bash", "tool_input": {"command": "mise use -g shellcheck@latest"}}
    _main(monkeypatch, record, own="1", shared="0")
    got = capsys.readouterr()
    assert not got.out
    assert "ADMITTING" in got.err


def test_an_armed_hook_with_no_linter_admits_a_non_shell_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A non-shell file never reaches the linter, so the settings stay editable.

    ⚑ THE CONTROL IS THE ARM ABOVE THIS FILE'S FIRST: the same environment denies a Bash call.
    """
    _absent(monkeypatch, tmp_path)
    record: dict[str, object] = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "settings.json"), "content": "{}"}}
    _main(monkeypatch, record, own="1", shared="0")
    assert not capsys.readouterr().out


def test_an_unparseable_verdict_is_refused_as_unknown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A present linter that returns no parseable verdict is UNKNOWN, and refused as such."""
    fake = tmp_path / "shellcheck"
    fake.write_text("#!/bin/sh\necho not-json\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    _main(monkeypatch, _BASH, own="1", shared="0")
    out = capsys.readouterr().out
    assert '"deny"' in out
    assert "no parseable verdict" in out


def test_the_own_switch_at_zero_stands_down_over_the_shared_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`SHELLCHECK_HOOK_BLOCK=0` wins over `STRUCT_HOOK_BLOCK=1`: no deny."""
    _absent(monkeypatch, tmp_path)
    _main(monkeypatch, _BASH, own="0", shared="1")
    assert not capsys.readouterr().out


def test_the_shared_switch_arms_when_the_own_one_is_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """With its own switch unset, the shared one arms this hook — by ITS name, not pycheck's."""
    _absent(monkeypatch, tmp_path)
    monkeypatch.setenv("PYCHECK_HOOK_BLOCK", "0")
    _main(monkeypatch, _BASH, own=None, shared="1")
    assert '"deny"' in capsys.readouterr().out


@pytest.mark.needs_shellcheck
@_needs_linter
def test_an_armed_hook_denies_a_finding_and_names_the_rule(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Armed, a linted defect is a deny naming the rule and the pyproject waiver table."""
    record: dict[str, object] = {"tool_name": "Bash", "tool_input": {"command": "[ $x = y ]"}}
    _main(monkeypatch, record, own="1", shared="0")
    out = capsys.readouterr().out
    assert "SC2086" in out
    assert "tool.mikemol-hooks.shellcheck.exclude" in out


@pytest.mark.needs_shellcheck
@_needs_linter
def test_an_armed_hook_allows_clean_shell(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Armed, clean shell produces no decision — the not-deny arm."""
    record: dict[str, object] = {"tool_name": "Bash", "tool_input": {"command": 'echo "hi"'}}
    _main(monkeypatch, record, own="1", shared="0")
    assert not capsys.readouterr().out


def test_a_malformed_payload_denies_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Garbage on stdin exits 0 and denies nothing."""
    monkeypatch.setenv(shellcheck.OWN_SWITCH, "1")
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert shellcheck.main() == 0
    assert not capsys.readouterr().out
