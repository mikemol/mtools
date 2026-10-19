# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Bash guard refuses a command that writes a file past the edit bar (W1560, step two).

⚑ STEP ONE (`writeguard`, 74749cb) IS THE FINDER; THIS IS ITS CALL IN THE LIVE HOOK. It could not be
wired until the bazel-built hooks venv linked `writeguard.py`, since a guard hook that crashes fails
OPEN. The witnesses run `no_chaining.analyze` with a project root and `no_chaining.main` on a
payload, and the one that matters is the refusal naming the project tree and the way out.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import no_chaining

if TYPE_CHECKING:
    import pytest

ROOT = Path("/repo")


def _tokens(findings: list[tuple[str, str]]) -> list[str]:
    return [token for token, _why in findings]


def test_a_redirect_into_the_project_is_a_finding_and_plain_text_is_not() -> None:
    """The positive control and its absence: the same hook, a write and then nothing."""
    assert ">" in _tokens(no_chaining.analyze("cat > x.py <<EOF\nhi\nEOF", ROOT, ROOT))
    assert not no_chaining.analyze("echo hi", ROOT, ROOT)


def test_with_no_root_only_the_location_free_tells_apply() -> None:
    """An unknown project root is never guessed: perl is refused, a redirect is left alone."""
    assert "perl" in _tokens(no_chaining.analyze("perl -pe 1 x.py"))
    assert ">" not in _tokens(no_chaining.analyze("echo a > x.py"))


def test_main_denies_a_write_into_the_project_and_names_the_way_out(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The deny the harness reads: the project tree is named and so is Write or Edit."""
    body: dict[str, object] = {"tool_input": {"command": "echo a > x.py"}, "cwd": str(ROOT)}
    monkeypatch.setenv("NOCHAIN_HOOK_BLOCK", "1")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(ROOT))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(body)))
    assert no_chaining.main() == 0
    said = capsys.readouterr().out
    assert "a redirect into the project tree" in said
    assert "Write or Edit the file" in said
