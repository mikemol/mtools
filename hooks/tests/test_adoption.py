# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Can a real repo ADOPT this package — asserted against a real checkout, not a fixture.

⚑⚑⚑ THIS IS THE ARC'S LOAD-BEARING CASE, AND EVERY OTHER FILE IN THIS SUITE PASSES WITHOUT IT. A
package nobody can adopt is a copy with extra steps. The rest of the suite hands the hook a table
it built in `tmp_path`, which proves the READER works and says nothing about whether an adopting
repo's real table is in the shape the reader expects, or in the place it looks.

⚑⚑ AND THE DEFECT IT GUARDS IS THE ONE THE PORT COULD MOST EASILY HAVE SHIPPED. The origin script
found its table by walking up from `__file__`; an installed distribution has no `.claude` above
its own files, so that lookup yields NOTHING here — an empty claims table, a gate that refuses
every violation it is shown by refusing none of them, and a green suite throughout, because a
fixture-built table would have kept passing. The claim count below is the positive control: a
refusal against a table of zero rows is impossible, and a pass against one is meaningless.

⚑ THE CASES SKIP RATHER THAN FAIL WHEN THE REPO IS ABSENT, AND SKIP IS NOT PASS. This suite must
run on a machine that has never seen the adopter; a case that silently passed there would report
the absence of a checkout as evidence of adoptability, which is the method-versus-substrate
confusion these hooks were written to refuse.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.hooks import routing_table, structural_query

# A checkout that declares a routing table — the adopter this package was extracted FROM, so its
# table is the one shape we know a hook in the wild must read.
_ADOPTER = Path("/home/mikemol/github/substrate")

# Below this, a "table" is furniture rather than a routing map, and a refusal proves nothing.
_ENOUGH_CLAIMS_TO_BE_A_TABLE = 2


@pytest.fixture()
def adopter(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bind the adopting repo as the governing project, or skip when it is not on this machine.

    ⚑ `CLAUDE_PROJECT_DIR` IS THE WHOLE ADOPTION MECHANISM, exercised here rather than described.
    It is how the harness tells a hook which repo the session is in, and it is what replaced the
    `__file__` walk that cannot survive being installed.
    """
    if routing_table.table_path(_ADOPTER) is None:
        pytest.skip(f"no adopting checkout at {_ADOPTER}")
    monkeypatch.setenv(routing_table.PROJECT_DIR_ENV, str(_ADOPTER))
    return _ADOPTER


def test_the_adopting_repos_own_table_is_found(adopter: Path) -> None:
    """The installed package locates the ADOPTER's table, having none of its own."""
    found = routing_table.table_path()
    assert found is not None
    assert found.is_relative_to(adopter)


def test_the_adopting_repos_table_actually_claims_artifacts(adopter: Path) -> None:
    """⚑ THE POSITIVE CONTROL FOR EVERY VERDICT BELOW.

    An empty claims map refuses nothing while reporting itself installed and armed. Counting the
    rows first is what separates "the gate allowed this command" from "the gate has nothing to
    allow it against".
    """
    assert adopter.exists()
    assert len(routing_table.claims()) >= _ENOUGH_CLAIMS_TO_BE_A_TABLE


def test_the_adopting_repos_table_claims_python(adopter: Path) -> None:
    """A `.py` is owned by a structural editor in any repo that declares one."""
    assert adopter.exists()
    assert ".py" in routing_table.claims()


def test_a_textual_query_in_the_adopting_repo_is_refused(adopter: Path) -> None:
    """⚑ END TO END: installed package, adopter's table, the live bypass shape.

    A `timeout` prefix is the ordinary invocation shape, and it is what the predecessor could not
    see. This asserts the packaged hook still sees it, against a table nobody wrote for a test.
    """
    assert adopter.exists()
    assert structural_query.verdict("timeout 180 grep -c foo scripts/tool.py")[0] is True


def test_locating_a_file_in_the_adopting_repo_is_allowed(adopter: Path) -> None:
    """⚑ AND THE REFUSAL ABOVE MEANS NOTHING WITHOUT THIS.

    Against the adopter's real table — not a curated one — the gate must still let a non-query
    through. A gate that refuses every command in a real repo is not adoptable at all.
    """
    assert adopter.exists()
    assert structural_query.verdict("ls -la scripts/tool.py")[0] is False


def test_the_refusal_names_a_tool_the_adopting_repo_actually_declares(adopter: Path) -> None:
    """⚑ A ROUTE THE ADOPTER CANNOT TAKE IS A BLOCK WITHOUT A ROUTE.

    The message must name a tool from THAT repo's table, since the refusal text is the only thing
    a blocked author sees. This is what a hardcoded owner list would fail.
    """
    assert adopter.exists()
    _hit, reasons = structural_query.verdict("wc -l scripts/tool.py")
    named = {tool for _p, hits in reasons for _a, _s, (_k, tool) in hits}
    declared = {tool for _artifact, tool in routing_table.routes()}
    assert named
    assert named <= declared
