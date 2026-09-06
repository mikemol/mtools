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
