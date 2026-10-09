# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Survey each repo's pre-commit hook: where it lives and whether it invokes bazel (W796, W876).

Ported from the host katas.py `precommit_survey`. The operator's rule (2026-10-06): a pre-commit
should be a bazel build, with the gate logic in a BUILD file, so BuildBuddy captures its logs and
artifacts. "Invokes bazel" is the test here (a non-comment line of the hook names bazel); whether
the logic is in a BUILD file is the next step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.katas import fleet, workstreams

if TYPE_CHECKING:
    from pathlib import Path

NO_HOOK = "NO HOOK"
BAZEL = "BAZEL"
SCRIPT = "script"
_DEFAULT_HOOKS = ".git/hooks"
_SNIPPET = 60


@dataclass(frozen=True)
class HookRow:
    """One repo's hook: the verdict, where the hook is (or would be), and the first bazel line."""

    repo: str
    verdict: str
    where: str
    first_bazel_line: str = ""


def bazel_lines(text: str) -> list[str]:
    """Pick the non-comment lines of a hook that name bazel.

    Returns:
        each such line, stripped.

    """
    return [
        line.strip()
        for line in text.splitlines()
        if "bazel" in line and not line.lstrip().startswith("#")
    ]


def hook_row(host: fleet.Fleet, repo: str) -> HookRow:
    """Survey one repo's pre-commit hook.

    ⚑ `core.hooksPath` DECIDES WHERE THE HOOK IS: a repo that sets it (`.githooks`) keeps its hook
    there, and reading `.git/hooks` for it would call a gated repo hookless.

    Returns:
        the verdict (NO HOOK, BAZEL or script), the hook's repo-relative path, and the first line
        of it that names bazel, cut to a snippet.

    """
    root: Path = host.root / repo
    configured = fleet.git(host, repo, "config", "core.hooksPath").strip()
    hook = root / (configured or _DEFAULT_HOOKS) / "pre-commit"
    if not hook.exists():
        return HookRow(repo, NO_HOOK, configured or "default hooks dir")
    lines = bazel_lines(hook.read_text(encoding="utf-8", errors="replace"))
    verdict = BAZEL if lines else SCRIPT
    return HookRow(repo, verdict, str(hook.relative_to(root)), lines[0][:_SNIPPET] if lines else "")


def survey(host: fleet.Fleet) -> list[HookRow]:
    """Survey every workstream's pre-commit hook.

    Returns:
        one row per workstream, in the workstreams' sorted order.

    """
    return [hook_row(host, repo) for repo in workstreams.repos(host.root)]
