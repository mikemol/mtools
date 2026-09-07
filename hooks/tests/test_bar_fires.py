# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The bar's own F-arms: each configured rule FIRES on the absence of the thing it means.

⚑⚑⚑ A CONFIGURED-BUT-INERT GATE IS THE EASY CASE. It fires on nothing and someone eventually
notices. AN ACTIVE GATE AIMED AT THE WRONG PREDICATE IS THE HARD CASE: it produces findings, it
passes review, and its greens are indistinguishable from correct ones. This repo and a peer were
MIRROR IMAGES of exactly that — one `notice-rgx` matched the SPDX line only, the other's default
matched `Copyright` only, so neither gated both and each party ran the arm its own config would
pass. Three separate grids were run over one rule and none carried a separator arm.

⚑⚑ SO THE ASSERTION IS PER PROPOSITION, NOT PER RULE. "CPY001 is enabled" was true in both repos
while both were half-blind. What must be asserted is that the rule fires on the absence of the
thing we mean — and a rule meaning four things needs four arms.

⚑⚑ AND EVERY F-ARM NEEDS ITS P-ARM. Without one, "every arm fires" is indistinguishable from a
checker that rejects everything, which is not a strict gate but a broken one that gets disabled
within a day.

⚑ THE CHECKER IS INVOKED AS THE GATE INVOKES IT — the distribution's own pinned binary against
the distribution's own config, on a file in a temp tree. Reading the config text would assert
INTENT; running the checker asserts EFFECT. A resolver, not a config file, decides which rules
exist: this repo's lock pinned one ruff while its venv ran another, so every arm had been measured
on a version the build would not install.
"""

from __future__ import annotations

import ast as pyast
import os
import re as pyre
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ⚑ `Path` IS A RUNTIME IMPORT HERE, NOT ANNOTATION-ONLY. ruff's TC003 asked for it to move
# into a type-checking block; these module-level constants evaluate it at import time, so that
# move turns collection into a NameError. The rule was right about the common case and wrong
# about this file — which is why the finding was answered by reading the use, not by obeying the
# suggestion.
# ⚑⚑⚑ `.parent`, NOT `.resolve().parent` — AND THAT IS A SANDBOX ESCAPE, MEASURED. bazel stages
# runfiles as SYMLINKS back into the source tree, so `resolve()` follows them out of the sandbox
# and every read below then hit the LIVE WORKING COPY rather than the staged one. The probe that
# showed it: inside a hermetic action, `_DIST/.venv/bin/ruff` reported `is_file() == True` and
# resolved to `/home/mikemol/github/mtools/hooks/.venv/bin/ruff` — a developer venv that is not
# part of the repository at all, reached from a sandbox that is supposed to have staged inputs
# only. That is precisely the escape MODULE.bazel refuses for editable installs, in a test.
_DIST = Path(__file__).parent.parent


def _ruff_argv() -> list[str]:
    """Return the argv prefix that runs ruff, REFUSING when there is none.

    ⚑⚑⚑ THIS FILE ONCE READ `.venv/bin/ruff` UNCONDITIONALLY, so it passed only where a
    developer venv happened to exist. Measured from a fresh `git clone` with no venvs: 24 of 25
    hermetic targets passed and this one failed — the suite that exists to catch a gate aimed at
    the wrong thing, itself aimed at a path that is not part of the repository.

    ⚑⚑ `RUFF_BIN` NAMES A HASH-PINNED http_archive, NOT A pip DEPENDENCY. rules_python stages
    only `site-packages`, dropping the wheel's `bin/ruff`, so the installed package is a shim
    whose `find_ruff_bin()` searches for a binary that was never staged — `python -m ruff` inside
    a hermetic action raised and listed the paths it had tried. A pip requirement that cannot be
    EXECUTED is not a usable dependency for a test that runs the checker.

    ⚑ ABSENT EVERY SOURCE, THIS RAISES RATHER THAN SKIPPING. A skipped case and a passing one are
    indistinguishable in a summary line, and every arm below would then report green over a
    checker that was never run.

    Returns:
        The argv prefix to run ruff with.

    Raises:
        RuntimeError: when no ruff can be found by any route.

    """
    # ⚑⚑ `$(location ...)` YIELDS A PATH RELATIVE TO THE RUNFILES `_main` DIRECTORY, which is
    # `../+_repo_rules+ruff/ruff` for an external archive — it escapes `_main` by design.
    # MEASURED rather than guessed, after three cuts resolved it against the wrong base: this
    # file is staged at `<runfiles>/_main/hooks/tests/`, so `_DIST.parent` IS `_main` and the
    # declared path resolves against it. Passing the value raw produced a TypeError about
    # path-like args from a subprocess that never started.
    declared = os.environ.get("RUFF_BIN")
    if declared:
        candidate = (_DIST.parent / declared).resolve()
        if candidate.is_file():
            return [str(candidate)]
    local = _DIST / ".venv" / "bin" / "ruff"
    if local.is_file():
        return [str(local)]
    found = shutil.which("ruff")
    if found:
        return [found]
    msg = "no ruff available — refusing rather than reporting green over a checker that never ran"
    raise RuntimeError(msg)


_GOOD_HEADER = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Mike Mol\n"


def _ruff(rel: str, body: str, tmp: Path) -> str:
    """Run this distribution's ruff, with this distribution's config, over one written file.

    ⚑ `--no-cache` because a cache keyed on a path would answer about a previous body, and this
    function writes many bodies to few paths.

    Returns:
        the this distribution's ruff, with this distribution's config, over one written file.

    """
    target = tmp / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — the checker is the subject of these cases
        [*_ruff_argv(), "check", "--no-cache", "--config", str(_DIST / "pyproject.toml"),
         "--output-format", "concise", str(target)],
        capture_output=True, text=True, check=False, cwd=tmp)
    return proc.stdout + proc.stderr


@pytest.fixture(scope="module")
def tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a temp tree shaped like a distribution.

    ⚑ The shape matters: per-file-ignores resolve by PATH, so a probe written to `src/` and one
    written to `tests/` must sit under those names to be judged the way real files are.

    Returns:
        a temp tree shaped like a distribution.

    """
    return tmp_path_factory.mktemp("bar")


# ────────────────────────── the header notice: four propositions, one rule ──────────────────────

def test_the_header_gate_passes_a_correct_notice(tree: Path) -> None:
    """The P-arm. Without it every arm below passes against a rule that rejects all input."""
    assert "CPY001" not in _ruff("src/probe_ok.py", _GOOD_HEADER + '"""D."""\n', tree)


@pytest.mark.parametrize(
    ("proposition", "header"),
    [
        ("the SPDX line is present",
         "# Copyright (c) 2026 Mike Mol\n"),
        ("the copyright line is present",
         "# SPDX-License-Identifier: Apache-2.0\n"),
        ("SPDX comes first",
         "# Copyright (c) 2026 Mike Mol\n# SPDX-License-Identifier: Apache-2.0\n"),
        ("the two lines are adjacent, blank line between",
         "# SPDX-License-Identifier: Apache-2.0\n\n# Copyright (c) 2026 Mike Mol\n"),
        ("the two lines are adjacent, comment between",
         "# SPDX-License-Identifier: Apache-2.0\n#\n# Copyright (c) 2026 Mike Mol\n"),
        ("the holder is this repo's",
         "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Someone Else\n"),
    ],
)
def test_the_header_gate_fires_when_a_proposition_fails(
        proposition: str, header: str, tree: Path) -> None:
    """The gate fires when any one of the notice's propositions fails.

    ⚑ ONE ARM PER PROPOSITION. `notice-rgx` asserts presence, ORDER, ADJACENCY and HOLDER —
    four claims in one regex — and an earlier version of it silently accepted a blank line between
    the two notices while rejecting a `#` line between them. The tidier-looking file was the one
    that slipped through, so the gate was teaching the wrong habit rather than merely missing one.
    """
    out = _ruff("src/probe_bad.py", header + '"""D."""\n', tree)
    assert "CPY001" in out, f"gate did not fire on: {proposition}"


def test_the_header_gate_accepts_a_shebang_before_the_notice(tree: Path) -> None:
    """A shebang may precede the notice.

    ⚑ A `#!` that is not on line 1 stops being a shebang, so the notice follows it rather than
    preceding it. codemod_header.py depends on this and would otherwise be unadoptable here.
    """
    body = "#!/usr/bin/env python3\n" + _GOOD_HEADER + '"""D."""\n'
    assert "CPY001" not in _ruff("src/probe_shebang.py", body, tree)


def test_the_header_gate_accepts_a_later_year(tree: Path) -> None:
    r"""A later year passes.

    ⚑ The year is `\d{4}`, not a literal 2026. A copyright year is the year of AUTHORSHIP, so a
    file written in a later year carries a later year without a config change — and pinning the
    literal would make every January a silent, tree-wide false negative.
    """
    body = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2031 Mike Mol\n" + '"""D."""\n'
    assert "CPY001" not in _ruff("src/probe_year.py", body, tree)


# ────────────────────────── the scoped exemptions: refused where the reason does not obtain ─────

def test_assert_is_refused_in_src(tree: Path) -> None:
    """`assert` is refused in src.

    ⚑ S101 is scoped to tests by PATH, and a scope is only meaningful if it has an outside.
    """
    body = _GOOD_HEADER + '"""D."""\n\n\ndef f() -> None:\n    """D."""\n    assert True\n'
    assert "S101" in _ruff("src/probe_assert.py", body, tree)


def test_assert_is_permitted_in_tests(tree: Path) -> None:
    """The P-arm for the scope. `assert` is the test idiom and `-O` never runs these."""
    body = _GOOD_HEADER + '"""D."""\n\n\ndef test_f() -> None:\n    """D."""\n    assert True\n'
    assert "S101" not in _ruff("tests/probe_assert.py", body, tree)


# ────────────────────────── declare-never-suppress, asserted as an effect ───────────────────────

def test_the_ignore_list_is_exactly_three_rules() -> None:
    """The ignore list holds exactly three rules.

    ⚑⚑ THE BAR IS THE MAX, SO IGNORES DO NOT ACCUMULATE. Three entries, each a checker-vs-checker
    conflict rather than a finding declined: D203/D213 are docstring-style pairs whose alternatives
    are mutually exclusive, and COM812 fights the formatter. A fourth entry appearing without this
    test failing is how a bar erodes — one exemption at a time, each defensible alone.

    ⚑ A peer carries a fourth (CPY001, deferred for want of a LICENSE). This repo has a LICENSE,
    which is that deferral's own stated exit condition, so it is not inherited.
    """
    text = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("ignore = "))
    assert line == 'ignore = ["D203", "D213", "COM812"]'


def test_the_checker_that_runs_is_the_one_the_lock_pins() -> None:
    """The checker that runs is the one the lock pins.

    ⚑⚑ A RULE SET IS A PROPERTY OF THE RESOLVER, NOT OF THE CONFIG TEXT. This repo's lock pinned
    ruff 0.16.6 while its venv ran 0.16.5, so every arm above had been measured against a version
    the build would not install. The drift was benign and being UNMEASURED was not.
    """
    pinned = next(ln for ln in (_DIST / "requirements.txt").read_text(encoding="utf-8").splitlines()
                  if ln.startswith("ruff=="))
    proc = subprocess.run(  # noqa: S603 — the checker is the subject of this case
        [*_ruff_argv(), "--version"], capture_output=True, text=True, check=True)
    assert proc.stdout.split()[1] == pinned.split("==")[1].strip()


def test_an_unknown_pytest_marker_is_an_error_rather_than_a_skip(tree: Path) -> None:
    """An unknown marker fails collection rather than skipping the case.

    ⚑ `--strict-markers` — a typo'd marker on a test must fail COLLECTION, not silently skip it.
    A skipped test and a passing one are indistinguishable in a summary line, which is the
    green-over-nothing shape this repo keeps finding one layer down.

    ⚑⚑ TWO EARLIER VERSIONS OF THIS ARM WERE AIMED AT THE WRONG PREDICATE, in the file whose
    whole subject is that failure. The first passed `-m nonexistent` and expected an error; `-m`
    DESELECTS an unknown expression and exits 5, saying nothing about strictness, because
    `--strict-markers` validates markers APPLIED TO TESTS. The second applied a marker but also
    passed `--strict-markers` ON THE COMMAND LINE — so it asserted that pytest's flag works, which
    nobody doubted, and stayed green when the flag was deleted from `addopts`. VERIFIED BY
    MUTATION: removing `--strict-markers` from the config must fail this case, and until the flag
    was dropped from the invocation it did not.
    """
    probe = tree / "marker_probe" / "test_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import pytest\n\n\n@pytest.mark.nonexistent_marker_probe\ndef test_x() -> None:\n"
        "    assert True\n", encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — pytest's own configuration is the subject
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-c", str(_DIST / "pyproject.toml"), str(probe)],
        capture_output=True, text=True, check=False, cwd=_DIST)
    assert proc.returncode != 0
    assert "nonexistent_marker_probe" in proc.stdout + proc.stderr


def test_a_declared_pytest_marker_collects_cleanly(tree: Path) -> None:
    """The P-arm for strictness: a marker the config DECLARES must not trip it.

    ⚑⚑ AND IT PINS `-c` TO THIS DISTRIBUTION'S pyproject. The probe file lives in a temp tree, so
    pytest picks its rootdir from there and never reads the config under test — the arm would then
    assert strictness against pytest's DEFAULTS rather than against this repo's. Naming the config
    is what makes the subject of the case the thing it claims to be about.

    ⚑ It uses THIS distribution's marker. A first draft used a sibling's (`needs_pandoc`, which
    mdstruct declares and hooks does not) and the arm failed correctly -- the marker list is
    per-distribution, so a shared arm would have asserted a config neither repo has.
    """
    probe = tree / "marker_ok" / "test_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import pytest\n\n\n@pytest.mark.needs_shellcheck\ndef test_x() -> None:\n"
        "    assert True\n", encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — pytest's own configuration is the subject
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-c", str(_DIST / "pyproject.toml"), str(probe)],
        capture_output=True, text=True, check=False, cwd=_DIST)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_mypy_path_pair_is_present_and_both_halves_are_set() -> None:
    """Both `mypy_path` and `explicit_package_bases` are set, or neither is.

    ⚑⚑ EITHER ONE ALONE LEAVES A WORKING-LOOKING CONFIG THAT CHECKS THE WRONG THING.
    `mypy_path` alone makes the source reachable under two names, so a module can be checked
    twice under different identities; `explicit_package_bases` alone does not make it
    reachable at all. The sibling distribution once had `mypy_path` without `src` and
    reported 14 errors, 13 of them `Any`, while its 90 tests passed — a green suite standing
    in for a checked one.

    ⚑ AND THE PAIR IS NOT TEMPORARY, WHICH ⟡mtools-drop-mypypath ASSERTED IT WAS. Measured
    against a fresh NON-EDITABLE install with both lines deleted, mypy passes cleanly — so
    the variable is the editable install, not bazel. Retiring it would mean a reinstall
    before any checker saw an edit. The ticket is closed won't-fix and this arm is what stops
    a future reader deleting the pair on the strength of the retired ticket's premise.
    """
    text = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    assert 'mypy_path = "src"' in text
    assert "explicit_package_bases = true" in text


def test_the_bazel_test_rule_runs_pytest_rather_than_the_module() -> None:
    """Every py_test names the pytest entry point as `main`, not the test module.

    ⚑⚑⚑ `main = <the test module>` RUNS THAT MODULE AS A SCRIPT. Import-time code executes,
    pytest never collects, and the process exits 0 — so every target reported GREEN OVER ZERO
    ASSERTIONS. Measured: a module whose only statement was `raise AssertionError` PASSED
    under bazel, across all 23 targets, for the life of the rule.

    ⚑⚑ IT IS ASSERTED HERE RATHER THAN LEFT TO THE SUITE BECAUSE THE SUITE CANNOT SEE IT. A
    broken runner reports success, so no witness inside it can fail — the defect is invisible
    from exactly the place one would look for it, and only a probe designed to fail could
    reveal it. This reads the BUILD files instead.
    """
    root = _DIST.parent
    for name in ("hooks", "mdstruct", "ratchet"):
        build = (root / name / "BUILD.bazel").read_text(encoding="utf-8")
        assert 'main = "//:pytest_main.py"' in build, name
        assert "main = src," not in build, name


def test_the_gates_own_shell_is_checked() -> None:
    """`.githooks/pre-commit` and the checker script are both in a shellcheck target.

    ⚑⚑⚑ THE SHELL THAT RUNS EVERY OTHER CHECK WAS ITSELF CHECKED BY NOTHING. It was clean
    only because its author ran shellcheck by hand after each edit — a convention held in one
    person's memory, guarding the file that guards everything else. Measured: `grep -n
    shellcheck .githooks/pre-commit` returned only a comment.

    ⚑⚑ AND THE CHECKER'S OWN SCRIPT IS IN THE SAME LIST. A gate that checks every shell file
    except itself leaves exactly the one nobody would think to look at, for the same reason
    nobody checked the hook. Both are asserted here rather than assumed from the BUILD file
    being present, because a `data` entry that is not also an `args` entry stages a file the
    checker never opens.

    ⚑⚑⚑ THE ASSERTION IS OVER THE FILESYSTEM, NOT OVER THE BUILD FILE'S TEXT, AND THE FIRST CUT
    WAS OVER THE TEXT. It held a seven-name list and grepped for `$(location //:<name>)` — so it
    verified the BUILD file's LISTING STYLE, not its coverage, and it broke the moment that list
    became a `glob()` while coverage went UP from 7 files to 11. ⚑⚑ Worse, it carried the same
    hand-written population as the thing it guarded: two copies of one list, drifting together,
    and the test could never have reported the two files (`domain_witness.sh`, `collect_check.sh`)
    that were missing from BOTH. A guard that enumerates the same way as its subject cannot
    detect an omission they share.
    """
    build = (_DIST.parent / "BUILD.bazel").read_text(encoding="utf-8")
    # ⚑⚑⚑ NO FILESYSTEM ENUMERATION HERE, AND THE SANDBOX IS WHY. A cut of this test globbed
    # `*.sh` and `.githooks/*` off disk to build the expected population: it PASSED locally and
    # FAILED hermetically with `FileNotFoundError: .../.githooks`, because inside the sandbox only
    # DECLARED inputs exist. That is the escape this target's own BUILD comment warns about —
    # these witnesses once "passed only by resolving OUT of the sandbox into the live tree" — and
    # declaring `.githooks` as data to make the read work would have re-opened the hole rather
    # than closed it.
    #
    # ⚑⚑ THE GLOB IS THE COVERAGE CLAIM, SO THE GLOB IS WHAT GETS ASSERTED. `glob()` covers every
    # matching file by construction and cannot drift as files are added — which the seven-name
    # list it replaced could and did, missing two. Asserting the mechanism is strictly stronger
    # than re-listing its outputs, and it needs no input the sandbox has not staged.
    assert 'glob(["*.sh", ".githooks/*"]' in build, (
        "the shellcheck target must glob its population, not enumerate it")
    assert '"@shellcheck//:bin"' in build, "the checker binary must be staged"


def test_no_witness_reads_a_developer_venv() -> None:
    """No test resolves a path into `.venv`, which is not part of the repository.

    ⚑⚑⚑ THIS FILE DID EXACTLY THAT, AND IT PASSED. It read `.venv/bin/ruff` and used
    `Path(__file__).resolve()`, which follows bazel's runfiles symlinks OUT of the sandbox and
    back into the live working tree — so a hermetic action was reading a developer venv that no
    clone contains. Measured two ways: a probe inside the sandbox reported
    `venv.is_file() == True` resolving to `/home/mikemol/github/mtools/hooks/.venv/bin/ruff`,
    and a fresh `git clone` with no venvs failed this one target out of 25.

    ⚑⚑ THAT IS THE EDITABLE-INSTALL ESCAPE MODULE.bazel REFUSES, REPRODUCED IN A TEST. A
    sandbox that can reach the source tree is not a sandbox, and a suite that passes only where
    its author's machine is set up a particular way says nothing about the repository.
    """
    # ⚑⚑ THE CHECK PARSES THE MODULE RATHER THAN GREPPING IT, and both weaker cuts are why. A
    # `.venv` under `tmp_path` is a FIXTURE building a fake tree — legitimate, and a substring
    # search flagged three of them. Stripping `#` comments then flagged this very docstring,
    # which DESCRIBES the defect. Only an AST walk distinguishes an expression from prose about
    # an expression, and a witness that cannot make that distinction cannot live in a file that
    # documents what it forbids.
    for dist in ("hooks", "mdstruct", "ratchet"):
        for module in sorted((_DIST.parent / dist).glob("tests/test_*.py")):
            tree = pyast.parse(module.read_text(encoding="utf-8"))
            for node in pyast.walk(tree):
                if not isinstance(node, pyast.Call):
                    continue
                func = node.func
                if not isinstance(func, pyast.Attribute) or func.attr != "resolve":
                    continue
                inner = func.value
                names = {n.id for n in pyast.walk(inner) if isinstance(n, pyast.Name)}
                assert "__file__" not in names, (
                    f"{dist}/{module.name}:{node.lineno} resolves out of the runfiles tree")


def test_the_hermetic_sandbox_is_a_default_not_a_config() -> None:
    """The sandbox flags are unconditional `build` lines, never `build:<config>`.

    ⚑⚑⚑ AN OPT-IN HERMETICITY FLAG IS NOT HERMETICITY. These flags are NOT in the action key —
    measured: a target run without them caches a green verdict, and the same target run WITH
    them reports `Executed 0 out of 1 test: 1 test passes`, the verdict crossing the boundary
    unexecuted. So a `--config` would be a regime a cache hit silently bypasses, and a flag
    that changes what an action can READ but not what it is KEYED on cannot be left to the
    caller.

    ⚑⚑ WHAT THEY BUY, MEASURED BY PROBE IN BOTH ARMS: without them a hermetic action reads
    `/home/mikemol/github/mtools/hooks/.venv/bin/ruff` and the whole source tree; with them
    neither exists. That is the escape the AST witness above catches BY PATTERN, closed here BY
    CONSTRUCTION — and the two are not substitutes.
    """
    rc = (_DIST.parent / ".bazelrc").read_text(encoding="utf-8")
    for flag in ("--experimental_use_hermetic_linux_sandbox",
                 "--sandbox_add_mount_pair=/usr"):
        assert f"build {flag}" in rc, f"{flag} is not an unconditional build flag"
        assert f"build:hermetic {flag}" not in rc, f"{flag} was made opt-in"


# ⚑⚑⚑ HOST TIER, AND THE SKIP IS A DECLARATION RATHER THAN A CONVENIENCE. `rule_citations.sh`
# asks whether a heading exists in a markdown document — a STRUCTURAL query, which this repo's
# routing rule assigns to `mdstruct`. That dependency is correct, not incidental: answering it
# with `grep` is the textual fallback the hook refuses. But `mdstruct` lives in a developer venv,
# and a witness resolving into `.venv` is the sandbox escape another test in this very file
# exists to forbid.
# ⚑⚑ So these arms cannot be hermetic without vendoring a reader, and pretending otherwise would
# mean either staging a venv or weakening the gate to use `grep`. They SKIP with a stated reason
# instead — `--strict-markers` is on, so the skip is declared and visible, never silent.
_CITATION_GATE_READER = _DIST.parent / "mdstruct" / ".venv" / "bin" / "mdstruct"
_needs_reader = pytest.mark.skipif(
    not _CITATION_GATE_READER.is_file(),
    reason="rule_citations.sh routes its heading query through mdstruct, which is host-tier",
)


def _citations(message: str, rules: str, tree: Path) -> int:
    """Run the citation gate over `message` against a `rules` fixture; return its exit code.

    Returns:
        the the citation gate over `message` against a `rules` fixture; return its exit code.

    """
    msg = tree / "msg.txt"
    msg.write_text(message, encoding="utf-8")
    doc = tree / "rules.md"
    doc.write_text(rules, encoding="utf-8")
    gate = _DIST.parent / "rule_citations.sh"
    return subprocess.run(  # noqa: S603
        [str(gate), str(msg), str(doc)],
        capture_output=True, check=False, cwd=str(_DIST.parent)).returncode


@_needs_reader
def test_the_citation_gate_passes_a_rule_that_exists(tree: Path) -> None:
    """The P-arm. Without it every arm below passes against a gate that refuses all input."""
    assert _citations("x; Rule 25\n", "## Rule 25 — real\n", tree) == 0


@_needs_reader
def test_the_citation_gate_fires_on_a_rule_that_does_not_exist(tree: Path) -> None:
    """⚑⚑ The defect this gate was built for, as a permanent arm.

    A commit announced `Rule 23`; the code, tests and warrants landed and the rule did not. It
    stood two hours and was found by eye, from the heading sequence stepping 22 to 24. ⚑ A
    citation to a rule that does not exist reads exactly like a citation to one that does —
    nothing is malformed, the document exists, and only following the pointer separates them.
    """
    assert _citations("x; Rule 99\n", "## Rule 25 — real\n", tree) == 1


@_needs_reader
def test_the_citation_gate_is_silent_when_nothing_is_cited(tree: Path) -> None:
    """⚑ A message citing no rule must PASS, not pass vacuously for want of a corpus.

    Most commits cite nothing. A gate that refused them would be bypassed within a day, and a
    bypassed gate is a disarmed one — so this arm guards the gate's own survival rather than a
    property of the corpus.
    """
    assert _citations("an ordinary commit\n", "## Rule 25 — real\n", tree) == 0


def _orphans(tree: Path, scripts: dict[str, str], sites: dict[str, str]) -> int:
    """Build a fixture tree of shell files and call sites; return the orphan gate's exit code.

    ⚑ THE CALL SITE IS WRITTEN OUTSIDE THE GLOB. `blockers.sh` is itself a `.sh`, so writing the
    fixture's call site there makes it a subject of the very census it is meant to feed — the
    first cut did exactly that and the P-arm failed because the SITE was an orphan, not because
    the invoked script was. The gate reads `.githooks/pre-commit` as a site too, and that name is
    not matched by `*.sh`.

    Returns:
        the a fixture tree of shell files and call sites; return the orphan gate's exit code.

    """
    (tree / ".githooks").mkdir(exist_ok=True)
    for name, body in scripts.items():
        (tree / name).write_text(body, encoding="utf-8")
    for name, body in sites.items():
        (tree / name).write_text(body, encoding="utf-8")
    if not (tree / "BUILD.bazel").exists():
        (tree / "BUILD.bazel").write_text("", encoding="utf-8")
    gate = _DIST.parent / "orphan_check.sh"
    return subprocess.run(  # noqa: S603
        [str(gate), str(tree)],
        capture_output=True, check=False, cwd=str(_DIST.parent)).returncode


def test_the_orphan_gate_passes_an_invoked_script(tmp_path: Path) -> None:
    """The P-arm. Without it every arm below passes against a gate that refuses all input."""
    assert _orphans(
        tmp_path,
        {"used.sh": "#!/usr/bin/env bash\n"},
        {".githooks/pre-commit": "#!/usr/bin/env bash\n./used.sh\n"},
    ) == 0


def test_the_orphan_gate_fires_on_a_script_nothing_invokes(tmp_path: Path) -> None:
    """⚑⚑ A checker nothing runs is a green over nothing, and had no check until now.

    A `.sh` can be written, pass its linter, sit in the tree and never execute. ⚑ An INTENTIONAL
    orphan is the same file on disk as a forgotten one, which is why the gate demands a
    declaration rather than trusting anyone's memory.
    """
    assert _orphans(
        tmp_path,
        {"lonely.sh": "#!/usr/bin/env bash\n"},
        {".githooks/pre-commit": "#!/usr/bin/env bash\n"},
    ) == 1


def test_an_exports_files_entry_is_not_an_invocation(tmp_path: Path) -> None:
    """⚑⚑⚑ Availability is not use, and conflating them SILENCED a real waiver.

    An earlier cut matched any quoted mention of a filename in `BUILD.bazel`. The moment
    `collect_check.sh` was added to `exports_files` — which only makes a source dependable, never
    run — the gate reported it as invoked and stopped printing its declared-orphan line. ⚑ The
    waiver did not fail loudly; it went QUIET, which is the failure direction that removes its own
    detector.
    """
    (tmp_path / "BUILD.bazel").write_text('exports_files(["lonely.sh"])\n', encoding="utf-8")
    assert _orphans(
        tmp_path,
        {"lonely.sh": "#!/usr/bin/env bash\n"},
        {".githooks/pre-commit": "#!/usr/bin/env bash\n"},
    ) == 1


def test_a_srcs_entry_is_an_invocation(tmp_path: Path) -> None:
    """⚑ The other side of the same edit, because narrowing over-corrected.

    Restricting the match to `srcs`/`$(location)` reported four action wrappers as orphans — they
    are `srcs = ["//:mypy_check.sh"]` in the PER-DISTRIBUTION build files, a label form the first
    pattern missed in files it never read. Narrowing a predicate and narrowing its POPULATION are
    different edits; doing both at once turned one false negative into four false positives.
    """
    (tmp_path / "BUILD.bazel").write_text(
        'sh_test(\n    name = "x",\n    srcs = ["//:wrapped.sh"],\n)\n', encoding="utf-8")
    assert _orphans(
        tmp_path,
        {"wrapped.sh": "#!/usr/bin/env bash\n"},
        {".githooks/pre-commit": "#!/usr/bin/env bash\n"},
    ) == 0


def _freshness(tree: Path, rules: str, *, readable: bool) -> int:
    """Run the freshness gate against a corpus fixture; return its exit code.

    Returns:
        the the freshness gate against a corpus fixture; return its exit code.

    """
    doc = tree / "rules.md"
    doc.write_text(rules, encoding="utf-8")
    script = (_DIST.parent / "rule_freshness.sh").read_text(encoding="utf-8")
    probe = tree / "probe.sh"
    probe.write_text(
        script.replace('rules="findings/bazel/mtools.md"', f'rules="{doc}"'),
        encoding="utf-8")
    probe.chmod(0o755)
    doc.chmod(0o644 if readable else 0o000)
    try:
        return subprocess.run(  # noqa: S603
            [str(probe)], capture_output=True, check=False,
            cwd=str(_DIST.parent)).returncode
    finally:
        doc.chmod(0o644)


def test_the_freshness_gate_passes_a_corpus_citing_no_environment_claim(tmp_path: Path) -> None:
    """⚑ A corpus with no environment claim has nothing to re-check, and that is a PASS.

    Most rules are claims about reasoning and do not decay. A gate that refused them would be
    refusing the ordinary case.
    """
    assert _freshness(tmp_path, "## Rule 1 — a claim about reasoning\n", readable=True) == 0


def test_the_freshness_gate_refuses_a_corpus_it_cannot_read(tmp_path: Path) -> None:
    """Refuse a corpus the reader cannot open, rather than calling it empty.

    ⚑⚑⚑ A READER FAILURE AND A GENUINE ABSENCE BOTH EXIT NONZERO FROM `grep`, and the first
    cut treated them as one. `grep -q` returns 1 for *no match* and 2 for *cannot read* — so
    a missing binary, an unreadable file or a permission error all printed "no rule cites the
    metrics port" and exited 0.

    ⚑ Measured with a degraded PATH: the script reported nothing to re-check and returned
    success, having checked nothing. A green over a reader failure, inside the checker written
    to catch stale claims.

    ⚑ Same file, same content, only the permission bit differs — and the verdicts are opposite.
    """
    assert _freshness(tmp_path, "## Rule 1 — a claim\n", readable=False) == 1


# ⚑ NAMED, because `2` is a CONTRACT rather than an arbitrary code: the witness reserves it for
# "this argument is unusable", distinct from 1, which every arm uses to mean "the domain claim
# failed". A test comparing against a bare literal cannot say which of those it is asserting.
_ARG_REFUSED = 2


def _witness_args(*argv: str) -> int:
    """Call the domain witness with `argv`; return its exit code.

    ⚑ ONLY THE PRE-BAZEL BRANCHES ARE REACHABLE HERE. Every arm of this witness invokes bazel,
    which the sandbox has no business running — so what a test can assert is what the script
    refuses BEFORE its first side effect: a missing argument, and a probe kind no checker seeks.
    """
    return subprocess.run(  # noqa: S603
        [str(_DIST.parent / "domain_witness.sh"), *argv],
        capture_output=True, check=False, cwd=str(_DIST.parent)).returncode


def test_the_witness_refuses_an_unknown_probe_kind_before_running_anything() -> None:
    """⚑⚑ A probe the checker does not seek is indistinguishable from a domain that excludes it.

    Both produce an identical arm-2 red, so a typo'd kind reports a DOMAIN finding about whatever
    target it was aimed at. ⚑ The guard originally sat after the control and after arm 1 — a
    mistyped kind paid for a full control invocation and a mutate-plus-rebuild before refusing,
    and refused with the victim already edited. The cheapest correct refusal is before the first
    side effect.
    """
    # ⚑ A REAL TRACKED VICTIM, because the witness now refuses an untracked one — and the first
    # cut of this test passed `ratchet/x.py`, a path that did not exist. The witness CREATED it,
    # appending a probe payload on each invocation, and `git checkout` could not restore an
    # untracked file. Five runs left a 432-byte file of accumulated payloads; the ratchet censused
    # the debris and refused the commit, which is the only reason it surfaced.
    assert _witness_args(
        "ratchet", "//ratchet:mypy",
        "ratchet/src/mikemol/ratchet/state.py", "nonsense") == _ARG_REFUSED


def test_the_witness_accepts_every_declared_probe_kind() -> None:
    """The P-arm for that guard: a validator that rejects everything is not a validator.

    ⚑ It must not return the ARGUMENT-REFUSAL code for a kind the dispatch implements. Anything
    past this point needs bazel and is out of scope here.
    """
    # ⚑⚑ READ FROM THE SCRIPT, NOT BY INVOKING IT. Running each kind past the guard costs a bazel
    # invocation apiece — measured at 16.9s for this one test — and every second of that exercises
    # the ARMS, which this test is not about. ⚑ The guard is a `case` list; asserting that the
    # dispatch and the validator name the SAME kinds is the property, and a mismatch between them
    # is exactly the defect a slow invocation would find more expensively.
    text = (_DIST.parent / "domain_witness.sh").read_text(encoding="utf-8")
    validated = text.split('case "$probe_kind" in', 1)[1].split(")", 1)[0]
    for kind in ("mypy", "ruff", "ratchet", "baseline", "shellcheck"):
        assert kind in validated, f"{kind} is dispatched but not validated"


def test_the_witness_refuses_a_missing_argument() -> None:
    """⚑ A witness invoked with no target must refuse, not default to one.

    Every argument here names something the arms will MUTATE or measure; a default would pick a
    victim the caller did not choose.
    """
    assert _witness_args() != 0


def test_the_witness_refuses_an_untracked_victim() -> None:
    """⚑⚑⚑ A witness that can bring a file into existence is editing a domain, not probing one.

    `git checkout` on an untracked path silently does nothing, so every arm ran, the payloads
    ACCUMULATED, and arm 3 reported RESTORED over a file it had not restored. ⚑ Measured: a test
    passed a path that did not exist, the witness created it across five invocations, and the
    432-byte result was censused by the ratchet — which refused the commit and is the only reason
    it surfaced at all.
    """
    assert _witness_args(
        "ratchet", "//ratchet:mypy", "ratchet/definitely_not_tracked.py", "mypy") == _ARG_REFUSED


def test_the_witness_refuses_a_victim_carrying_probe_residue(tmp_path: Path) -> None:
    """⚑⚑⚑ `trap ... EXIT` cannot fire on SIGKILL, so a killed witness leaves its probe behind.

    Measured: killing a witness inside its mutation window leaves the payload in the victim, and
    the NEXT gate run censuses it — reporting ratchet keys from a probe nobody wrote, in a file
    the author did not touch. SIGTERM is fine because the trap runs; SIGKILL is not, and no
    handler can make it be.

    ⚑ The residue is syntactically valid and the suite still passes, so only the ratchet notices,
    and it notices as NEW DEBT. A pre-flight refusal is the whole repair — the witness cannot
    prevent its own death, but it can decline to run on a corpse's leftovers.

    ⚑⚑ THE MESSAGE IS ASSERTED, NOT JUST THE CODE, and the first cut of this test could not tell
    which guard it had tripped. An untracked victim also exits 2 — measured — so a `tmp_path`
    fixture with no residue at all produces the same number. A test asserting a code that two
    guards share proves nothing about either, which is this repository's own green-over-nothing
    at the granularity of an exit status.

    ⚑ A FIXTURE, NOT A REAL SOURCE FILE. A first cut mutated a tracked file in another
    distribution: it passed locally and failed hermetically, because the sandbox does not stage
    another distribution's sources — and staging them would let a test write into them. The guard
    now runs before the tracked check, so a fixture reaches it.
    """
    victim = tmp_path / "residue.py"
    victim.write_text("x = 1\n# transient domain probe 123\n", encoding="utf-8")
    out = subprocess.run(  # noqa: S603
        [str(_DIST.parent / "domain_witness.sh"), "ratchet", "//ratchet:mypy",
         str(victim), "mypy"],
        capture_output=True, check=False, text=True, cwd=str(_DIST.parent))
    assert out.returncode == _ARG_REFUSED
    assert "probe residue" in out.stderr, "the residue guard must be the one that fired"


@pytest.mark.skipif(
    not (_DIST.parent / ".git").exists(),
    reason="materialisation is a property of the host git repository; the sandbox has none",
)
def test_the_gate_reads_the_index_not_the_working_tree(tmp_path: Path) -> None:
    """⚑⚑⚑ A property nobody designed for is one nobody is maintaining.

    The hook materialises the index into a temp tree and runs its checks there, so what is
    checked is what is being committed rather than what is on disk. That block predates every use
    made of it — it was written because `git add` is usually partial — and its most load-bearing
    consequence was never reasoned about: **a second session's dirty file is invisible to this
    gate.** A peer filed "a shared working tree has no safe operation" as structural; this is why
    half of it dissolved.

    ⚑ It had no test. A refactor for tidiness would take the guarantee with it and nothing would
    fail, which is exactly what "nobody is maintaining it" means.

    ⚑ HOST TIER, AND THE SKIP IS A DECLARATION. The subject is a property of THIS git repository
    — what `checkout-index` produces from a real index — and the sandbox has no repository at all,
    so `git checkout-index` exits non-zero there. Staging a `.git` directory to make it run would
    be staging the very thing under test. `--strict-markers` is on, so the skip is visible.

    ⚑⚑ THE ARM IS THE DIFFERENCE, NOT THE PRESENCE. Asserting the staged copy exists proves
    nothing — it would exist under any implementation. This writes text that is ONLY in the
    working tree and requires the materialised copy not to carry it.
    """
    root = _DIST.parent
    marker = "probe-only-in-working-tree"
    staged = tmp_path / "staged"
    staged.mkdir()
    # ⚑ RESOLVED, NOT BARE. `git` on PATH is a dependency this test does not declare, and S607 is
    # right to say so — the same reason no witness here reads a developer venv. If git is absent
    # the test cannot run, and that is a fact about the reader worth failing on rather than
    # silencing.
    git = shutil.which("git")
    assert git, "git is not on PATH — this test cannot measure what it claims"
    subprocess.run(  # noqa: S603
        [git, "checkout-index", "--all", f"--prefix={staged}/"],
        check=True, cwd=str(root), capture_output=True)
    victim = root / "ratchet" / "warrants.bib"
    committed = victim.read_text(encoding="utf-8")
    try:
        victim.write_text(committed + f"\n{marker}\n", encoding="utf-8")
        assert marker in victim.read_text(encoding="utf-8"), "the fixture did not take"
        assert marker not in (staged / "ratchet" / "warrants.bib").read_text(encoding="utf-8"), (
            "the materialised tree carries a working-tree-only change: the gate is reading disk")
    finally:
        victim.write_text(committed, encoding="utf-8")

# --- the five gate repairs of 2026-09-06, none of which had a test -----------------------------
#
# ⚑⚑⚑ EVERY ONE OF THESE WAS ARMED BY HAND, IN A SHELL, ONCE. Five repairs landed in
# `.githooks/pre-commit` and `domain_witness.sh` in one session — import closure, refusal-account,
# witness attribution, residue sweep, self-snapshot — each measured with both arms and none gated.
# ⚑ That is exactly what this module exists to refuse: an arm that lives in a transcript is an arm
# the next edit can silently remove. Measured the same session: a `git checkout --` cleanup
# reverted an uncommitted repair block, and only a re-measurement caught it.


_GATE = _DIST.parent / ".githooks" / "pre-commit"


def test_the_gate_snapshots_itself_before_running() -> None:
    """⚑⚑⚑ `core.hooksPath` points into the tree, so git executes this file LIVE.

    Measured across two trees 61 seconds apart (substrate's `gate-G86`): a peer's commit died at
    `.githooks/pre-commit:302`, *syntax error near `(`*, AFTER running 226+110+40 pytest and 35/35
    bazel — and `bash -n` parsed the file clean a minute later. They read it mid-write.

    ⚑ `git hash-object .githooks/pre-commit` equals its index entry, so the executed bytes ARE the
    tree's bytes. The re-exec is the whole repair; without the guard it would loop.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "_GATE_SNAPSHOT" in body, "the gate must re-exec from a snapshot of itself"
    assert 'exec bash "$_snap"' in body, "the snapshot must be the thing that runs"


def test_the_snapshot_survives_a_mid_write_edit_to_the_live_file(tmp_path: Path) -> None:
    """⚑⚑ THE ARM THAT REPRODUCES THE PEER'S FAILURE: a live edit must not reach a running gate.

    A copy taken before the mutation parses clean while the mutated original does not — which is
    substrate's failure and its repair in one measurement.
    """
    live = tmp_path / "gate.sh"
    live.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    snap = tmp_path / "snap.sh"
    snap.write_text(live.read_text(encoding="utf-8"), encoding="utf-8")
    live.write_text(live.read_text(encoding="utf-8") + "\nsyntax error (\n", encoding="utf-8")

    def parses(path: Path) -> bool:
        return subprocess.run(  # noqa: S603
            ["/usr/bin/env", "bash", "-n", str(path)],
            capture_output=True, check=False).returncode == 0

    assert not parses(live), "the mutated live file must fail to parse — else the arm is vacuous"
    assert parses(snap), "the snapshot must be immune to the live edit"


def test_the_gate_sweeps_its_own_probe_residue() -> None:
    """⚑⚑⚑ A refusal was generating its own next refusal.

    Each witness traps its own EXIT; the GATE had none. Any abandonment — an early refusal, or a
    harness killing a backgrounded commit at its timeout — strands a witness mid-mutation, and the
    probe survives into the next attempt, which then refuses on residue rather than content.

    ⚑ Measured: clearing four stranded victims by hand produced three more on the retry. And
    `gabion` falsified the concurrency story two parties had agreed on — a run on a
    verified-clean tree with no peer active injected fresh residue anyway.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "sweep_witness_residue" in body
    assert "trap sweep_witness_residue EXIT" in body, "the sweep must fire on ANY exit path"


def test_the_sweep_matches_the_probe_marker_and_not_mere_dirtiness() -> None:
    """⚑⚑ A BLANKET CHECKOUT WOULD DISCARD A PEER'S REAL WORK.

    Seven sessions write this tree. The sweep's predicate must be the probe marker, never
    `is this file modified` — which is the same discipline as `--only` on a commit, one layer down.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "transient domain probe" in body, "the sweep must key on the marker"


def test_the_sweep_uses_no_subshell() -> None:
    """⚑⚑⚑ THE FIRST CUT OF THE SWEEP DID NOTHING AND SAID NOTHING.

    `printf | while read` puts the loop in a SUBSHELL, so `git checkout` could not report failure
    to the caller. Measured: residue planted, sweep run, residue still present, no error printed.
    ⚑ That is the pipeline-swallows-the-status defect — the class `hook_no_chaining` exists to
    refuse — committed INSIDE the repair for a different silent failure, and the fifth instance of
    it in this repository in one day.
    """
    body = _GATE.read_text(encoding="utf-8")
    start = body.index("sweep_witness_residue() {")
    fn = body[start:body.index("\n}", start)]
    assert "| while" not in fn, "a piped loop runs in a subshell and cannot report failure"
    assert "for v in" in fn, "the sweep must iterate without a pipeline"


def test_the_witness_takes_a_before_image() -> None:
    """⚑⚑⚑ THE WITNESS COULD NOT TELL ITS OWN SABOTAGE FROM A PEER'S WORK.

    `restore` compared `git diff --quiet -- $victim`, a WHOLE-FILE predicate: it conflates *I
    failed to restore my own edit* with *someone else's edit arrived while I ran*. Both print
    `the tree is dirty`, and only the first is the witness's business.

    ⚑ The repair is a content hash taken before any mutation. `gabion` offered a scratch-copy
    alternative and withdrew it: a witness over a copy proves the COPY's domain, which is the whole
    reason arm 2 mutates the tracked file.
    """
    body = (_DIST.parent / "domain_witness.sh").read_text(encoding="utf-8")
    assert "before_image=" in body, "the witness must record what it found before mutating"
    assert "git hash-object" in body, "attribution needs a content hash, not a dirtiness check"


def test_the_gate_replays_a_failing_checks_own_output() -> None:
    """⚑⚑ A REFUSAL THAT NAMES AN OUTCOME AND NOT A SUBJECT IS ONE NOBODY CAN CLEAR.

    Measured: `linux-sources` was refused by `shellcheck domain reaches every shell file` and
    reported that `grep shellcheck` over the ENTIRE run returned two lines — a passing bazel target
    and the refusal summary. The witness DOES print three arms, to stderr, interleaved into a
    35-target bazel run hundreds of lines earlier. ⚑ Detail that exists somewhere and is not
    attached to the verdict is detail the reader does not have.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "failed_detail" in body, "a failing check must be able to carry its own account"
    assert "the failing check(s) said:" in body, "the account must be replayed under the verdict"


def test_the_gate_names_the_gap_when_no_check_captured_its_output() -> None:
    """⚑ A READER WHO CANNOT FIND THE REASON SHOULD BE TOLD THE REASON IS MISSING.

    Otherwise a bare label reads as an arbitrary gate, which is what gets bypassed.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "no check captured its own output" in body
    assert "defect in the CHECK, not in your commit" in body


def test_the_gate_points_the_checkers_at_the_staged_tree() -> None:
    """⚑⚑⚑ `cd` RELOCATES A CWD, NOT AN IMPORT CLOSURE.

    The venv is an EDITABLE install — a `.pth` plus an import-hook finder naming the live tree — so
    `cd $staged/$dist` changed the working directory and left imports resolving to unstaged source.
    ⚑ Measured: a type defect planted in the WORKING tree, absent from the staged copy, was still
    imported by a run inside the staged copy, and mypy reported Success.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert 'MYPYPATH="$staged/' in body, "mypy must resolve inside the staged tree"
    assert 'PYTHONPATH="$staged/' in body, "the import closure must be the staged one"

# --- blockers.sh: three defects in three consecutive ticks, none of them gated -----------------
#
# ⚑⚑⚑ THE POLL SELECTS EVERY SUBSEQUENT TICK'S WORK, SO A WRONG ANSWER HERE MIS-SEQUENCES
# EVERYTHING DOWNSTREAM — and its failure mode is worse than the gate's. A wrong gate refuses a
# commit LOUDLY. A wrong poll silently derives the wrong top item, which is what happened when it
# reported `7 of 7 FROZEN` while `HEAD` held 8 legs and I acted on that reading for a full tick.
#
# ⚑ Three defects, three consecutive ticks, each found by hand or by a peer's work and none gated:
# a hardcoded census path; `git ls-files` as the population (excluding the untracked run file of a
# census convened minutes earlier); and a one-sided reconciliation whose SILENCE read as agreement.


_POLL = _DIST.parent / "blockers.sh"
_THIS = Path(__file__)
_MSGCOUNT = _DIST.parent / "message_counts.sh"
# ⚑ THE SWEEP'S OWN COVERAGE FLOOR. 65 string-membership assertions existed when it was
# written; if it resolves far fewer, the resolver has broken and its silence is the
# vacuity it exists to catch — one level out.
# ⚑⚑⚑ A COVERAGE FLOOR IS ALSO A CLAIM ABOUT HISTORY, AND THIS ONE IS FALSE FOR MOST OF IT.
# `cassian` asked the question this repository had not: *would this arm have refused past work?*
# MEASURED over every commit touching this file — **31 of 42 carry fewer than 50 assertions and
# would be refused by their own floor.** The file had 48 at `b003d16`, four commits ago.
# ⚑⚑ THE HAZARD IS THE FLOOR, NOT THE PREDICATE. The floor exists because *the sweep found nothing*
# and *the sweep did not run* are byte-identical — that reasoning is sound and unchanged. What is
# false is the implicit assertion that the population was never smaller, **which is false by
# construction for any arm that introduced its own population.**
# ⚑ NOT LOWERED TO MAKE A SWEEP GREEN, AND THE EXPOSURE IS BOUNDED RATHER THAN PAPERED OVER: these
# arms read the WORKING TREE, never a blob, so no past commit is re-gated and nothing is
# retroactively refused. The live cost is a checkout or bisect of a pre-floor tree.
#
# ⚑⚑⚑ AND `cassian`'s BINARY NEEDS A THIRD TERM, MEASURED HERE AGAINST ITS OWN CLASSIFICATION.
# Their rule: *an arm that measures a PRE-EXISTING declaration inherits a true floor; an arm that
# ships its own population cannot.* They placed all three of this module's arms in the second
# class, on this dispatcher's own report. **Measured, that is wrong — all three read populations
# that predate them**: 65 assertions before the sweep, 188 warrants before the pairing arm, 5
# constant references before the disclosure arm.
# ⚑⚑ YET THE FLOOR IS STILL FALSE FOR 31 OF 44 COMMITS, WHICH THE CLASSIFICATION PREDICTS IT
# SHOULD NOT BE. The resolution: the population **predates the ARM and not the FILE.** It was 0 for
# the first six commits and first reached 50 at `1ad358d`, eight commits before the sweep shipped.
# ⚑ ***Inheriting a population is not inheriting a HISTORY.*** An arm inherits a true floor only
# back to where its population first crossed the floor — never to the file's beginning — so the
# sweep is owed for every arm whose subject GREW, which is nearly all of them.
# ⚑ This floor would be refused by 31 of 44 commits and is honest from `1ad358d` onward.
_MIN_SWEPT_FLOOR_HONEST_FROM = "1ad358d"
_MIN_SWEPT = 50
# ⚑ A PAYDOWN CEILING, NOT A TARGET, AND IT IS NOW ZERO. All 20 were paid the tick after the
# ceiling was set — each resolved to a real test by its own key, so the debt was a missing `check`
# LINE rather than missing coverage. ⚑⚑ A ceiling left at 20 after paying 20 would let the debt
# return silently, which is the shape a paydown ratchet exists to refuse.
# ⚑ THE SAME HISTORICAL CLAIM, MEASURED: **27 of 30 sampled `warrants.bib` commits carry at least
# one check-less warrant** and would be refused by this ceiling. Kept at 0 for the same reason —
# a ceiling left where a paid debt used to sit lets it return silently — and bounded the same way.
_WARRANTS_WITHOUT_CHECK = 0
_WITNESS = _DIST.parent / "domain_witness.sh"
_PREFLIGHT = _DIST.parent / "preflight.sh"
# ⚑ A FLOOR ON THE POPULATION, not a target: a glob that stopped matching would make the
# comment-claim arm vacuous in the direction that reads as success. Measured 8 at the tick it
# shipped; set below that so adding or removing one script is not a false refusal.
_MIN_SHELL_SCRIPTS = 3


def test_the_poll_enumerates_censuses_from_the_filesystem() -> None:
    """⚑⚑⚑ TRACKED WAS A SECOND CHEAP KEY, INSIDE THE REPAIR FOR THE FIRST.

    Tick 1 replaced a hardcoded `CENSUS-deps-build.md` with `git ls-files`, which looked like
    deriving the population and was `is it committed` rather than `is it a census run file`.
    ⚑ Measured the tick after: `CENSUS-build-hermeticity.md` was convened by a peer, placed in this
    tree, carried mtools on its roster, and was INVISIBLE because its dispatcher had not committed
    it. That window is the one where a poll has the most to report.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "find findings" in body, "the population must be the filesystem, not the index"
    assert "git ls-files 'findings/CENSUS-" not in body, "trackedness is a column, not a filter"


def test_the_poll_marks_an_untracked_run_file_rather_than_hiding_it() -> None:
    """⚑ `§F` INVERTED: a run file not in `HEAD` still ROSTERS the parties who read it by path."""
    body = _POLL.read_text(encoding="utf-8")
    assert "NOT IN HEAD" in body, "an untracked census must be reported, not omitted"


def test_the_poll_derives_the_status_table_signature() -> None:
    """⚑⚑ A HARDCODED SIGNATURE REPORTED A FROZEN CENSUS AS NOT FROZEN.

    `deps-build`'s `§S` is `party | status`; `constitution`'s is `surveyor | status`. Measured the
    moment the block was generalised over both: roster `? of 7`, then
    `NOT FROZEN — the roster is SHORT`, against a census whose `§V` carries FREEZE CALLED at rev 37
    and whose seven legs are all in `HEAD`. ⚑ A confident refusal produced by a missing TABLE rather
    than a missing ROW — the same class as the positional `--table N` predicate this block already
    refuses, arriving through the header instead of the index.

    ⚑⚑⚑ AND THE SECOND COLUMN IS NOT ALWAYS `status`, WHICH IS HOW THIS WENT BLIND AGAIN.
    `build-hermeticity` renamed its `§S` to `party | state` at rev 27 — in the act of REPAIRING its
    own state vocabulary — and the poll reported it `PRE-FILING` while `HEAD` held 11 legs. That
    census's freeze is the stated dispatch trigger for TWO held runs, so the instrument that fires
    the trigger could not evaluate the condition. ⚑ Reported by `rosettapkg`, from outside.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "(party|surveyor|repo|leg) \\| (status|state)" in body, (
        "the signature must range over the NOUNS AND THE STATE WORDS actually in use; "
        "a set that covers only the headers its author had seen is a hand-written population"
    )


def test_the_poll_reports_an_unrecognised_status_header_rather_than_defaulting() -> None:
    """⚑⚑⚑ AN UNMATCHED SIGNATURE MUST NOT BECOME `grep ""`, WHICH MATCHES EVERY TABLE.

    Removing the `party | status` default fixes a wrong-answer defect and opens a worse one: an
    empty `$sig` makes `grep "$sig"` match the FIRST table in the document and report its row count
    as the roster. ⚑ Three outcomes, not two — recognised / no table at all / **a table shaped like
    a roster under a header I do not know**. The third is the state the poll was silently in, and
    it read as the second. The arm also PRINTS the headers it found, so the set above is widened by
    measurement rather than by another guessed literal.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "§S UNRECOGNISED, not absent" in body
    assert 'if [ -n "$sig" ]; then' in body, "the empty signature must be branched on, not used"


def test_the_poll_distinguishes_a_missing_status_table_from_a_short_one() -> None:
    """⚑⚑⚑ IT MANUFACTURED A DELETION CLAIM ABOUT A TABLE NOBODY HAD WRITTEN.

    A census with no `§S` yet made the roster read `? of 8`, and the branch reported
    *the roster is SHORT: a dropped row reads as terminal*. ⚑ Absent-versus-unavailable inside the
    instrument that reports it: a missing `§S` means *nobody has filed*; a short `§S` means *a row
    was dropped*; and reading the first as the second invents a defect out of a census's normal
    opening state.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "PRE-FILING, not short-rostered" in body


def test_the_poll_reconciles_head_against_the_status_roster() -> None:
    """⚑⚑⚑ THE UNADMITTED CHECK SAW ONE DIRECTION, AND ITS SILENCE READ AS AGREEMENT.

    The check finds files with no `§S` row. It cannot find `§S` rows that no longer cover the
    directory — so when a late leg went from untracked to COMMITTED, the only signal there was went
    quiet at the exact moment the disagreement became permanent rather than pending. ⚑ Measured:
    `HEAD` held 8 constitution legs, `§S` held 7 rows, and the poll reported `7 of 7 — FROZEN`.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "n_head=" in body, "the poll must count HEAD's legs, not only §S's rows"
    assert "DESCRIBES" in body, "the divergence must be reported rather than inferred"


def test_the_polls_fetchability_predicate_is_not_ls_files() -> None:
    """⚑⚑ `ls-files` REPORTS A STAGED FILE AS TRACKED, WHICH IS THE WRONG QUESTION FOR INTAKE.

    *Tracked in a peer's index* and *fetchable by me* are different properties and only the second
    decides whether code can move. ⚑ Measured: every island module this poll called TRACKED had
    ZERO commits on the branch — a blocker reported as clearing, for ten ticks, that never cleared.
    And `git log --all` is worse rather than better: 33 commits, every one under
    `refs/edit-snapshots/`, none carried by a clone.
    """
    body = _POLL.read_text(encoding="utf-8")
    start = body.index("tracked() {")
    fn = body[start:body.index("\n}", start)]
    assert "log --oneline" in fn, "fetchability needs branch history, not index membership"
    assert "staged only (NOT fetchable)" in fn, "the three-valued answer must be stated"


def test_the_ratchet_check_captures_its_own_output() -> None:
    """⚑⚑⚑ THE GATE NAMED THIS GAP ABOUT ITSELF BEFORE ANYONE ELSE DID.

    Refusing a commit, it printed the offending keys and then *no check captured its own output —
    the label above is all the account there is. That is a defect in the CHECK, not in your
    commit.* ⚑ The gap-naming repair converting a SILENCE into a NAMED gap — and the check it named
    is the one that has refused most often: two paydowns, a peer's fourth commit, three earlier
    rounds. Six refusals, four parties.

    ⚑⚑ The detail always existed: `mikemol-ratchet` lists every new key by `path:rule`. It went to
    the terminal, hundreds of lines above the verdict, interleaved with a 35-target bazel run.
    **A repair applied to one call site is not a repair to the class** — this is the second of
    twenty sites wired.
    """
    body = _GATE.read_text(encoding="utf-8")
    # ⚑ ANCHOR ON THE INVOCATION, NOT THE GUARD. The first `mikemol-ratchet` in the file is the
    # `[ -x ... ]` presence check; slicing from there missed the call site by nine lines and the
    # first cut of this test failed against a correct repair.
    start = body.index("if ! ratchet/.venv/bin/mikemol-ratchet")
    block = body[start:start + 400]
    assert 'note_failure "$dist: ratchet' in block
    assert '"$rlog"' in block, "the ratchet must capture its output for the verdict to replay"

# --- four repairs from two ticks, each armed by hand once and none gated ------------------------
#
# ⚑⚑⚑ A COMMENT NAMING A CLASS IS EVIDENCE THE CLASS WAS SEEN ONCE, AND IS ROUTINELY READ AS
# EVIDENCE IT WAS HANDLED (`gabion`, 2026-09-06). `.githooks/pre-commit` carries elaborate prose
# about the exit-trap distinction, the lock-versus-content separation and the marker gap — and not
# one of those paragraphs is an arm. ⚑ I gated five repairs for exactly this reason two ticks ago
# and then added four more ungated ones to the same file: **the prose accumulated faster than the
# coverage**, which is the cheap-proxy class with a comment as the proxy.


def test_every_witness_call_site_goes_through_the_capturing_helper() -> None:
    """⚑⚑⚑ EIGHT WITNESSES COULD NOT CARRY THEIR OWN ACCOUNT, IN A FILE WHOSE COMMENT SAID WHY.

    The shellcheck witness and the ratchet were wired to capture; the ratchet's own comment reads
    *a repair applied to one call site is not a repair to the class* — and eight witnesses sat
    unwired in the same file. ⚑ Measured from the blocked seat: a refusal named seven witnesses and
    printed seven bare labels, then the gate's own honest line about no check capturing its output.

    ⚑⚑ THE ASSERTION IS THAT NO BARE CALL SURVIVES, not that the helper exists. A helper nobody
    routes through is the same defect wearing a definition.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "witness() {" in body, "the capturing helper must exist"
    bare = [ln for ln in body.split("\n")
            if ln.startswith("./domain_witness.sh") and "note_failure" in ln]
    assert not bare, f"{len(bare)} witness call site(s) bypass the helper: {bare[:2]}"


def test_the_sweep_runs_up_front_as_well_as_at_exit() -> None:
    """⚑⚑⚑ AN EXIT TRAP CLEANS UP AFTER THE RUN IT COULD HAVE SAVED.

    Measured: a refusal showed two witnesses reporting `already carries probe residue` on
    `cmdparse.py`, and the **very next line of the same run** swept that residue. The sweep did its
    job one run too late.

    ⚑ The trap and the pre-flight are two jobs wearing one name — the trap clears THIS run's
    residue for the next party; the up-front call clears a PREDECESSOR's for this run. Neither
    substitutes for the other, and having only the first cost **exactly one extra full refusal per
    stranded probe**, which is the arithmetic that accounts for four of one peer's five refusals
    where no story about concurrency did.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "trap sweep_witness_residue EXIT" in body, "the trap must still fire on any exit"
    lines = [ln.strip() for ln in body.split("\n")]
    assert "sweep_witness_residue" in lines, "the sweep must also be CALLED, not only trapped"


def test_the_restore_separates_a_lock_failure_from_a_content_failure() -> None:
    """⚑⚑⚑ A BEFORE-IMAGE FIXES ATTRIBUTION; IT DOES NOT MAKE A READING CURRENT (`gabion`).

    Measured by a peer in one sequence: the gate printed `CONTENT DIFFERS before=… now=…`, an
    immediate check found `git hash-object` == `git ls-files -s` == **the very `before=` the
    message named as correct**, and the retry then failed with `Unable to create .git/index.lock`.
    ⚑ The `checkout` never ran; something else restored the file; and the message described a state
    that no longer existed when it was read.

    So a non-zero `checkout` is *I could not act* and says nothing about the file; a zero
    `checkout` with a differing hash is *I acted and it did not take*.
    """
    body = (_DIST.parent / "domain_witness.sh").read_text(encoding="utf-8")
    assert "COULD NOT RESTORE" in body, "a failed checkout must not read as a failed restore"
    assert "_co_rc" in body, "the checkout's own exit status must be captured, not discarded"


def test_every_probe_payload_carries_the_residue_marker() -> None:
    """⚑⚑⚑ ONE PAYLOAD CARRIED NO MARKER, SO THE GUARD AND THE SWEEP WERE BOTH BLIND TO IT.

    The residue guard and the gate's sweep key on the literal `transient domain probe`. The mypy
    payload appended a bare function definition without it — so a stranded mypy probe was invisible
    to **both** mechanisms built to catch exactly that.

    ⚑ Measured from two seats and resolved by neither: one peer saw four files swept with
    `state.py` absent and correctly declined to guess between a missing path and a late probe;
    another measured the same file by content hash and found a live probe. **It was neither — the
    path was in the list and the predicate could not see the payload.**
    """
    body = (_DIST.parent / "domain_witness.sh").read_text(encoding="utf-8")
    # ⚑ THE WHOLE FILE, NOT A SLICE. The first cut sliced 900 bytes from the `case` and matched
    # nothing at all — so the test failed for the right reason by accident, and a narrower bug
    # would have passed. Every append to the victim is a payload wherever it appears.
    payloads = [ln for ln in body.split("\n")
                if '>> "$victim"' in ln and "printf" in ln]
    assert payloads, "the probe payloads must be findable to be checked"
    unmarked = [ln for ln in payloads if "transient domain probe" not in ln]
    assert not unmarked, f"payload(s) without the residue marker: {unmarked}"


def test_the_gate_replays_detail_for_the_distribution_checks() -> None:
    """⚑⚑⚑ A REFUSAL THAT NAMES ONLY ITS CLAIM MAKES THE BLOCKED PARTY DO THE DIAGNOSIS.

    Measured in one afternoon: TWELVE peer refusals — six to `linux-sources`, six to `gabion` —
    and **every mechanism was found by the party the gate blocked rather than by the gate.** The
    checks stream to stderr, so a human at a terminal sees the detail; `note_failure`'s summary is
    what a peer reads out of a captured run, and for `ruff`, `mypy` and `pytest` it carried the
    claim with none of the evidence.

    ⚑⚑ The capture is `witness()`'s existing shape HOISTED rather than re-typed: run into a log,
    echo the log to stderr so the interactive path is unchanged, hand the log to `note_failure` so
    the refusal REPLAYS the finding. ⚑ Three sites repeating a pattern is how the log-path ordering
    defect got in the first time.

    MEASURED, BOTH ARMS, on a fixture before the sites were converted: a passing check contributes
    nothing to the summary; a failing one puts its own stderr into `failed_detail`. **A one-armed
    test passes a broken-shut gate.**
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "run_checked()" in body, "the capture helper must exist"
    for check in ("ruff — lint clean", "mypy — types clean", "pytest — every case passes"):
        assert f'run_checked "$dist: {check}' in body, (
            f"{check} must route through the capturing helper, not a bare note_failure"
        )
    assert 'fail=1; note_failure "$_rlabel" "$_rclog"' in body, (
        "the helper must pass the LOG to note_failure; a label alone is the defect being repaired"
    )


def test_the_warrant_count_is_anchored_against_a_quoted_delimiter() -> None:
    """⚑⚑⚑ AN UNANCHORED `@misc{` COUNTS A QUOTATION AS A WARRANT.

    This corpus's `claim` fields quote code, so a warrant claiming something about bibtex syntax
    puts the entry delimiter inside a field and the ledger reads 177 against 176 — a bare
    arithmetic refusal with **no pointer to the quotation that caused it**, blocking every commit
    in the distribution until someone reads the diff closely enough to find it.

    ⚑⚑ MEASURED on a fixture, both arms, before the gate was changed: one entry whose claim
    contains the string `@misc{` counts as **2** unanchored and **1** anchored. ⚑ The unanchored
    form agreed with the anchored one at 176 on the day it was written, which is exactly what made
    it invisible — `rosettapkg` named the mechanism (*a substring frequency offered as a count of
    kinds*) and it found this within minutes of being pointed at this gate.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "grep -c '^@misc{'" in body, "the warrant count must be anchored to line start"
    assert "grep -c '@misc{'" not in body, (
        "an unanchored count is the defect: a claim quoting the delimiter inflates the ledger"
    )


def test_the_gate_names_the_population_its_ledger_ranges_over() -> None:
    """⚑⚑⚑ A CORRECT COUNT OVER A MIS-NAMED POPULATION PASSES EVERY ARITHMETIC CHECK.

    The 1:1 ledger ranges over test FUNCTIONS. `hooks` holds 176 `def test_` lines and
    `pytest --collect-only` collects **248** — 15 `parametrize` decorators expand the rest. The
    invariant is correct as designed and the count is right; the sentence a reader takes from it is
    not. ⚑ This ledger does not say *every test case is warranted*. It says *every test function
    is*, and **248 cases run while 176 carry a warrant**.

    ⚑⚑ Named rather than changed: whether warrants should be per-case is the operator's call, and
    the plan settled per-function. What is repaired here is the claim, not the invariant.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert "TEST **FUNCTIONS**, NOT TEST **CASES**" in body
    assert "248" in body, "the case count must be stated, or the gap is invisible again"


def test_the_poll_reports_more_than_one_roster_shaped_table() -> None:
    r"""⚑⚑⚑ TWO MATCHING TABLES CONCATENATED THEIR ROW COUNTS AND FED `5\n12` TO `[`.

    At its freeze `build-hermeticity` carries BOTH `party | state at freeze` — `§G`'s publication,
    5 GROUPED rows — and `party | state`, `§S`'s running roster at 12 rows, one party each. Both
    are correct, and `§G` requires the first. ⚑ **So the poll broke at the exact moment its subject
    did the right thing**, which is the third instrument here to degrade that way in one day: a
    column renamed while its census repaired its own state vocabulary, and a correction-rate grep
    defeated by commit subjects that name the defect rather than the act.

    ⚑⚑ AND A FAILED `[` TAKES THE ELSE BRANCH, so the roster-identity guard did not run and the
    poll fell through to the `§V` check — which printed `FROZEN` correctly. **A right answer from a
    dead predicate is indistinguishable from a right answer.** Diagnosed from the consuming side by
    `cassian-observability` while `rosettapkg` measured the cause from the producing side.

    ⚑ BOUNDED, because the obvious worry is whether earlier verdicts were also ungated: measured
    `git show HEAD~1` of that census — **1 matching table before the freeze commit, 2 after** — so
    the second table arrived WITH the freeze and no earlier reading could have been affected.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert 'grep -c "$sig"' in body, "the poll must COUNT its matches, not assume one"
    assert "roster-shaped tables" in body, "multiplicity must be reported, not resolved silently"
    assert "tail -1" in body, "the running roster is taken; the summary is not a second roster"


def test_the_residue_guard_names_both_causes_not_one() -> None:
    """⚑⚑⚑ A GUARD WHOSE ACCOUNT NAMED ONE CAUSE OF TWO SENT HALF ITS READERS TO A HARMFUL REMEDY.

    The refusal said *a previous witness was killed inside its mutation window* and told the reader
    to run `git checkout`. ⚑ MEASURED: **seven witnesses refused at once** — mypy and ruff across
    all three distributions, plus shellcheck — while a PEER'S GATE WAS MID-RUN. Nothing had been
    killed. `_witness_victims` is a fixed five-path list and every party runs the same hook, so
    concurrent gates contend for those files **by construction**.

    ⚑⚑ AND THE WRONG HALF OF THE ADVICE IS ACTIVELY HARMFUL: `git checkout` on a LIVE probe
    destroys the mutation another party's witness is mid-way through measuring, converting their
    correct run into a spurious arm-1 failure. **The refusal was right; the account was not** — a
    hand-written population of causes, inside a guard, in the repository that has spent a day
    measuring hand-written populations.

    Both causes are now named with their differing remedies, and the concurrent case is told to
    check `pgrep` and WAIT rather than check out.
    """
    body = _WITNESS.read_text(encoding="utf-8")
    assert "TWO CAUSES" in body, "the guard must not name one cause of two"
    assert "ANOTHER PARTY'S GATE IS RUNNING RIGHT NOW" in body
    assert "Do NOT check it out" in body, (
        "the concurrent case must be steered away from the remedy that breaks a live measurement"
    )
    assert "pgrep -f domain_witness" in body, "the reader needs a way to tell the two apart"


def test_the_gate_ends_on_a_decision_not_on_an_echo() -> None:
    """⚑⚑⚑ THE GATE'S SUCCESS PATH EXITED ON A `printf`'s STATUS, NOT ON A VERDICT.

    The last line was `say "ok"` — a `printf` that succeeds unconditionally. The gate was CORRECT,
    because the refusal path `exit 1`s above it; but "the commit is clean" and "printf worked" are
    two different propositions that agreed only by luck of the control flow. ⚑ **Right by accident,
    with nothing saying so.**

    ⚑⚑ A CALLER TWO SEATS AWAY PAID FOR THIS SHAPE. `rosettapkg` reported a backgrounded run that
    printed `All checks passed!`, exited 0, and left its file STAGED AND UNCOMMITTED — two runs,
    same exit status, opposite outcomes, distinguishable only by `git ls-tree`. Reproduced on a
    fixture: a loop whose every attempt refused reports `rc=1`, but the same loop followed by one
    trailing `echo` reports **`rc=0`**.

    ⚑ THE GENERAL FORM IS NOT ABOUT PIPES OR LOOPS: **the last command wins, and a wrapper's last
    command is almost never the work.** A pipe reports its last stage, a loop its last iteration, a
    script its last line — same rule, three surfaces.

    MEASURED, four arms, before this test was written: an appended `false` sets `rc=1` on an
    unguarded script and **cannot reach the exit status** on one ending in `exit 0`.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert body.rstrip().endswith("exit 0"), (
        "the gate must end on an explicit decision; a trailing command appended later would "
        "otherwise become its exit status"
    )


def test_the_gate_retains_a_refusal_record() -> None:
    """⚑⚑⚑ TWO CENSUS LEGS CLAIMED THE REFUSAL DATA EXISTED. MEASURED: IT DID NOT.

    `MT-06` row 1 and `MT-K4` both state that this gate emits a refusal account on every failure
    and nothing aggregates them — filed as *the population was never named*, with the data asserted
    present and only the reader missing. ⚑ MEASURED in the log directory: **17 files, 0 containing
    a refusal**, because every run OVERWRITES them.

    ⚑⚑ **THE MISSING PIECE WAS RETENTION, NOT A READER, AND THE WRONG ONE WAS NAMED TWICE.** A
    reader built against that claim would have found an empty population and reported **zero peer
    refusals** — a confident answer over a corpus that does not exist, which is this session's own
    recurring defect arriving inside the repair for it.

    MEASURED, three arms, on a fixture before the gate was changed: a PASS writes nothing; a
    refusal appends one line; a second refusal APPENDS rather than overwrites.

    ⚑ Append-only with no pruning: a rotation policy decides what may be forgotten and this gate
    has no standing to make that decision. Growth is bounded by how often the gate refuses, which
    is the quantity being measured.
    """
    body = _RECORDER.read_text(encoding="utf-8")
    assert "REFUSALS.tsv" in body, "a refusal must leave a durable record"
    assert '>> "$_rr_log"' in body, (
        "the record must APPEND; a truncating write reproduces the defect being repaired"
    )
    # ⚑ THE ORDERING IS A PROPERTY OF THE CALLER, NOT THE RECORDER, since the writer moved to a
    # shared file. Read where the assertion's subject now lives rather than where it used to.
    gate = _GATE.read_text(encoding="utf-8")
    assert gate.index("record_refusal pre-commit") < gate.index('say "REFUSED'), (
        "the record is written before the verdict is printed"
    )


def test_every_refusal_site_carries_its_own_detail() -> None:
    """⚑⚑⚑ SIX REFUSALS NAMED A CLAIM AND DISCARDED THE FINDING THAT PROVED IT.

    Each of these had its detail in hand and threw it away: the warrant ledger computed both counts
    and passed neither; the section check ran `diff -q` FOR ITS STATUS ALONE, so the refusal said a
    disagreement existed and never which sections; `orphan_check` and `stubtest` streamed to stderr
    and passed a bare label; and the markdown check sent `verify` to **/dev/null** — for the one
    check whose entire output is a list of specific swallowed headings and line numbers.

    ⚑⚑ THAT MATTERS MORE SINCE `REFUSALS.tsv` EXISTS: the durable record carries the LABEL, so a
    bare label writes a row saying *something disagreed* with no way to learn what. **A refusal is
    read by the party it blocked, and twelve peer refusals in one afternoon were each diagnosed by
    the blocked party rather than by this gate.**

    ⚑ AND ONE SITE MY OWN SWEEP MISCLASSIFIED: the hermetic-suite refusal takes no log argument but
    extracts the failing target names INTO its label. My `grep` defined the population by *absence
    of a second argument* rather than by *whether the refusal is informative* — the population was
    defined by the instrument's shape, not the claim's question, which is the defect this session
    has recorded four times.
    """
    body = _GATE.read_text(encoding="utf-8")
    assert 'note_failure "$dist: warrant ledger 1:1" "$_wlog"' in body, (
        "the two disagreeing counts exist at the site and must reach the record"
    )
    assert 'note_failure "$dist: warrant sections vs rubric sections" "$_slog"' in body
    # ⚑ THE `diff -q` IN THE CONDITION IS CORRECT AND MUST STAY — it is the test. What was missing
    # is a SECOND, un-`-q` diff writing the symmetric difference into the record. An earlier form
    # of this assertion searched for the absence of `diff -q` and failed against the guard it was
    # meant to protect: the predicate was defined by a string rather than by the property.
    assert '> "$_slog"' in body, (
        "a second diff must write the symmetric difference to the log, not merely a status"
    )
    assert 'run_checked "every shell checker is invoked or declared parked"' in body
    assert 'run_checked "stubtest' in body
    assert 'note_failure "$md: headings unreachable to mdstruct" "$_mdlog"' in body, (
        "verify names the swallowed heading and its line; /dev/null discarded exactly that"
    )


def test_the_poll_detects_a_duplicate_revision_number() -> None:
    """⚑⚑⚑ `§V` HAS NO ALLOCATOR, TWO ROWS COLLIDED TWICE, AND NOTHING CHANGED IN BETWEEN.

    Rev 12 recorded it — `gabion` filed 10 and `linux-sources` 11 while the dispatcher was writing
    another 10 — and rev 19 hit it again, `gabion`'s 18 reaching `HEAD` first. **Both were resolved
    by renumbering BY HAND.** ⚑ A finding recorded twice and never repaired is being treated as
    decoration.

    ⚑⚑ THE POLL READS `§V` BY COLUMN (`--col 2 --starts FREEZE`) AND NEVER BY ROW NUMBER, so a
    duplicate index was invisible to it: the log stays **structurally valid** and becomes
    **semantically ambiguous**, and `mdstruct` sees only the first. A leg citing that revision
    cites two rows.

    ⚑ AND THE DEFECT IS SELF-CLEARING BY MANUAL LABOUR, which is why it survived — by the time
    anyone looks, whoever noticed has already renumbered. **Both arms measured on fixtures before
    this was written**: a table with rows `1 2 2` reports `2`; one with `1 2 3` reports nothing.
    A duplicate-detector that never fires is a print statement wearing a control's name.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "uniq -d" in body, "the poll must detect a repeated revision index"
    assert "DUPLICATE REVISION NUMBER" in body, "and must report it rather than resolve it"
    assert "sort -n | uniq -d" in body, (
        "numeric sort before uniq -d: lexical order groups 1, 10, 11 and misses 2, 2"
    )


def test_the_poll_detects_a_malformed_table_row() -> None:
    """⚑⚑⚑ A MALFORMED ROW BLINDS EVERY TABLE READER PAST IT, SILENTLY.

    `§V` rows 18 and 22 carry **unescaped pipes inside code spans**, so markdown counts 5 and 6
    cells against the table's 4 and `mdstruct rows` stops at the first one. MEASURED on the live
    file: **20 rows at 4 cells, one at 5, one at 6.**

    ⚑⚑ THAT IS HOW THE DUPLICATE DETECTOR SHIPPED ONE TICK EARLIER REPORTED CLEAN ON A DUPLICATE
    THAT WAS PRESENT — it read a mode that had already stopped. And the dispatcher's first
    diagnosis of the truncation was **the row is oversized**, which is false: *not too long,
    ill-formed*, and a length hypothesis would never have been falsified by shortening rows.

    ⚑ SILENCE PAST ROW 18 IS INDISTINGUISHABLE FROM A CLEAN READ. It was found by accident while
    checking something else, and nothing would have reported it. **So the SHAPE is checked before
    any count over the table is trusted** — a cell count that differs from its siblings is the
    property, and it needs no knowledge of what the columns mean.

    Both arms measured on fixtures first: a table with one pipe-carrying row yields cell counts
    `4 5`; a clean one yields `4`.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "ROWS DISAGREE ON CELL COUNT" in body, "a malformed row must be reported, not skipped"
    assert "NF-2" in body, "the cell count per row is the property; column meaning is irrelevant"
    assert "UNRELIABLE" in body, (
        "a count over a truncated table must be marked unreliable rather than printed as a fact"
    )
    # ⚑⚑⚑ AND THE FIRST VERSION OF THIS ARM'S MESSAGE SAID "unescaped pipe", WHICH IS WRONG ADVICE.
    # `gabion` attempted the escape and measured no change; reproduced on a fixture here: a row
    # containing `` `a \| b` `` still yields 5 cells against 4, because `awk -F'|'` and every
    # field-splitting reader split on the RAW BYTE. ⚑ Escaping changes RENDERING, not the split.
    # Only REMOVING the pipe works, and a filer following the original message would have believed
    # the row repaired.
    assert "escaping it does NOT help" in body, "escape is not the remedy; removal is"
    # ⚑⚑ AND THE ARM ANSWERS *ARE THE SHAPES UNIFORM*, NOT *IS EACH ROW CORRECT*. A peer read
    # `4 5 6` after a FAILED revert as evidence the revert had worked; the file was at 3 cells and
    # the distinct-value set happened to contain the right numbers. **A `sort -u` over a set that
    # contains the right values is not a check that the values are in the right places.**
    assert "re-measure PER ROW" in body, (
        "the set of shapes cannot certify an individual row; say so where the arm is read"
    )


def test_the_poll_splits_over_from_under_cell_counts() -> None:
    """⚑⚑⚑ A SHAPE DISAGREEMENT HAS THREE CAUSES AND A UNIFORM REMEDY DAMAGES SOME OF THEM.

    `cassian` measured this over **105 tracked files in an independent corpus**: 12 anomalies,
    **three mechanisms**. Nine were a raw pipe inside a cell — and ⚑ **every one was already
    escaped**, which is independent confirmation that escaping does not help, reached on a corpus
    neither this repository nor `gabion` had touched. Five were the `||||` spanning-row idiom,
    **deliberate and correct**. Two were a genuinely missing cell.

    ⚑⚑ **A UNIFORM `fix the pipe` SWEEP WOULD HAVE DAMAGED FIVE AND MISSED NINE.**

    The over/under split routes the remedy and costs one comparison: a row with MORE cells than its
    header **gained a separator**; one with FEWER **lost a cell**. ⚑ The arm still cannot name the
    cause — it reports a shape disagreement — but it can say which of two remedies is even
    applicable, *which the set alone could not*.

    ⚑ And one of `cassian`'s two genuinely-missing cells is in its `§5` table — **the table whose
    subject is that controls get misread** — where a merged cell makes a reader attribute the
    control text to the reader column.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "OVER their header" in body, "the over/under split must be reported, not just the set"
    assert "must not be 'repaired'" in body, (
        "the ||||-spanning-row idiom is a legitimate OVER; a uniform remedy would damage it"
    )
    assert "if(NF>h)" in body, "rows OVER their header must be counted"
    assert "if(NF<h)" in body, "rows UNDER their header are a different cause and count separately"


def test_the_poll_measures_reader_reach_not_a_cause() -> None:
    """⚑⚑⚑ FOUR CAUSE HYPOTHESES, THREE DEAD AND ONE NECESSARY-NOT-SUFFICIENT — SO MEASURE REACH.

    Pipes (a real defect, repaired, not the cause), length (row 11 is longer and reads fine),
    encoding (clean both sides), and finally the escaped backtick — **which bisection located and a
    minimal fixture of the same construct does NOT reproduce.** Something in that row combined with
    it and what remains unknown.

    ⚑⚑ **SO THE ARM STOPPED HUNTING THE CAUSE AND MEASURES THE CONSEQUENCE**: rows the structural
    reader REACHES versus rows PRESENT. It needs no theory of the trigger.

    Both arms measured before this was written:

        pre-repair blob   reach=18  present=27   -> TRUNCATED, arm fires
        clean fixture     reach=2   present=2    -> ok, arm silent

    ⚑ AND THE ESCAPED-BACKTICK ARM WAS CORRECTED IN THE SAME PASS. It had asserted that such a line
    *loses every table row after it*; the two it fires on in this repository are **prose, correctly
    fenced, and all 29 revisions read.** ***An arm that warns about a non-defect trains its reader
    to ignore it.*** It now reports a smell, says it cannot tell harmless from truncating, and
    names the check that settles it.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "STRUCTURAL READER STOPS EARLY" in body, "reach must be measured, not inferred"
    assert "_present=" in body, "rows present is the denominator and must be computed"
    # ⚑⚑⚑ THE DENOMINATOR MUST NOT COUNT HEADERS OR SEPARATORS, AND `cassian`'s REACH ARM DID.
    # Adopting this design, theirs flagged two clean files as TRUNCATION with a shortfall of
    # **exactly 4 in each, each having exactly 4 tables** — header rows, present as pipe lines and
    # never emitted as rows. ⚑ The caveat naming that confound sat three lines below their verdict.
    # ⚑⚑ THIS ONE ANCHORS ON `^| <number> |`, which cannot match a header or a separator. Verified
    # rather than argued: numerator 30 = denominator 30 here, and 45=45, 38=38, 37=37 across the
    # other three census files. **An arm silent because its denominator is wrong and one silent
    # because the file is clean are byte-identical in the output.**
    assert r"grep -cE '^\| [0-9]+ \|'" in body, (
        "the denominator must anchor on a NUMBERED row; counting pipe lines counts headers"
    )
    # ⚑⚑⚑ POSITION IS THE WHOLE PREDICTIVE CONTENT AND IT WAS ABANDONED FOR A TICK. Measured
    # across three blobs of one file: 49a4f5a has the escape INSIDE table row 18 and reads 18 of
    # 27; 057bf13 has two in PROSE and reads 28 of 28. ⚑ RAGGEDNESS came and went across that same
    # pair WITHOUT changing the reach — so the correlation four revisions asserted as a mechanism
    # was never the cause. Two real defects in one row: pipes break field-splitting readers, the
    # escaped backtick breaks the structural one.
    assert "INSIDE A TABLE ROW" in body, "position decides; a bare count cannot"
    assert "_ebt_row=" in body, "the in-table subset must be counted separately"


def test_no_string_assertion_in_this_module_is_vacuous() -> None:
    """⚑⚑⚑ AN ASSERTION WHOSE LITERAL IS NOT IN ITS TARGET PASSES WHILE TESTING NOTHING.

    Written after one shipped and survived a full tick. It checked for a pattern whose escaping did
    not match `blockers.sh`, so `in body` was satisfied by a string the file does not contain —
    ⚑ **caught only by evaluating the membership by hand**, which is not a procedure.

    ⚑⚑ **65 SUCH ASSERTIONS EXIST IN THIS MODULE AND NOTHING ENUMERATED THEM.** A hand-written
    population with no enumeration procedure is this repository's most-measured defect, and it was
    sitting in the suite that measures it. **This is the enumeration.**

    ⚑ AND IT IS ALSO THE ANSWER TO THE T139 GAP `cassian` NAMED — *an arm nobody has seen fire.*
    Every assertion here now has a live positive by construction: **if its literal is absent from
    the file it names, this test fails.** A green suite means the literals are real, not that
    nobody looked.

    ⚑⚑ THE SWEEP READS THE MODULE'S OWN SOURCE AND RESOLVES EACH ASSERTION AGAINST THE FILE ITS
    ENCLOSING TEST READS, so it needs no list to maintain — *a list would be the same defect one
    level out.*
    """
    src = _THIS.read_text(encoding="utf-8")
    tree = pyast.parse(src)
    # ⚑ A TARGET MISSING FROM THIS MAP IS NOT A GAP THE SWEEP REPORTS — the test resolves to
    # whatever OTHER file it reads, and its assertions are checked against the wrong haystack.
    # `_RECORDER` was absent when the refusal writer moved into it, and three arms went red
    # against `pre-commit` rather than being swept against the file they now read.
    targets = {
        "_POLL": _POLL, "_GATE": _GATE, "_WITNESS": _WITNESS, "_THIS": _THIS,
        "_RECORDER": _RECORDER, "_MSGHOOK": _MSGHOOK, "_MSGCOUNT": _MSGCOUNT,
        "_PREFLIGHT": _PREFLIGHT,
    }
    checked = 0
    missing: list[str] = []
    for fn in (n for n in pyast.walk(tree) if isinstance(n, pyast.FunctionDef)):
        # which file does this test read?  the `X.read_text(...)` call names it
        reads = {
            n.value.func.value.id
            for n in pyast.walk(fn)
            if isinstance(n, pyast.Assign)
            and isinstance(n.value, pyast.Call)
            and isinstance(n.value.func, pyast.Attribute)
            and n.value.func.attr == "read_text"
            and isinstance(n.value.func.value, pyast.Name)
        }
        named = [targets[r] for r in reads if r in targets]
        # ⚑⚑⚑ `len(named) != 1: continue` SILENTLY SKIPPED EVERY MULTI-FILE TEST, which is the
        # vacuity the sweep exists to catch, inside the sweep. The first test to read two files
        # exposed it — and it exposed it by FAILING rather than by being skipped only because a
        # target was missing from the map above; with the map complete it would have gone quiet.
        # ⚑ THE UNION IS ALSO THE CORRECT PREDICATE, not merely the one that admits these tests:
        # an assertion is vacuous when its literal appears in NO file the test reads, and taking
        # `named[0]` asserted that a test's first file is its only one.
        if not named:
            continue
        haystack = "\n".join(f.read_text(encoding="utf-8") for f in named)
        for node in pyast.walk(fn):
            if (
                isinstance(node, pyast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], pyast.In)
                and isinstance(node.left, pyast.Constant)
                and isinstance(node.left.value, str)
            ):
                checked += 1
                if node.left.value not in haystack:
                    missing.append(f"{fn.name}: {node.left.value!r}")
    assert checked >= _MIN_SWEPT, (
        f"the sweep resolved only {checked} assertions; it is not covering this module"
    )
    assert not missing, (
        "assertion literal(s) absent from the file the test reads — these pass vacuously:\n  "
        + "\n  ".join(missing)
    )


def test_every_warrant_names_a_test_that_exists() -> None:
    r"""⚑⚑⚑ THE 1:1 LEDGER COUNTS ENTRIES AND NEVER CHECKS THE PAIRING.

    The gate refuses unless `@misc{` count equals `def test_` count. Measured: **188 entries, 187
    test names, and the arithmetic passes** — while **20 entries carry no `check` field at all**
    and **20 tests are named by no warrant.** ⚑ *A correct count over an unverified pairing*, which
    is the defect this suite exists to find, in the ledger that enforces it.

    ⚑⚑ AND THE FIRST PREDICATE FOR THIS MEASURED ITS OWN PROSE. `'check' not in entry` reported
    **12**; a structural `^\s*check\s*=` reported **20**. The 8 difference were entries whose
    *claim text* contains the word *check* — *"A checker nothing invokes is a green over nothing"*
    among them. ***A resolver whose population admits its own documentation***, which `cassian` hit
    in the same hour from the other side: their T140 resolver matched the comment explaining its
    own marker convention.

    Both arms measured before this was written: 20 selector-less entries on the live corpus, 21
    with one planted.

    ⚑ **UNRESOLVABLE SELECTORS: 0.** Every `-k` names a real test. The defect is not dangling
    pointers — it is entries with **no pointer at all**, which the count cannot see.
    """
    bib = (_DIST / "warrants.bib").read_text(encoding="utf-8")
    entries = bib.split("@misc{")[1:]
    # ⚑ STRUCTURAL, not substring: `check` must be a FIELD, else a claim mentioning the word
    # "check" reads as one. That distinction is 8 entries wide here.
    without: list[str] = [
        e.split(",", 1)[0].strip()
        for e in entries
        if not pyre.search(r"^\s*check\s*=", e, pyre.MULTILINE)
    ]
    sel_found: list[str] = pyre.findall(r"-k ([a-z_0-9]+)", bib)
    selectors: set[str] = set(sel_found)
    names: set[str] = set()
    for f in sorted((_DIST / "tests").glob("test_*.py")):
        found: list[str] = pyre.findall(
            r"^def (test_[a-z_0-9]+)", f.read_text(encoding="utf-8"), pyre.MULTILINE
        )
        names |= set(found)
    dangling = sorted(selectors - names)
    assert not dangling, f"warrant selector(s) naming no test: {dangling}"
    assert len(without) <= _WARRANTS_WITHOUT_CHECK, (
        f"{len(without)} warrants carry no check field, up from {_WARRANTS_WITHOUT_CHECK}. "
        f"A warrant with no check asserts a claim nothing can run: {without[:5]}"
    )


def test_a_commit_message_cannot_assert_a_wrong_ledger_count() -> None:
    """⚑⚑⚑ A MESSAGE ASSERTING A COUNT OF THE FILE IT IS COMMITTING, MEASURED BEFORE ITS OWN CHANGE.

    `2c75167`'s message reads *"188 entries, 187 test names"* and the ledger **at that very commit**
    holds **189** — the figure was taken pre-commit and the commit added a warrant. ⚑ *The message
    describes the state the author started from, published as the state the commit produced*, in a
    commit whose subject was unverified pairings.

    ⚑⚑ IT IS `rule_citations.sh`'s CLASS ONE LEVEL OVER. That gate exists because *a citation to a
    rule that does not exist reads exactly like a citation to one that does.* **A count off by one
    reads exactly like a count that is right.**

    ⚑ SCOPE IS DELIBERATELY NARROW so the arm cannot drift: ONE quantity, `N entries` or
    `N warrants`, against `grep -c '^@misc{'` on the **staged** ledger. A message with no such
    count passes — *this is not a demand to quote figures, it is a refusal to quote wrong ones.*

    Three arms measured on fixtures before wiring: wrong count `rc=1`, right count `rc=0`, no count
    `rc=0`.
    """
    body = _MSGCOUNT.read_text(encoding="utf-8")
    assert 'git show ":$bib"' in body, (
        "the STAGED ledger is the subject; the working tree describes a file nobody is landing"
    )
    assert "grep -c '^@misc{'" in body, (
        "anchored, matching the gate's own count — unanchored counts a quotation as a warrant"
    )
    assert "asserts no ledger count" in body, "a message with no count must pass, not be demanded"
    # ⚑⚑⚑ AND THE NOUN ALONE IS NOT THE CLAIM. The first cut matched any `N entries|warrants` and
    # would have REFUSED 13 OF 15 historical commits — *"All 20 check-less warrants paid"* is a
    # SUBSET count read as a ledger total. ⚑ **A checker that cannot tell *how many of X* from
    # *how many X exist* refuses the messages most careful about their populations.** Measured
    # against its own history: the corrected predicate inspects 1 commit and refuses 0.
    assert "ledger (holds|has)" in body, (
        "the claim must be POSITIONED as a total; a subset count is not a ledger claim at all"
    )
    # ⚑ NAMED, NOT INLINE. The sweep resolves a test's sources by VARIABLE NAME, so an inline
    # path expression is a file the sweep cannot see — these two assertions were checked against
    # `message_counts.sh`, where they are absent, and the multi-file skip hid that they were.
    hook = _MSGHOOK.read_text(encoding="utf-8")
    assert "message_counts.sh" in hook, "the checker must be invoked, not merely present"
    assert "cannot verify counts, commit refused" in hook, (
        "an absent checker refuses rather than skips; a skip and a pass are indistinguishable"
    )


def test_every_threshold_states_its_historical_exposure() -> None:
    """⚑⚑⚑ A COVERAGE FLOOR IS A CLAIM ABOUT HISTORY, FALSE HERE FOR MOST OF IT.

    `cassian` asked the question nobody here had asked of their own arms — ***would this have
    refused past work?*** — after this repository measured a shipped checker that would have
    refused **13 of 15** historical commits. Run against both thresholds:

        _MIN_SWEPT = 50             31 of 42 commits touching this file carry fewer
        _WARRANTS_WITHOUT_CHECK=0   27 of 30 sampled ledger commits carry at least one

    ⚑⚑ **THE HAZARD IS THE FLOOR, NOT THE PREDICATE.** A floor exists because *the sweep found
    nothing* and *the sweep did not run* are byte-identical, and that reasoning is unchanged. What
    is false is the implicit assertion that the population was never smaller — ***false by
    construction for any arm that introduced its own population.***

    ⚑ NEITHER NUMBER IS LOWERED TO MAKE A SWEEP GREEN. The exposure is **bounded**: these arms read
    the WORKING TREE, never a blob, so no past commit is re-gated and nothing is retroactively
    refused. The live cost is a checkout or bisect of a pre-floor tree.

    ⚑⚑ THIS ARM MAKES THE DISCLOSURE STRUCTURAL RATHER THAN REMEMBERED: a threshold constant must
    carry the measurement of what it would have refused, beside itself, where the next author sets
    one.
    """
    src = _THIS.read_text(encoding="utf-8")
    for const in ("_MIN_SWEPT", "_WARRANTS_WITHOUT_CHECK"):
        idx = src.index(f"{const} = ")
        preamble = src[max(0, idx - 1400):idx]
        assert "would have refused" in preamble or "would be refused" in preamble, (
            f"{const} is a claim about history and must state what it would have refused"
        )


def test_the_refusal_record_names_the_party_not_the_committer() -> None:
    """⚑⚑⚑ EVERY PARTY IN THIS SHARED TREE COMMITS AS THE SAME `user.email`.

    MEASURED: `mikemol@gmail.com` for all of them. The refusal record was built to answer *how many
    peer refusals has this gate caused* — the row this repository's own leg lists as **unbuildable,
    a lower bound with an unknown denominator** — and it recorded a **constant**. ⚑ *A column that
    is the same for every row is a column that was never asked.*

    ⚑⚑ `CLAUDE_CODE_SESSION_ID` IS IN THE HOOK'S ENVIRONMENT AND DISTINGUISHES. Both arms run
    before the change: the committer email is **identical** across two simulated parties, the
    session id **differs**. Then the block itself was executed twice with different ids and wrote
    two rows differing in exactly that column.

    ⚑ THE COMMITTER IS KEPT ANYWAY AND NOT BECAUSE IT DISCRIMINATES — it does not. It is the
    identity the commit will carry, so a reader joining this record against `git log` needs it.
    **Dropping it would make the row true and unjoinable.**
    """
    body = _RECORDER.read_text(encoding="utf-8")
    assert "CLAUDE_CODE_SESSION_ID" in body, (
        "the party is the session; the committer is a constant in this tree"
    )
    assert "unknown-session" in body, "an absent session id is named, not silently empty"
    assert "git config user.email" in body, (
        "the committer is kept for the join against git log, not for discrimination"
    )
    sess = body.index("CLAUDE_CODE_SESSION_ID")
    email = body.index("git config user.email", sess)
    assert sess < email, "session before committer: the discriminating column leads"


def test_the_poll_repeats_its_unread_count_where_a_trailing_window_reaches_it() -> None:
    """⚑⚑⚑ A CORRECT LINE THE READER NEVER RECEIVES IS NOT A REPORT.

    `linux-sources` sharpened this repository's furniture rule from the outside: **their probe
    prints SIX** and they read past it six consecutive ticks, so the operative property is
    CONSTANT, not ZERO — and a non-zero constant is worse, because it looks like the probe works.

    ⚑⚑ This tick produced a THIRD position neither party held. The inbox arm reported their letter
    correctly and by name, and the dispatcher still missed it: STEP 0 ran the poll through
    `sed -n '/CENSUS-remaining-work/,$p' | head -6`. MEASURED — the notice is line 44 of 91 and
    the window opens at line 74. Not furniture, not constant: **excluded by construction.**

    ⚑ And the truncating pipeline existed NOWHERE in the tree, so nothing could gate it. The
    repair must be a file (§8 B5), and it must not be a wider window — a window is the reader's
    and can always be narrowed again. The poll repeats the count LAST, where every trailing
    window reaches it, and names its own terminus so a truncated read is DETECTED rather than
    mistaken for a quiet one.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "END OF POLL" in body, "a reader must be able to tell truncation from a quiet poll"
    assert "UNREAD LETTERS" in body, "the unread count must be repeated after every section"
    # ⚑ THE DIGEST MUST BE LAST. Its whole property is positional: a digest emitted mid-script is
    # exactly the line this defect discarded. Measured by position, not by presence.
    assert body.rindex("END OF POLL") > body.rindex("=== NOT COVERED"), (
        "the digest must follow every other section, or a trailing window can exclude it too"
    )


def test_the_poll_diagnoses_the_roster_divergence_by_sign_not_by_one_sentence() -> None:
    """⚑⚑⚑ A CORRECT COUNT UNDER A MIS-NAMED CAUSE PASSES EVERY ARITHMETIC CHECK.

    This arm was built for `gabion`'s late leg, where HEAD EXCEEDS §S, and its prose said exactly
    that: *an accounting that an admission outgrew.* It then fired on the OPPOSITE sign with the
    same sentence, and this dispatcher read it every tick for three ticks without noticing —
    because the count was right. ⚑ Measured across all three frozen censuses:

        constitution       §S 7,  HEAD 8    a leg arrived after the freeze     prose TRUE
        remaining-work     §S 8,  HEAD 7    `substrate` filed elsewhere        prose FALSE
        build-hermeticity  §S 12, HEAD 11   one `filed elsewhere` row          prose FALSE

    ⚑⚑ The `grep -vc apex` population and the subtraction were both correct. Only the sentence was
    wrong, which is why nothing caught it: an arithmetic check cannot see a mis-named cause.

    ⚑ The under-sign cause is CHECKABLE rather than narratable — a surveyor marked `filed
    elsewhere` is rostered here and files into its own tree, absent by design. So the poll
    distinguishes *accounted-for* from a genuine DROPPED ROW, which is the one shape it exists to
    catch and the one shape no census in this tree currently exhibits.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "HEAD EXCEEDS §S" in body, "the over-sign keeps the outgrown-accounting diagnosis"
    assert "filed elsewhere" in body, "the under-sign must check the cause, not narrate it"
    assert "is a DROPPED ROW" in body, "an unexplained under-sign is the shape worth catching"
    # ⚑ THE SIGN MUST BE TESTED, not merely mentioned. A body naming both outcomes while emitting
    # one unconditionally is exactly the defect this arm repairs, one level out.
    assert 'if [ "${n_head:-0}" -gt "${roster:-0}" ]' in body, (
        "the diagnosis must branch on the sign of the divergence"
    )


def test_the_refusal_record_names_its_own_columns() -> None:
    """⚑⚑⚑ THE COLUMN ADDED TO DISCRIMINATE RETURNS THE NON-DISCRIMINATING CONSTANT.

    The session column was added at `6963eaa` because `git config user.email` is the same for
    every party in this shared tree. ⚑ MEASURED in the live record: rows 1-2 carry three fields
    and row 3 carries four, so a reader splitting on tab reads `$2` as `mikemol@gmail.com` — the
    session id, for two of three rows. **Not a parse error. A plausible wrong value**, in exactly
    the column that exists because that value cannot tell two parties apart.

    ⚑⚑ Ragged is not truncated and position decides — this repository learned that from a census
    table. Here the short rows come FIRST, so every later row reads correctly and only the oldest
    two are silently wrong: the direction that looks healthy from the tail.

    ⚑ A HEADER IS THE FIX AND A VERSION FIELD IS NOT, and the measurement chose it. The record
    has ZERO readers over its whole lifetime — `grep -rn REFUSALS` across every `.sh` and `.py`
    returns the writer and two assertions about it, no consumer — so there is nothing to migrate
    and no parser to teach. What a header buys is columns that are self-describing when a first
    reader arrives, and a field count a reader can DISAGREE with.
    """
    body = _RECORDER.read_text(encoding="utf-8")
    assert "'utc' 'session' 'committer' 'hook' 'failed_checks'" in body, (
        "the record must name its columns, or a short row is plausible rather than detectable"
    )
    # ⚑ WRITTEN ONLY WHEN ABSENT. An append-only file that re-emits its header on every refusal
    # is worse than one with none: the header becomes a row.
    assert 'if [ ! -s "$_rr_log" ]; then' in body, (
        "the header must be conditional on an empty file, never appended per refusal"
    )
    # ⚑ THE HEADER MUST PRECEDE THE ROW WRITE. Positional, like the digest arm: a header emitted
    # after the row it describes is a header for the next row.
    assert body.index("'utc' 'session'") < body.index('"${CLAUDE_CODE_SESSION_ID:-'), (
        "the header is written before the row it describes"
    )


def test_the_durable_refusal_record_keeps_the_account_not_only_the_label() -> None:
    """⚑⚑⚑ THE RECORD KEPT THE LABEL AND DROPPED THE ARMS.

    This gate already argues the principle, at the line that replays the account under the
    verdict: *a reader who greps for the failing check's name must find its arms next to it.* ⚑ It
    applies that to the TRANSCRIPT, which is the ephemeral half, and `failed_detail` reaches
    stderr only.

    ⚑⚑ MEASURED on this gate's own last refusal. The durable row preserves
    `hooks: warrant sections vs rubric sections` and nothing more, while the account that actually
    resolved it — a two-line diff naming `tests/test_bar_fires.py` as the section carrying no
    rubric row — lived for one screen. It was gone by the next tick and re-derived by hand.

    ⚑ A LABEL IS A POINTER INTO A TRANSCRIPT. The row outlives the session that caused it; the
    scratch log it points at is TRUNCATED by the next run of the same check, because those logs
    are per-run scratch read back immediately — measured across all four of them. So the durable
    half kept precisely the part that needs the ephemeral half to be legible. **That is the
    furniture rule inverted: not a line nobody reads, but a line that cannot be acted on by the
    time anybody does.**
    """
    body = _RECORDER.read_text(encoding="utf-8")
    assert "-detail.log" in body, "the account must outlive the run that produced it"
    # ⚑ THE JOIN MUST BE THE ROW'S OWN KEY. A detail file a reader cannot tie to a row is a second
    # artifact with the first one's problem.
    assert "refusal-$(date -u +%Y%m%dT%H%M%SZ)-detail.log" in body, (
        "the detail file is keyed by the same UTC stamp the row carries"
    )
    # ⚑ AND IT MUST BE CONDITIONAL. An empty detail file asserts that a refusal had no account,
    # which is a different claim from a check that captured none — the gate says that in words.
    assert 'if [ -n "${3:-}" ]; then' in body, (
        "no detail must create no file, never an empty one"
    )


_MSGHOOK = _DIST.parent / ".githooks" / "commit-msg"
_RECORDER = _DIST.parent / "refusal_record.sh"


def test_every_refusal_path_records_not_only_the_verdict_one() -> None:
    """⚑⚑⚑ THE RECORD COUNTED ONE REFUSAL PATH AND CALLED ITSELF REFUSALS.

    Its purpose is a lower bound on how many peer commits this gate has refused. ⚑ MEASURED across
    every hook in `.githooks/`: **seven paths reach `exit 1` and exactly one wrote a row** —
    `pre-commit`'s accumulated-failure verdict. The two early exits (a missing tool, a missing
    bazel) and all four `commit-msg` exits refused and vanished.

    ⚑⚑ A CORRECT COUNT OVER A MIS-NAMED POPULATION. Every row was true and the arithmetic was
    right; the column said `failed_checks`, so nothing in the file could reveal that its
    population was *refusals of one kind*. It undercounts in the FLATTERING direction — a gate
    refusing more than it records reads as cheaper than it is, which is the live question an
    operator is holding open about this gate's cost.

    ⚑ ONE FILE SOURCED BY BOTH HOOKS, because this gate's own `note_failure` comment says a repair
    applied to one call site is not a repair to the class. A second copy in `commit-msg` would be
    the exact shape that comment was written about.
    """
    rec = _RECORDER.read_text(encoding="utf-8")
    msg = _MSGHOOK.read_text(encoding="utf-8")
    gate = _GATE.read_text(encoding="utf-8")
    assert "record_refusal()" in rec, "the recorder is one function in one file"
    # ⚑ THE HOOK IS A COLUMN because the PATH is what was missing. A row saying only that some
    # check failed cannot answer which gate refused, and that is the record's whole question.
    assert "'hook'" in rec, "the row must name which hook refused"
    assert '"$1" \\' in rec, "the hook argument must reach the row it names"
    # ⚑ BOTH HOOKS SOURCE IT RATHER THAN COPYING IT. Two writers for one record is the defect.
    assert 'refusal_record.sh"' in msg, "commit-msg must source the shared recorder"
    assert 'refusal_record.sh"' in gate, "pre-commit must source the shared recorder"
    assert '_refusal_log="$_witness_logs' not in gate, (
        "pre-commit's inline writer must be gone, or the record has two authors"
    )
    # ⚑ EVERY `exit 1` IN EITHER HOOK IS PRECEDED BY A RECORD. Counted, not spot-checked: this
    # defect was six unwired sites and one wired, which no single spot-check would have caught.
    for name, body in (("commit-msg", msg), ("pre-commit", gate)):
        exits = [
            i for i, ln in enumerate(body.splitlines())
            if ln.strip() == "exit 1" and not ln.strip().startswith("#")
        ]
        lines = body.splitlines()
        # ⚑⚑ A PROXIMITY WINDOW WAS THE WRONG PREDICATE, AND ITS OWN F-ARM SAID SO. Six lines
        # caught five sites and failed the verdict's, whose `record_refusal` sits eight lines up
        # with the account-printing block between. ⚑ Widening the window would weaken the check to
        # fit one case — a threshold tuned until it stops complaining. The property is ORDER, not
        # nearness: every `exit 1` must carry a record since the PREVIOUS one, so each refusal
        # path is covered exactly once and none inherits its predecessor's row.
        prev = 0
        for i in exits:
            block = "\n".join(lines[prev:i])
            assert "record_refusal" in block, (
                f"{name} line {i + 1}: an exit 1 with no record_refusal since the previous one"
            )
            prev = i


_RULECITE = _DIST.parent / "rule_citations.sh"


def test_the_citation_gate_checks_the_rules_file_against_itself() -> None:
    """⚑⚑⚑ IT CHECKED EVERY MESSAGE AGAINST THE RULES FILE AND NEVER THE FILE AGAINST ITSELF.

    Its whole subject is *a pointer to nothing reads like a pointer* — and the densest population
    of such pointers is the document doing the pointing. ⚑ MEASURED: 31 rules defined, 31 distinct
    rule numbers named within the file, every intra-file reference resolving today.

    ⚑⚑ A CLEAN CORPUS IS THE ONLY MOMENT A CHECK ARMS WITH ZERO MIGRATION, which is why this is
    worth gating now rather than after the first dangling reference. Armed now it is a ratchet;
    armed later it is a paydown.

    ⚑ TWO DEFECTS FOUND WHILE MEASURING IT, both in the arm itself. `exit 0` on the cites-no-rule
    path discarded the self-check's verdict — and 19 of the last 20 commits take that path, so the
    one arm firing on nearly every commit was the one throwing its result away. And the control's
    `case` matched a space-separated string against `comm`'s newline-separated output, reporting
    itself broken on a corpus where it worked.
    """
    body = _RULECITE.read_text(encoding="utf-8")
    assert "does not define it" in body, "the rules file must be checked against itself"
    # ⚑ THE CONTROL RUNS EVERY TIME rather than as a fixture: a comparison gone blind and a clean
    # corpus both print nothing, so the arm's silence is only worth reading if a planted number
    # is reported missing on the same invocation.
    assert "SELF-CHECK INVALID" in body, (
        "a self-check with no live control cannot distinguish clean from blind"
    )
    # ⚑ THE VERDICT MUST SURVIVE THE COMMONEST PATH. `exit 0` here was measured masking a real
    # dangling-reference finding on a message that cited nothing.
    assert 'exit "$fail"' in body, (
        "the cites-no-rule path must carry the self-check's verdict, not discard it"
    )
    # ⚑ LEXICAL SORT, NOT NUMERIC: `sort -n` made `comm` print an ordering error and NO OUTPUT,
    # which reads exactly like a clean corpus. Measured while writing this arm.
    # ⚑ SCOPED TO THE SELF-CHECK BLOCK. A first draft sliced to `cited=` and caught the
    # PRE-EXISTING `sort -u -k2 -n` that orders citations for display, which is correct where it
    # is. An assertion whose window is wider than its subject reports the wrong file's habits.
    # ⚑⚑ COMMENTS ARE STRIPPED FIRST, and that is not a convenience. The block's own comment
    # NAMES the defect — *`sort -n` produced an ordering error and no output* — so a text search
    # matches the description of the bug and reports the bug. A checker that cannot tell a
    # description from an instance is this module's own subject, one level in.
    selfcheck = "\n".join(
        ln for ln in body.split("_defined=")[1].split("\ncited=")[0].splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "| sort -u" in selfcheck, "the comparison's inputs are sorted lexically"
    assert "sort -n" not in selfcheck, (
        "comm requires its inputs in the collation it compares with"
    )


_SQ = _DIST / "src" / "mikemol" / "hooks" / "structural_query.py"


def test_the_structural_gate_discloses_an_empty_routing_table() -> None:
    """⚑⚑⚑ AN EMPTY ROUTING TABLE ALLOWS EVERY COMMAND, SILENTLY.

    `claims()` resolves the table relative to the CWD, so the hook invoked anywhere without a
    `.claude/skills/` tree reads ZERO claims and every textual read of every claimed artifact
    passes. ⚑ MEASURED: from `hooks/` the table holds 0 entries and a plain `grep` of a claimed
    artifact returns a clean verdict; from the repo root it holds 1 and the same command refuses.
    **The gate reads as armed either way.**

    ⚑⚑ THAT IS THE SHAPE THIS HOOK EXISTS TO REFUSE — a check whose silence cannot be told from a
    pass — and the shape this repository declined from a peer's `check_scratch_runtime.py`, which
    printed SKIPPED and exited 0.

    ⚑ IT DISCLOSES RATHER THAN REFUSING. A hook blocking every Bash call over its own
    configuration would take the session down; the honest act is to say the gate covers nothing
    and let the command through. Both arms measured through the console script, which is the real
    entry point — the module has no `__main__` guard, so `-m` runs nothing and prints nothing,
    which is how three readings of this instrument came back empty before the entry point was
    read rather than assumed.
    """
    body = _SQ.read_text(encoding="utf-8")
    assert "NO ROUTING TABLE resolved" in body, (
        "an unarmed gate must say so; silence is indistinguishable from a pass"
    )
    # ⚑ THE DISCLOSURE MUST PRECEDE THE VERDICT. Emitted after, it would describe a decision the
    # empty table had already made — the account arriving behind the thing it explains.
    assert body.index("NO ROUTING TABLE resolved") < body.index("hit, reasons = verdict(cmd)"), (
        "the table is checked before a verdict is computed from it"
    )
    # ⚑ AND IT MUST NOT REFUSE. A gate that blocks on its own misconfiguration is a worse failure
    # than the one being repaired.
    tail = body.split("NO ROUTING TABLE resolved")[1].split("hit, reasons")[0]
    assert "return 0" in tail, "a missing table discloses and allows; it does not block the session"


_SETTINGS = _DIST.parent / ".claude" / "settings.json"
_PYPROJECT = _DIST / "pyproject.toml"


def test_every_shipped_hook_is_actually_invoked() -> None:
    """⚑⚑⚑ SHIPPED, WARRANTED 52:52, AND INVOKED BY NOTHING.

    `no_chaining` carried a rubric section, 52 test functions and 52 warrants — an exact 1:1 — and
    `settings.json` wired only its sibling. ⚑ Its own module docstring says so in the first
    paragraph: *this repo ran ONE PreToolUse hook while its own plan listed `no_chaining` as
    adopted*, and names three measurement errors the absent hook cost in one session.

    ⚑⚑ A COMPONENT WITH FULL COVERAGE AND NO ENTRY POINT IS THIS REPOSITORY'S OWN NAMED DEFECT —
    *the packager is not a user of its own package* — with every test passing. Coverage measures
    whether the code is right; it cannot measure whether anything runs it.

    ⚑ THE ARM IS OVER THE POPULATION, NOT THIS ONE HOOK. A single-hook assertion would be the
    same defect: correct today, silent for the next module shipped unwired. Every declared
    console script whose name marks it a hook must appear in the settings that invoke hooks.
    """
    pyproject = _PYPROJECT.read_text(encoding="utf-8")
    settings = _SETTINGS.read_text(encoding="utf-8")
    scripts: list[str] = pyre.findall(
        r"^(mikemol-hook-[a-z-]+)\s*=", pyproject, pyre.MULTILINE
    )
    # ⚑ POSITIVE CONTROL. A regex that silently stopped matching would make this arm vacuous in
    # the direction that reads as success — no scripts found, nothing to check, green.
    assert scripts, "no console scripts parsed; this arm would pass by finding nothing"
    unwired: list[str] = sorted(s for s in scripts if s not in settings)
    assert not unwired, (
        f"declared hook script(s) that nothing invokes: {unwired}. "
        "A gate with full coverage and no caller refuses nothing."
    )
    # ⚑ AND THE WIRING MUST ARM INLINE. Both peer repos measured that a session already running
    # when `env` changes never picks it up, so a hook armed only by the env block keeps exiting 0
    # — detecting every violation and reporting none.
    # ⚑ NARROWED AT THE BOUNDARY rather than trusting `json.loads`. This distribution ships
    # `payload.py` with nine warrants arguing exactly this: an untyped `Any` from a decoder is a
    # claim about a shape nothing checked.
    commands: list[str] = pyre.findall(r'"command":\s*"([^"]+)"', settings)
    assert commands, "no hook commands parsed from settings"
    for command in commands:
        assert "_HOOK_BLOCK=1 " in command, f"hook armed only ambiently: {command}"


_PKG = _DIST / "src" / "mikemol" / "hooks"


def test_a_module_with_no_local_caller_declares_who_consumes_it() -> None:
    """⚑⚑⚑ THE TWO MOST-REUSED MODULES HERE ARE CALLED BY NOTHING IN THIS REPOSITORY.

    Last tick gated *every declared hook script is wired*. Asking the wider question — for each
    module, what calls it — found `checker_context` and `project_root` imported by no production
    source and **no test**, while `checkers` is imported only by its own test.

    ⚑⚑ A FLEET SWEEP INVERTED THAT READING. Each has **8 importers** across `substrate`,
    `paperkit` and `summit`. They are the most cross-repo-reused code in this distribution, and by
    the operator's membership criterion — *reuse across repos, not repo-local* — the most clearly
    earned. The local zero was never evidence of dead code.

    ⚑⚑⚑ AND THE PEERS IMPORT THEIR OWN COPIES. Measured by hash: `substrate/scripts/` and
    `summit/scripts/` carry byte-identical siblings that DIFFER from mtools'. mtools' are strictly
    ahead — they carry the `Returns:` sections its ruff demands and drop the shebang its own
    `EXE001` reasoning removed — and no consumer reads them. **The interning this repository
    exists to perform has not happened for its two most-reused modules.**

    ⚑ THE ARM CANNOT ASSERT THE INTERNING, because the peer trees are not this repository's to
    edit. What it can hold is the thing that made the divergence survivable: a module with no
    local caller must SAY who consumes it, so the next reader does not read *unused* off an
    import count, delete it, and break three repos.
    """
    # ⚑ THE POPULATION IS DERIVED, not listed. A hand-written module list is the reified-symbol
    # defect this suite was built around; it goes stale the tick a module is added.
    modules = sorted(f for f in _PKG.glob("*.py") if f.stem != "__init__")
    assert modules, "no modules found; this arm would pass by finding nothing"
    sources = [f.read_text(encoding="utf-8") for f in _PKG.glob("*.py")]
    sources += [f.read_text(encoding="utf-8") for f in (_DIST / "tests").glob("*.py")]
    orphans: list[str] = []
    for mod in modules:
        name = mod.stem
        imported = any(
            pyre.search(rf"^\s*from\s+[\w.]+\s+import\s+[^\n]*\b{name}\b", src, pyre.MULTILINE)
            for src in sources
        )
        if imported:
            continue
        body = mod.read_text(encoding="utf-8")
        # An entry point is consumed by the settings that invoke it, not by an import.
        if pyre.search(rf"mikemol\.hooks\.{name}:", _PYPROJECT.read_text(encoding="utf-8")):
            continue
        if "CONSUMED BY:" not in body:
            orphans.append(name)
    assert not orphans, (
        f"module(s) with no local caller and no consumer declaration: {orphans}. "
        "An import count of zero is not evidence of disuse when peers import a copy."
    )


def test_the_preflight_runs_the_ruff_the_gate_runs() -> None:
    """⚑⚑⚑ THE PREFLIGHT PREDICTS THE GATE, SO ITS RUFF MUST BE THE GATE'S RUFF — MEASURED BOTH.

    `preflight.sh` exists to answer *what will the gate say about what I am about to stage*, and
    it carried a comment asserting `--preview` was passed while the command beneath it did not
    pass it. ⚑ I read that as the defect and nearly made the preflight stricter.

    ⚑⚑ MEASURED, THE COMMENT WAS WRONG AND THE COMMAND WAS RIGHT. The gate's own ruff — the
    `$dist: ruff — lint clean under select=[ALL]` check — runs `ruff check --no-cache .` with no
    `--preview` either. Adding it to the preflight would have surfaced **34 findings in `hooks`,
    51 in `mdstruct`, 11 in `ratchet`, none of which the gate's ruff refuses**, including
    `rule-codes-in-selectors`, which is an OPEN OPERATOR DECISION. A preflight failing every run
    on a decision nobody has made is furniture by the second tick.

    ⚑ THE PREVIEW CENSUS BELONGS TO THE RATCHET, which the preflight also runs. So the prediction
    was already complete — via the ratchet line, not the ruff line. The original comment got the
    fact right (the three `blank-lines-*` refusals were preview keys) and attributed the coverage
    to the wrong instrument.

    ⚑⚑ SO THE ARM HOLDS AGREEMENT, NOT A FLAG. Whatever ruff the gate runs, the preflight runs —
    which is the property that makes a prediction one, and it stays true if either side changes.
    """
    preflight = _PREFLIGHT.read_text(encoding="utf-8")
    gate = _GATE.read_text(encoding="utf-8")

    def _ruff_flags(body: str) -> set[str]:
        """Collect flags from every non-comment `ruff check` line, so prose cannot satisfy it.

        Returns:
            the flags passed on each line that actually invokes ruff.

        """
        flags: set[str] = set()
        found = False
        for line in body.splitlines():
            if "ruff" not in line or "check" not in line or line.lstrip().startswith("#"):
                continue
            found = True
            flags |= {w for w in line.split() if w.startswith("--")}
        assert found, "no ruff invocation found; this arm would pass by finding nothing"
        return flags

    # ⚑ THE COMPARISON IS BETWEEN COMMANDS, NOT AGAINST A LITERAL. Asserting `--preview` absent
    # would encode today's answer; asserting AGREEMENT survives the gate changing its mind.
    assert _ruff_flags(preflight) == _ruff_flags(gate), (
        f"preflight runs a ruff the gate does not: preflight={_ruff_flags(preflight)} "
        f"gate={_ruff_flags(gate)}. A prediction that differs from its subject is not one."
    )
    # ⚑⚑ AND THE EXIT STATUS MUST BE DISCRIMINATED. `||` folds *the checker could not start* into
    # *the gate will refuse this* — ruff exits 2 on a usage or internal error, which is not a
    # lint finding, and the census this repo runs raises on exactly that distinction.
    assert "ruff EXITED" in preflight, (
        "a checker that failed to RUN must not be reported as a checker that found something"
    )


def test_a_comment_naming_a_flag_says_whether_it_is_passed() -> None:
    """⚑⚑⚑ THE OBVIOUS SWEEP FOR LAST TICK'S DEFECT SCORES THE FIXED FILE WORSE THAN THE BROKEN ONE.

    At `d2596d7` a comment asserted `--preview` was included while the command beneath it never
    passed it. The mechanical generalisation is: *a comment naming a flag absent from every command
    in its own file.* ⚑ MEASURED against the pre-fix blob, that sweep FIRES — one hit, the right
    line. The control passes.

    ⚑⚑ AND AGAINST THE FIXED FILE IT FIRES FOUR TIMES. The repair added prose explaining WHY
    `--preview` is not passed, and every sentence of that explanation is another hit. **The sweep
    cannot tell an assertion from an explanation, so its signal is inverted by its own repair** —
    a metric that rewards deleting the reasoning and punishes recording it.

    ⚑ SO THE SHIPPED PROPERTY IS NARROWER AND IT IS ABOUT THE VERB. A comment may name any flag it
    likes while discussing another tool, another target, or a decision not to pass it. What it may
    not do is claim THIS file passes one it does not. `IS INCLUDED` was that claim; the corrected
    text says `is NOT passed below`. The check is on assertions of inclusion, not on mentions.

    ⚑⚑ THE OTHER EIGHT HITS WERE MEASURED AND ARE ALL LEGITIMATE — `.githooks/pre-commit` on the
    ratchet's blanket census, `ratchet_check.sh` on a flag applied inside the census it delegates
    to, `rule_citations.sh` on the mdstruct modes that motivated it. A sweep whose true-positive
    rate is one in nine does not ship as a gate; the property it was reaching for does.
    """
    inclusion = pyre.compile(
        r"`(--[a-z][a-z0-9-]{2,})`[^\n]*?\b(IS INCLUDED|is included|is passed)\b"
    )
    offenders: list[str] = []
    scanned = 0
    for script in sorted(_DIST.parent.glob("*.sh")):
        text = script.read_text(encoding="utf-8")
        scanned += 1
        code = "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        )
        # ⚑⚑⚑ A QUOTATION IS NOT AN ASSERTION, AND THIS IS THE THIRD CHECKER HERE TO NEED THAT.
        # `message_counts.sh` exempts four-space-indented lines so a message can quote the figure
        # it is correcting; `rule_citations.sh` has no such exemption and has refused two commits
        # of mine for quoting a rule number. ⚑ The marker differs by medium — indentation in a
        # commit message, quotation marks in a shell comment — but the property is one: a checker
        # that cannot tell a claim from a report of a claim refuses the authors most careful to
        # record what they corrected.
        # ⚑⚑ STRIPPED OVER THE JOINED COMMENT TEXT, NOT PER LINE. Measured: the quotation that
        # motivated this opens on one line and closes on the next, so a per-line strip leaves both
        # halves bare and the arm fires on the correction it was written to permit.
        comment_text = "\n".join(
            ln.lstrip().lstrip("#") for ln in text.splitlines() if ln.lstrip().startswith("#")
        )
        unquoted = pyre.sub(r'"[^"]*"', "", comment_text, flags=pyre.DOTALL)
        offenders.extend(
            f"{script.name}: claims {m.group(1)} is passed, and it is not"
            for m in inclusion.finditer(unquoted)
            if m.group(1) not in code
        )
    # ⚑ POSITIVE CONTROL ON THE POPULATION, not on the predicate: a glob that stopped matching
    # would make this arm vacuous in the direction that reads as success.
    assert scanned >= _MIN_SHELL_SCRIPTS, (
        f"only {scanned} shell script(s) scanned; the population is wrong"
    )
    assert not offenders, (
        "comment(s) asserting a flag the file does not pass:\n  " + "\n  ".join(offenders)
    )


def test_the_count_checker_narrows_by_position_not_by_indent_alone() -> None:
    """⚑⚑⚑ THREE CHECKERS NEEDING ONE EXEMPTION WAS A RESEMBLANCE, NOT A CLASS.

    Last tick recorded that `message_counts.sh`, `rule_citations.sh` and the comment-claim arm all
    need the same exemption — *the marker differs by medium but the property is one.* ⚑ MEASURED
    against the two commits `rule_citations.sh` actually refused, **no marker exempts both**:
    four-space indent (its own precedent) exempts one, quotation marks exempt neither, backticks
    exempt neither.

    ⚑⚑ THE DISCRIMINATOR WAS IN `message_counts.sh` ALL ALONG AND IT IS NOT THE INDENT. Its
    predicate is `ledger (holds|has) N` — the number must be **positioned as a total**, so a subset
    count is not a ledger claim at all rather than a ledger claim that is wrong. The indent is
    secondary, covering the quotation of the very figure being corrected. `rule_citations.sh` has
    no positional requirement: any `Rule N` anywhere is a citation.

    ⚑⚑⚑ AND A POSITIONAL NARROWING DOES NOT TRANSFER. A candidate reading citation verbs and
    semicolon tails passed all six arms — until `citing` was added to the verb list, which it
    plainly belongs in. Then it refuses the very message it appeared to exempt. **The exemption
    was luck about my word list.** *"a message citing Rule 9999"* is lexically identical to a
    citation; what separates them is a SPEAKER between the verb and the author, and no regex
    reads speakers.

    ⚑ SO THE PROPERTY THIS ARM HOLDS IS THE ONE THAT SURVIVED: the count checker narrows by
    POSITION, and that narrowing is what makes its indent exemption safe rather than the reverse.
    An indent exemption without it would let a wrong total through by indenting it.
    """
    body = _MSGCOUNT.read_text(encoding="utf-8")
    # ⚑ THE POSITIONAL PREDICATE IS THE LOAD-BEARING HALF. Measured: it is what makes a subset
    # count a non-claim, and the arm asserts it rather than the indent that gets the attention.
    assert "ledger (holds|has)" in body, (
        "the count must be positioned AS A TOTAL, or a subset count reads as a wrong total"
    )
    # ⚑ AND THE INDENT EXEMPTION IS SECONDARY, not the mechanism. It is asserted too, because a
    # message that cannot quote the figure it is correcting cannot record a correction at all.
    assert "grep -vE '^    '" in body, (
        "a message must be able to quote the figure it is correcting"
    )


_RULECITE = _DIST.parent / "rule_citations.sh"


def test_the_citation_gate_reports_a_figure_that_moves() -> None:
    """⚑⚑⚑ THE ONLY LINE THIS GATE PRINTS ON THE COMMON PATH REPORTS THE ABSENCE OF A CLAIM.

    ⚑ MEASURED over 30 commits: `this message cites no rule` fires on **29 of 30 — 96%**. By
    `linux-sources`' sharpening, a line reporting the same thing every run stops being read.

    ⚑⚑ AND DELETING IT IS THE WRONG FIX, which is why the constant-line rule does not simply
    apply. It is the ONLY stdout on that path: remove it and a checker that ran is byte-identical
    to one that did not — the shape this repository refuses in every other gate. The line is
    load-bearing as a *gate ran* signal and uninformative as a *finding*.

    ⚑⚑⚑ MEANWHILE THE SAME RUN DOES REAL WORK IT NEVER MENTIONS. The corpus self-check — every
    rule NAMED in the rules document is also DEFINED there, with a live planted control — executes
    on every commit and says nothing when it passes. So the gate announces the trivial half and
    stays silent about the half that could actually be wrong.

    ⚑ THE FIGURE MOVES, WHICH IS WHAT MAKES REPORTING IT DIFFERENT FROM RENAMING FURNITURE.
    Measured across 37 commits touching the corpus: **26 distinct rule counts**, stepping nearly
    every time it changes. A number that moves is read; a number that never moves is the same
    furniture with a digit on it.
    """
    body = _RULECITE.read_text(encoding="utf-8")
    # ⚑ THE GATE-RAN SIGNAL MUST SURVIVE. Exactly one unconditional stdout line on the pass path,
    # and it must carry the corpus figure rather than only the absence of a citation.
    assert "rules define" in body, (
        "the pass line must report the corpus it checked, not only that nothing was cited"
    )
    # ⚑ AND IT MUST STILL SAY THE SELF-CHECK RAN. A count with no verdict attached is a number;
    # the reader needs to know the arm that could have failed did not.
    assert "every named one resolves" in body, (
        "the pass line must report the self-check's verdict, which is the half that can be wrong"
    )
    # ⚑⚑ AND THE VERDICT TEXT MUST FOLLOW THE VERDICT. A first version asserted it unconditionally
    # and was MEASURED contradicting itself: against a corpus naming an undefined rule it printed
    # the dangling reference on stderr, then claimed on stdout that everything resolved. A line
    # that contradicts the finding two lines above it is worse than the constant one it replaced.
    assert 'if [ "$fail" -eq 0 ]; then' in body, (
        "the pass line's claim must be conditional on the self-check having passed"
    )
    assert "self-check above FAILED" in body, (
        "a failed self-check must be named on the same stream the pass line uses"
    )


_SHELLCHECK_TEST = _DIST.parent / "shellcheck_test.sh"


def test_the_shell_gate_says_what_it_checked() -> None:
    """⚑⚑⚑ ZERO BYTES ON THE PASS PATH: A RUN AND A NON-RUN ARE BYTE-IDENTICAL.

    ⚑ MEASURED by running it on a clean file: **0 bytes of output, exit 0**. `shellcheck` prints
    nothing when it finds nothing, and this script ends in `exec "$sc" "$@"`, so the pass path
    emits literally nothing. That is the shape this repository refuses in every other gate —
    `preflight.sh` refuses a missing tool rather than skipping, `rule_citations.sh` keeps a pass
    line *specifically* so a run is distinguishable from a non-run — and it is sitting in the gate
    that checks the shell those refusals are written in.

    ⚑⚑ THE FILE COUNT IS THE FIGURE, AND IT MOVES. The `sh_test` receives its targets from bazel's
    `$(location …)` expansion, so *how many shell files were staged* is exactly the quantity a
    silent pass hides: a rule that stopped matching would stage FEWER files and still exit 0 with
    no output. Its own comment records that a `find`-based version once returned nothing and was
    caught only because the guard refused an empty list.

    ⚑ NOT A CONSTANT LINE. `linux-sources` measured that a probe printing a fixed number is read
    past — theirs printed SIX for six consecutive ticks — so the pass line carries the count, which
    changes whenever the staged set does, rather than a fixed *ok*.
    """
    body = _SHELLCHECK_TEST.read_text(encoding="utf-8")
    # ⚑ THE PASS PATH MUST EMIT SOMETHING. Asserting on the string alone would be satisfied by a
    # comment; this asserts the count is interpolated, which only a command can do.
    assert "shellcheck_test: " in body, "the pass path must be distinguishable from a non-run"
    assert "$#" in body.split("exec")[0], (
        "the staged-file count must be read before the exec that replaces this shell"
    )
    # ⚑⚑ AND IT MUST PRECEDE THE `exec`. After it, this shell no longer exists — a pass line
    # written below the exec is a line that never runs, which is the defect with extra steps.
    assert body.index("shellcheck_test: checked") < body.index('exec "$sc"'), (
        "the pass line must be emitted before exec replaces this process"
    )


def test_the_preflight_does_not_hardcode_the_witness_count() -> None:
    """⚑⚑⚑ THE TOOL THAT PREDICTS THE GATE ASSERTED A FIGURE THE GATE DISAGREES WITH.

    `preflight.sh`'s pass line read *the bazel suite and nine domain witnesses are still ahead*.
    ⚑ MEASURED: the gate invokes **eight** — three `mypy`, three `ruff`, two ratchet-gate. A
    hand-written population inside the instrument whose entire job is predicting that gate.

    ⚑⚑ THIS IS THE DEFECT THIS SESSION HAS MEASURED MOST, AND IT PASSES EVERY ARITHMETIC CHECK.
    Nothing about `nine` is malformed; it is a correct-looking number over a population nobody
    enumerated. A reader trusting the preflight would expect one more witness than exists and
    would not learn otherwise from any green run.

    ⚑ AND THE FIGURE MOVES BY CONSTRUCTION — a witness is added by writing one `witness` line, so
    the count changes whenever the gate's coverage does. That is precisely the case where a
    hardcoded number rots silently: the thing it describes is designed to grow.

    ⚑⚑ SO THE ARM ASSERTS THE ABSENCE OF A LITERAL, NOT A VALUE. Asserting *eight* here would
    reproduce the defect one level out — a second hand-written population, in the file that exists
    to catch hand-written populations.
    """
    body = _PREFLIGHT.read_text(encoding="utf-8")
    gate = _GATE.read_text(encoding="utf-8")
    # ⚑ POSITIVE CONTROL ON THE POPULATION: a pattern that stopped matching would make the
    # comparison below vacuous in the direction that reads as agreement.
    witnesses: list[str] = pyre.findall(r"^witness ", gate, pyre.MULTILINE)
    assert witnesses, "no witness invocations found; this arm would pass by finding nothing"
    # ⚑ NO SPELLED-OUT COUNT IN THE PASS LINE. The words are checked rather than digits, because
    # the defect was spelled `nine` and a digit-only check would have read it as clean.
    # ⚑⚑ COMMENTS ARE STRIPPED FIRST, AND THIS ARM FIRED ON ITS OWN CORRECTION TO PROVE IT. The
    # repair records the old figure in prose — *this line once said `nine` and the gate invokes
    # eight* — and a whole-file search reads that record as the defect. **A checker that cannot
    # tell a description of a bug from an instance of one refuses the authors who document what
    # they fixed**, which is the same finding this suite reached at `36249ea` and `6702b03`,
    # arriving a third time in a third medium.
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    spelled: list[str] = pyre.findall(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+domain witness",
        commands,
    )
    assert not spelled, (
        f"the preflight hardcodes a witness count {spelled}; the gate invokes "
        f"{len(witnesses)}, and the figure moves whenever a witness is added"
    )


def test_no_gate_asserts_a_figure_it_cannot_reach() -> None:
    """⚑⚑⚑ A HARDCODED FIGURE WHOSE REFERENT NO SCRIPT CAN READ IS WORSE THAN A STALE ONE.

    `domain_witness.sh` told a reader whose target went red: *seven sessions write this tree;
    check `git status` before treating it as a defect.* ⚑ MEASURED at the tick it was found:
    `ListAgents` reports **seven interactive peers plus this session — eight writers.**

    ⚑⚑ AND THE DEFECT IS NOT THE ARITHMETIC. A stale count can be re-derived; this one cannot,
    because **its referent is not in the tree.** Live sessions are a harness reading available for
    one instant, which the poll already declares about peer reachability: *NOT COVERED — run
    `ListAgents`; it is a reading, not a fact.* A shell script has no path to that number, so the
    figure was authored once and can only ever drift.

    ⚑ THE REPAIR IS TO DROP THE COUNT, NOT TO CORRECT IT. The sentence's work is *other parties
    write here, so check before concluding* — which is true at any cardinality and stays true when
    a session starts or exits. A number added to that sentence buys nothing and rots.

    ⚑⚑ MEASURED AGAINST THE SIBLING CLAIM THAT SURVIVED. `rule_freshness.sh` says *three rules
    cite it* about the metrics port, and that IS reachable: rules 5, 12 and 26 name it, counted
    from the corpus. The discriminator is not *is it hardcoded* but *can anything here check it* —
    which is why this arm names the unreachable referent rather than banning figures.
    """
    body = _WITNESS.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the file must still emit the warning this arm is about, or the
    # assertion below passes because the sentence vanished rather than because it was fixed.
    assert "write this tree" in commands, (
        "the concurrent-writer warning must still be emitted; this arm would pass on its absence"
    )
    # ⚑ NO SESSION COUNT. Only a harness reading can produce it, and only for one instant.
    counted: list[str] = pyre.findall(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+sessions?\b", commands
    )
    assert not counted, (
        f"a gate asserts {counted} sessions write this tree — a figure no script can reach, "
        "since live sessions are a harness reading rather than a fact about the tree"
    )
