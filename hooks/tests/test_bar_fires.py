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
import importlib.metadata
import json
import os
import re as pyre
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# ⚑⚑ `Callable` IS ANNOTATION-ONLY AND SO IT BELONGS HERE — WHICH IS THE OPPOSITE VERDICT TO
# `Path` BELOW, FROM THE SAME RULE, FOR THE SAME REASON. TC003 asked for both; the answer is read
# off the USE, not off the rule. `Path` is evaluated by module-level constants at import time and
# moving it breaks collection with a NameError; this name appears only inside one annotation, so
# deferring it costs nothing and the rule is simply right.
# ⚑ THE PAIR IS WHY THE COMMENT BELOW SAYS THE RULE WAS *ANSWERED BY READING THE USE*: one file,
# one rule, two opposite correct answers. A blanket obey or a blanket ignore gets one of them
# wrong, and neither would look wrong at review.
if TYPE_CHECKING:
    from collections.abc import Callable

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

    ⚑⚑ `RUFF_BIN` NAMES A HASH-PINNED http_archive, NOT A pip DEPENDENCY — AND THE REASON THIS
    DOCSTRING GAVE WENT STALE. It said *rules_python stages only `site-packages`, dropping the
    wheel's `bin/ruff`*. True at rules_python 1.0.0, FALSE at 2.3.3: `bazel cquery
    '@hooks_dev//ruff:extracted_whl_files'` lists `bin/ruff`, and `file` reports a real ELF. The
    bump at `50cb2c2` invalidated the premise here and in `MODULE.bazel`, and nothing noticed
    because NOTHING ASSERTED IT — see `test_the_ruff_archive_rests_on_a_measured_entry_point_set`.

    ⚑ THE CHOICE STANDS ON ITS OTHER LEG: `ruff` declares ZERO console-script entry points, so
    there is nothing for `py_console_script_binary` to regenerate. That is the leg the decision
    procedure in `MODULE.bazel` actually keys on, and it is now under an arm.

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
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the checker is the subject of these cases
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

    ⚑⚑⚑ AND THE RULE IS NAMED, NOT CODED, BECAUSE PREVIEW CHANGED WHAT THE CHECKER PRINTS. These
    six arms asserted `"CPY001" in out`; under `preview = true` ruff's diagnostics carry
    `missing-copyright-notice` and the code appears nowhere in the output, so all six went red at
    once while the gate was firing correctly on every one of them.
    ⚑⚑ SIX FALSE REDS ARE THE MIRROR OF THE FAILURE THIS FILE EXISTS FOR — the greens that mean
    nothing have a twin in reds that mean nothing, and a suite crying wolf gets its arms deleted.
    The spelling is the checker's to choose; what these arms own is that the gate FIRES.
    """
    out = _ruff("src/probe_bad.py", header + '"""D."""\n', tree)
    assert "missing-copyright-notice" in out, f"gate did not fire on: {proposition}"


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

    ⚑⚑⚑ NAMED, NOT CODED, AND THE NEGATIVE ARM IS WHY THIS MATTERS. Under `preview = true` ruff
    prints `assert:` and never the code `S101`, so the F-arm here went red — loudly, correctly
    diagnosable. Its P-arm twin asserted `"S101" not in out` and went **GREEN**, because a code
    that the checker no longer prints is absent from every output whether the exemption holds or
    not. ⚑⚑ THE VOCABULARY CHANGE TURNED A REAL P-ARM INTO A VACUOUS ONE, and only its F-arm twin
    made that visible — which is the two-armed discipline earning its keep on a rule that was not
    even the subject of the change.
    """
    body = _GOOD_HEADER + '"""D."""\n\n\ndef f() -> None:\n    """D."""\n    assert True\n'
    assert "assert:" in _ruff("src/probe_assert.py", body, tree)


def test_assert_is_permitted_in_tests(tree: Path) -> None:
    """The P-arm for the scope. `assert` is the test idiom and `-O` never runs these.

    ⚑ SEE THE F-ARM ABOVE: this arm is the one that went vacuous when the checker's vocabulary
    changed, so the spelling it matches is the one the checker actually emits.
    """
    body = _GOOD_HEADER + '"""D."""\n\n\ndef test_f() -> None:\n    """D."""\n    assert True\n'
    assert "assert:" not in _ruff("tests/probe_assert.py", body, tree)


# ────────────────────────── declare-never-suppress, asserted as an effect ───────────────────────

def test_the_ignore_list_is_exactly_three_rules() -> None:
    """The ignore list holds exactly three rules.

    ⚑⚑ THE BAR IS THE MAX, SO IGNORES DO NOT ACCUMULATE. Three entries, each a checker-vs-checker
    conflict rather than a finding declined: D203/D213 are docstring-style pairs whose alternatives
    are mutually exclusive, and COM812 fights the formatter. A fourth entry appearing without this
    test failing is how a bar erodes — one exemption at a time, each defensible alone.

    ⚑ A peer carries a fourth (CPY001, deferred for want of a LICENSE). This repo has a LICENSE,
    which is that deferral's own stated exit condition, so it is not inherited.

    ⚑⚑⚑ THE THREE ARE NAMED, NOT CODED, ON THE `rule-codes-in-selectors` RULING (adopt, 2026-09-07;
    arm tree-wide preview first, 2026-09-08). The rules are the same three; only the spelling the
    config is allowed to use has changed, and this arm moved with it rather than pinning the tree
    to a vocabulary its own checker now refuses.
    """
    text = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("ignore = "))
    assert line == (
        'ignore = ["incorrect-blank-line-before-class", "multi-line-summary-second-line", '
        '"missing-trailing-comma"]'
    )


def test_the_checker_that_runs_is_the_one_the_lock_pins() -> None:
    """The checker that runs is the one the lock pins.

    ⚑⚑ A RULE SET IS A PROPERTY OF THE RESOLVER, NOT OF THE CONFIG TEXT. This repo's lock pinned
    ruff 0.16.6 while its venv ran 0.16.5, so every arm above had been measured against a version
    the build would not install. The drift was benign and being UNMEASURED was not.
    """
    pinned = next(ln for ln in (_DIST / "requirements.txt").read_text(encoding="utf-8").splitlines()
                  if ln.startswith("ruff=="))
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the checker is the subject of this case
        [*_ruff_argv(), "--version"], capture_output=True, text=True, check=True)
    assert proc.stdout.split()[1] == pinned.split("==")[1].strip()


def test_the_ruff_archive_rests_on_a_measured_entry_point_set() -> None:
    """⚑⚑⚑ A LOAD-BEARING COMMENT'S PREMISE WENT FALSE AT A DEPENDENCY BUMP AND NOTHING NOTICED.

    `MODULE.bazel` justified fetching ruff as an `http_archive` by saying *rules_python STAGES
    ONLY `site-packages`. The wheel's `bin/ruff` is dropped.* That was measured and true at
    rules_python 1.0.0. At 2.3.3 it is FALSE — `bazel cquery
    '@hooks_dev//ruff:extracted_whl_files' --output=files` lists `bin/ruff`, and `file` reports
    `ELF 64-bit LSB pie executable … stripped`. The bump at `50cb2c2` invalidated the sentence
    and it kept being read as evidence.

    ⚑⚑ IT SURVIVED BECAUSE NOTHING ASSERTED IT. The comment carries a decision procedure — check
    `entry_points`; non-empty means `py_console_script_binary`, empty plus a compiled `bin/` means
    `http_archive` — and the CONCLUSION rests on that, not on staging. This arm puts the
    load-bearing leg under measurement so the next bump cannot quietly move it.

    ⚑ THE POSITIVE CONTROL IS IN THE SAME RUN: `mypy` and `pytest` are asked identically and DO
    declare console scripts. Without that, an empty result would be indistinguishable from a
    probe that cannot see entry points at all — which is the shape this suite exists to refuse.

    ⚑ AND IT ASSERTS THE PROPERTY, NOT THE NAMES. Requiring exactly `['dmypy', 'mypy', …]` would
    break when mypy adds a script, which is not this repository's business; what must hold is
    that ruff declares NONE while a comparable wheel declares SOME.
    """
    dist = importlib.metadata.distribution("ruff")
    ruff_scripts = [e.name for e in dist.entry_points if e.group == "console_scripts"]
    # ⚑ THE CONTROL FIRST: if the probe cannot see a known-good case, the negative below says
    # nothing about ruff and everything about the probe.
    control = [
        e.name
        for pkg in ("mypy", "pytest")
        for e in importlib.metadata.distribution(pkg).entry_points
        if e.group == "console_scripts"
    ]
    assert control, (
        "neither mypy nor pytest reports a console script — the probe cannot see entry points, "
        "so ruff reporting none would be a fact about this reader rather than about ruff"
    )
    assert not ruff_scripts, (
        f"ruff now declares console scripts {ruff_scripts} — the `http_archive` in MODULE.bazel "
        "is justified by there being NOTHING to regenerate, and that premise has moved: "
        "`py_console_script_binary` may now be the right instrument"
    )


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
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — pytest's own configuration is the subject
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
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — pytest's own configuration is the subject
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
    # ⚑ DERIVED: `fence` landed and this arm never checked its BUILD file. It passes today, which
    # is the point — an omission that happens to be harmless is still an omission.
    for name in _distributions():
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
    for dist in _distributions():
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
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
        return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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

    Returns:
        The witness script's exit code. ⚑ THE CODE IS THE MEASUREMENT, not a pass/fail flag: the
        arms below distinguish `_ARG_REFUSED` from any other nonzero, because "refused its
        arguments" and "ran and failed" are different verdicts and a boolean would merge them.

    """
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
    out = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
    subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
        return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
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
    """⚑⚑⚑ `cd` RELOCATES A CWD, NOT AN IMPORT CLOSURE — AND THE FIX IS NOW STRUCTURAL.

    The venv is an EDITABLE install — a `.pth` plus an import-hook finder naming the live tree — so
    `cd $staged/$dist` changed the working directory and left imports resolving to unstaged source.
    ⚑ Measured: a type defect planted in the WORKING tree, absent from the staged copy, was still
    imported by a run inside the staged copy, and mypy reported Success.

    ⚑⚑⚑ THIS ARM ASSERTED THE REPAIR (`MYPYPATH`/`PYTHONPATH` pointing into `$staged`) AND ITS
    SUBJECT HAS BEEN DELETED. The gate no longer runs a host-venv mypy at all — `//<dist>:mypy`
    does, over a bazel sandbox built from DECLARED `srcs`. An editable install's import hook is not
    present there, so the hazard this arm guarded cannot arise: it is closed by construction rather
    than by two environment variables a future edit could drop.

    ⚑⚑ SO THE ARM NOW ASSERTS THE STRONGER FACT, and refuses the weaker repair's RETURN. Keeping
    the old assertion would have been an arm demanding a workaround for a defect that no longer
    exists — green only while the workaround is present, and failing if the structural fix were
    made more thorough.
    """
    body = _GATE.read_text(encoding="utf-8")

    # ⚑ THE HOST CHECKERS ARE GONE: no `.venv/bin/mypy` invocation to need a staged import closure.
    assert '.venv/bin/mypy"' not in body, (
        "a host-venv mypy is back in the gate — it carries the editable-install import closure "
        "again, and this arm's original repair would be needed a second time"
    )
    # ⚑ AND THE DELEGATION IS REAL: the suite that runs `//<dist>:mypy` must still be invoked.
    assert "bazel test //..." in body, (
        "the gate does not run the suite, so no mypy runs anywhere — the closure question is moot "
        "only because nothing is checked"
    )

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
# ⚑ A FLOOR, NOT A COUNT. Four distributions exist today; this asserts only that the derivation
# found SOMETHING, so an absence claim over the population cannot pass because the population is
# empty. Writing `== 4` would make a derived figure a hand-written one, which is the whole defect.
_MIN_DISTRIBUTIONS = 2
# ⚑ A QUOTED SHELL PATTERN NEEDS BOTH QUOTES. `line.count("'") >= 2` is the test for *this line
# carries a single-quoted string I can extract*; naming it says which 2 — an opening and a
# closing quote — rather than leaving a bare integer for a reader to re-derive.
_QUOTED_PAIR = 2
# ⚑⚑⚑ THE SWEEP'S OWN SKIPPED POPULATION, AND THE FIRST NUMBER WRITTEN HERE WAS WRONG BY 6x.
# A regex over the test module reported FOUR — it matched one syntactic form, `(_CONST / "a")`.
# The sweep's actual predicate is broader: any `read_text` receiver that is not a mapped NAME.
# ⚑⚑ MEASURED BY THE SWEEP ITSELF: 23. A ceiling of 4 over a population of 23 would have been a
# correct-looking figure over a MIS-NAMED POPULATION — this session's most-measured defect, and
# it was caught only because the assertion fired on the real count rather than on my regex's.
# ⚑ THE POPULATION IS CLEAN, which is what makes this a ceiling rather than tolerated debt.
# Resolving every skipped test's path against this module's own constants and running the
# sweep's predicate by hand: 0 vacuous. Two forms, 12 path expressions and 4 bare names.
# ⚑ A CEILING, NOT A TARGET. It may fall; it rises only when a new unresolvable read is added,
# which is exactly the moment a reader should be told rather than the moment coverage drops.
# ⚑⚑⚑ LOWERED FROM 23 BY RESOLVING, NOT BY EDITING. A bounded evaluator now reaches the
# `_CONST / "literal"` form, and the sweep itself reports the new figure — my hand-count said
# four and the sweep found FIVE, because one arm I had classified by eye also uses that form.
# The ceiling is the instrument's number, never the reader's: two readers computing one figure
# is the defect three consecutive ticks were spent repairing.
# ⚑⚑ THE FORMER VALUE IS KEPT so the ratchet's DIRECTION is assertable. A ceiling that only
# ever holds reports the same number every run and stops being read; one that must fall is a
# paydown with a witness.
_MAX_UNRESOLVED_WAS = 23
# ⚑⚑⚑ 18 -> 19, AND A RISE IS THE ONE MOVE THIS CEILING EXISTS TO MAKE VISIBLE. The arm added
# this tick reads its population by GLOB — every census whose §R marks this repo as its host —
# so there is no named constant to resolve and no single haystack its literals could live in.
# That is the same reason the subprocess probes sit outside the sweep, arriving by a different
# route: the file is chosen by a predicate at runtime rather than written down.
# ⚑⚑ RAISING IT IS THE HONEST MOVE AND KEYING THE ARM TO A FIXED PATH WOULD NOT BE. A named
# constant would have resolved the sweep and re-introduced the hand-written population the arm
# was built to refuse — buying coverage of the arm by breaking what the arm measures. The ceiling
# says "reader, you are told"; it does not say "do not add one".
# ⚑⚑ 19 -> 20, THE SECOND RISE, AND THE SAME CAUSE AS THE FIRST. The arm added this tick reads
# `<dist>/pyproject.toml` for each of three distributions through a LOOP VARIABLE, so the resolver
# has no name to resolve — the population is chosen at runtime rather than written down, which is
# the property that makes the arm honest and the sweep blind. Keying it to three literal paths
# would resolve the sweep and re-introduce the hand-written population the arm refuses.
# ⚑ 20 -> 21, THE THIRD RISE, AND THE THREE SHARE ONE CAUSE: each arm's population is chosen at
# RUNTIME — a glob over hosted censuses, a loop over three distributions, an rglob for sources
# carrying a directive. The resolver needs a NAME, and a runtime predicate has none. That is the
# property making these arms honest, so the ceiling rises rather than the arms being rewritten to
# name paths they would then have to keep in sync.
# ⚑ 21 -> 22, THE FOURTH RISE, SAME CAUSE AS THE THREE ABOVE AND SHARPER. The new arm forbidding
# a hand-written distribution list reads `.githooks/pre-commit`, `preflight.sh` and this module,
# and derives its population from `*/pyproject.toml` at RUNTIME. Naming those paths to satisfy
# the resolver would re-introduce the very literal the arm exists to refuse — so the ceiling
# rises, which is the honest direction: it reports a reader's reach, not the arm's quality.
_MAX_UNRESOLVED = 22

# ⚑⚑⚑ THE MOST TIMES ONE READER MODE IS INVOKED ON THE SAME FILE IN ONE LOOP ITERATION. Measured
# at 11 for `tables` and 9 for `rows`, against 10 censuses — so 22 sites in the loop plus 2 outside
# is 222 process starts per run, and roughly two hundred of those re-ask a question already
# answered on an unchanged path.
# ⚑⚑ A CEILING, NOT A TARGET, AND IT BOUNDS THE REPEATS RATHER THAN THE TOTAL. A total would fall
# when a census is deleted and rise when one is added — reporting the CORPUS rather than the poll.
# The per-mode repeat count is a property of the script alone, so it moves only when someone adds
# another redundant call, which is the event worth refusing.
# ⚑ THE FIGURE IS THE INSTRUMENT'S, not a round number chosen to be comfortable: it is what the
# script measures today, so any rise is a change someone made rather than a threshold crossed.
_MAX_SAME_QUERY = 11
# ⚑⚑ THE SHARE OF ARMS THE SWEEP ACTUALLY CHECKS, as a percentage floor. MEASURED at the tick
# it shipped: 48 of 94 arms, 51%. The remainder is not debt — 21 arms run subprocesses and
# have no haystack to be absent from, and 8 assert by regex or count, which a string-membership
# check cannot see without becoming a different tool.
# ⚑ A FLOOR BELOW THE MEASUREMENT, not a target at it: the reach may grow, and this refuses a
# silent shrink. Stated because a green sweep reads as module coverage and is not — the
# mis-named population this repository has measured eight times, arriving in the arm that
# enumerates the others.
_SWEEP_COVERS_ARMS = 45
# ⚑ A FLOOR ON THE COUNTING SITES, not a target. Three files count the warrant ledger --- the
# gate, the preflight that predicts it, and the message checker. If a sweep finds fewer, the
# pattern stopped matching and the anchoring arm passes by finding nothing to check.
_MIN_WARRANT_COUNT_SITES = 3
# ⚑ A FLOOR ON THE HARNESS SCRIPT POPULATION, not a target. Sixteen shell scripts plus the
# two git hooks were present when this shipped; a glob that stopped matching would make any
# harness-wide arm pass by finding nothing to check, which is the direction that reads as
# success. Set below the measured count so adding or removing one script is not a refusal.
_MIN_HARNESS_SCRIPTS = 12
# ⚑ THE FLOOR IS THE COUNT MEASURED WHEN THE RESOLVER WAS WRITTEN, minus room for a
# distribution to shrink. 241 checks parsed in `hooks` at that moment; a reader that suddenly
# parses 3 is reading the wrong shape, and its zero unresolved would be vacuous.
_MIN_RESOLVABLE_CHECKS = 200
# ⚑ A FLOOR ON THE COUNTING DERIVATIONS. Fourteen were present when the one-literal-one-
# predicate arm shipped; a regex that stopped matching would report no derivations and no
# possible disagreement, which is vacuity in the direction that reads as success. Set below
# the measured count so adding or removing one is not a false refusal.
_MIN_COUNTING_SITES = 10
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
# ⚑⚑ A MODULE CONSTANT SO THE VACUITY SWEEP CAN RESOLVE IT. The sweep follows
# `<CONST>.read_text(...)`; an inline `(_DIST.parent / ".claude" / "settings.json")` is
# unresolvable and pushes its unresolved ceiling — measured, 22 -> 23, twice now, and raising that
# ceiling to fit new code is expanding a baseline.
_SETTINGS = _DIST.parent / ".claude" / "settings.json"
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


def _distributions() -> list[str]:
    """Every distribution in this repository, derived from the filesystem.

    ⚑⚑⚑ THE PREDICATE IS *A DIRECTORY CARRYING A `pyproject.toml`*, and it is not invented here:
    `blockers.sh` already enumerates components that way, with a comment arguing that a structural
    criterion *cannot drift as this repo grows, and a landed component necessarily satisfies it*.
    This reuses that rather than adding a second spelling for one idea.

    Returns:
        Every distribution name, sorted. ⚑ DERIVED FROM THE FILESYSTEM ON EVERY CALL, never a
        literal list — a hand-written roster is the shape that silently stops covering the
        distribution added after it was written, which is the failure the arms calling this
        exist to prevent.

    """
    root = _DIST.parent
    return sorted(p.parent.name for p in root.glob("*/pyproject.toml"))


def test_no_hand_written_distribution_list_survives_in_the_gate_or_its_checker() -> None:
    """⚑⚑⚑ ONE POPULATION, NINE SITES, AND A LANDED DISTRIBUTION IN NONE OF THEM.

    `fence` landed at `cc3d301` and every one of these loops still read
    `hooks mdstruct ratchet`. The consequences were real and silent: fence's 27 test functions
    carried ZERO warrants because the gate's 1:1 ledger never looked at them, and the arm
    asserting every BUILD file wires `pytest_main.py` never checked fence's.

    ⚑⚑ AND THE RECORDED SCOPE WAS ITSELF A HAND-WRITTEN POPULATION. The seed said SIX sites.
    MEASURED from the tree this tick: NINE — three in this module (I had recorded two), four in
    `.githooks/pre-commit`, one in `preflight.sh`, and one more in `blockers.sh`. The count of
    the defect had the defect.

    ⚑ ONE OF THE NINE IS NOT A DEFECT AND IS DELIBERATELY LEFT ALONE. `blockers.sh:151` sets
    `known="hooks mdstruct ratchet"` as a POSITIVE CONTROL over a population already derived by
    `git ls-files '*/pyproject.toml'` — the list is there to prove the structural query finds
    what it must, not to BE the population. A bulk edit would have destroyed that distinction,
    which is why each site was read before any was changed.

    ⚑ THE ARM ASSERTS THE ABSENCE OF THE LITERAL, not a count of sites. A count goes stale the
    moment a site is added or removed and says nothing about which; the literal is the defect.
    """
    root = _DIST.parent
    # ⚑ POSITIVE CONTROL: the derivation must find the distributions, or an absence assertion
    # below passes because the population is empty rather than because it is derived.
    dists = _distributions()
    assert len(dists) >= _MIN_DISTRIBUTIONS, (
        f"derived only {dists} — this arm would pass vacuously over an empty population"
    )
    assert "fence" in dists, "the derivation must see the distribution that exposed this defect"

    offenders: list[str] = []
    # ⚑ ASSERTED, NOT ASSUMED. A first cut wrote `../.githooks/pre-commit` — `_DIST.parent` is
    # ALREADY the repo root, so the path doubled and the arm failed with FileNotFoundError. RED,
    # which is what an F-arm should be, AND FOR THE WRONG REASON: a test failing on plumbing
    # proves nothing about its subject, and the real repair would have "fixed" it by accident.
    for rel in (".githooks/pre-commit", "preflight.sh"):
        target = root / rel
        assert target.is_file(), f"{rel} does not exist — this arm would fail on plumbing"
        for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.lstrip().startswith("#") and "hooks mdstruct ratchet" in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    # ⚑⚑⚑ THE PYTHON FILE IS PARSED, NOT SCANNED, AND A LINE SCAN PROVED WHY IN ONE RUN. It
    # reported ELEVEN offenders — three of them THIS ARM: its own docstring naming the literal,
    # its comment about `blockers.sh`'s positive control, and the comparison expression doing the
    # matching. ⚑ The sibling arm at `test_no_witness_reaches_a_venv` records the identical
    # lesson: *stripping `#` comments then flagged this very docstring, which DESCRIBES the
    # defect. Only an AST walk distinguishes an expression from prose about an expression.*
    # A witness that cannot make that distinction cannot live in a file documenting what it
    # forbids — and this one has to, because the offending sites are in it.
    module = _DIST / "tests" / "test_bar_fires.py"
    tree = pyast.parse(module.read_text(encoding="utf-8"))
    # ⚑⚑ THE PATTERN IS BUILT, NOT WRITTEN, AND THE FIRST CUT FLAGGED ITSELF FOR GOOD REASON.
    # A literal `("hooks", "mdstruct", "ratchet")` here is indistinguishable to the AST walk from
    # the sites it hunts — it WAS one, reported at its own line number. Deriving it from the
    # measured population minus the newcomer keeps the arm honest and keeps the predicate true
    # if a fifth distribution lands: the shape being refused is *the set as it was before the
    # last arrival*, which is exactly what a stale hand-written list is.
    stale = tuple(d for d in dists if d != "fence")
    for node in pyast.walk(tree):
        if not isinstance(node, pyast.Tuple):
            continue
        values = [e.value for e in node.elts
                  if isinstance(e, pyast.Constant) and isinstance(e.value, str)]
        if tuple(values) == stale:
            offenders.append(f"tests/test_bar_fires.py:{node.lineno}: {stale!r} as a literal")

    assert not offenders, (
        f"{len(offenders)} site(s) hard-code the distribution list; a landed distribution is "
        "silently outside every check that reads one:\n  " + "\n  ".join(offenders)
    )


def test_every_status_table_finder_uses_one_signature() -> None:
    r"""⚑⚑⚑ ONE PREDICATE, FOUR SITES, TWO SPELLINGS — AND THE ARM PINNED THE RIGHT ONE.

    The sibling arm below asserts `(party|surveyor|repo|leg) \| (status|state)` appears in the
    poll. It does, at ONE site. MEASURED this tick: the poll finds the `§S` table at FOUR places,
    and three of them spell the noun class `(surveyor|party)` — dropping `repo` and `leg`. So an
    arm reading *the signature is derived, not hardcoded* passed while three quarters of the
    finders used a narrower predicate than the one it checked.

    ⚑⚑ A ONE-SITE ASSERTION ABOUT A FOUR-SITE PREDICATE IS AN N-OF-M WITH THE M UNSTATED. Its
    population is *places I looked*, not *places the predicate lives*, and a correct check over
    that population passes every time while the divergence grows.

    ⚑ THE DIVERGENCE IS CURRENTLY HARMLESS AND THAT IS WHY IT SURVIVES. Measured across all ten
    run files the poll reads: the two spellings select the SAME table in every case, because no
    census today heads its `§S` with `repo` or `leg`. A predicate that only differs on inputs
    nothing produces yet cannot be caught by output at all — the census whose header first uses
    `leg |` would be found by one site and missed by three, and the poll would report a roster
    from one branch and a vocabulary refusal from another about the same file.

    ⚑ POSITIVE CONTROL for the absence claim above: `leg | why` DOES occur as a two-column header
    in `findings/CENSUS-deps-build-ANALYSIS.md`, so the noun is real in this corpus and the reader
    can see it. That file is excluded from the poll's population by `grep -v ANALYSIS`, which is
    why it is a control rather than a finding.

    ⚑ THE ARM COUNTS SPELLINGS, NOT SITES. Requiring `== 4` would break at the next legitimate
    finder; requiring ONE distinct noun class is the property that makes four sites one predicate.
    """
    body = _POLL.read_text(encoding="utf-8")
    found: list[str] = pyre.findall(
        r"\(([a-z|]*(?:surveyor|party)[a-z|]*)\) \\\| \(status\|state\)", body)
    spellings = set(found)
    assert spellings, (
        "no §S signature found in the poll at all — this arm would pass vacuously"
    )
    assert len(spellings) == 1, (
        f"the §S table is found by {len(spellings)} different noun classes, so the poll holds "
        "more than one idea of what a roster table is; a census heading its §S with a noun only "
        f"some of them admit is found by some branches and missed by others: {sorted(spellings)}"
    )


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


def test_the_unrecognised_header_probe_anchors_the_left_edge_of_the_header() -> None:
    r"""⚑⚑⚑ THE LINE SUPPLYING THE EVIDENCE FOR `UNRECOGNISED` WAS FABRICATING IT.

    The probe read `'[a-z-]+ \| [a-z-]+$'` — right-anchored, LEFT-OPEN — so it matched the last two
    fields of a header of any width and reported them as a two-column table. MEASURED on
    `CENSUS-backlog.md`, whose tables are 3, 4 and 3 columns wide and none of which is two: it
    printed `two-column headers present: changed | affects prefix | file`, both fragments being
    tails of wider headers. On `build-hermeticity` it emitted five, one of them off a FIVE-column
    table.

    ⚑⚑ The line exists to separate *unrecognised* from *absent*, and its own comment invites a
    reader to widen the signature set from what it prints — so the fabrication was load-bearing:
    acting on it would have installed `changed | affects` as an §S signature, a header no census
    has. ⚑ And the `PRE-FILING` verdict underneath was CORRECT, which is what let a fabricated
    premise sit above a true conclusion without looking wrong.

    ⚑ The assertion is on the ANCHOR, not on the header set: a probe whose left edge is open cannot
    report a header, only a suffix of one, whatever literals happen to be in the corpus today.
    """
    body = _POLL.read_text(encoding="utf-8")
    assert "grep -oE '[a-z-]+ \\| [a-z-]+$'" not in body, (
        "a left-open header probe reports the TAIL of any wide header as a two-column table"
    )
    assert "grep -oE 'col\\(s\\)  [a-z-]+ \\| [a-z-]+$'" in body, (
        "the left edge must anchor on the `col(s)` marker, which is where this reader's "
        "output provably starts the header — an anchor derived from the format, not guessed"
    )


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
    # ⚑⚑⚑ THE POPULATION IS DERIVED FROM THE FILE, AND IT USED TO BE THREE TYPED LABELS —
    # `ruff — lint clean`, `mypy — types clean`, `pytest — every case passes`. Two of those checks
    # were deleted when the gate delegated ruff and mypy to `//<dist>:ruff` and `//<dist>:mypy`,
    # and this arm then refused a correct change: it was asserting the CONTINUED EXISTENCE of
    # specific checks while claiming to assert a property of whatever checks exist.
    # ⚑⚑ THE PROPERTY IS UNCHANGED AND IS WHAT IS ASSERTED NOW: every `run_checked` site — however
    # many there are — hands a LOG to `note_failure` rather than a bare label. A hand-written list
    # of three inside an arm about capture discipline was a hand-written population, which is the
    # defect this suite has now paid for four times.
    per_dist: list[str] = pyre.findall(r'run_checked "\$dist: ([^"]+)"', body)
    others: list[str] = pyre.findall(r'^run_checked "([^"]+)"', body, flags=pyre.MULTILINE)
    labels = per_dist + others
    # ⚑ NON-EMPTY, ASSERTED: zero labels makes every check below vacuous, and this arm would then
    # certify a gate that had stopped checking anything at all.
    assert labels, "no `run_checked` site found in the gate — this arm would pass by finding none"
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


def _resolve_path(node: pyast.expr, targets: dict[str, Path]) -> Path | None:
    """Resolve `_CONST` and `_CONST / "literal" / …` to a path, and nothing else.

    ⚑⚑⚑ BOUNDED ON PURPOSE. The sweep skipped every test whose file-read receiver was not a bare
    NAME, and 12 of the 23 skipped open their file with a path expression — but only **4** are
    this shape. The rest divide by names or call results, and resolving those needs a parser this
    module should not grow: a skipped test that is REPORTED stays honest, while a half-built
    evaluator guessing at expressions would resolve to the WRONG file and check assertions against
    it, which is worse than skipping.

    Returns:
        the path the expression denotes, or None when it is outside this bounded form.

    """
    if isinstance(node, pyast.Name):
        return targets.get(node.id)
    if isinstance(node, pyast.BinOp) and isinstance(node.op, pyast.Div):
        left = _resolve_path(node.left, targets)
        if left is None or not isinstance(node.right, pyast.Constant):
            return None
        if not isinstance(node.right.value, str):
            return None
        return left / node.right.value
    return None


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
            "_PREFLIGHT": _PREFLIGHT, "_SETTINGS": _SETTINGS,
        # ⚑ `_DIST` IS A DIRECTORY, not a file — it is here only so `_DIST / "pyproject.toml"`
        # resolves. `is_file()` above rejects the bare name, so adding it cannot make a test
        # resolve to a directory and read nothing.
        "_DIST": _DIST,
        "_BRIEF": _BRIEF,
    }
    checked = 0
    missing: list[str] = []
    unresolved: list[str] = []
    # ⚑⚑⚑ THE SWEEP COVERS A PREDICATE SHAPE, NOT ARMS, AND SAID SO NOWHERE. Its floor counts
    # ASSERTIONS, and a green run reads as covering this module — MEASURED, it does not: some arms
    # read no file at all (subprocess probes, correctly outside — there is no haystack to be
    # absent from), some read a file this resolver cannot reach, and some resolve but assert by
    # regex or count rather than string membership.
    # ⚑ THAT IS NOT A DEFECT IN THE SWEEP. A vacuity check for `"literal" in body` cannot check a
    # regex without becoming a different tool. What was missing is the SCOPE, and a coverage
    # figure read as covering the whole is the mis-named population this repository has measured
    # eight times in its own checkers — this is the ninth, in the arm built to enumerate them.
    total_arms = 0
    swept_arms = 0
    for fn in (n for n in pyast.walk(tree) if isinstance(n, pyast.FunctionDef)):
        if fn.name.startswith("test_"):
            total_arms += 1
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
        # ⚑ AND THE BOUNDED EVALUATOR REACHES THE `_CONST / "literal"` FORM, which is 4 of the 12
        # path-expression skips. Anything else still falls through to the counted-and-ceilinged
        # branch below rather than being guessed at.
        if not named:
            named = [
                resolved
                for call in pyast.walk(fn)
                if isinstance(call, pyast.Call)
                and isinstance(call.func, pyast.Attribute)
                and call.func.attr == "read_text"
                for resolved in [_resolve_path(call.func.value, targets)]
                if resolved is not None and resolved.is_file()
            ]
        # ⚑⚑⚑ `len(named) != 1: continue` SILENTLY SKIPPED EVERY MULTI-FILE TEST, which is the
        # vacuity the sweep exists to catch, inside the sweep. The first test to read two files
        # exposed it — and it exposed it by FAILING rather than by being skipped only because a
        # target was missing from the map above; with the map complete it would have gone quiet.
        # ⚑ THE UNION IS ALSO THE CORRECT PREDICATE, not merely the one that admits these tests:
        # an assertion is vacuous when its literal appears in NO file the test reads, and taking
        # `named[0]` asserted that a test's first file is its only one.
        if not named:
            # ⚑⚑⚑ A QUIET `continue` IS HOW THIS SWEEP HID ITS OWN BLIND SPOT TWICE. The first was
            # `len(named) != 1`, which skipped every multi-file test until one failed for an
            # unrelated reason. This is the second: a test opening its file by an INLINE path
            # expression — `(_DIST / "pyproject.toml")` — resolves to no name and vanishes.
            # ⚑ MEASURED at the tick this was added: FOUR such tests, 2 string-membership
            # assertions between them, 0 vacuous. A coverage gap rather than a live defect, which
            # is the honest sizing.
            # ⚑ RESOLVING ARBITRARY PATH EXPRESSIONS IS A PARSER THIS MODULE SHOULD NOT GROW. A
            # skipped test that is REPORTED is honest; one that vanishes is the vacuity being
            # measured, one level out. So the skip is counted and ceilinged.
            # ⚑⚑⚑ TEST FUNCTIONS ONLY, AND THE CEILING COUNTED HELPERS TOO. This collected every
            # `FunctionDef` that reads a file, while `total_arms` above counts only `test_`-prefixed
            # ones — TWO POPULATIONS IN ONE FUNCTION, and the assertion's own message calls the
            # bigger one *N test(s)*. MEASURED: `_freshness`, a helper at line 584, sat in that
            # list. A helper cannot pass vacuously; nothing asserts inside it.
            # ⚑ SO THE CEILING NAMED ONE MORE THAN THE PROPERTY IT MEASURES, and every figure
            # derived from it inherited the mis-named population — including the carried symbol the
            # poll prints. A correct count over the wrong set is the defect this module refuses.
            if fn.name.startswith("test_") and any(
                isinstance(n, pyast.Call)
                and isinstance(n.func, pyast.Attribute)
                and n.func.attr == "read_text"
                for n in pyast.walk(fn)
            ):
                unresolved.append(fn.name)
            continue
        haystack = "\n".join(f.read_text(encoding="utf-8") for f in named)
        arm_swept = False
        for node in pyast.walk(fn):
            if (
                isinstance(node, pyast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], pyast.In)
                and isinstance(node.left, pyast.Constant)
                and isinstance(node.left.value, str)
            ):
                checked += 1
                arm_swept = True
                if node.left.value not in haystack:
                    missing.append(f"{fn.name}: {node.left.value!r}")
        if arm_swept and fn.name.startswith("test_"):
            swept_arms += 1
    assert checked >= _MIN_SWEPT, (
        f"the sweep resolved only {checked} assertions; it is not covering this module"
    )
    assert not missing, (
        "assertion literal(s) absent from the file the test reads — these pass vacuously:\n  "
        + "\n  ".join(missing)
    )
    # ⚑ A CEILING, NOT A TARGET. It may fall; it rises only when a new inline read is added, which
    # is exactly the moment a reader should be told rather than the moment coverage quietly drops.
    # ⚑ THE SHARE IS DERIVED AND STATED, never written down: a recorded figure is the
    # hand-written population this module exists to refuse. It is a FLOOR, so the sweep's reach
    # may grow and cannot silently shrink.
    assert swept_arms * 100 >= total_arms * _SWEEP_COVERS_ARMS, (
        f"the sweep checks string membership in {swept_arms} of {total_arms} arm(s) — "
        f"below the {_SWEEP_COVERS_ARMS}% floor. A green sweep is not module coverage."
    )
    assert len(unresolved) <= _MAX_UNRESOLVED, (
        f"{len(unresolved)} test(s) read a file the sweep cannot resolve, up from "
        f"{_MAX_UNRESOLVED} — their assertions are unswept: {sorted(unresolved)}"
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
    # ⚑⚑ THE COUNT BELONGS IN THIS ASSERTION AND THE TRUNCATION DID NOT, AND THE TWO ARE DIFFERENT
    # QUESTIONS. This is a RATCHET: the cardinality IS the subject, compared against a frozen
    # ceiling, so `len(without)` in the assertion is the measurement rather than a summary of one.
    # The EVIDENCE was the defect — it printed five names and no total, so a reader over the
    # threshold saw a sample and could not tell how large the population was.
    # ⚑ `linux-sources-94` found the same shape in an arm of theirs printing `unpaired e.g.` with
    # a three-element slice, and named the cost exactly: a failure message is prose that SHIPS, and
    # it is read precisely when someone is deciding what went wrong. A truncation there withholds
    # the thing the reader came for, in the one arm whose job is naming what is missing.
    assert len(without) <= _WARRANTS_WITHOUT_CHECK, (
        f"{len(without)} warrants carry no check field, up from the frozen "
        f"{_WARRANTS_WITHOUT_CHECK}. A warrant with no check asserts a claim nothing can run. "
        f"All of them, not a sample: {sorted(without)}"
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
    # ⚑⚑ THE LITERAL MOVED WHEN THE VERDICT LINE STARTED PRINTING ITS OPERANDS: `is a DROPPED ROW`
    # became `DROPPED ROW: $_elsewhere < $_gap`. **The behaviour this arm asserts was preserved and
    # its string was not**, so the arm went red on a change that strengthened its subject — which is
    # the correct direction for that failure. Caught twice independently in the same run: here, and
    # by the vacuity sweep reporting the literal absent from the file this arm reads.
    # ⚑ ANCHORED ON THE VERDICT WORD RATHER THAN THE SENTENCE, because the sentence around a verdict
    # is where operands and explanations accrete, and this arm is about the verdict existing.
    assert "DROPPED ROW:" in body, "an unexplained under-sign is the shape worth catching"
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
    `rule-codes-in-selectors`. ⚑ THAT WAS RECORDED HERE AS AN OPEN OPERATOR DECISION AND IS NOW
    ANSWERED — adopt, ruled 2026-09-07, with a second ruling on 2026-09-08 to take tree-wide
    `--preview` FIRST because a renamed selector is unloadable without it: measured, every ruff
    target exits 2 with *selecting rules by name requires preview mode*. A preflight failing every
    run on a decision nobody has made is furniture by the second tick; a stale record of a decision
    that HAS been made is worse, because a reader treats it as still open.

    ⚑ THE PREVIEW CENSUS BELONGS TO THE RATCHET, which the preflight also runs. So the prediction
    was already complete — via the ratchet line, not the ruff line. The original comment got the
    fact right (the three `blank-lines-*` refusals were preview keys) and attributed the coverage
    to the wrong instrument.

    ⚑⚑ SO THE ARM HOLDS AGREEMENT, NOT A FLAG. Whatever ruff the gate runs, the preflight runs —
    which is the property that makes a prediction one, and it stays true if either side changes.
    """
    preflight = _PREFLIGHT.read_text(encoding="utf-8")
    gate = _GATE.read_text(encoding="utf-8")

    # ⚑⚑⚑ THE AGREEMENT IS NOW ABOUT THE INSTRUMENT, NOT ITS FLAGS — AND THAT IS A STRONGER FORM
    # OF THE SAME PROPERTY. This arm used to compare the `--` flags on each file's `ruff check`
    # line. Both files have stopped invoking ruff directly: the gate delegates to `//<dist>:ruff`,
    # and the pre-flight now runs THAT SAME TARGET. Comparing flags of commands that no longer
    # exist would be an arm about a deleted subject, and comparing them as absent-in-both would be
    # satisfied by two files that check nothing.
    # ⚑⚑ SO WHAT IS ASSERTED IS THAT NEITHER RUNS A PRIVATE COPY, AND BOTH REACH THE TARGET. Two
    # callers of one target cannot pass different flags to it — the agreement holds by
    # construction rather than by two lines being kept in sync, which is what the flag comparison
    # was approximating.
    # ⚑⚑⚑ NON-COMMENT LINES ONLY, AND THE FIRST CUT MATCHED ITS OWN PROSE. Both files now EXPLAIN
    # why they no longer invoke `.venv/bin/ruff`, and a substring search over the whole text reads
    # that explanation as the thing it forbids — the sweep-cannot-tell-an-assertion-from-an-
    # explanation defect that `test_a_comment_naming_a_flag_says_whether_it_is_passed` records
    # immediately below, reproduced here while writing an arm one screen above it.
    for name, body in (("the gate", gate), ("the pre-flight", preflight)):
        live = [ln for ln in body.splitlines() if not ln.lstrip().startswith("#")]
        offenders = [ln.strip() for ln in live if ".venv/bin/ruff" in ln]
        assert not offenders, (
            f"{name} runs a private host-venv ruff again — the two can now disagree, which is "
            f"what delegating to //<dist>:ruff removed: {offenders}"
        )
    assert ':ruff"' in preflight or ":ruff " in preflight, (
        "the pre-flight does not reach //<dist>:ruff, so it predicts a check it never runs"
    )
    assert "bazel test //..." in gate, (
        "the gate does not run the suite, so //<dist>:ruff runs nowhere and the pre-flight "
        "predicts a check the gate has stopped performing"
    )
    # ⚑⚑ AND THE EXIT STATUS MUST STILL BE DISCRIMINATED. `||` folds *the checker could not start*
    # into *the gate will refuse this*. bazel exits 3 for a FAILING TEST and 1 for a BUILD failure,
    # so the pre-flight distinguishes them exactly as it did for ruff's 1-vs-2.
    assert "bazel EXITED" in preflight, (
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
# ⚑ HOISTED BESIDE THE OTHERS so the sweep's target map can carry it. Defined at its arm, it
# resolved to no NAME and the ceiling caught the arm — third consecutive tick, and the third time
# the honest repair was making the arm visible rather than raising the number.
_BRIEF = _DIST.parent / "findings" / "CENSUS-BRIEF.md"


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
    # ⚑⚑⚑ THIS ARM SAID *NO GATE* AND READ ONE OF EIGHTEEN SCRIPTS. Its name states a universal
    # over gates; its haystack was `domain_witness.sh` alone, so any sibling could carry the same
    # unreachable figure with this green. That is the defect measured at `383dacd` — an arm whose
    # population is one file where the property is about the harness — reproduced in an arm
    # written two ticks earlier, by me, three ticks before I named the class.
    # ⚑⚑ MEASURED ACROSS ALL EIGHTEEN: zero violations. So this is COVERAGE, not a live defect,
    # and saying so is the honest sizing rather than the alarming one.
    body = _WITNESS.read_text(encoding="utf-8")
    witness_commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the file must still emit the warning this arm is about, or the
    # assertion below passes because the sentence vanished rather than because it was fixed.
    assert "write this tree" in witness_commands, (
        "the concurrent-writer warning must still be emitted; this arm would pass on its absence"
    )
    # ⚑ NO SESSION COUNT, IN ANY SCRIPT. Only a harness reading can produce it, and only for one
    # instant — `blockers.sh` says so in as many words about peer reachability.
    session_count = pyre.compile(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+sessions?\b"
    )
    counted: list[str] = []
    scanned = 0
    for script in [*sorted(_DIST.parent.glob("*.sh")), _GATE, _MSGHOOK]:
        scanned += 1
        commands = "\n".join(
            ln for ln in script.read_text(encoding="utf-8").splitlines()
            if not ln.lstrip().startswith("#")
        )
        counted.extend(
            f"{script.name}: {m.group(0)}" for m in session_count.finditer(commands)
        )
    # ⚑ FLOOR ON THE POPULATION: a glob that stopped matching would make this vacuous in the
    # direction that reads as success.
    assert scanned >= _MIN_HARNESS_SCRIPTS, (
        f"only {scanned} script(s) scanned; the population is wrong"
    )
    assert not counted, (
        f"a gate asserts {counted} — a figure no script can reach, "
        "since live sessions are a harness reading rather than a fact about the tree"
    )


def test_the_paperkit_arm_names_a_cause_and_carries_a_control() -> None:
    """⚑⚑⚑ ONE WORD FOR THREE STATES WITH THREE DIFFERENT OWNERS.

    The poll printed `paperkit unimportable` every tick for the life of this session, and I
    carried it as a standing blocker without measuring it once. ⚑ MEASURED: it probes ONE
    interpreter — `mdstruct/.venv` — and prints an unqualified verdict about the repository.

    ⚑⚑ THE VERDICT IS RIGHT AND THE ACCOUNT IS MISSING, which is the harder shape. All three venvs
    agree, so nothing about the word is false. But *unimportable* collapses three states:
    **paperkit is broken** (paperkit's owner), **it is not installed here** (this repo's), and
    **the interpreter is absent** (a fact about the reader, not the subject). A blocker that
    cannot say which of those it found cannot be acted on, and this one sat unacted-on for the
    whole session.

    ⚑ MEASURED WHICH: `uv pip install --dry-run` resolves the local checkout in 4ms —
    *Would install 1 package*. paperkit is not broken and not missing. Nothing here installs it,
    and the declaration in `mdstruct/pyproject.toml` says why: *a published package, never a
    path*. **That is an operator decision and this arm does not settle it** — it only requires the
    poll to report which state it observed.

    ⚑⚑ AND THE PROBE NEEDS A CONTROL, because `import paperkit` failing and the interpreter not
    existing are byte-identical through `2>/dev/null`. A probe whose failure mode includes *the
    reader was absent* must exhibit a hit of the same shape, or its negative is a statement about
    itself — this repository's own rule, applied to the one arm that never carried it.
    """
    body = _POLL.read_text(encoding="utf-8")
    # ⚑ THE CONTROL: a module known-importable must be probed by the same interpreter, so a
    # failing `import paperkit` is distinguishable from an interpreter that cannot import at all.
    assert "paperkit: CONTROL" in body, (
        "the probe must exhibit a known-importable module, or its negative describes the reader"
    )
    # ⚑ AND THE VERDICT MUST NAME WHICH STATE. `unimportable` alone is three findings with three
    # owners collapsed into one word.
    assert "not installed here" in body, (
        "the arm must distinguish 'nobody installed it' from 'it is broken'"
    )


def test_the_census_arm_can_tell_a_failed_read_from_an_empty_one() -> None:
    """⚑⚑⚑ THE POLL DISCARDS THE ONE FIELD THAT SEPARATES A BROKEN READ FROM AN EMPTY ONE.

    Line 213 guards *is the reader executable* and names its absence honestly. Every `mdstruct`
    call after it is `2>/dev/null`, reading only stdout — so a reader that RUNS and FAILS returns
    nothing and is byte-identical to a file that legitimately has no such table.

    ⚑ MEASURED against the real reader, and the states ARE separable:

        a real census file          rc=0, 5 lines
        a markdown file, no tables  rc=0, 1 line     <- the honest empty
        an undecodable file         rc=1, 0 lines
        a path that does not exist  rc=2, 0 lines

    **The honest empty carries `rc=0`.** Every failure carries a nonzero status and an empty
    stdout, so the discriminator exists and the poll throws it away — the same shape as the
    `paperkit` arm repaired at `f9feacf`, one level in, and reached by the same question.

    ⚑⚑ THE POLL SELECTS EVERY LATER TICK'S WORK, so a census whose reader failed reports as a
    census with no roster: `0 of 0 parties listed`, a clean-looking line. That is worse than an
    error, because a reader who sees it concludes something about the census rather than about
    the read.

    ⚑ THE REPAIR IS A GUARD ON THE FIRST READ, not on every call. One probe of the file with its
    status inspected tells the block whether anything below can be trusted; repeating it at ten
    call sites would be ten places to forget it — this gate's own `note_failure` lesson.
    """
    body = _POLL.read_text(encoding="utf-8")
    # ⚑ THE STATUS MUST BE INSPECTED SOMEWHERE. `2>/dev/null` on every call means the only
    # remaining signal is the exit code, and reading neither leaves the block guessing.
    assert "READER FAILED" in body, (
        "a reader that ran and failed must be named, not read as an empty result"
    )
    # ⚑ AND THE GUARD MUST PRECEDE THE READS IT PROTECTS. Placed after, it would describe a
    # verdict the failed read had already produced.
    assert body.index("READER FAILED") < body.index('sig=$("$md" tables'), (
        "the guard runs before the first read whose emptiness it explains"
    )


def test_the_island_arm_says_the_dependency_was_inverted() -> None:
    """⚑⚑⚑ A BLOCKER SECTION FOR A BLOCKER THAT WAS RESOLVED BY INVERSION.

    The poll prints 32 substrate modules as untracked-or-staged-only under the heading *the
    ratchet island*, and I carried `⟐SUBSTRATE-ISLAND` in the symbol set every tick without
    measuring what it blocks.

    ⚑ MEASURED: it blocks nothing here. The only reference to any island module anywhere in this
    repository is the poll line that reports it. mtools ships its OWN `mikemol-ratchet` —
    `census`, `cli`, `core`, `state` — landed at `6da1021`, whose subject reads *built from the
    design not the modules*.

    ⚑⚑ AND THE TWO ARE NOT THE SAME CODE. `core.py` here is 325 lines defining six functions;
    substrate's `ratchet_core.py` is 193 defining four. **One name is shared out of ten.** The
    commit says why: importing untracked modules *would vendor a snapshot nobody can fetch — the
    anti-pattern this repository exists to retire.*

    ⚑⚑⚑ SO THE SECTION REPORTS A TRUE FACT UNDER A HEADING THAT MAKES IT ACTIONABLE, AND IT IS
    NOT. Those modules being untracked is substrate's business; it stopped being mtools' blocker
    the moment the dependency inverted. A poll that lists 32 lines of another repo's working state
    under *the standing blockers* trains its reader to scroll past thirty-two lines — the furniture
    rule reached by volume rather than by constancy.

    ⚑ THE SECTION IS KEPT, NOT DELETED. The count is still evidence about a peer this repo
    consumes from, and deleting it would lose the enumeration whose derivation the block's own
    comment argues for. What changes is that it names its own status: reported, not blocking.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ THE SECTION MUST SAY WHOSE STATE IT IS. Without that a reader takes 32 untracked modules
    # for work this repository is waiting on.
    assert "not a blocker here" in commands, (
        "the island section must say it reports a peer's state rather than a blocker of ours"
    )
    # ⚑ AND IT MUST NAME THE COMMIT THAT INVERTED IT, so the claim is checkable rather than
    # asserted — a reader can run `git show` and read the decision.
    assert "6da1021" in commands, (
        "the inversion must cite the commit that performed it, not merely assert it happened"
    )


def test_the_ledger_section_distinguishes_deferred_from_resolved() -> None:
    """⚑⚑⚑ TWO POLL SECTIONS, ONE SHAPE, AND THE OBVIOUS READING WOULD HAVE BEEN WRONG.

    Last tick the ratchet-island section turned out to report *a blocker resolved by inversion*.
    The membudget-ledger section sits beside it, is also one substrate path reported as untracked,
    and the tempting move was to repair it identically.

    ⚑ MEASURED, AND IT IS A DIFFERENT STATUS. The island blocks nothing because mtools built its
    own ratchet from the design. The ledger has no mtools counterpart: **no `membudget/`
    directory, no distribution, no commit deciding it.** What exists is
    `findings/membudget/` — **22 filings from five parties**, eight of which discuss the keyway
    that the intake plan named as its open design question.

    ⚑⚑ SO ONE IS RESOLVED AND THE OTHER IS DEFERRED, and those are not the same line. *Not a
    blocker here* would be false: this repository does intend to intern membudget, and the thing
    stopping it is a design question with a named owner rather than an inverted dependency.
    Reporting deferred work as resolved is the flattering direction — the same direction the
    refusal record undercounted in.

    ⚑ THE WORD `membudget` NAMES TWO REFERENTS IN THIS TREE, which is why the sweep needed reading
    rather than counting. `figure_freshness.sh` mentions it twice and both are
    `findings/membudget/`, a filed corpus here; `mdstruct/pyproject.toml` mentions it twice and
    both are prose about a hypothetical sibling distribution. Neither is substrate's ledger
    script. A hit count of four would have read as four consumers.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ THE SECTION MUST NAME ITS STATUS, like the island's — but with the status it actually has.
    assert "DEFERRED" in commands, (
        "the ledger section must say it is deferred, not leave a reader to infer a blocker"
    )
    # ⚑ AND IT MUST NAME WHAT WOULD END THE DEFERRAL. A deferral with no stated exit is
    # indistinguishable from a thing nobody looked at again.
    assert "keyway" in commands, (
        "a deferral must name the question that ends it, or it is a hold nobody revisited"
    )
    # ⚑ IT MUST NOT CLAIM TO BE RESOLVED. The island's wording is correct there and false here;
    # copying it would report deferred work as done, which is the flattering direction.
    ledger_block = commands.split("membudget ledger")[1].split("=== ")[0]
    assert "not a blocker here" not in ledger_block, (
        "the ledger is deferred, not resolved; the island's wording would be a false claim"
    )


def test_the_poll_covers_the_symbols_carried_between_ticks() -> None:
    """⚑⚑⚑ THE POLL FIXED THE REMEMBERED-LIST DEFECT FOR FILESYSTEM BLOCKERS AND NOT FOR MINE.

    Its opening comment states the rule it was built on: *a claim with no re-derivation procedure
    will not be re-checked however load-bearing it is, because nothing about it announces that it
    could be.* ⚑ MEASURED against the symbols actually carried between ticks: **four have no
    procedure at all** — the apex's unfilled slot, the refusal record's pre-column rows, the
    vacuity sweep's inline reads, and the interning gap.

    ⚑⚑ AND TWO HAD ALREADY DRIFTED, WHICH IS THE EVIDENCE RATHER THAN THE WORRY. I carried the
    refusal record as *two ragged rows*; a field count finds **three of seven**. I carried the
    sweep gap as *one instance fixed*; it is **23**. Both were re-stated from memory every tick
    and neither was re-read.

    ⚑⚑⚑ AND THE SWEEP FIGURE WAS WRONG AGAIN ONE TICK LATER, BY 6x. This section first counted it
    with a regex matching one syntactic form and reported FOUR; the sweep's own predicate — any
    `read_text` receiver that is not a mapped NAME — measures **23**. A correct-looking number
    over a mis-named population, produced by the instrument built to refuse exactly that.
    ⚑ SO THE POLL ASKS THE SWEEP rather than re-deriving with a second, weaker predicate. Two
    instruments computing one figure two ways is how they disagree without either noticing.

    ⚑ THE SYMBOLS THAT DISSOLVED THIS WEEK WERE ALL POLLED ONES — paperkit, the island, the
    ledger. They dissolved because the poll re-printed them until someone asked what they blocked.
    **An unpolled symbol has no such pressure**, which is why the four that rotted are exactly the
    four the poll never printed. The discriminator was never importance.

    ⚑⚑ REACHABLE, ALL FOUR, and that is what makes this coverable rather than a complaint: a
    structural read answers the apex slot, a field count answers the record, a regex answers the
    sweep. The fourth's subject is peer trees — reachable, but a fact about them.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ THE SECTION MUST EXIST. A carried symbol with no printed line is one nothing re-derives.
    assert "carried symbols" in commands, (
        "the poll must re-derive the symbols carried between ticks, not only filesystem blockers"
    )
    # ⚑ AND IT MUST DERIVE THEM, not list them. A hand-written list of symbol names inside the
    # instrument that exists to refuse hand-written lists is the defect one level out — this
    # repository has measured eight of those in its own checkers.
    # ⚑ SPLIT, because a compound assertion names neither half when it fails. The gate's own
    # ruff caught this: one message for two properties is the collapsed verdict this suite
    # refuses elsewhere, arriving in an assertion rather than in a checker.
    # ⚑⚑⚑ THE PROPERTY IS THAT THE RECORD IS READ, not that the word `ragged` appears — and this
    # assertion was keyed on the word until a repair that IMPROVED the line broke it. The line now
    # separates two shapes (pre-schema rows versus rows attributable to a session but not a gate)
    # because one sentence was describing both; the word `ragged` went with the collapsed sentence.
    # ⚑⚑ THE COMMENT TWO ASSERTIONS BELOW ALREADY RECORDS THIS LESSON, about `inline`, in this same
    # block: *an arm keyed to today's phrasing rather than to what makes the line trustworthy.*
    # It was applied to that assertion and not to this one, and this one broke the same way.
    assert "REFUSALS.tsv" in commands, (
        "the refusal record must be READ, not remembered — the poll must open the file rather "
        "than restate a figure from a previous tick"
    )
    # ⚑ THE PROPERTY IS THAT THE FIGURE COMES FROM THE SWEEP, not that a particular word appears.
    # This asserted `inline`, a word the repaired line no longer uses — an arm keyed to today's
    # phrasing rather than to what makes the line trustworthy.
    assert "_MAX_UNRESOLVED" in commands, (
        "the sweep's skipped count must be read from the sweep, not re-derived by the poll"
    )


def test_the_accounted_verdict_does_not_assert_a_liveness_the_poll_cannot_read() -> None:
    """⚑⚑⚑ THE POLL'S ONE UNCOVERABLE CLAIM WAS LOAD-BEARING INSIDE A CLAIM IT DOES MAKE.

    The poll declares `NOT COVERED: peer reachability — run ListAgents; it is a reading, not a
    fact`, and that declaration is correct and deliberate: only the harness can run it. ⚑ But the
    census section then reads an `accepted` cell and concludes *every rostered surveyor without a
    leg here carries a state that explains it: filed elsewhere, STILL PENDING, or terminally
    declined. None is a dropped row.*

    ⚑⚑ `accepted` IS A PAST-TENSE DOCUMENT STATE AND `still pending` IS A PRESENT-TENSE CLAIM
    ABOUT A PARTY. The document records that someone accepted; whether they are still running is
    exactly the reading the poll says it cannot make. The verdict *none is dropped* rests on it.

    ⚑⚑ FIRST MEASURED 2026-09-08, when the peer count fell from 12 to 10 with the other six refs
    unchanged. RE-MEASURED 2026-09-10 across a fleet restart — and the second reading is the
    stronger one, because `CENSUS-paperkit-use.md`'s §S is BYTE-IDENTICAL across both while every
    liveness fact under it moved:

        row (unchanged both days)               session on 09-08   on 09-10
        gabion      filed elsewhere             gone               gone
        rosettapkg  not yet filed — dispatcher  gone               gone
        summit      accepted, not yet filed     RUNNING            GONE
        linux-sources / substrate / paperkit    running            GONE

    ⚑⚑⚑ THE ROSTER CANNOT MOVE WHEN A PARTY STOPS EXISTING, so a §S table two days stale and one
    written this minute are byte-identical — the roster's default state and its measured state,
    exactly the equality this poll's own opening refuses elsewhere. On 09-08 an earlier draft of
    this docstring recorded *summit — still running* as evidence; two days later that sentence was
    false and nothing in the file could have said so.

    ⚑ `rosettapkg` is `not yet filed` by a party that no longer exists, and it is this census's
    DISPATCHER — neither pending nor terminal. The census vocabulary has no state for it, and the
    poll cannot acquire one.

    ⚑ THE ARM DOES NOT ASK THE POLL TO READ LIVENESS. It asks it not to ASSERT liveness: the
    verdict may say a row carries a state, and must not upgrade that to a claim the party is still
    working. A tool that names its blind spot in one section and spends it in another has
    published the disclosure and kept the defect.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: both halves must exist, or this arm passes because one vanished.
    assert "NOT COVERED: peer reachability" in commands, (
        "the reachability disclaimer must still be emitted; this arm would pass on its absence"
    )
    assert "ACCOUNTED" in commands, (
        "the accounted verdict must still be emitted; this arm would pass on its absence"
    )
    # ⚑⚑⚑ AND MY FIRST PREDICATE HERE EXAMINED THE WRONG REGION AND REPORTED GREEN. It read
    # `commands.split("ACCOUNTED")[1].split("DROPPED ROW")[0]` — but `ACCOUNTED` occurs TWICE in
    # the poll, so `[1]` is the slice after the FIRST, which is the `ACCOUNTED by declared states`
    # branch, and it ends exactly where the verdict under test begins. A mis-named population,
    # inside the arm written to catch a mis-named claim.
    # ⚑ SO THE KEY IS THE EMITTED SENTENCE, which is unique and is the thing being asserted about.
    assert "still" not in commands.split("leg here carries a state that explains it")[1][:200], (
        "the ACCOUNTED verdict claims a surveyor is STILL pending, which is a present-tense fact "
        "about a live party — precisely the reading this poll declares NOT COVERED. Report the "
        "document's state without upgrading it to a claim about who is still working"
    )


def test_the_poll_does_not_report_a_ceiling_as_a_measurement() -> None:
    r"""⚑⚑⚑ THE POLL PRINTS A BOUND AND CALLS IT A READING FROM THE SWEEP.

    The line reads `vacuity sweep: N test(s) it cannot resolve — ceiling read from the sweep
    itself`, and `N` comes from `grep -oE '^_MAX_UNRESOLVED = [0-9]+'` over this module. That is a
    HAND-TYPED CONSTANT. The sweep never runs; what runs is a grep for a literal.

    ⚑⚑ THE TWO ARE DIFFERENT OBJECTS. `_MAX_UNRESOLVED` is what someone declared the sweep MAY
    report; `len(unresolved)` is what it DOES report, and the sweep asserts only `<=` between
    them. MEASURED this tick by forcing the ceiling to `-1` so the assertion prints its own set:
    ceiling 21, actual 21 — EQUAL TODAY, because the ceiling was last lowered until it touched the
    count. The next test the sweep resolves drops the count to 20 while the poll keeps printing
    21, and nothing distinguishes that from correct.

    ⚑⚑ AND `test_the_poll_covers_the_symbols_carried_between_ticks` REQUIRES THE DEFECT. Its
    comment reads *THE PROPERTY IS THAT THE FIGURE COMES FROM THE SWEEP*, and it asserts the
    string `_MAX_UNRESOLVED` appears in the poll — which is satisfied by, and only by, reading the
    ceiling. An arm that cannot tell a bound from a measurement, guarding the line that confuses
    them. It still passes after this repair, because the grep is not the defect: the SENTENCE was.

    ⚑ THIS IS b98f14b's DEFECT TWO COMMITS LATER: a typed figure reprinted every tick, in the poll
    whose opening forbids typed figures. There it was a sum; here it is a bound wearing a
    measurement's sentence.

    ⚑ THE ARM ASSERTS THE LINE'S OWN HONESTY, not a number. Either the poll derives the count, or
    it names the figure a CEILING — a bound reported AS a bound is a true statement, and it is the
    cheap repair, because deriving `len(unresolved)` costs a full pytest run per poll invocation.

    ⚑⚑⚑ AND THE FIRST FORM OF THIS ARM WENT VACUOUS THE INSTANT IT PASSED — see the comment on the
    assertion below. Two-armed after the reformulation, by restoring the original defective line in
    a copy of the poll: defect present -> rc 1, repaired -> rc 0. A positive-form arm that had
    merely stopped firing would pass both.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the vacuity line must still exist, or this arm passes on its absence.
    # ⚑⚑ AND THIS CONTROL FIRED ON MY OWN REPAIR. It read `vacuity sweep:` with the colon, which
    # the repair moved when the label became `vacuity sweep CEILING:` — so the control refused
    # rather than passing on an absence I had just created. Keyed to the two words that survive
    # any honest relabelling, since the label is exactly what this arm expects to change.
    assert "vacuity sweep" in commands, (
        "the vacuity line must still be emitted; this arm would pass if it vanished"
    )
    # ⚑⚑⚑ AND MY FIRST FORM OF THIS ASSERTION WENT VACUOUS THE MOMENT IT PASSED. It read
    # `not (reads_ceiling and "read from the sweep itself" in commands)` — a NEGATIVE keyed to the
    # phrase the repair DELETES, so after the repair that operand is permanently False, the
    # conjunction can never fire, and half the arm is dead while the whole reads green.
    # ⚑⚑ THE SWEEP CAUGHT IT IN ONE RUN, by exactly its own predicate: an assertion literal absent
    # from the file the test reads. The instrument this arm was written about found this arm.
    # ⚑ SO THE PROPERTY IS STATED POSITIVELY: if the poll greps the constant, the line must NAME it
    # a ceiling. A required presence cannot be emptied by deleting prose — which is the difference
    # between an arm that survives its own repair and one that only survived until it worked.
    if "_MAX_UNRESOLVED" in commands:
        assert "CEILING" in commands, (
            "the poll greps the hand-typed `_MAX_UNRESOLVED` constant, which is what the sweep "
            "MAY report rather than what it does, and the printed line does not name it a "
            "ceiling. Either derive `len(unresolved)`, or label the figure a CEILING so a bound "
            "is reported as a bound"
        )


def test_the_vacuity_sweep_resolves_an_inline_path_read() -> None:
    """⚑⚑⚑ FOUR TESTS ARE SKIPPED ENTIRELY BY THE SWEEP, AND IT SAYS SO NOWHERE.

    The sweep resolves a test's subject by matching `X.read_text(...)` where `X` is a NAME in its
    target map. A test opening its file by an inline expression — `(_DIST / "pyproject.toml")` —
    resolves to nothing, hits `if not named: continue`, and every assertion in it goes unchecked.

    ⚑ MEASURED, now that the poll derives the figure rather than my memory carrying it: **four
    such tests**, and the sweep sees NOTHING for all four. Not *the wrong file* — nothing.

    ⚑⚑ AND THEY ARE NOT CURRENTLY VACUOUS, which is the honest sizing rather than the alarming
    one. Resolving all four by hand and running the sweep's own predicate: **2 string-membership
    assertions, 0 vacuous.** This is a coverage gap, not a live defect, and saying so is the
    difference between a finding and a scare.

    ⚑⚑⚑ THE SKIP IS THE PART WORTH FIXING REGARDLESS. `continue` on an unresolvable test is the
    same shape the sweep already repaired once: `len(named) != 1: continue` silently skipped every
    MULTI-file test until one failed for an unrelated reason. **The sweep has now hidden its own
    blind spot twice by the same mechanism** — a quiet `continue` — and both times the population
    it skipped was invisible in a green run.

    ⚑ SO THE SWEEP COUNTS WHAT IT SKIPPED. Resolving arbitrary path expressions is a parser this
    module should not grow; a skipped test that is REPORTED is honest, while one that vanishes is
    the vacuity being measured, one level out.
    """
    # ⚑⚑⚑ THIS ARM PASSED BEFORE ITS SUBJECT EXISTED, because its literals appear in the prose
    # above. Written as a whole-file search it read its OWN DOCSTRING and reported the fix as
    # already shipped — a checker that cannot tell a description from an instance, for the third
    # time in this suite and the first time inside the arm that measures vacuity.
    # ⚑ SO THE SUBJECT IS THE PARSED MODULE, not its text: the sweep function's own body, with
    # docstrings excluded by construction rather than by stripping comments.
    module = pyast.parse(_THIS.read_text(encoding="utf-8"))
    sweep = next(
        (n for n in pyast.walk(module)
         if isinstance(n, pyast.FunctionDef)
         and n.name == "test_no_string_assertion_in_this_module_is_vacuous"),
        None,
    )
    assert sweep is not None, "the sweep function was not found; this arm would pass on absence"
    # drop the docstring node, which is where a description of the defect lives
    body = sweep.body[1:] if (
        sweep.body and isinstance(sweep.body[0], pyast.Expr)
        and isinstance(sweep.body[0].value, pyast.Constant)
    ) else sweep.body
    code = "\n".join(pyast.dump(n) for n in body)
    # ⚑ THE SWEEP MUST ACCOUNT FOR WHAT IT COULD NOT RESOLVE. A count it prints is a count a
    # reader can compare against the poll's, which derives the same figure independently.
    assert "unresolved" in code, (
        "the sweep must report the tests it skipped, not drop them silently"
    )
    # ⚑ AND THE ACCOUNTING MUST BE A CEILING, not a target: it may fall, and rises only when a
    # new inline read is added — which is the moment a reader should be told.
    assert "_MAX_UNRESOLVED" in code, (
        "the skipped population needs a ceiling, or it grows back silently"
    )


def test_every_test_function_count_in_the_harness_sees_a_method() -> None:
    """⚑⚑⚑ THE COUNTER REPORTED ZERO FOR A WHOLE DISTRIBUTION AND 0:0 SATISFIES 1:1.

    Both counting sites read `grep -h -c '^def test_'` — anchored at COLUMN 0. Every test in
    `fence` is a CLASS METHOD (`    def test_`), so the harness counted **zero** test functions
    there. ⚑ A ledger with zero warrants against zero functions is 1:1 and PASSES, while 33 real
    tests go unwarranted. The gate would have reported green over a distribution it could not see
    into, on the very tick that taught it to walk fence at all.

    ⚑⚑ AND THE FIGURE I CARRIED FOR IT WAS FROM A THIRD POPULATION. The seed said fence had 27
    test functions to warrant. MEASURED: **0** by the gate's predicate, **33** methods, **45**
    cases collected by pytest. The 27 came from an early pytest run and matched none of them — a
    count with no stated provenance, carried across ticks as ready work.

    ⚑ THE STYLE IS FENCE'S ALONE, MEASURED: every sibling distribution writes module-level
    functions and `grep -c '^    def test_'` returns 0 for each. So the predicate matched the
    convention rather than the population, and a distribution arriving from another repo with a
    different-but-valid style was invisible to it. The operator ruled: widen the counter.

    ⚑ THE ARM ASSERTS THE PREDICATE, NOT A COUNT. A count goes stale the next time a test lands;
    what must hold is that both counting sites admit an indented `def test_`, since the gate and
    the preflight disagreeing is the defect the sibling arm below exists for.
    """
    root = _DIST.parent
    sites = (".githooks/pre-commit", "preflight.sh")
    blind: list[str] = []
    for rel in sites:
        target = root / rel
        assert target.is_file(), f"{rel} does not exist — this arm would fail on plumbing"
        for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
            # ⚑ THE COUNTING SITES ARE THE ONES PIPING A `grep` INTO `bc`. A comment mentioning
            # `def test_` is prose about the predicate, not the predicate — the same
            # expression-versus-prose-about-an-expression distinction the AST arm above pays for.
            if line.lstrip().startswith("#"):
                continue
            if not ("grep" in line and "bc" in line and "def test_" in line):
                continue
            # ⚑⚑⚑ THE PROPERTY IS *INDENTATION IS ADMITTED*, NOT ONE SPELLING OF THE FIX. A first
            # cut required the literal `    def test_` and then FAILED AGAINST THE REPAIR ITSELF:
            # `^(    )?def test_` admits an indented definition without containing that substring.
            # ⚑ An arm keyed to a form rather than a fact — the same defect as the one it hunts,
            # in the hunter. What is asserted now is that the pattern is not anchored at column 0
            # with nothing before `def`.
            pattern = line.split("'")[1] if line.count("'") >= _QUOTED_PAIR else line
            if pattern.startswith("^def test_"):
                blind.append(f"{rel}:{lineno}: {line.strip()}")
    assert not blind, (
        f"{len(blind)} counting site(s) anchor `def test_` at column 0, so a distribution whose "
        "tests are class methods counts as ZERO and its empty ledger reads as 1:1:\n  "
        + "\n  ".join(blind)
    )


def test_every_warrant_count_in_the_harness_is_anchored() -> None:
    """⚑⚑⚑ AN ARM ALREADY FORBIDS THE UNANCHORED COUNT, AND THE PREFLIGHT USES IT ANYWAY.

    `test_the_warrant_count_is_anchored_against_a_quoted_delimiter` asserts
    `grep -c '@misc{'` must not appear — ⚑ MEASURED, it reads `_GATE` and nothing else. The
    preflight's `w=$(grep -c '@misc{' …)` is outside its population entirely, so the rule is
    stated, enforced, and violated in the same tree with every run green.

    ⚑⚑ THE COUNTS AGREE TODAY BY LUCK. 215 both ways, because the ledger has **zero** lines
    carrying `@misc{` off column 0. One quoted example inside a `note` field would split them,
    and the preflight — whose entire job is predicting the gate — would predict a warrant total
    the gate disagrees with.

    ⚑ THIS IS THE SAME DEFECT AS `01dc5e7`, ONE FILE OVER. There the poll and the sweep computed
    the skipped-test count two ways and disagreed 4 against 23; here the preflight and the gate
    compute the warrant total two ways and agree only while an accident holds. **Two instruments
    deriving one figure independently is how they drift without either noticing**, and a
    single-file arm cannot see the pair.

    ⚑⚑ SO THE POPULATION IS EVERY COUNTING SITE, derived rather than listed: any non-comment line
    in the harness that counts `@misc{` must anchor it. A per-file arm would be the hand-written
    population this suite exists to refuse.
    """
    # ⚑⚑⚑ READ THROUGH NAMED CONSTANTS, NOT A DICT — AND THE CEILING ADDED LAST TICK CAUGHT THIS
    # ARM ON ITS FIRST LIVE OPPORTUNITY. A dict of paths resolves to no NAME, so the sweep could
    # not see this test and its own assertions would have gone unswept: the arm about a blind
    # spot, blind in the same way. Raising the ceiling would have been the flattering repair.
    preflight = _PREFLIGHT.read_text(encoding="utf-8")
    gate = _GATE.read_text(encoding="utf-8")
    msgcount = _MSGCOUNT.read_text(encoding="utf-8")
    sources = {
        "preflight.sh": preflight,
        ".githooks/pre-commit": gate,
        "message_counts.sh": msgcount,
    }
    unanchored: list[str] = []
    counting = 0
    for name, text in sources.items():
        for line in text.splitlines():
            if line.lstrip().startswith("#") or "@misc{" not in line:
                continue
            if "grep -c" not in line:
                continue
            counting += 1
            if "'^@misc{'" not in line:
                unanchored.append(f"{name}: {line.strip()}")
    # ⚑ POSITIVE CONTROL ON THE POPULATION: a pattern that stopped matching would make this arm
    # vacuous in the direction that reads as success — no counting sites, nothing to check.
    assert counting >= _MIN_WARRANT_COUNT_SITES, (
        f"only {counting} warrant-counting site(s) found; the population is wrong"
    )
    assert not unanchored, (
        "warrant count(s) not anchored to column 0 — these disagree with the gate the moment a "
        "quoted `@misc{` appears in the ledger:\n  " + "\n  ".join(unanchored)
    )


def test_the_test_function_count_survives_a_missing_trailing_newline() -> None:
    """⚑⚑⚑ THE GATE COUNTS OVER A CONCATENATION AND THE PREFLIGHT COUNTS PER FILE.

    Both compare warrants against `^def test_`, and they agree only while every test module ends
    in a newline. ⚑ `cat a b | grep -c` welds `a`'s last line to `b`'s first, so a `def test_` at
    the start of the next file stops matching the anchor. MEASURED on a two-file fixture where the
    first lacks its newline: **preflight 3, gate 2.**

    ⚑⚑ AND THE GATE'S ERROR IS THE REFUSING DIRECTION. It reads FEWER test functions than exist,
    so a ledger that is genuinely 1:1 looks like it carries surplus warrants and the commit is
    refused. The preflight — whose whole job is predicting that refusal — would have said the
    tree was clean.

    ⚑ ALL 25 TEST MODULES END IN A NEWLINE TODAY, across all three distributions, so the counts
    agree at 216, 88 and 37. That is the accident holding, not the property being enforced: this
    is the third consecutive tick where two instruments derive one figure by different predicates
    and agree only by luck.

    ⚑⚑ THE FIX IS THE GATE COUNTING THE WAY THE PREFLIGHT DOES, not the reverse. Per-file counting
    is correct independent of file endings; concatenation is correct only under a condition
    nothing here enforces. A `.editorconfig` or a lint rule would ALSO work and would be a second
    thing to keep true — the weaker repair, because it fixes the accident rather than the reader.
    """
    gate = _GATE.read_text(encoding="utf-8")
    # ⚑ THE GATE MUST NOT COUNT OVER A CONCATENATION. `cat … | grep -c` is the exact construction
    # that loses a match at every file boundary lacking a newline.
    catted = [
        ln.strip() for ln in gate.splitlines()
        if not ln.lstrip().startswith("#")
        and "def test_" in ln and "cat " in ln
    ]
    assert not catted, (
        "the gate counts test functions over a concatenation; a file without a trailing newline "
        f"welds two lines and the count drops: {catted}"
    )
    # ⚑ AND IT MUST STILL COUNT THEM — a repair that removed the check would pass the assertion
    # above by deleting the property, which is the vacuity this suite exists to refuse.
    # ⚑⚑⚑ THIS LOOKED FOR THE STRING `def test_` IN THE GATE, AND THAT KEYED IT TO ONE
    # IMPLEMENTATION. The counter moved into `count_test_functions.py` — a PARSE rather than a
    # match, because a grep counted `def test_` inside a string literal in `test_grade.py`
    # (ast 17, pytest 17, grep 20). The property survived; the arm read its ABSENCE FROM THIS
    # FILE as its removal and refused a correct repair.
    # ⚑⚑ AN ARM KEYED TO A FORM RATHER THAN A FACT, which its own comment above warns about one
    # sentence earlier — and the third instance this tick. What must hold is that the gate still
    # OBTAINS a count, wherever the counting lives.
    counts = [
        ln.strip() for ln in gate.splitlines()
        if not ln.lstrip().startswith("#")
        and ("def test_" in ln or "count_test_functions" in ln)
    ]
    assert counts, "the gate no longer counts test functions at all, by any means"


def test_two_instruments_counting_one_literal_use_one_predicate() -> None:
    """⚑⚑⚑ THREE CONSECUTIVE TICKS FOUND ONE FIGURE DERIVED TWO WAYS, EACH BY HAND.

        `01dc5e7`  skipped-test count   poll regex vs sweep predicate     4 vs 23
        `383dacd`  warrant total        unanchored vs anchored grep       agreed by luck
        `a644aa8`  test-function count  concatenation vs per-file         agreed by luck

    ⚑ Each was found by reading, not by a check. The class is what has leverage, and it is
    ENUMERABLE: a derivation is an assignment whose value counts a literal, and two derivations
    counting the SAME literal are deriving the same quantity.

    ⚑⚑ THE GROUPING KEY IS A WITNESS FROM THE SOURCE, not my judgement that two expressions mean
    the same thing. The census-kit rule is that an identification without a witness is the
    reader's convenience; here the witness is the counted pattern itself, stripped of anchoring.
    Two sites counting `@misc{` are counting warrants whatever else differs — and if one anchors
    and the other does not, that is exactly `383dacd`.

    ⚑ MEASURED: 14 counting derivations, three literals counted more than once — `@misc{` at four
    sites, an escaped backtick at two, `def test_` at two — and **all three groups now agree**.
    Three count a literal at exactly one site and have no pair to disagree with.

    ⚑⚑ SO THIS ARM IS A RATCHET OVER A CLEAN POPULATION, not a paydown. It fires the moment a
    fourth instance appears, which is the moment the last three were introduced and nothing said
    so for a tick or more.
    """
    derivation = pyre.compile(r"^\s*(\w+)=\$\((.*(?:grep -c|wc -l|grep -h -c).*)\)")
    pattern = pyre.compile(r"grep(?: -\w+)* +'([^']+)'|grep(?: -\w+)* +\"([^\"]+)\"")
    # ⚑⚑ THE SWEEP'S CEILING CAUGHT THIS ARM, AS IT CAUGHT LAST TICK'S. Reading each script inside
    # the loop resolves to no NAME, so the sweep could not see this test and its own assertions
    # would have gone unswept — an arm about instruments disagreeing, invisible to the instrument
    # that checks arms. Naming the two files it also reads is the honest repair; raising the
    # ceiling from 23 to 24 would be the flattering one.
    gate = _GATE.read_text(encoding="utf-8")
    msghook = _MSGHOOK.read_text(encoding="utf-8")
    scripts = {p.name: p.read_text(encoding="utf-8") for p in sorted(_DIST.parent.glob("*.sh"))}
    scripts[".githooks/pre-commit"] = gate
    scripts[".githooks/commit-msg"] = msghook
    groups: dict[str, set[str]] = {}
    sites = 0
    for text in scripts.values():
        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                continue
            found = derivation.search(line)
            if not found:
                continue
            sites += 1
            # ⚑ ANNOTATED: `findall` returns `Any`, and this distribution ships `payload.py` with
            # nine warrants arguing that an untyped decoder result is a claim nothing checked.
            pairs: list[tuple[str, str]] = pattern.findall(found.group(2))
            for first, second in pairs:
                literal = first or second
                groups.setdefault(literal.lstrip("^").rstrip("$"), set()).add(literal)
    # ⚑ FLOOR ON THE POPULATION: a regex that stopped matching would make this vacuous in the
    # direction that reads as success — no derivations, no disagreement possible.
    assert sites >= _MIN_COUNTING_SITES, (
        f"only {sites} counting derivation(s) found; the population is wrong"
    )
    split = {subject: sorted(pats) for subject, pats in groups.items() if len(pats) > 1}
    assert not split, (
        "one quantity counted by two different predicates — they agree only while an accident "
        f"holds, which is how the last three of these were found: {split}"
    )


def test_the_sweeps_ceiling_falls_rather_than_standing() -> None:
    """⚑⚑⚑ A CEILING OVER A STATIC POPULATION IS FURNITURE WITH A NUMBER ATTACHED.

    Two ticks running, the ceiling caught a new arm at 24 and I recorded that as the ceiling
    earning itself. ⚑ MEASURED against every arm added since it shipped: **10 of 11 were
    resolvable as written.** The two it caught were caught in DRAFT, before commit. The ceiling
    is not under pressure from my authoring, and the story I was telling about it was wrong.

    ⚑⚑ THE 23 ARE A FIXED INHERITANCE, almost all from the founding commit. A ceiling over a
    population that neither grows nor shrinks reports the same number every run — `linux-sources`
    measured that a probe printing SIX gets read past for six consecutive ticks, and the operative
    property is CONSTANT rather than zero.

    ⚑ AND A BOUNDED EVALUATOR REACHES PART OF IT. Of the 12 unresolvable arms opening their file
    with a path expression, **4 are exactly `_CONST / "literal"`** — no arbitrary expressions, no
    parser this module should not grow. The remaining 8 divide by names or call results, and 6
    more read through a local variable. Those stay counted.

    ⚑⚑ SO THE CEILING FALLS BY MEASUREMENT RATHER THAN BY DECREE. It is asserted to be BELOW its
    former value, which is the property that distinguishes a ratchet paying down from a ratchet
    holding: a number that only ever holds is one nobody will read again.
    """
    # ⚑ THE CEILING MUST HAVE FALLEN. Asserting a value would fix today's answer; asserting the
    # DIRECTION keeps the constant honest as the evaluator reaches further.
    assert _MAX_UNRESOLVED < _MAX_UNRESOLVED_WAS, (
        f"the ceiling stands at {_MAX_UNRESOLVED}, unchanged from {_MAX_UNRESOLVED_WAS}; "
        "a ceiling over a static population is a constant nobody reads twice"
    )
    # ⚑ AND THE EVALUATOR MUST EXIST, or the fall came from lowering a number rather than from
    # resolving anything — the flattering repair this suite has declined twice.
    body = _THIS.read_text(encoding="utf-8")
    assert "_resolve_path" in body, (
        "the ceiling may only fall because more paths resolve, not because the number was edited"
    )


def test_the_sweep_states_the_share_of_arms_it_covers() -> None:
    """⚑⚑⚑ THE SWEEP COVERS A PREDICATE SHAPE, NOT ARMS, AND HAS NEVER SAID SO.

    Its floor counts ASSERTIONS — `_MIN_SWEPT = 50` — and its docstring says every assertion has a
    live positive by construction. Both true. ⚑ But I have read a green sweep as covering this
    module, and MEASURED it does not:

        arms in the module                          94
        read no file at all                         21
        read a file the sweep cannot resolve        17
        resolved, but assert no string membership    8
        resolved AND string-membership checked      48

    **48 of 94.** The 21 running subprocesses are correctly outside — there is no haystack to be
    absent from. The 8 resolved-but-unchecked assert by regex, count or parsed structure, which
    the sweep's predicate does not see.

    ⚑⚑ THIS IS NOT A DEFECT IN THE SWEEP AND NAMING IT AS ONE WOULD BE WRONG. A vacuity check for
    `"literal" in body` cannot check a regex without becoming a different tool. What was missing
    is the SCOPE STATEMENT: a coverage figure read as covering the whole is the mis-named
    population this session has measured eight times in its own checkers, and this is the ninth —
    in the arm built to enumerate the others.

    ⚑ AND LAST TICK'S GAIN WAS SMALLER THAN I RECORDED IT. Five arms became resolvable; **three of
    them carry zero string-membership assertions**, so sweeping them added nothing. The two that
    did carry assertions were checked and both resolve to their real subject. Clean, and worth
    one sentence rather than the sentence I wrote.
    """
    # ⚑⚑⚑ THIS ARM PASSED BEFORE ITS SUBJECT EXISTED, FOR THE FOURTH TIME IN THIS SUITE. Written
    # as a whole-file search it matched its own docstring, where both literals appear in prose
    # describing the fix. The repair is the one already used by the sibling arm above: read the
    # PARSED sweep function with its docstring node dropped, so a description cannot satisfy a
    # check about an instance.
    module = pyast.parse(_THIS.read_text(encoding="utf-8"))
    sweep = next(
        (n for n in pyast.walk(module)
         if isinstance(n, pyast.FunctionDef)
         and n.name == "test_no_string_assertion_in_this_module_is_vacuous"),
        None,
    )
    assert sweep is not None, "the sweep function was not found; this arm would pass on absence"
    statements = sweep.body[1:] if (
        sweep.body and isinstance(sweep.body[0], pyast.Expr)
        and isinstance(sweep.body[0].value, pyast.Constant)
    ) else sweep.body
    code = "\n".join(pyast.dump(n) for n in statements)
    # ⚑ THE SWEEP MUST STATE WHAT IT DOES NOT COVER. A floor over assertions with no statement of
    # the arm share reads as a floor over arms — which is what I read it as for six ticks.
    assert "_SWEEP_COVERS_ARMS" in code, (
        "the sweep's arm-share must be stated, or its assertion floor reads as arm coverage"
    )
    # ⚑ AND THE SHARE MUST BE DERIVED, not asserted: a written figure is the hand-written
    # population this module exists to refuse, one level in.
    assert "swept_arms" in code, (
        "the arm share must be counted by the sweep, not recorded as a constant"
    )


def test_the_brief_states_what_homing_grants_and_what_it_does_not() -> None:
    """⚑⚑⚑ FOUR CENSUSES ARE HOMED IN THIS TREE AND THE GRANT WAS NEVER WRITTEN DOWN.

    `rosettapkg` asked to home a fifth and split the ask in two: may the run file live here, and
    would this tree OWN the accounting. ⚑ They were right to split it, and right not to read the
    existing grant as covering a new run file — because there was no written grant to read. Four
    censuses landed here by precedent, and precedent is what a peer has to guess at.

    ⚑⚑ THE TWO PERMISSIONS ARE GENUINELY DIFFERENT AND THE BRIEF NOW SAYS SO. Hosting is this
    tree's to give: it is a path in this repository and the operator asked for findings homed
    rather than scattered. **Ownership of a census — the §S accounting, the freeze — is the
    OPERATOR's**, and a homing tree that assumed it would be deciding an ownership question by
    writing code, which is the one thing this session's standing instructions forbid.

    ⚑ A GRANT THAT LIVES IN A MESSAGE IS NOT A GRANT. This session has measured that a claim with
    no re-derivation procedure will not be re-checked however load-bearing it is; a permission
    with no written form is worse, because the next party to ask cannot find it and the one who
    does not ask cannot be refused.
    """
    brief = _BRIEF.read_text(encoding="utf-8")
    # ⚑ HOSTING IS GRANTED IN WRITING, so a peer need not ask a session that may not be running.
    assert "may host a run file" in brief, (
        "the brief must state the homing grant; precedent is what a peer has to guess at"
    )
    # ⚑ AND THE LIMIT IS STATED WITH IT. A grant whose boundary is unwritten reads as unlimited to
    # whoever needs it to be — the shape this repository refuses in its own gates.
    assert "does not transfer ownership" in brief, (
        "hosting and owning are different permissions; the brief must not let one imply the other"
    )


def test_the_poll_does_not_carry_a_self_raised_decision_as_blocked() -> None:
    """⚑⚑⚑ I CARRIED A DECISION TO THE OPERATOR THAT I HAD RAISED MYSELF, AND ANSWERED ALREADY.

    The operator asked *why are we concerned about cost?* — and there was no answer. ⚑ MEASURED:
    the only commit raising it is mine, `614163d`, and its own finding is that **no stable
    quantity exists**: four runs on an unchanged tree read 132s, 88s, 65s, 61s, converging as the
    action cache warmed while three checkers were ADDED. The measurement dissolved the question it
    was then listed under.

    ⚑⚑ AND NOTHING RECORDS A CONSEQUENCE. Searching the corpus for a refused commit, a bypass, or
    a complaint that the gate is unaffordable returns **none**. A decision with no consequence and
    no petitioner is not blocked on anyone — it is a measurement promoted to a standing ask, then
    re-derived every tick as though the promotion were a fact.

    ⚑ THE DEFECT IS THE PROMOTION, NOT THE FIGURE. `614163d` is a good measurement and its range —
    cold at least 132s, warm about 61s, stated with conditions — is the honest form. What was
    wrong is that *I measured something* became *the operator must decide something* with no step
    between where anyone asked.

    ⚑⚑ THE PROPERTY IS HELD IN THE POLL, NOT IN MY FILED LEG. `§D` forbids amending a filed leg
    and that leg is filed at `22e4ca1`; the correction belongs where the symbol is re-derived each
    tick, which is the only place it could have been caught.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ A CARRIED OPERATOR DECISION MUST NAME ITS PETITIONER. Without one, a measurement I
    # promoted and a request someone made are byte-identical in the symbol set — and one of them
    # is not blocked at all.
    assert "raised by" in commands, (
        "an operator decision the poll carries must name who raised it; a self-raised measurement "
        "promoted to a decision is indistinguishable from a request nobody made"
    )


def test_the_roster_count_derives_the_apex_row_rather_than_assuming_it() -> None:
    """⚑⚑⚑ `expected = |§R| - 1` WAS RIGHT FOUR TIMES AND WRONG THE FIRST TIME A PEER HOSTED HERE.

    ⚑ REPORTED BY `rosettapkg`, from outside, against my instrument: their §R holds eight parties
    and the poll read seven. They offered a candidate cause — a trailing `⚑` annotation on one row
    — and explicitly did not assert it. **Measured, the cause is different and worse.**

    ⚑⚑ THE SUBTRACTION IS A HARDCODED POPULATION ASSUMPTION. `remaining-work`'s §R carries an apex
    line that is not a surveying party, so the poll subtracts one — unconditionally. Measured
    across all six run files: **five carry an apex row and one does not**, and the one that does
    not is the first census hosted here by another dispatcher.

    ⚑ THE FOUR EARLIER CENSUSES MADE IT LOOK DERIVED. A constant that is correct for every file
    its author has seen is indistinguishable from a measurement until a file arrives from
    somewhere else — which is what `§13` now guarantees will keep happening.

    ⚑⚑ AND THE REPORTER DECLINED THE REPAIR THAT WOULD HAVE HIDDEN IT. They said so: editing their
    roster to satisfy the probe would have meant deleting a real party to make a green line. The
    file was right and the reader was short.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ THE APEX ROW MUST BE COUNTED, NOT ASSUMED. A literal `- 1` is a claim about every §R this
    # poll will ever read, made from the four its author had seen.
    assert "grep -ci apex" in commands, (
        "the apex row must be derived from the roster, not subtracted as a constant"
    )


def test_the_apex_probe_reads_a_column_rather_than_grepping_a_phrase() -> None:
    """⚑⚑⚑ THE ANNOUNCEMENT OF THE FIX IS HALF THE EVIDENCE THAT IT IS UNFIXED.

    The poll reported the apex slot unfilled while `§R` read `mtools`. ⚑ It keys on the phrase
    *named at the freeze*, which survives in every retrospective description of the state it
    names — including `§V` rev 32, **the row recording that the slot was filled**, which quotes
    the old wording to say it changed.

    ⚑⚑ SO THE SLOT COULD NOT BE OBSERVED AS FILLED WHILE ITS OWN `§V` ROW EXISTED. A probe whose
    needle is a phrase cannot distinguish a state from a report of that state, and a correction
    necessarily discusses what it corrected — this is `table_rows`' own `--starts` lesson, which
    exists because *a fix and its announcement necessarily discuss the thing being fixed, so a
    table used as an instrument ACCRETES MENTIONS OF ITS OWN TRIGGER.* The poll had that lesson
    available and did not apply it here.

    ⚑ REPORTED BY `rosettapkg`, who did not touch either file — `§R` is this tree's accounting and
    the poll is this tree's instrument. They also supplied the discriminator from their own tree:
    key on POSITION rather than wording, because a roster row's identity is its place in a table.
    Their ragged-row arm uses the same shape.

    ⚑⚑ AND MY OWN CLASSIFIER REPEATED THE POLL'S ERROR while verifying theirs: it labelled the
    `§V` row as a `§R` roster row because the line contains `AX-`. Two readers, one confusion,
    and the structural read settles it — the roster's `AX-` row reads `mtools`.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ THE PROBE MUST READ THE ROSTER ROW, not the file. `rows --col` names a position; a phrase
    # names a wording that every correction reproduces.
    assert "--col 1 --starts" in commands, (
        "the apex slot must be read by column position, not by grepping a phrase that survives "
        "in the record of its own removal"
    )


def test_asserted_comparisons_print_both_operands() -> None:
    """⚑⚑⚑ ANYWHERE A GATE ASSERTS AN EXPRESSION, IT MUST PRINT THAT EXPRESSION'S COMPONENTS.

    The poll's roster arm asserted `_elsewhere >= _gap` and printed only `_elsewhere`. A reader got
    a verdict with one operand invisible and no way to check the comparison that produced it — so
    when `_elsewhere` turned out to count the wrong population entirely, **the number on screen was
    never the number doing the work, and nothing on the line could reveal that.**

    ⚑⚑ MEASURED, AND THE MEASUREMENT IS THE ARGUMENT: the arm reported `13 surveyor(s)` against a
    roster of 8, then `11` after unrelated prose edits, because it counted lines-carrying-a-
    substring over a text range that included every paragraph explaining the mark. Both figures
    passed the comparison. **A count that moves when you edit prose is not counting surveyors**,
    and one printed operand could not show that while the other stayed hidden.

    ⚑ A PRINTED EXPRESSION IS A PROOF-CARRYING ARTIFACT — or a DISPROOF-carrying one, which is the
    half that earns it: a reader can falsify the claim from the line alone, without re-deriving
    anything or trusting the deriver. An asserted verdict with hidden operands can only be believed
    or doubted, and this corpus has measured what happens to claims that offer no third option.

    ⚑ THE ARM IS ABOUT THE SHAPE, NOT THIS ONE SITE. It requires that every branch which announces
    an accounting verdict names both sides of its comparison. A future arm added with a hidden
    operand fails here rather than three ticks later when its figure is absurd on its face.

    ⚑⚑ AND IT WAS ITSELF WRITTEN TOO SPECIFICALLY, WHICH THE NEXT REPAIR EXPOSED. It asserted the
    literal `$_elsewhere`, so when the left operand correctly became `$_accounted` — because a gap
    is not made of one state — **this arm failed on a change that strengthened its subject.** An arm
    that names a variable cannot outlive the variable, and it was asserting an IDENTIFIER where the
    rule is about a RELATION. It now derives both operand names from the `-ge` condition itself, so
    a rename passes and a hidden operand still fails.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the verdict lines this arm is about must still exist, or the assertions
    # below pass because the branch vanished rather than because it prints its operands.
    # ⚑ SPLIT, AND PT018 IS RIGHT FOR THIS ARM'S OWN REASON: a composite assertion reports that the
    # conjunction failed without saying WHICH conjunct — a verdict with a hidden operand, which is
    # the exact defect this arm exists to forbid. The checker caught me writing it here.
    assert "ACCOUNTED:" in commands, (
        "the accounted-for verdict must still be emitted; this arm would pass on its absence"
    )
    assert "DROPPED ROW:" in commands, (
        "the dropped-row verdict must still be emitted; this arm would pass on its absence"
    )
    # ⚑⚑⚑ THE OPERANDS ARE DERIVED FROM THE COMPARISON, NOT HARDCODED — and this arm learned that
    # by going red for the wrong reason. It asserted the literal `$_elsewhere`, so when the left
    # operand correctly became `$_accounted` (a gap is not made of one state), the arm failed on a
    # change that STRENGTHENED its subject. ⚑⚑ AN ARM THAT NAMES A VARIABLE CANNOT OUTLIVE THE
    # VARIABLE, and it was asserting an identifier where the rule is about a RELATION. Now it reads
    # the `-ge` condition, extracts whatever two operands the poll actually compares, and requires
    # both on the verdict lines — so the next rename passes and the next hidden operand still fails.
    # ⚑ THE COMPARISON, NOT THE LINE. A first attempt matched every `${_x:-0}` on the line and read
    # THREE operands, because the branch also carries `&& [ "${_accounted:-0}" -gt 0 ]`. Extracting
    # from the whole line answers "what variables appear near a comparison"; the rule is about the
    # comparison's own two sides.
    # ⚑⚑⚑ EVERY COMPARISON, NOT THE FIRST — AND THIS ARM WENT RED BY PAIRING THEM WRONG. `next()`
    # took comparison[0] and checked it against verdict-line[0], which was correct while the poll
    # held exactly one of each. A second verdict then landed — a census whose four prefixes match
    # nothing can still be adjudicated by its OWN declared states — and the arm compared the new
    # branch's operands against the OLD branch's line. It reported a hidden operand where both
    # lines were complete.
    # ⚑⚑ THAT IS THIS ARM COMMITTING THE DEFECT IT MEASURES, one level up: `next()` names a
    # population of one and says so nowhere, so a poll with two comparisons is read as a poll with
    # one. A count of 1 over a population of 2, arithmetically fine and about the wrong thing.
    # ⚑ SO EACH COMPARISON IS PAIRED WITH THE VERDICT IT GUARDS, by scanning forward from the
    # condition to the next verdict line rather than by index.
    lines = commands.splitlines()
    conds = [i for i, ln in enumerate(lines) if '" -ge "' in ln]
    assert conds, "the poll must still assert a `-ge` comparison; this arm needs one to read"
    checked = 0
    for at in conds:
        ge = pyre.search(r"\$\{(_\w+):-0\}\"\s+-ge\s+\"\$\{(_\w+):-0\}", lines[at])
        if ge is None:
            continue
        left, right = ge.group(1), ge.group(2)
        verdict = next(
            (ln for ln in lines[at:] if "ACCOUNTED" in ln or "DROPPED ROW:" in ln), None
        )
        assert verdict is not None, (
            f"the comparison `{left} >= {right}` guards no verdict line: {lines[at].strip()}"
        )
        for operand in (left, right):
            assert f"${operand}" in verdict, (
                f"the verdict asserts `{left} >= {right}` but does not print "
                f"its operand ${operand}: {verdict.strip()}"
            )
        checked += 1
    # ⚑ A FLOOR, so a regex that stopped matching cannot report zero failures vacuously.
    assert checked == len(conds), (
        f"{len(conds)} `-ge` comparison(s) in the poll and only {checked} were readable — an "
        "unread comparison is an unchecked one"
    )
    # ⚑ AND THE GAP IS PRINTED AS ITS OWN DERIVATION, so a reader can check the subtraction rather
    # than accept a difference. `roster` and `n_head` are the two facts it comes from.
    assert "$_gap = roster $roster - HEAD legs $n_head" in commands, (
        "the gap must be printed with the subtraction that produced it, not as a bare number"
    )


def test_roster_mark_is_read_from_a_cell_not_a_substring() -> None:
    """⚑⚑⚑ COUNT THE MARK IN A TABLE CELL, NEVER THE STRING IN A SECTION.

    The roster arm counted `filed elsewhere` with `grep -ciE` over a `sed` range and reported the
    result as `surveyor(s)`. It counted neither: it counted **lines carrying a substring**, over a
    range including the prose that explains the mark. `CENSUS-vfs.md` read 11 against a roster of
    8, and that file's own `§S` documents walking into the same trap twice *while writing the
    paragraph about it*.

    ⚑⚑ A TABLE USED AS AN INSTRUMENT ACCRETES MENTIONS OF ITS OWN TRIGGER — recorded at
    `mdstruct/src/mikemol/mdstruct/tables.py:137`, and `table_rows` carries the discriminator in
    its own docstring: *`--where` asks whether any cell MENTIONS a term, `--starts` asks whether
    one column DECLARES it.* **The right instrument existed, its documentation was written about
    this exact failure, and the arm used a text search anyway.**

    ⚑ FOUR PARTIES CONVERGED ON THE SAME REPAIR INDEPENDENTLY, from different corpora: a peer's
    conduit census scored ten of nineteen rows on prose in comments and string literals and
    repaired it by reaching the read through a Call node. Structure, not text, in both cases.

    ⚑⚑ AND THE PREFIX PREDICATE DISCOVERED SOMETHING THE SUBSTRING COULD NOT: the mark's wording is
    **not uniform across censuses**. One phrases it `filed (authored elsewhere ...)`, with the mark
    inside a parenthetical. A substring search cannot discover that its term has dialects, because
    every dialect satisfies it — so the poll now reports UNADJUDICATED rather than absorbing the
    difference into a count.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the roster diagnosis must still run, or every assertion below is vacuous.
    assert "§S DESCRIBES" in commands, (
        "the roster diagnosis must still be emitted; this arm would pass on its absence"
    )
    # ⚑ THE MARK IS READ AS A COLUMN DECLARATION.
    assert "--col 1 --starts 'filed elsewhere'" in commands, (
        "the roster mark must be counted as a column-1 declaration, not as a substring anywhere "
        "in the section — prose explaining the mark is not a surveyor"
    )
    # ⚑ NO SUBSTRING COUNT OF THE MARK SURVIVES ANYWHERE IN THE POLL.
    assert "grep -ciE 'filed elsewhere'" not in commands, (
        "a substring count of the roster mark counts the prose that explains it"
    )
    # ⚑ THE THIRD OUTCOME EXISTS. A reader that cannot settle the question must say so rather than
    # report a dropped row, which would be a statement about the reader dressed as a finding.
    assert "UNADJUDICATED:" in commands, (
        "a census whose mark this reader cannot parse must report UNADJUDICATED, not a dropped row"
    )


def test_the_roster_gap_is_compared_against_every_state_not_only_the_mark() -> None:
    """⚑⚑⚑ A GAP IS NOT MADE OF ONE STATE, AND THE ARM COUNTED AS IF IT WERE.

    `_gap` is every rostered party with no leg in the census's own directory — which includes
    parties that have not filed **anywhere**. A surveyor who accepted and has not yet written is
    PENDING. One who declined with a measured reason is TERMINAL. **Neither is a dropped row**, and
    the arm called both one because it compared the gap against `filed elsewhere` alone.

    ⚑⚑ MEASURED on `CENSUS-paperkit-use.md`: roster 8, legs in HEAD 0, gap 8, and the states are
    `4 filed + 2 pending + 1 declined + 1 not-yet = 8`. **Every rostered party carried a state that
    explained its absence, and the arm reported the one shape it exists to catch.**

    ⚑ THE PRECEDENT IS THIS SAME ARM'S `UNADJUDICATED` BRANCH, one axis over: calling a census this
    reader cannot parse a dropped row *reports the READER*. Calling a party who has not filed
    anywhere a dropped row **reports the CALENDAR**. Same three-state discipline, different axis.

    ⚑⚑ REPORTED BY `rosettapkg`, who verified before claiming a pattern — they cross-tabulated
    every census in this tree that rosters them against what their own HEAD holds, found ONE
    disagreeing row out of seven adjudicable, and handed over the row rather than a claim about the
    table's reliability. They did not touch `blockers.sh`.

    ⚑ AND THE STATES CANNOT BE SUMMED FROM A NAIVE PROBE: `--starts 'filed'` is a PREFIX of
    `filed elsewhere`. Measured — `--starts filed` returns 14 against a 12-row §S. The arm probes
    the states that are actually disjoint at the head of the cell.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the verdict branches must still exist, or every assertion below passes
    # because the arm vanished rather than because it improved.
    assert "ACCOUNTED:" in commands, (
        "the accounted verdict must still be emitted; this arm would pass on its absence"
    )
    assert "DROPPED ROW:" in commands, (
        "the dropped-row verdict must still be emitted; this arm would pass on its absence"
    )
    # ⚑ THE COMPARISON IS AGAINST THE UNION OF STATES, NOT THE MARK ALONE.
    assert '"${_accounted:-0}" -ge "${_gap:-0}"' in commands, (
        "the gap must be compared against every state that explains an absence, not against "
        "`filed elsewhere` alone — a pending or declined party is not a dropped row"
    )
    # ⚑ EACH STATE IS READ AS A COLUMN DECLARATION, so prose describing a state is not a party.
    for state in ("accepted", "scoped decline", "not yet filed"):
        assert f"--col 1 --starts '{state}'" in commands, (
            f"the {state!r} state must be counted as a column-1 declaration"
        )
    # ⚑ AND THE COMPOSITION IS PRINTED, so a reader can check the sum rather than accept a total.
    assert (
        "$_accounted = $_elsewhere filed + $_pending pending "
        "+ $_declined declined + $_notyet not-yet"
    ) in commands, (
        "the accounted total must be printed with the states that compose it, not as a bare number"
    )


def test_a_partitions_terms_and_total_come_from_different_measurements() -> None:
    """⚑⚑⚑ PRINTING THE TERMS DOES NOT SAVE A PARTITION WHOSE TERMS SHARE A SOURCE.

    The operator's rule — *anywhere you assert an expression, print that expression's components* —
    stops a HIDDEN operand. **It does not stop a partition whose terms are all zero because the
    same failed match produced every one of them.** Then the printed terms prove only that they
    agree with each other, and agreement among four readings of one failure is not evidence.

    ⚑⚑ THE BOUND IS `rosettapkg`'s, ON A RULE THEY HAD JUST TAKEN FROM ME, and they found it in
    their own instrument first: a figure line reading `0 of >=0`, which is **true of every
    population** — a claim that cannot be wrong wearing the shape of a clean result. The floor
    notation made it look deliberate, which is worse than a bare zero.

    ⚑⚑⚑ MEASURING IT HERE FOUND A SECOND DEFECT UNDERNEATH. On `CENSUS-build-hermeticity.md` all
    four state terms read 0 while `--starts 'filed'` returns **14 rows at rc=0** — the reader parses
    that file perfectly. Every `§S` row there says `filed`, a terminal state the four probes never
    enumerated **because they were built from the two censuses I happened to be reading.** A
    hand-written vocabulary, inside the arm written to repair a hand-written population.

    ⚑ SO THE TOTAL IS READ FROM THE TABLE rather than summed from the probes, and the remainder is
    printed. `§S`'s row count and the probes' classification are two measurements of one population;
    their difference is the only thing that can reveal a vocabulary this arm does not speak.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the partition must still be computed, or every assertion below passes
    # because the arm vanished rather than because it gained a second source.
    assert "_accounted=$((" in commands, (
        "the state partition must still be summed; this arm would pass on its absence"
    )
    # ⚑ THE TOTAL COMES FROM THE TABLE, NOT FROM THE TERMS.
    assert '_rows=$("$md" tables "$census"' in commands, (
        "the §S row count must be measured from the table itself — a total summed from the same "
        "probes that produced the terms cannot disagree with them"
    )
    # ⚑ AND THE REMAINDER IS PRINTED, so a vocabulary gap is visible rather than absorbed into 0.
    assert "carry a state these probes do not name" in commands, (
        "the rows the probes could not classify must be reported; absorbing them into a zero is "
        "what made four agreeing terms look like a measurement"
    )
    # ⚑ THE ALL-ZERO CASE IS ITS OWN VERDICT, ahead of the others, because it explains them.
    assert "UNCLASSIFIED:" in commands, (
        "a §S holding rows where none classified must say so rather than report a downstream "
        "figure that is 0 for that one reason"
    )


def test_an_unmatched_state_says_whether_the_census_declared_it() -> None:
    """⚑⚑⚑ FIVE OF EIGHT CENSUSES PUBLISH THEIR STATE VOCABULARY AND THIS ARM READ NONE OF THEM.

    The poll's four state prefixes were written by hand from the two files their author happened to
    be reading. **Measured, the declared union across the corpus is far wider** — `filed`,
    `not surveyed`, `retired`, `no response`, `DRAFTED`, `STAGED`, `declined`, `filed (rev n)` —
    each published by a census in its own `state | means` table.

    ⚑⚑ TWO OF THE UNSEEN STATES ARE LOAD-BEARING, AND ONE CENSUS SAYS SO IN ITS OWN TABLE.
    `not surveyed` is annotated there as *⚑⚑⚑ NO — and it READS as a zero. Nobody was asked.* An
    arm blind to it reports **the absence of a survey as the absence of a finding**, which is the
    single confusion this entire poll exists to refuse.

    ⚑⚑⚑ AND `filed` IS NOT ADDED TO THE PROBES, THOUGH IT WOULD TURN SEVEN UNNAMED ROWS GREEN.
    Measured: `--starts 'filed'` returns **8 of 8** on `remaining-work` because it also matches
    `filed elsewhere` — **one declared state is a prefix of another.** The declared states are not
    a partition and cannot be summed; doing so is the arithmetic that already read 14 against a
    12-row table. So the row count from the table stays the total, and what this adds is the
    DIAGNOSIS a residue needs to be actionable rather than a larger sum that is wrong in a new way.

    ⚑ THE DISCRIMINATOR IS WHETHER THE CENSUS PUBLISHED ANYTHING. An unmatched row in a census that
    DECLARES its states is *this reader failing to read a published list*; an unmatched row in one
    that declares nothing is *a state nobody wrote down*. Different repairs, and the arm could not
    tell them apart until it looked for the declaration.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the residue must still be computed, or the diagnosis below is attached
    # to nothing and this arm passes on the absence of its own subject.
    assert "_unmatched=$((" in commands, (
        "the unclassified residue must still be computed; this arm would pass on its absence"
    )
    # ⚑ THE DECLARATION IS LOOKED FOR, in the census rather than in this script.
    assert "'state | means'" in commands, (
        "the arm must detect whether the census publishes its own state vocabulary — a residue "
        "against a published list is a different fact from a residue against no list"
    )
    # ⚑ AND THE TWO CASES ARE REPORTED DIFFERENTLY.
    assert "the vocabulary is declared and unread" in commands, (
        "an unmatched row in a census that declares its states must say so; collapsing it with "
        "the undeclared case hides which repair is owed"
    )


def test_the_poll_reads_each_census_against_its_own_declared_vocabulary() -> None:
    """⚑⚑⚑ A SHIPPED MODE WITH NO CALLER IS THE PACKAGER NOT USING ITS OWN PACKAGE.

    The previous tick measured that five censuses publish a `state | means` table, reported that
    the poll read none of them, and shipped `mdstruct classify` to close it — **and then did not
    consume it.** One tick later the poll's output was byte-identical: same four hand-written
    prefixes, same residue. This repository has the named instance: a hook carrying 52 tests and 52
    warrants that `settings.json` invoked nowhere, its own docstring saying so while the suite
    stayed green.

    ⚑⚑ THE HAND-WRITTEN PROBES ARE KEPT, NOT REPLACED, AND THAT IS THE DESIGN. Three censuses
    publish no vocabulary at all, so a classifier refuses them while the prefixes still say
    something. Deleting the fallback would trade a blind spot for a hole — and the two readings
    answer different questions, so the poll prints **both** and reconciles neither.

    ⚑⚑⚑ WHERE THEY DISAGREE IS THE FINDING, and they do. Measured on one frozen census: the
    prefixes report *12 rows carry a state these probes do not name* while the document's own
    vocabulary names **11 of those 12**. The residue of one is a row using a state the census
    never declared — which only the document-relative reading can reveal, and which the
    reader-relative line reports as its own blindness.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the reader-relative residue must still be reported, or this arm passes
    # because the pair collapsed to one reading rather than because both are printed.
    assert "carry a state these probes do not name" in commands, (
        "the reader-relative residue must still be emitted; this arm would pass on its absence"
    )
    # ⚑ THE MODE IS ACTUALLY INVOKED, not merely available.
    assert '"$md" classify "$census"' in commands, (
        "the poll must read each census against the vocabulary that census publishes — a mode "
        "with no caller is a component whose own packager does not use it"
    )
    # ⚑ AND THE DOCUMENT-RELATIVE READING IS PRINTED BESIDE THE READER-RELATIVE ONE.
    # ⚑⚑ THE LITERAL MOVED WHEN THE READING WAS LIFTED OUT OF THE DIVERGENCE BRANCH: the phrase
    # `declared:` became `§S vocabulary:` and the emission now runs for every census rather than
    # only the diverging ones. **The behaviour this arm asserts was strengthened and its string
    # changed**, so it went red on an improvement — the correct direction, and caught twice in one
    # run, here and by the vacuity sweep reporting the literal absent from the file this arm reads.
    assert "§S vocabulary:" in commands, (
        "the document-relative count must be printed; where it disagrees with the probes is the "
        "only place a state used-but-never-declared can show up"
    )
    # ⚑ A CENSUS THAT PUBLISHES NOTHING IS SAID SO, rather than reported as a residue of zero.
    assert "publishes no state|means table" in commands, (
        "a census with no vocabulary cannot be read against one, and that is a fact about the "
        "document rather than a clean result"
    )


def test_the_vocabulary_reading_is_not_gated_on_the_divergence_branch() -> None:
    """⚑⚑⚑ A CENSUS CAN AGREE ON TOTALS AND STILL USE A STATE IT NEVER DECLARED.

    The vocabulary reading was emitted inside the branch that fires when `§S` and HEAD DISAGREE.
    That is right for a divergence diagnosis and wrong for a classification: they are independent
    questions that happened to share a branch. **`CENSUS-deps-build.md` has 7 rostered and 7 legs
    in HEAD, so it agrees, so the whole block was skipped** — and that census printed no reading and
    no refusal, leaving a reader unable to tell a clean census from an unreached one.

    ⚑⚑ I NAMED THE WRONG CAUSE FOR A TICK AND THE SYMBOL SURVIVED ON IT. The carried finding said
    the §S table-finder missed `party | status | evidence`, and it did — that is repaired here too,
    as a measured predicate rather than a longer list. **But the finder was never why deps-build
    was silent**, and fixing it alone would have left the silence while reading as a repair.

    ⚑ THE FINDER IS NOW A PREDICATE: column 0 names a party, column 1 names a state, anything after
    is description. Measured against all 25 distinct table headers in the corpus, two-armed, 12 of
    12. The false-positive arm earned the boundary — `surveyor | prefix | file` and `party | the
    hole | resolution` both open with a party word and are NOT status tables, so a widened list
    would have classified a roster against a state vocabulary.

    ⚑⚑ AND `party | state at freeze` IS REFUSED DELIBERATELY. My first expectation listed it as a
    table to take; the predicate was right to leave it. It is §G's freeze summary, which the poll's
    own prose calls a summary of §S rather than a second roster — taking both would make the
    last-match rule a coin-flip between two tables answering different questions.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the divergence diagnosis must still exist, or this arm passes because the
    # branch vanished rather than because the reading was lifted out of it.
    assert "§S DESCRIBES" in commands, (
        "the divergence diagnosis must still be emitted; this arm would pass on its absence"
    )
    # ⚑ THE READING IS EMITTED UNCONDITIONALLY FOR ANY CENSUS WITH A §S.
    assert "§S vocabulary:" in commands, (
        "the vocabulary reading must run for every census with a §S, not only diverging ones"
    )
    # ⚑ THE FINDER IS A PREDICATE OVER TWO COLUMNS, not an enumeration of header spellings.
    # ⚑⚑ THE NOUN CLASS HERE WAS `(surveyor|party)` AND THE SIBLING SITE'S WAS
    # `(party|surveyor|repo|leg)` — one predicate, two spellings, and TWO TESTS EACH PINNING ITS
    # OWN SITE. Neither could see the divergence, because each was correct about the site it read.
    # That is why `test_every_status_table_finder_uses_one_signature` asserts over the SET of
    # spellings rather than the presence of any one: a per-site literal is exactly the shape that
    # let four finders drift into two rules while every arm stayed green.
    assert "(party|surveyor|repo|leg) \\| (status|state)( \\||$)" in commands, (
        "the §S table must be found by shape — a party column then a state column — rather than "
        "by a hand-written list of header spellings that misses the next census"
    )
    # ⚑ AND THE NO-VOCABULARY CASE STILL SPEAKS, so silence never stands for either answer.
    assert "publishes no state|means table" in commands, (
        "a census with no vocabulary must say so; a census that prints nothing is "
        "indistinguishable from one this reader never reached"
    )


def test_the_witness_reads_bazels_artifact_not_its_exit_status() -> None:
    """⚑⚑⚑ AN EXIT STATUS IS NOT A VERDICT ABOUT THE SUBJECT, AND THE WITNESS SAID SO TWICE.

    `domain_witness.sh` carries two comments warning that a reporter's status must not stand in for
    the subject's — one about SIGPIPE closing a pipe so bazel's death becomes the verdict, one about
    a wrapper reporting itself — **and then read `bazel test`'s exit code as the target's health.**

    ⚑⚑ IT REFUSED A CORRECT COMMIT. Six targets reported `CONTROL FAILED: red BEFORE the probe`
    while `bazel test` printed `1 test passes` and `Build completed successfully`. Bazel exited
    **38** because its Build Event Protocol upload failed: a peer measured that the buildbuddy
    Service object had been deleted after the node hit DiskPressure and evicted 57 pods. **The sink
    was gone and the tests were green.**

    ⚑ REPRODUCED DELIBERATELY rather than inferred — `--bes_backend=grpc://127.0.0.1:1` over a
    passing target gives rc=38 with `Executed 0 out of 1 test: 1 test passes`.

    ⚑⚑⚑ AND THE FIRST FIX WAS WRONG IN THE DIRECTION THAT HIDES DEFECTS. It asked whether a FAILURE
    line was present and called its absence green; the second arm refuted it in one run.
    `bazel test //hooks:no_such_target` exits 1 and prints `ERROR: no such target` with **no
    `Exit N`, no `BUILD FAILURE`, no `FAILED in`** — so a missing target read as CLEAN. The
    predicate is therefore POSITIVE: bazel must SAY it succeeded and print a test tally. Three arms,
    3 of 3: dead sink → green, nonexistent target → red, working sink → green.

    ⚑ NOT KEYED ON 38, DELIBERATELY. Keying on the number would make the next infrastructure code a
    false red, and this witness can no more enumerate bazel's exit codes than an arm here could
    enumerate a census's state vocabulary. **The artifact is the population.**
    """
    body = _WITNESS.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the control gate must still exist, or this arm passes because the check
    # was deleted rather than because it reads the right thing.
    assert "CONTROL FAILED" in commands, (
        "the pre-probe control must still be emitted; this arm would pass on its absence"
    )
    # ⚑ THE VERDICT COMES FROM WHAT BAZEL SAID.
    assert "Build completed successfully" in commands, (
        "green must require bazel's own success line — a nonzero status with no failure reported "
        "is an infrastructure fault, not a red target"
    )
    # ⚑ AND FROM A TEST TALLY, so a build that succeeds while running no tests is not green.
    assert "test passes" in commands, (
        "green must also require a test tally; a successful build that ran nothing is not a "
        "passing suite"
    )
    # ⚑ NO DECISION SITE READS THE BARE STATUS ANY MORE.
    assert 'bazel test "$target" >/dev/null 2>&1' not in commands, (
        "no decision may rest on bazel's exit status alone — that is the defect this file's own "
        "comments warn about twice, committed in the code between them"
    )


def test_no_conventional_under_declaration_survives_in_this_tree() -> None:
    """⚑⚑⚑ THE ONLY LIVE CAS RISK IS AN OMISSION SEVERAL REPOSITORIES MAKE IDENTICALLY.

    Operator ruling: *there is no false green risk if the cache keys are constructed properly, and
    if they are not constructed properly the risk does not depend on peers to cause the collision.*
    A shared cache introduces no failure mode that correct keying does not already prevent, and
    none that incorrect keying would not produce in isolation — **cache sharing is not the
    variable, key construction is.**

    ⚑⚑ WHICH LOCATES THE RESIDUAL RISK PRECISELY. Poisoning needs BOTH parties' keys improper in
    the SAME WAY: an under-declaring producer computes a key describing that narrower action, and a
    consumer receives the entry only by making the same omission. So idiosyncratic sloppiness is
    harmless — it produces keys nobody else computes — and **a SHARED HABIT is the only thing that
    collides.** Undeclared host tools, `$HOME` reads, `__file__` escaping the runfiles tree.

    ⚑⚑⚑ AND THE FIRST AUDIT PROBE WAS BLIND IN EXACTLY THE WAY IT WAS AUDITING FOR. It reported
    three `__file__.resolve()` sites; **all three were COMMENTS explaining why not to write one.**
    A corpus containing prose about itself must strip the prose before measuring — recorded at
    `mdstruct/src/mikemol/mdstruct/tables.py:137` — and the probe written to find blind spots
    matched its own documentation. Re-measured through the AST: **0 live call sites**, with a
    control confirming the reader finds `.resolve()` calls at all.

    ⚑ SAME SHAPE ON THE HOST-TOOL ARM. `pandoc` appeared to be invoked from three `hooks/` files
    while only `mdstruct/BUILD.bazel` declares `@pandoc//:bin`. Read: two are prose and one is a
    test fixture string. `hooks` never runs it.
    """
    src = _THIS.read_text(encoding="utf-8")
    # ⚑ THE READ IS THROUGH THE AST, so a comment about the pattern is not an instance of it.
    tree = pyast.parse(src)
    live = [
        node.lineno
        for node in pyast.walk(tree)
        if isinstance(node, pyast.Call)
        and isinstance(node.func, pyast.Attribute)
        and node.func.attr == "resolve"
        and any(isinstance(c, pyast.Name) and c.id == "__file__"
                for c in pyast.walk(node.func.value))
    ]
    # ⚑ POSITIVE CONTROL: the reader must find `.resolve()` calls of SOME kind here, or its zero
    # above is a statement about the reader rather than about the file.
    any_resolve = [
        node.lineno
        for node in pyast.walk(tree)
        if isinstance(node, pyast.Call)
        and isinstance(node.func, pyast.Attribute)
        and node.func.attr == "resolve"
    ]
    assert any_resolve, (
        "the AST reader found no `.resolve()` call of any kind — its zero for the escaping form "
        "would be a fact about the reader, not about this module"
    )
    assert not live, (
        f"`__file__`.resolve() escapes the runfiles tree back to the working copy; live at "
        f"line(s) {live}"
    )


def test_every_warrant_check_resolves_to_a_test_that_exists() -> None:
    """⚑⚑⚑ COUNTING IS A DIFFERENT PREDICATE FROM RESOLVING, AND 55 CHECKS ACCUMULATED IN THE GAP.

    This distribution's warrants are 1:1 with its test functions, verified on every commit by the
    section-vs-rubric diff. **That ratio stayed green while 55 claims carried a `check` naming a
    runner that does not exist** — `check = {pytest tests/x.py -k y}` where `paper.toml` declares
    exactly one runner, `[checks.cmd]`, addressed by a `cmd:` prefix.

    ⚑⚑ ALL 55 WERE WRITTEN BY ONE SESSION, ONE PER TICK, each beside a real arm that passes. The
    arm was sound and the ADDRESS was unresolvable, and nothing here could tell: no tool in this
    tree parses a check field, because the tool that would is paperkit and paperkit is not
    installed. **The warrant-to-test ratio was verified continuously while the checks'
    executability was never verified at all.**

    ⚑ NAMED `UNRUNNABLE-ADDRESS` AND ACCEPTED INTO `CENSUS-paperkit-use` §Q-3 by its dispatcher, as
    a mechanism wider than the four that census listed: those all assume the check RESOLVES and
    asks the wrong question. This is the case where resolution never happens and no arm notices.

    ⚑⚑⚑ SO THIS ARM RESOLVES RATHER THAN COUNTS. For every check it reads the module it names and
    parses it, then requires the named function to be defined there. A check whose module is absent,
    or whose `-k` names nothing in that module, fails here — which is the predicate a ratio cannot
    express.
    """
    checks = pyre.compile(r"check\s*=\s*\{cmd:[^}]*?-m pytest\s+(\S+)\s+-k\s+([A-Za-z0-9_]+)\}")
    body = (_DIST / "warrants.bib").read_text(encoding="utf-8")
    # ⚑ `findall` IS TYPED `list[Any]`, so the pairs are named explicitly rather than carried
    # untyped into the loop — this distribution forbids an `Any` expression, and a resolver whose
    # own operands are untyped is a poor advertisement for resolving over counting.
    hits: list[tuple[str, str]] = [
        (m.group(1), m.group(2)) for m in checks.finditer(body)
    ]
    # ⚑ POSITIVE CONTROL: the reader must find checks at all, or its zero failures below is a
    # statement about the regex rather than about the corpus.
    assert len(hits) >= _MIN_RESOLVABLE_CHECKS, (
        f"only {len(hits)} check(s) parsed from warrants.bib; the resolver is reading the wrong "
        f"shape and every verdict below would be vacuous"
    )
    known: dict[str, set[str]] = {}
    unresolved: list[str] = []
    for module, func in hits:
        if module not in known:
            path = _DIST / module
            if not path.is_file():
                unresolved.append(f"{module} does not exist (-k {func})")
                known[module] = set()
                continue
            known[module] = {
                n.name
                for n in pyast.walk(pyast.parse(path.read_text(encoding="utf-8")))
                if isinstance(n, pyast.FunctionDef)
            }
        if known[module] and func not in known[module]:
            unresolved.append(f"{module} defines no {func}")
    assert not unresolved, (
        "warrant check(s) address a test that does not exist — the 1:1 count cannot see this:\n  "
        + "\n  ".join(unresolved)
    )


@_needs_reader
def test_a_census_this_repo_hosts_declares_the_vocabulary_its_own_status_uses() -> None:
    """⚑⚑⚑ THE POLL READ `8 filed + 0 pending` OVER A TABLE WHERE ONLY TWO PARTIES HAD FILED.

    `CENSUS-vfs.md` §S marked all eight rows `filed elsewhere`, the poll counted eight marks, and
    the count was arithmetically perfect over the WRONG POPULATION: five of those rows read *filed
    elsewhere when it files — no leg yet*, which names a DESTINATION, not a state. The mark says
    where a leg would go; it does not say one exists. §S's own prose argued exactly this
    distinction two paragraphs above the table — *the destination and the state, said separately* —
    and the table then encoded both into one phrase the reader-relative probe matches.

    ⚑⚑ A `state | means` TABLE IS WHAT MAKES THE DISTINCTION MACHINE-READABLE, and this census
    published none. The poll reports that honestly (*this census publishes no state|means table*),
    which is a statement about the READER; the defect is in the DOCUMENT, and only the host can fix
    it. mtools hosts this file, so this is mtools' arm and not a peer's.

    ⚑ KEYED ON THE PREDICATE, NOT ON A FILENAME. The population is every census whose §R marks
    mtools as `hosts this file` — so a census this repo hosts LATER is covered on the day it is
    created, and a hardcoded name would be the mis-named population one layer up.
    """
    hosted = [
        path
        for path in sorted((_DIST.parent / "findings").glob("CENSUS-*.md"))
        if "hosts this file" in path.read_text(encoding="utf-8")
    ]
    # ⚑ POSITIVE CONTROL: an empty population would pass this arm vacuously, and the predicate
    # is a phrase a future edit could reword. Assert the population is non-empty and name it.
    assert hosted, (
        "no census in findings/ marks a host — either mtools hosts none (then this arm is "
        "vacuous and should be deleted) or the `hosts this file` phrase was reworded"
    )
    undeclared = []
    for path in hosted:
        # ⚑ THE READER IS THE SAME BINARY THE POLL RUNS, invoked the way the poll invokes it.
        # `hooks` cannot import `mdstruct` — they are separate distributions, and that separation
        # is what makes the subprocess the honest read rather than a workaround.
        # ⚑ `noqa`, NOT A CONFIG ENTRY, AND THAT IS THIS FILE'S CONVENTION RATHER THAN A LAPSE.
        # Three sibling modules declare `S603` in `per-file-ignores` because their whole subject is
        # running an installed binary. This file is not one of them: eleven of its calls carry a
        # line directive and the rest are ordinary code, so a whole-file entry would clear eleven
        # suppressions the ratchet is currently holding as keys.
        proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the reader is the subject of this case
            [str(_CITATION_GATE_READER), "tables", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            f"the reader failed on {path.name} (rc={proc.returncode}) — a reader that did not "
            f"run cannot report an absence:\n{proc.stderr}"
        )
        if not pyre.search(r"state \| means", proc.stdout):
            undeclared.append(path.name)
    assert not undeclared, (
        f"{len(undeclared)} of {len(hosted)} census(es) this repo HOSTS publish no `state | means` "
        "table, so their §S cannot be read against their own declarations and a mark that names a "
        "destination is indistinguishable from one that names a filed leg:\n  "
        + "\n  ".join(undeclared)
    )


def test_the_classifiers_count_is_printed_and_not_merely_computed() -> None:
    """⚑⚑⚑ THE CLASSIFIER'S READING WAS MEASURED, ASSIGNED TO A VARIABLE, AND NEVER PRINTED.

    `_cls_named` and `_cls_residue` are computed for every census whose §S is found — the
    document-relative classification, against the states that census itself declares — and only a
    conditional POINTER to re-run the tool by hand is emitted. The four hand-written prefix terms
    are what a reader actually sees.

    ⚑⚑ AND THAT IS THE EXACT DEFECT THE SURROUNDING COMMENT NAMES, one level in. The block argues
    that shipping `classify` and not consuming it is *the packager is not a user of its own
    package*; the wiring was then added, and the wired value is discarded before the report. **A
    computed value nothing prints is a caller that does not consume its own call.** Measured this
    tick on three censuses at once: `vfs` and `build-hermeticity` both print `states: 0 = 0 + 0 +
    0 + 0` over §S tables of 8 and 12 rows, while `§S vocabulary:` — the one line that does read
    the document — reports 8 of 8 and 11 of 12 matching.

    ⚑⚑⚑ THE FOUR ZEROS ARE NOT FOUR MEASUREMENTS. They are one failed match reported four times,
    which is the partition rule this poll already carries and which printing the operands cannot
    save: the terms share a source. The classifier's count is the second source, it is already in
    hand, and the report withholds it.

    ⚑ THE HAND-WRITTEN PREFIXES STAY. Three censuses publish no vocabulary, so the classifier
    refuses them while the prefixes still say something — the two readings answer different
    questions and the poll's own design prints both rather than reconciling them. This arm adds
    the missing half of that pair; it does not remove the half that is there.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the classifier must still be CALLED, or this arm passes because the
    # second reading was deleted rather than because its result reached the reader.
    assert 'classify "$census"' in commands, (
        "the document-relative classification must still be measured; this arm would pass on "
        "its absence"
    )
    # ⚑⚑ AND THE COUNT MUST REACH AN `echo`. A variable assigned and never emitted is invisible
    # to every reader of the poll, which is the only interface this script has.
    # ⚑⚑⚑ THIS ARM ONCE NAMED THE VARIABLE `_cls_named` AND THAT WAS THE WEAKER ASSERTION. The
    # emission it guarded sat inside the divergence branch, so the arm passed while two censuses
    # printed nothing — it required the value to reach AN echo, and an unreachable echo is one.
    # The property wanted is that a SECOND SOURCE is reported, whatever variable carries it;
    # reachability is asserted structurally by the sibling arm.
    # ⚑ THE CONTINUATION IS PART OF THE STATEMENT. This poll wraps its `echo`s with `\`, so the
    # reported text routinely sits on the line AFTER the verb — an arm keyed on a line STARTING
    # with `echo` reads the script's line breaks rather than its statements, which is the same
    # header-versus-body error this file records about table readers. Joined first.
    joined = commands.replace("\\\n", " ")
    assert any(
        "SECOND source" in ln and "echo" in ln for ln in joined.splitlines()
    ), (
        "no echo reports a second source — a reader then sees only the four hand-written prefix "
        "terms, which is the partition whose terms share one query"
    )


def test_the_second_source_is_not_gated_on_the_divergence_branch() -> None:
    """⚑⚑⚑ THE SAME GATING DEFECT, IN THE FIX FOR THE SAME GATING DEFECT, ONE TICK LATER.

    `test_the_vocabulary_reading_is_not_gated_on_the_divergence_branch` exists because the
    document-relative reading sat inside the `n_head -ne roster` branch, so a census whose §S and
    HEAD AGREE printed nothing — neither a reading nor a refusal. That was repaired by hoisting the
    `§S vocabulary:` line out of the branch. **The `declared:` second source was then added INSIDE
    that same branch**, reproducing the defect the sibling arm was written to prevent, in the
    script it was written about.

    ⚑⚑ MEASURED: `CENSUS-deps-build.md` (7 rostered, 7 legs) and `CENSUS-constitution.md` agree on
    totals, so the block is skipped and neither prints a `declared:` line. The four censuses that
    DO print one are exactly the four that diverge — which reads as a property of those censuses
    and is a property of the branch.

    ⚑⚑⚑ AND I NAMED THE WRONG CAUSE FOR THIS SILENCE FOR THE SECOND TIME. Last tick's symbol said
    the §S table-finder does not match `party | status | evidence`. **Measured against the finder's
    own predicate, it matches** — the finder was never why deps-build was silent, and the sibling
    arm's docstring already records that exact misdiagnosis from the tick before. A recorded lesson
    is not an applied one, measured here in the file that records it.

    ⚑ SO THE ASSERTION IS STRUCTURAL, NOT TEXTUAL. Requiring the string to appear somewhere is what
    let the regression through: the previous arm asserted the value reaches AN echo, and it did —
    an unreachable one. This one requires the emitting line to sit outside the divergence branch,
    which is the property that was actually wanted both times.
    """
    body = _POLL.read_text(encoding="utf-8")
    lines = body.splitlines()
    # ⚑ POSITIVE CONTROL: the branch this arm reasons about must still exist, or the assertion
    # passes because the structure changed rather than because the line was hoisted.
    branch = [i for i, ln in enumerate(lines) if '"${n_head:-0}" -ne "${roster:-0}"' in ln]
    assert len(branch) == 1, (
        f"the divergence branch must exist exactly once to anchor this arm; found {len(branch)}"
    )
    # ⚑ THE EMISSION IS FOUND BY ITS TEXT, NOT BY THE VERB'S LINE. This poll wraps `echo`s with
    # `\`, so the reported string sits on the line after the verb; keying on a line that STARTS
    # with `echo` would read the script's line breaks rather than its statements. The line index
    # of the text is what the branch comparison needs, and it is bounded by the same statement.
    # ⚑ COMMENTS EXCLUDED, or the arm passes on a comment that merely MENTIONS the phrase — the
    # accreting-mentions defect this repository has measured in its own table reader.
    emit = [
        i
        for i, ln in enumerate(lines)
        if "SECOND source" in ln and not ln.lstrip().startswith("#")
    ]
    assert emit, "the second source must still be emitted; this arm would pass on its absence"
    # ⚑ EVERY EMISSION OF IT MUST SIT BELOW THE BRANCH, not merely one of them. Asserting that
    # SOME line is reachable is what let the regression through: the previous arm required the
    # value to reach AN echo, and it did — an unreachable one.
    assert min(emit) > branch[0], (
        f"a second-source emission (line {min(emit) + 1}) sits inside the divergence branch "
        f"(line {branch[0] + 1}) — a census whose §S and HEAD agree then prints neither a "
        "reading nor a refusal, which is absence-versus-unavailable in the accounting itself"
    )
    # ⚑ AND THE REFUSAL PATH CARRIES IT TOO. A census with no vocabulary must say that the prefix
    # terms are then the only reading; otherwise a reader takes four agreeing zeros as evidence.
    assert any(
        "ONLY reading" in ln and "share one source" in ln for ln in lines
    ), (
        "the no-vocabulary path must say the prefix terms are the only reading and share one "
        "source — a refusal that does not say what remains leaves the zeros looking corroborated"
    )


def test_the_gap_verdict_uses_the_declared_vocabulary_when_the_prefixes_cannot() -> None:
    """⚑⚑⚑ TWO CENSUSES REACH NO VERDICT AT ALL WHILE THEIR OWN VOCABULARY ANSWERS PERFECTLY.

    `CENSUS-vfs.md` and `CENSUS-build-hermeticity.md` both print `states: 0 = 0 + 0 + 0 + 0` over
    §S tables of 8 and 12 rows, so the arm takes the UNCLASSIFIED branch and correctly refuses to
    call the zeros a finding. **Three lines below, the document-relative reading partitions the
    same rows without residue** — vfs classifies 3 `filed` + 5 `no leg yet` = 8, exactly its
    roster.

    ⚑⚑ THE PREFIXES ARE THE LAST HAND-WRITTEN POPULATION IN THIS POLL, and their provenance is the
    defect: they were written from the two censuses their author happened to be reading. This
    session then REWROTE `CENSUS-vfs.md`'s §S to say `filed` / `no leg yet`, and the prefixes —
    `filed elsewhere`, `accepted`, `scoped decline`, `not yet filed` — matched none of it. **A
    hand-written vocabulary made stale by its own author's edit, in the arm built to catch stale
    hand-written vocabularies.**

    ⚑ THE VERDICT NEEDS A COUNT OF ROWS THAT EXPLAIN AN ABSENT LEG, not those four words. The
    classifier already produces that per state, from the census's own declarations, so a census
    whose vocabulary partitions its §S can be adjudicated rather than refused.

    ⚑ AND THE UNCLASSIFIED BRANCH STAYS. Three censuses publish no vocabulary at all, so the
    classifier refuses them while the prefixes still say something — the branch remains the honest
    answer for exactly those, which is why this arm requires it to survive.
    """
    body = _POLL.read_text(encoding="utf-8")
    lines = body.splitlines()
    commands = "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))
    # ⚑ POSITIVE CONTROL: the refusal branch must still exist. A repair that adjudicated every
    # census by deleting the refusal would trade a blind spot for a false verdict, which is the
    # trade this poll's own comments refuse three times over.
    assert "UNCLASSIFIED:" in commands, (
        "the refusal branch must survive — three censuses publish no vocabulary, and a reader "
        "that adjudicates them anyway reports itself rather than the file"
    )
    # ⚑ THE VERDICT MUST HAVE A SECOND WAY TO REACH `_accounted`. Asserting only that the
    # classifier is called would pass on the call it already makes for the residue pointer.
    assert "_cls_accounted" in commands, (
        "the gap verdict must be able to draw its accounting from the census's own declared "
        "states; with only the four prefixes, a census that renames its states reaches no verdict"
    )
    # ⚑ AND THE SOURCE OF THE FIGURE MUST BE SAID OUT LOUD IN THE REPORT. A verdict that silently
    # switches instruments is two measurements printed under one label — the manufactured
    # corroboration this poll already refuses elsewhere.
    joined = commands.replace("\\\n", " ")
    assert any(
        "declared states" in ln and "echo" in ln for ln in joined.splitlines()
    ), (
        "when the verdict comes from the declared vocabulary rather than the prefixes, the line "
        "must say so — otherwise one label carries two different measurements"
    )


@_needs_reader
def test_every_census_declares_every_state_its_own_status_rows_use() -> None:
    """⚑⚑⚑ TWO FROZEN CENSUSES USED A STATE THEIR VOCABULARY NEVER DECLARED, AND BOTH WERE RIGHT.

    `CENSUS-remaining-work.md` carried `substrate | filed elsewhere (rev 5)` against a vocabulary
    declaring only `filed (rev n)` — *in THIS HEAD, verified there*. Substrate's leg is in
    substrate's own tree, so the row is accurate and the state is real. `CENSUS-build-hermeticity`
    carried `paperkit | written and UNTRACKED — not no response`, whose cell says outright which
    declared state it is NOT: its author knew none fitted and wrote the negation into the row.

    ⚑⚑ NEITHER IS A DEFECT IN A ROW. Both are the vocabulary being narrower than the fleet's
    actual states — a domain the census partitioned correctly until a case arrived it could not
    express. `filed` and `filed elsewhere` were one cell until a leg landed in another party's
    tree; `filed` and `written but untracked` were one cell until a leg existed on disk and not in
    HEAD.

    ⚑ AND THE PREFIX RULE IS WHY NEITHER FALLS BACK. `filed (rev n)` is not a prefix of `filed
    elsewhere (rev 5)`: the stem `filed` continues with a WORD, which the classifier treats as
    ambiguous rather than as a match. That refusal is correct — silently reading the longer state
    as the shorter one would report a leg in another tree as a leg in this one.

    ⚑ THE ROWS ARE UNTOUCHED, BY OPERATOR RULING, AND THIS ARM PINS THAT. §D forbids amending a
    frozen census; the ruling permits the vocabulary alone, so no filing status moves and no
    accounting changes. An arm asserting only that the residue reached zero would pass if a future
    reader "fixed" a row to match the vocabulary — which is the amendment §D exists to prevent.
    """
    censuses = sorted((_DIST.parent / "findings").glob("CENSUS-*.md"))
    assert censuses, "no censuses found — this arm would pass vacuously"
    unnamed: list[str] = []
    checked = 0
    for path in censuses:
        # ⚑⚑⚑ SCOPED TO THE STATUS TABLE, AND UNSCOPED WOULD BE THE WRONG POPULATION. A peer
        # measured that `classify` walks EVERY table, so an unscoped read counts revision-log and
        # roster rows as residue — 25 of 33 on one census, which reads alarming and is not. The
        # status table is found the way the poll finds it: a header naming a party and a state.
        listing = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the reader is the subject of this case
            [str(_CITATION_GATE_READER), "tables", str(path)],
            capture_output=True, text=True, check=False,
        )
        assert listing.returncode == 0, (
            f"could not list tables in {path.name} (rc={listing.returncode}): {listing.stderr}"
        )
        shaped = pyre.compile(
            r"\s*table (\d+)\s.*(?:surveyor|party) \| (?:status|state)(?: \||$)"
        )
        status = [
            m.group(1)
            for ln in listing.stdout.splitlines()
            if (m := shaped.match(ln))
        ]
        if not status:
            continue
        proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the reader is the subject of this case
            [str(_CITATION_GATE_READER), "classify", str(path), "--table", status[-1]],
            capture_output=True,
            text=True,
            check=False,
        )
        # ⚑ rc=2 IS A REFUSAL, NOT A FAILURE: a census publishing no vocabulary cannot be read
        # against one. Three do, and counting them as residue would report this reader.
        if proc.returncode == _ARG_REFUSED:
            continue
        assert proc.returncode == 0, (
            f"the reader failed on {path.name} (rc={proc.returncode}): {proc.stderr}"
        )
        checked += 1
        # ⚑ THE RESIDUE LINE ITSELF, NOT A POSITION. A first cut took `splitlines()[1]` and
        # reported the first DECLARED state — a message naming the wrong line is a hidden operand
        # in the failure a reader acts on.
        residue = [ln.strip() for ln in proc.stdout.splitlines() if "UNCLASSIFIED" in ln]
        if residue:
            unnamed.append(f"{path.name}: {residue[0]}")
    # ⚑ POSITIVE CONTROL: some census must have been readable, or the loop skipped everything and
    # an empty residue means the reader refused rather than that the corpus is clean.
    assert checked, (
        "no census could be classified — every one refused, so this arm measured nothing"
    )
    assert not unnamed, (
        f"{len(unnamed)} of {checked} readable census(es) use a state their own vocabulary does "
        "not declare — the row is a fact and the vocabulary is the gap:\n  " + "\n  ".join(unnamed)
    )


def test_the_gate_refuses_a_ragged_row_it_did_not_already_have() -> None:
    """⚑⚑⚑ THE RECEIVING REPOSITORY'S GATE IS THE ONLY MOMENT A WRITE AND A CHECK COINCIDE.

    A peer's line-based arm has been finding ragged rows in this tree from outside it, and they
    measured why that is not enough: their arm fires at THEIR commit on THEIR repo, so a peer file
    is swept strictly later than the write — often later than someone else's repair. Every party
    in this fleet writes rows into every other party's censuses, so every structural arm in the
    fleet has that hole. **The gate that runs when the bytes land is the receiver's.**

    ⚑⚑ AND THIS DEFECT IS UNREADABLE TO EVERY AST-BASED READER HERE. Pandoc pads a short row to
    its header's width before the AST exists, so the table module asserts that limit rather than
    repairing it. The shape linter reads raw lines, which is why the rule lives there and why the
    gate can see it at all.

    ⚑ ARMED AGAINST NEW ROWS ONLY, AND THE DIFFERENCE IS THE WHOLE DESIGN. A first sweep measured
    fifteen ragged rows across thirteen files, several in frozen censuses and two in this
    session's own filed legs — neither of which may be amended. Arming a gate over a tree that
    does not pass it blocks the commits that would clean it, which this corpus records as a
    measured hazard. So the refusal compares the staged file against the same file in HEAD and
    fires only on an INCREASE.

    ⚑ A COUNT, NOT A LINE SET, AND THE WEAKNESS IS STATED RATHER THAN HIDDEN: moving a ragged row
    while adding another elsewhere holds the count and passes. The set-membership form is stronger
    and belongs with the ratchet's machinery; a count catches the case this gate exists for — a
    row that was not ragged becoming ragged — and says what it cannot catch.
    """
    body = _GATE.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the staged-markdown walk must still exist, or every assertion below
    # passes because the walk vanished rather than because it gained a check.
    assert "--diff-filter=ACM" in commands, (
        "the gate must still walk staged markdown; this arm would pass on its absence"
    )
    assert "MD056" in commands, (
        "the gate must check for ragged table rows — the one structural defect no AST reader in "
        "this tree can see, and the receiving gate is the only place it is catchable at write time"
    )
    # ⚑⚑ AGAINST HEAD, NOT ABSOLUTE. An absolute refusal would block every commit touching the
    # thirteen files that already carry one, including the frozen censuses and filed legs that may
    # not be amended at all — the clean-the-tree-then-arm hazard, armed backwards.
    # ⚑ THE PROPERTY, NOT A SPELLING. A first cut asserted the literal `git show HEAD` and the
    # gate writes `git show "HEAD:$md"` — an arm that names a spelling cannot outlive a rename,
    # which this file has now measured three times on one comparison arm. What must hold is that
    # the check reads the SAME PATH out of HEAD and compares two counts.
    assert pyre.search(r'git show "HEAD:\$\w+"', commands), (
        "the ragged-row check must read the same path out of HEAD, or it refuses commits to the "
        "fifteen rows that already exist and cannot all be repaired"
    )
    assert pyre.search(r'"\$\{_rag_now:-0\}"\s+-gt\s+"\$\{_rag_head:-0\}"', commands), (
        "the refusal must fire on an INCREASE against HEAD; an absolute test arms a gate over a "
        "tree that does not pass it and blocks the commits that would clean it"
    )
    # ⚑⚑ AND A CRASHED LINTER MUST NOT READ AS A CLEAN DOCUMENT. `lint` exits 1 when it has
    # findings, so piping into a counter reports the counter's status and turns a broken reader
    # into a zero — a false negative from the instrument, inside the check built to catch false
    # reads. The gate separates rc>1 from rc<=1 and says so.
    assert "shape linter FAILED" in body, (
        "a linter that could not run must be distinguished from a document with no findings"
    )


def _rule_name(code: str) -> str | None:
    """Return ruff's own name for a rule code, or None when ruff does not know it.

    ⚑ ASKED OF THE CHECKER, NOT TABULATED HERE. `ruff rule <code>` is the authority on what a code
    is called; a table written into this file would be a hand-written population that goes stale
    at exactly the moment a rule is renamed — which is the event this arm exists to catch.

    Returns:
        the rule's name, or None if the code does not resolve.

    """
    argv = _ruff_argv()
    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the checker is the subject of this case
        [*argv, "rule", code, "--output-format", "json"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return None
    parsed: object = json.loads(proc.stdout)
    if not isinstance(parsed, dict):
        return None
    name: object = parsed.get("name")
    return name if isinstance(name, str) else None


def test_a_selector_and_the_comment_explaining_it_name_the_same_rule() -> None:
    """⚑⚑⚑ THE AUTOFIX REWRITES THE VALUE AND LEAVES THE PROSE, SO THE TWO CAN DISAGREE.

    The operator ruled on 2026-09-07 to adopt `RUF201`, which replaces a rule CODE in a selector
    with the rule's NAME. Measured across the three distributions: twenty-six findings, every one
    inside a `pyproject.toml`, every one autofixable. **But this repository's selectors carry
    comments that cite those codes BY CODE** — *`S101` bans `assert`*, *the `S603` exemption a
    subprocess needs* — and an autofix touches the list while leaving the sentence above it.

    ⚑⚑ A CONFIG WHOSE VALUE AND WHOSE EXPLANATION NAME DIFFERENT THINGS IS WORSE THAN EITHER
    SPELLING ALONE. A reader checking whether an exemption is justified reads the comment, finds
    a code, and greps for a code that is no longer there. The rename is the easy half; keeping the
    two halves saying one thing is the half that has to be asserted.

    ⚑ THE ARM DOES NOT REQUIRE A PARTICULAR SPELLING, which is deliberate. Requiring names would
    re-litigate the operator's ruling every time ruff renames a rule; requiring codes would
    contradict it. What must hold is AGREEMENT: every code named in a selector is either absent
    from the surrounding prose or present in it, and never contradicted by a name for a different
    rule.
    """
    codes = pyre.compile(r"\b([A-Z]{1,4}\d{3,4})\b")
    checked = 0
    disagreeing: list[str] = []
    for dist in _distributions():
        config = _DIST.parent / dist / "pyproject.toml"
        if not config.is_file():
            continue
        checked += 1
        lines = config.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#") or "=" not in line:
                continue
            # ⚑⚑⚑ NO `if not in_value: continue` HERE, AND A FIRST CUT HAD ONE. It skipped every
            # entry carrying no code — which after the rename is EXACTLY the population this arm
            # exists for. The arm went blind at the moment it was supposed to fire, and passed
            # green over a config whose comments cite codes the values no longer carry. Measured
            # by probing the walk-back directly rather than trusting the green.
            value = line.split("=", 1)[1]
            # ⚑ THE PROSE IMMEDIATELY ABOVE, walking back to the blank line or section head that
            # bounds the comment block. A fixed window would read a neighbouring entry's comment
            # and report a disagreement between two entries that each agree with themselves.
            prose: list[str] = []
            for back in range(i - 1, -1, -1):
                if not lines[back].lstrip().startswith("#"):
                    break
                prose.append(lines[back])
            # ⚑ NARROWED AT THE EDGE. `findall` is typed `list[Any]`, and under this repo's
            # `disallow_any_expr` that `Any` poisons every downstream expression — ten errors from
            # one unannotated call. Declaring the type here is the narrowing the flag exists to
            # force, rather than carrying `Any` inward and reading green.
            found: list[str] = codes.findall("\n".join(prose))
            in_prose = set(found)
            # ⚑⚑⚑ ONLY A CODE THE SELECTOR ALSO NAMES BY ITS RULE NAME IS A DISAGREEMENT, and the
            # first cut got this wrong: it flagged every comment mentioning ANY other code. Three
            # findings, all false — the prose there cites a DIFFERENT rule to explain why the
            # entry exists at all (`RUF100` for why a line directive became a config entry,
            # `CPY001` for a peer's ignore this repo declined). **A comment naming another rule is
            # normal and correct**; a comment naming a rule the same entry has since RENAMED is
            # the defect, because a reader greps for a code the selector no longer carries.
            # ⚑⚑ THE CODE-TO-NAME MAP IS ASKED OF RUFF, NEVER WRITTEN HERE. A hand-written table
            # is the population defect this tree has measured eleven times, and it would go stale
            # the first time ruff renamed a rule — which is the very event this arm exists for.
            contradicted = {
                code for code in in_prose
                if (name := _rule_name(code)) is not None and name in value
            }
            if contradicted:
                disagreeing.append(
                    f"{dist}/pyproject.toml:{i + 1}: the selector names this rule by NAME while "
                    f"the comment above still cites {sorted(contradicted)} — a reader greps for "
                    "a code the selector no longer carries"
                )
    # ⚑ POSITIVE CONTROL: the configs must have been read, or an empty disagreement list means the
    # loop found no files rather than that the tree agrees with itself.
    assert checked, "no pyproject.toml was read — this arm would pass vacuously"
    assert not disagreeing, (
        f"{len(disagreeing)} selector(s) are explained by prose naming a rule the selector does "
        "not:\n  " + "\n  ".join(disagreeing)
    )


def test_every_suppression_directive_suppresses_under_the_gates_config() -> None:
    """⚑⚑⚑ A DIRECTIVE THE GATE'S CHECKER DOES NOT HONOUR FAILS SILENTLY, WHICH IS THE WORSE HALF.

    Two preview rules chain over suppression comments: the first moves `# noqa: CODE` to `# ruff:
    ignore[CODE]`, and the second then objects to that very code and wants the rule's NAME.
    Satisfying the second before tree-wide preview is armed produces directives the gate's ruff
    **silently ignores** — measured, and worse than the selector rename that started this: that one
    exited 2 and stopped the build, while this one merely stops suppressing and lets the
    suppressed findings reappear with nothing saying a directive died.

    ⚑⚑ MEASURED WITH AN F-ARM, so a clean result means suppression rather than a rule that never
    fired. A bare violation is REPORTED in both configurations; then:

        # ruff: ignore[S101]      no-preview rc=0   --preview rc=0
        # ruff: ignore[assert]    no-preview rc=1   --preview rc=0
        # ruff: ignore  (bare)    no-preview rc=1   --preview rc=1

    ⚑⚑⚑ AND THAT TABLE'S PREMISE HAS SINCE BEEN RETIRED BY THE PREVIEW ARMING — KEPT, BECAUSE IT
    RECORDS WHY THE ORDER MATTERED. `preview = true` now lives in `[tool.ruff.lint]`, so there is
    no longer a no-preview configuration for the gate to run: the gate passes no flag and gets
    preview from the config, which is precisely what made the name form safe to adopt. The rows
    above describe the window BETWEEN the two rulings — adopt `rule-codes-in-selectors`
    (2026-09-07) and arm tree-wide preview first (2026-09-08) — and that window is now closed.
    ⚑⚑ A STALE PREMISE IN A LIVE ARM IS THE FAILURE THIS FILE IS FULL OF, so it is corrected in
    place rather than left to be re-derived: the arm no longer asserts anything about `--preview`.

    ⚑⚑⚑ AND THIS ARM CURRENTLY HAS NO F-ARM, WHICH IS RECORDED RATHER THAN GLOSSED. Measured: revert
    one directive to the code form (`# ruff: ignore[S108]`) and this arm stays GREEN — because with
    preview armed the code form STILL SUPPRESSES. `ruff check` on that file reports
    `rule-codes-in-suppression-comments` and no `hardcoded-temp-file`: the style rule objects to the
    spelling while the suppression itself keeps working.
    ⚑⚑ SO THE HAZARD THIS ARM WAS BUILT FOR IS CLOSED BY THE ARMING, and what remains is a standing
    guard against its RETURN — a future ruff that drops a name, or a config that unarms preview,
    puts an unhonourable directive back in reach. That is worth keeping, but an arm no available
    mutation can redden is one whose green says less than it looks like it says, and a reader is
    owed that distinction here rather than discovering it by trusting this line.
    ⚑ THE RULE THAT NOW POLICES THE SPELLING IS `rule-codes-in-suppression-comments`, enforced by
    `//hooks:ruff`. Suppression FORM has an owner; this arm owns suppression EFFECT.

    ⚑ SO THIS ARM CHECKS THE PROPERTY, NOT THE SPELLING: every suppression directive in this
    distribution's sources is one the gate's checker HONOURS. A directive form that stops working
    is caught here rather than by 16 findings reappearing three ticks later.

    ⚑⚑⚑ AND THE POPULATION IS THE DIRECTIVES, NOT THE FILES CARRYING THEM. This arm required each
    sweeping file to be entirely CLEAN, which silently made it an arm about every rule in the
    repository: when preview was armed, four unpaid judgement findings — two of
    `docstring-missing-returns`, one `suspicious-subprocess-import`, one
    `docstring-missing-exception` — landed in files that happen
    to carry directives, and this arm went red for debt that has nothing to do with suppression.
    ⚑⚑ AN ARM THAT FAILS FOR A REASON OUTSIDE ITS SUBJECT IS AN ARM WHOSE RED IS UNINFORMATIVE,
    and it is the same defect as a green that means nothing. So the assertion is now scoped to the
    rules actually named in the directives: a finding for a rule some directive claims to suppress
    is this arm's business, and any other finding belongs to `//hooks:ruff`, which reports it.

    ⚑⚑ AND RUNNING THE ARM'S OWN F-ARM CORRECTED THE PROBE THAT MOTIVATED IT. Swapping one
    directive to the name form makes this fail with TWO findings, not one: the un-suppressed
    `S603`, and `RUF102 Invalid rule code in suppression` naming the directive directly. So the
    failure is **not fully silent** — the probe measured suppression alone and missed that
    non-preview ruff does complain about the form. The harm is still the reappearing finding; the
    correction is that a reader has one more signal than I claimed, and claiming less than is
    there is its own defect.
    """
    argv = _ruff_argv()
    sources = sorted(
        p
        for p in (_DIST / "tests").rglob("*.py")
        if "ruff: ignore" in p.read_text(encoding="utf-8")
    )
    # ⚑ POSITIVE CONTROL: some file must carry a directive, or a clean result means this arm found
    # nothing to check rather than that every directive works.
    assert sources, (
        "no source carries a `ruff: ignore` directive — this arm would pass vacuously"
    )
    # ⚑⚑⚑ THE FLAGS ARE THE GATE'S AND THE POPULATION IS THIS REPOSITORY'S, AND IT TOOK TWO
    # HERMETIC FAILURES TO SEPARATE THOSE. First cut: absolute paths plus `--config`, which made
    # `per-file-ignores` patterns like `tests/*` resolve against the wrong root — 296 `S101`
    # findings in the sandbox, zero locally. Second cut: `ruff check .` from the distribution
    # directory, copying the gate exactly — which in the sandbox sweeps `__init__.py` files that
    # EXIST ONLY IN THE RUNFILES TREE, generated by the build to make the package importable and
    # absent from the repository.
    # ⚑⚑ SO "RUN IT AS THE GATE RUNS IT" IS TWO CLAIMS, NOT ONE. The gate's FLAGS are what this arm
    # must share — no `--preview`, since that is the whole question. The gate's WORKING SET is a
    # staged checkout that does not exist here, and copying its `.` imports the sandbox's own
    # staging artifacts into the population. Naming the files keeps the population honest;
    # `--config` keeps the per-file patterns resolving; neither is a deviation from the gate on the
    # axis this arm measures.
    # ⚑⚑⚑ AND THE GATE ALSO NORMALISES THE STAGED MODE BITS, WHICH THIS ARM DID NOT — SO IT WENT
    # RED REMOTELY WHILE THE GATE'S OWN TARGET WENT GREEN. The executor stages sources
    # `-rwxr-xr-x` where the repository holds `-rw-rw-r--`, so `EXE002 The file is executable but
    # no shebang is present` fires on a filesystem the CAS invented. `ruff_check.sh` strips those
    # bits before invoking ruff, on the operator's ruling to normalise the POPULATION rather than
    # disable the rule — and this arm runs its OWN invocation, so the repair reached the target and
    # not the arm.
    # ⚑⚑ "A REPAIR APPLIED TO ONE CALL SITE IS NOT A REPAIR TO THE CLASS" is recorded elsewhere in
    # this repository about a different check; measured again here, one commit later, in the arm
    # whose comment already says it must share the gate's setup.
    for src in sources:
        mode = src.stat().st_mode
        if mode & 0o111:
            src.chmod(mode & ~0o111)

    proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the checker is the subject of this case
        [*argv, "check", "--no-cache", "--config", str(_DIST / "pyproject.toml"),
         "--output-format", "concise", *[str(p) for p in sources]],
        capture_output=True, text=True, check=False, cwd=str(_DIST),
    )

    # ⚑⚑⚑ THE RULES THE DIRECTIVES THEMSELVES NAME — derived from the population, never typed. A
    # literal list here would go stale at the next directive and quietly narrow what is checked.
    # `RUF102 Invalid rule code in suppression` is added unconditionally: it is the checker's own
    # report that a directive is unhonourable, which is this arm's subject stated by the tool.
    claimed = {"RUF102", "invalid-rule-code"}
    for src in sources:
        # ⚑ DECLARED AT THE EDGE: `findall` is typed `list[Any]`, and under this repo's
        # `disallow_any_expr` that `Any` poisons every downstream expression. The sibling arm
        # `test_a_selector_and_the_comment_explaining_it_name_the_same_rule` carries the same
        # annotation for the same reason — narrowing here is the flag doing its job.
        names: list[str] = pyre.findall(
            r"#\s*ruff:\s*ignore\[([^\]]+)\]", src.read_text(encoding="utf-8")
        )
        claimed.update(names)
    # ⚑ POSITIVE CONTROL: a bracketed directive must exist, or the filter below admits nothing and
    # the arm passes by matching no line rather than by every directive working.
    assert claimed > {"RUF102", "invalid-rule-code"}, (
        "no directive names a rule — this arm would pass by having nothing to match"
    )

    resurfaced = [
        ln for ln in proc.stdout.splitlines()
        if any(f" {rule}" in ln or f"{rule}:" in ln for rule in claimed)
    ]
    assert not resurfaced, (
        f"{len(sources)} file(s) carry `ruff: ignore` directives and the gate's ruff reports "
        f"findings for {len(resurfaced)} rule(s) those directives claim to suppress:\n"
        + "\n".join(resurfaced)
        + "\na directive form the gate cannot honour lets the finding it suppressed reappear"
    )


def test_no_baseline_key_names_a_rule_that_no_longer_exists() -> None:
    """⚑⚑⚑ A SUBSTITUTED KEY AND A BANKED ONE ARE BYTE-IDENTICAL IN A BARE KEY LIST.

    The suppression-directive paydown cleared `noqa-comments` at two files and opened
    `rule-codes-in-suppression-comments` at the same two, because the two preview rules chain: the
    first moves a noqa comment to a bracketed ignore directive, the second objects to the code
    inside those brackets. The ratchet refused, correctly — a new key is a new key regardless of
    what it replaced — and the operator ruled to SUBSTITUTE rather than grow: fifteen keys before,
    fifteen after, measured from the diff as two insertions and two deletions.

    ⚑⚑ BUT THE BASELINE IS A BARE LIST WITH NO PLACE TO SAY THAT. A later reader meeting
    `rule-codes-in-suppression-comments` cannot tell a rename recorded from a defect banked, and
    this repository's standing rule is pay-never-bank. The distinction has to live somewhere the
    reader will meet it, and a comment in a file the ratchet parses is not that place.

    ⚑ SO THE ARM CHECKS THE PROPERTY THAT MAKES THE SUBSTITUTION HONEST: every key in the baseline
    names a rule the checker still recognises. A key naming a rule that no longer exists is debt
    nothing can ever pay — the rule is gone, so the finding cannot recur, so the key sits forever
    reading as tolerated debt. That is the shape a rename leaves behind when the OLD key is kept
    instead of replaced, and it is exactly what this substitution avoided.
    """
    # ⚑ READ INLINE RATHER THAN THROUGH A LOCAL, so the vacuity sweep's bounded evaluator can
    # resolve it. Assigning `baseline = _DIST / "…"` first makes the read's receiver a NAME the
    # sweep's target map does not carry, and the arm joins the unresolved list — a fourth ceiling
    # rise for a file that is perfectly resolvable in the `_CONST / "literal"` form the evaluator
    # already handles. The three earlier rises were runtime populations and genuinely unresolvable;
    # this one would have been my own spelling.
    assert (_DIST / "ratchet-preview.txt").is_file(), (
        f"no baseline at {_DIST / 'ratchet-preview.txt'} — this arm would pass vacuously"
    )
    keys = [
        ln.strip()
        for ln in (_DIST / "ratchet-preview.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    # ⚑ POSITIVE CONTROL: an empty baseline would satisfy every assertion below.
    # ⚑⚑⚑ AND IT IS NOW EMPTY, BY AN OPERATOR RULING, SO THIS SKIPS RATHER THAN FAILS — the
    # distinction being that a vacuous arm and a broken one are different facts. The hooks baseline
    # was LOWERED to zero on 2026-09-12 after the preview paydown cleared all thirteen keys
    # (`mikemol-ratchet --write`, thirteen paid keys removed). There is no key left to name a rule,
    # so the property this arm asserts is true of nothing.
    # ⚑⚑ A FAILING ASSERTION HERE WOULD SAY *THE BASELINE IS BROKEN* WHEN WHAT HAPPENED IS *THE
    # DEBT IS PAID*, which is the best possible outcome reported as a defect. A suite that reddens
    # on success teaches its reader to delete the arm. The arm stays armed for the moment a key
    # returns — and the sibling arm below is what proves a returning key is REFUSED.
    if not keys:
        pytest.skip(
            "the baseline is empty — every key was paid down and the operator lowered it; "
            "this arm's property is vacuous over an empty set and re-arms when a key returns"
        )
    unknown: list[str] = []
    for key in keys:
        _, _, rule = key.rpartition(":")
        # ⚑ ASKED OF THE CHECKER, as the sibling arm does. `ruff rule` is the authority on whether
        # a name resolves; a list here would go stale at the rename this arm watches for.
        proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the checker is the subject of this case
            [*_ruff_argv(), "rule", rule, "--output-format", "json"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            unknown.append(key)
    assert not unknown, (
        f"{len(unknown)} of {len(keys)} baseline key(s) name a rule this checker does not "
        "recognise — a key for a rule that no longer exists is debt nothing can ever pay, and it "
        f"reads as tolerated forever:\n  " + "\n  ".join(unknown)
    )


def _staged_ratchet() -> Path | None:
    """Locate the built ratchet CLI under bazel AND under the bare pytest the gate runs.

    ⚑⚑⚑ THE FIRST SPELLING NAMED NOTHING OUTSIDE THE SANDBOX, AND THAT IS THE ENVIRONMENT THE
    GATE USES. `_DIST.parent / "ratchet" / "ratchet_cli"` is the RUNFILES layout: correct under
    `bazel test`, where both arms passed, and absent under `.venv/bin/python3 -m pytest`, where
    they SKIPPED with "the instrument is absent". A skip is honest, but two arms skipping in the
    gate's own environment is two arms that never run where it matters.
    ⚑⚑ MEASURED BY RUNNING BOTH WAYS rather than by reading either path — the fifth time in this
    repository that a path was a string naming nothing, and the second time this session.

    Returns:
        The first candidate that exists, or `None` when the CLI has not been built. ⚑ `None`
        rather than a guess: a caller that skips on absence is honest, and a caller handed a
        non-existent path would fail with a confusing `FileNotFoundError` from a subprocess.

    """
    for candidate in (
        # The runfiles tree, when bazel staged it as a declared input.
        _DIST.parent / "ratchet" / "ratchet_cli",
        # ⚑ THE CONVENIENCE SYMLINK, which is what a bare pytest run in a checkout sees. It is a
        # build OUTPUT and deliberately gitignored, so its absence means "not built yet" rather
        # than "not part of this repository".
        _DIST.parent / "bazel-bin" / "ratchet" / "ratchet_cli",
    ):
        if candidate.is_file():
            return candidate
    return None


def test_a_key_absent_from_the_baseline_is_refused_when_its_finding_returns() -> None:
    """⚑⚑⚑ A PAYDOWN THAT ARMS NOTHING IS A DELETION WEARING A PAYDOWN'S NAME.

    The operator ruled on 2026-09-08 to lower this baseline by the two keys the ratchet reported
    paid down. ⚑ Removing a line and *arming a refusal* are different events, and the diff shows
    only the first: two deletions, zero additions. Whether the gate now REFUSES what it used to
    tolerate is a separate claim, and nothing in the artifact carries it.

    ⚑⚑ MEASURED, BOTH ARMS, on the real baseline before this was written. Re-introducing the paid-
    down comparison at `tests/test_payload.py:48` — `== _EMPTY` back to `== ""` — made the ratchet
    exit 1 with `1 new key(s) REFUSED: + tests/test_payload.py:compare-to-empty-string`. Restored,
    it read `baseline ok: 13 key(s), unchanged`. Before the paydown that same comparison was
    baselined and SILENT. So the removal did arm the gate against exactly the finding it retired.

    ⚑ THE ARM ASSERTS THE ABSENCE, not the count. A count-shaped assertion (`13 keys`) goes stale
    at the next legitimate paydown and says nothing about which keys; this asserts that these two
    specific retired keys are not present, which is the property the F-arm proved load-bearing. A
    key re-entering the baseline would restore the silence the operator's ruling ended.

    ⚑ POSITIVE CONTROL BELOW: an unreadable or empty baseline satisfies an absence assertion
    trivially, so the file's own content is asserted before the absence is claimed.

    ⚑⚑⚑ AND THE BASELINE IS NOW EMPTY, WHICH RETIRES THE ABSENCE READING AND STRENGTHENS THE ARM.
    A second ruling on 2026-09-12 lowered hooks to ZERO keys after the preview paydown cleared all
    thirteen. Over an empty set *these two specific keys are absent* is true of every key at once,
    so the assertion stops discriminating — the positive control above was written for exactly this
    and is why the change was caught rather than absorbed.
    ⚑⚑ SO THE ARM NOW ASSERTS THE PROPERTY ITS OWN DOCSTRING ALWAYS NAMED, AND IT IS A STRICTLY
    BETTER ONE: **the ratchet REFUSES a finding the baseline does not carry.** That is what "a
    paydown that arms nothing is a deletion wearing a paydown's name" was always about, and this
    file recorded it being MEASURED BY HAND twice — once on 2026-09-08 and again on 2026-09-12 —
    without any arm carrying it. A measurement that has to be repeated by hand each time the
    baseline moves is a measurement nobody will take on the tick that matters.
    ⚑ EMPTY IS THE STRONGEST STATE FOR THIS QUESTION, not the weakest: with no keys at all, ANY
    finding the checker reports must be refused, so the arm needs no retired key to aim at and
    cannot go stale at the next paydown.
    """
    assert (_DIST / "ratchet-preview.txt").is_file(), (
        f"no baseline at {_DIST / 'ratchet-preview.txt'} — this arm would pass vacuously"
    )
    keys = {
        ln.strip()
        for ln in (_DIST / "ratchet-preview.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }
    retired = {
        "tests/test_payload.py:compare-to-empty-string",
        "tests/test_structural_query.py:compare-to-empty-string",
    }
    returned = sorted(keys & retired)
    assert not returned, (
        f"{len(returned)} key(s) retired by the operator's 2026-09-08 paydown are back in the "
        "baseline — a re-entered key restores the silence that paydown ended, and the ratchet "
        f"would tolerate the finding again:\n  " + "\n  ".join(returned)
    )

    # ⚑⚑⚑ THE REFUSAL ITSELF, RUN RATHER THAN DESCRIBED. A copy of the distribution gets one
    # planted finding whose key the baseline does not carry; the ratchet must exit NONZERO and name
    # it. ⚑ ON A COPY, because the ratchet reads a whole distribution and this must not depend on —
    # or disturb — the working tree the gate is about to read.
    # ⚑⚑ THE DECLARED `//ratchet:ratchet_cli`, NOT `ratchet/.venv/bin/mikemol-ratchet`. The first
    # draft of this arm reached for the host venv — a path that exists on this workstation and in
    # NO sandbox, which is ⟐UNDECLARED-HOST-INPUTS written fresh into a new arm while the symbol
    # for it sits in the poll. `hooks/BUILD.bazel` already stages this target for `//hooks:ratchet`,
    # so the instrument is in the graph and needs only naming in THIS target's data.
    # ⚑ `_DIST.parent` IS THE RUNFILES ROOT (`_main`) UNDER BAZEL AND THE REPO ROOT OUTSIDE IT —
    # the property this file's header records and every sibling arm relies on. So one expression
    # names the staged binary in the sandbox and the built one under a bare pytest run.
    # ⚑⚑ STAT IT, NEVER ASSUME IT — `_staged_ratchet` returns None rather than a path that names
    # nothing, and it checks BOTH the runfiles layout and the bare-pytest one because this arm
    # used to skip in the gate's own environment while passing in the sandbox.
    ratchet = _staged_ratchet()
    if ratchet is None:
        pytest.skip("the ratchet CLI is not built — the instrument is absent, not passing")

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "hooks"
        # ⚑ DECLARED AT THE EDGE: `shutil.ignore_patterns` is typed to return
        # `Callable[[Any, list[str]], set[str]]`, and under this repository's `disallow_any_expr`
        # that `Any` poisons the `copytree` call it is passed to. Naming the type here is the
        # narrowing the flag exists to force — the same move the two `re.findall` sites in this
        # file already carry, for the same reason.
        ignore: Callable[[str, list[str]], set[str]] = shutil.ignore_patterns(
            ".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__",
            "build", "dist", "*.egg-info")
        shutil.copytree(_DIST, probe, symlinks=True, ignore=ignore)
        # ⚑ THE PLANTED FINDING IS A SUPPRESSION DIRECTIVE IN THE CODE FORM, which raises
        # `rule-codes-in-suppression-comments` — a preview rule this distribution pays rather than
        # baselines, so its key is genuinely absent and the ratchet has no licence to tolerate it.
        # ⚑⚑⚑ THE CODE FORM IS DERIVED, NOT SPELLED, AND THE VACUITY SWEEP IS WHY. Writing
        # `"ignore[S108]"` here made the sweep report this arm unresolvable: it checks that every
        # asserted literal occurs in the file the test READS, and `S108` exists only in a
        # TemporaryDirectory this arm creates at runtime. The sweep was right — a literal it cannot
        # resolve is a literal nothing proves is reachable — and `_MAX_UNRESOLVED` may only ever
        # DECREASE (an arm enforces that), so the repair is to stop needing the literal.
        # ⚑⚑ SO THE MUTATION IS EXPRESSED AS A TRANSFORMATION OF WHAT THE FILE HOLDS: take the
        # directive's bracketed NAME and put back a code. Both halves of the substitution are now
        # values read from the source, and the arm asserts only that the text CHANGED.
        planted = probe / "tests" / "test_checkers.py"
        before = planted.read_text(encoding="utf-8")
        after = pyre.sub(r"ruff: ignore\[[a-z][a-z0-9-]+\]", "ruff: ignore[S108]", before, count=1)
        planted.write_text(after, encoding="utf-8")
        # ⚑ POSITIVE CONTROL ON THE FIXTURE: if the substitution did not land, the run below
        # measures an unmodified tree and its green says nothing. Asserted as a DIFFERENCE rather
        # than as a literal, for the reason above.
        assert after != before, (
            "the planted finding did not take — no name-form directive was found in "
            f"{planted.name}, so this arm would measure an unmodified copy"
        )
        # ⚑⚑⚑ `RUFF_BIN` IS THE CONTRACT, read from `ratchet_check.sh` rather than guessed. That
        # script exports it so *the census does not reach for a developer venv* — the same
        # discipline as the pandoc and stubtest witnesses — and an arm that omitted it would either
        # fail for want of `<dist>/.venv/bin/ruff` or, worse, measure whatever host ruff it found.
        env = {**os.environ, "RUFF_BIN": str(Path(_ruff_argv()[0]).resolve())}
        proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the ratchet is the subject of this case
            [str(ratchet), str(probe)],
            capture_output=True, text=True, check=False, env=env,
        )

    assert proc.returncode != 0, (
        "the ratchet TOLERATED a finding whose key the baseline does not carry — a lowered "
        "baseline that refuses nothing is the deletion-wearing-a-paydown's-name shape this arm "
        f"is named for:\n{proc.stdout}{proc.stderr}"
    )
    # ⚑⚑ THE KEY IS NAMED BY THE FILE, NOT BY A LITERAL HERE — the same vacuity-sweep constraint as
    # the substitution above. What must appear in the refusal is the PLANTED FILE's key, and the
    # file's name is a value this arm already holds. Asserting the rule name as a literal would
    # make this arm unresolvable for a string that is the checker's to choose anyway.
    assert planted.name in proc.stdout, (
        "the ratchet refused, but did not name the file the finding was planted in — an arm that "
        f"cannot tell its own finding from an unrelated failure is measuring the fixture:\n"
        f"{proc.stdout}{proc.stderr}"
    )


def test_every_emptied_baseline_arms_a_refusal() -> None:
    """⚑⚑⚑ THE LOWERING IS NOW A STANDING POLICY, SO THE ARM QUANTIFIES OVER DISTRIBUTIONS.

    The sibling arm above proves the property for `hooks`, whose baseline the operator lowered on
    2026-09-12. On 2026-09-13 that ruling was extended: *lower each distribution's baseline as its
    paydown lands*. ⚑ A POLICY THAT APPLIES TO EVERY DISTRIBUTION AND AN ARM THAT CHECKS ONE IS
    THE SHAPE THIS REPOSITORY KEEPS MEASURING — `ratchet` was emptied the same day and nothing
    would have noticed if its lowering had armed nothing.

    ⚑⚑ THE POPULATION IS DERIVED, NEVER TYPED: every directory carrying a `pyproject.toml` that
    also carries an EMPTY `ratchet-preview.txt`. A hand-written list would stop covering the
    distribution emptied after it was written, which is the defect the policy makes more likely
    rather than less — each paydown adds a member.

    ⚑ AND EMPTY IS THE ONLY STATE THIS ARM CAN CHECK CHEAPLY. With keys present, a planted finding
    might collide with a baselined one and the refusal would be ambiguous; with none, ANY finding
    the checker reports must be refused, so the assertion needs no knowledge of what is tolerated.

    ⚑⚑ THE PLANT IS A NEW FILE, NOT A MUTATION. The sibling arm rewrites a directive inside
    `test_checkers.py`, which only exists in `hooks`; a new module under the distribution's own
    package works in any of them and disturbs no existing arm's meaning.
    """
    ratchet = _staged_ratchet()
    if ratchet is None:
        pytest.skip("the ratchet CLI is not built — the instrument is absent, not passing")

    root = _DIST.parent
    # ⚑⚑⚑ THE POPULATION IS WHAT IS BOTH EMPTIED *AND REACHABLE*, AND THE TWO ARE DIFFERENT
    # NUMBERS IN THE SANDBOX. This target stages every distribution's `pyproject.toml` — so
    # `_distributions()` names four — but NOT their `src/` trees or baselines, so a sibling's
    # files are absent there and present under a bare pytest run.
    # ⚑⚑ REPORTING THE SHORTFALL RATHER THAN ABSORBING IT. A `continue` over the unreachable ones
    # would leave this arm checking one distribution while its name promises every one — the
    # `confidently over a population its ENVIRONMENT truncated` defect that `hooks/BUILD.bazel`'s
    # data list records, arriving through the same door. The counts are printed in the failure
    # message and the skip, so a reader can tell "nothing to check" from "could not look".
    emptied: list[str] = []
    unreachable: list[str] = []
    for dist in _distributions():
        baseline = root / dist / "ratchet-preview.txt"
        if not baseline.is_file() or not (root / dist / "src" / "mikemol" / dist).is_dir():
            unreachable.append(dist)
            continue
        if not baseline.read_text(encoding="utf-8").strip():
            emptied.append(dist)
    # ⚑ POSITIVE CONTROL: with no emptied baseline the loop below runs zero times and every
    # assertion in it is vacuously satisfied. Skipping says so rather than reporting green, and
    # names how many distributions could not be read at all.
    if not emptied:
        pytest.skip(
            f"no reachable distribution carries an empty baseline "
            f"({len(unreachable)} of {len(_distributions())} not readable here) — this arm's "
            "population is empty and its property would be vacuously true"
        )

    # ⚑⚑⚑ `build`, `dist` AND `*.egg-info` ARE IN THIS LIST BECAUSE AN F-ARM CAUGHT THEM, and the
    # tree is not the thing that was wrong. `mdstruct/build/lib/` is a stale setuptools artifact
    # holding PRE-PAYDOWN copies of every source — gitignored, so the real ratchet never sees it
    # and the distribution is genuinely clean. A `copytree` that copies it hands the census ten
    # findings from files that are not the distribution, and the arm then refuses a CLEAN copy.
    # ⚑⚑ ONLY THE F-ARM SEPARATED THOSE. A planted copy also refuses — by name, with the right
    # key — so a P-arm alone reads as success while the arm is measuring build residue.
    ignore: Callable[[str, list[str]], set[str]] = shutil.ignore_patterns(
        ".venv", ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__",
        "build", "dist", "*.egg-info")
    tolerated: list[str] = []
    for dist in emptied:
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / dist
            shutil.copytree(root / dist, probe, symlinks=True, ignore=ignore)
            # ⚑ THE PLANTED FINDING IS A COMPARISON TO AN EMPTY STRING, which a preview rule names
            # and which needs no existing construct to mutate. Its docstring deliberately omits a
            # Returns section, so a second preview rule fires too — one planting, two independent
            # reasons the ratchet must refuse.
            # ⚑ REACHABILITY WAS ESTABLISHED WHEN THE POPULATION WAS BUILT, so this is an
            # assertion rather than a skip: a package absent HERE means the copy lost it, which is
            # a fixture failure and must be loud.
            pkg = probe / "src" / "mikemol" / dist
            assert pkg.is_dir(), f"the copy of {dist} lost its package — the fixture is broken"
            (pkg / "_probe.py").write_text(
                "# SPDX-License-Identifier: Apache-2.0\n"
                "# Copyright (c) 2026 Mike Mol\n"
                '"""A planted finding: an emptied baseline must refuse, not tolerate."""\n'
                "\n\n"
                "def f(s: str) -> bool:\n"
                '    """Compare to an empty string."""\n'
                '    return s == ""\n',
                encoding="utf-8",
            )
            proc = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] — the ratchet is the subject of this case
                [str(ratchet), str(probe)],
                capture_output=True, text=True, check=False,
                env={**os.environ, "RUFF_BIN": str(Path(_ruff_argv()[0]).resolve())},
            )
        if proc.returncode == 0 or "_probe.py" not in proc.stdout:
            tolerated.append(f"{dist}: rc={proc.returncode} {proc.stdout.strip()}")

    assert not tolerated, (
        f"{len(tolerated)} of {len(emptied)} emptied baseline(s) TOLERATED a planted finding — a "
        "lowering that refuses nothing is a deletion wearing a paydown's name:\n  "
        + "\n  ".join(tolerated)
    )


def test_the_refusal_records_ragged_rows_are_reported_by_shape() -> None:
    """⚑⚑⚑ THE COUNT IS RIGHT AND THE CAUSE IS WRONG, one layer down from a corrected count.

    The poll prints *N of M row(s) ragged — pre-column rows are unattributable*, and an earlier
    tick corrected the COUNT after I carried it from memory as two when a field count found three.
    The count has been right ever since. **The sentence attached to it is not.** Measured by
    reading the rows rather than counting them: the three ragged rows are TWO shapes, not one.

        3 fields   no session id AND no gate name   — genuinely pre-schema
        4 fields   HAS this session's id, missing only the gate name

    ⚑⚑ SO *pre-column rows are unattributable* DESCRIBES THE FIRST SHAPE AND IS APPLIED TO ALL
    THREE. The four-field row carries a session id, so it IS attributable to a session; what it
    cannot say is which gate refused. A reader acting on that line would look for a missing
    attribution that is present, and miss the missing gate name that is the actual gap.

    ⚑ AND THE FIGURE DESCRIBES A HOST-LOCAL CACHE, not the repository — which is why the numerator
    sat static across many ticks while I re-derived it as *carries* each time. Nothing a commit
    does can move it. That is not a defect in the record; it is a fact about the figure that the
    line does not say, and a reader watching it for movement is watching the wrong artifact.

    ⚑ THE ARM CHECKS THE POLL'S SHAPE, NOT THE RECORD'S CONTENT. The record is host-local and may
    legitimately be absent or hold different rows on another machine; what must hold is that the
    poll distinguishes the two shapes rather than collapsing them under one cause.
    """
    commands = "\n".join(
        ln for ln in _POLL.read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the record must still be read at all, or every assertion below passes
    # because the section vanished rather than because it distinguishes the shapes.
    assert "REFUSALS.tsv" in commands, (
        "the poll must still read the refusal record; this arm would pass on its absence"
    )
    # ⚑⚑ THE TWO SHAPES ARE COUNTED SEPARATELY. One figure over two causes is the collapsed verdict
    # this suite refuses elsewhere, and here it produced prose that is false of a third of its own
    # population.
    assert "NF<4" in commands, (
        "the pre-schema rows — no session id, no gate name — must be counted apart from rows that "
        "carry an id and lack only the gate, or one sentence describes two different gaps"
    )
    assert "NF==4" in commands, (
        "a row carrying a session id and missing only the gate name must be counted apart from a "
        "genuinely unattributable one; it IS attributable, and saying otherwise sends a reader "
        "looking for the wrong absence"
    )
    # ⚑ AND THE FIGURE'S SUBJECT IS NAMED. A reader watching a host-local cache for movement that
    # only a commit could cause is watching an artifact no commit touches.
    assert "host-local" in commands, (
        "the line must say the record is host-local — a static numerator otherwise reads as a "
        "carried blocker rather than as a figure no commit can move"
    )


def test_the_poll_does_not_re_ask_a_question_it_has_already_answered() -> None:
    """⚑⚑⚑ THE POLL'S COST IS A COUNTER, AND I CARRIED IT AS A DURATION FOR SEVERAL TICKS.

    Every tick the poll exceeded a foreground limit, and every tick the response was *a duration
    is not a property* followed by backgrounding it. That is true about SECONDS and useless as a
    diagnosis: the property is how many times the reader is STARTED, which does not move when an
    unrelated job runs, and it was measurable the whole time.

    ⚑⚑ MEASURED FROM THE SOURCE, because neither alternative was admissible. A PATH shim cannot
    see the calls — the poll resolves the binary by absolute path. Swapping the real binary would
    work and is refused: eight peers run in this tree, and a swapped binary is the concurrency
    hazard measured one tick earlier, when another party's planted defect was captured by my own
    build and reported as a failure in a distribution I had not touched.

        22 invocation sites inside the per-census loop, 10 censuses, 2 outside = 222 starts

    ⚑⚑⚑ AND THE ACTIONABLE HALF IS NOT THE TOTAL. `tables` is invoked ELEVEN times on the same
    file within one iteration, `rows` nine — the identical query on an unchanged path, whose
    answer cannot differ between calls. Roughly two hundred of those starts re-ask a question the
    poll has already answered.

    ⚑ THE ARM BOUNDS THE REPEATS, NOT THE TOTAL. A total would fall when a census is deleted and
    rise when one is added, reporting the corpus rather than the poll. The repeat count per mode
    is a property of the SCRIPT, so it moves only when someone adds another redundant call — which
    is exactly the event worth refusing.
    """
    lines = _POLL.read_text(encoding="utf-8").splitlines()
    # ⚑ THE LOOP HEADER IS READ, NOT ASSUMED. A first cut searched for `for census in` and found
    # nothing: the loop is `for rel in $censuses`, assigning `census` inside. Guessing a loop's
    # spelling is characterising an instrument from expectation rather than from its source.
    starts = [i for i, ln in enumerate(lines) if pyre.search(r"for rel in \$censuses", ln)]
    assert len(starts) == 1, (
        f"the per-census loop must be findable to bound its calls; found {len(starts)} header(s)"
    )
    ends = [
        i for i, ln in enumerate(lines[starts[0]:], start=starts[0])
        if pyre.match(r"^  done\s*$", ln)
    ]
    assert ends, "the per-census loop's `done` must be findable"
    modes: dict[str, int] = {}
    for ln in lines[starts[0]:ends[0]]:
        if ln.lstrip().startswith("#"):
            continue
        found = pyre.search(r'"\$md" (\w+) "\$census"', ln)
        if found:
            modes[found.group(1)] = modes.get(found.group(1), 0) + 1
    # ⚑ POSITIVE CONTROL: the loop must call the reader at all, or an empty `modes` reads as "no
    # repeats" when it means "the arm found nothing to measure".
    assert modes, "no reader call was found inside the per-census loop — this arm measured nothing"
    worst = max(modes.values())
    assert worst <= _MAX_SAME_QUERY, (
        f"one mode is invoked {worst} times on the same file in a single iteration, above the "
        # ⚑ NO `key=lambda` HERE. An inline lambda's parameter carries no annotation, infers as
        # `Any`, and the strict bar refuses the expression — measured as two errors. The identical
        # defect was fixed in the sibling distribution two ticks ago with a named function; the
        # lesson did not cross the distribution boundary. Sorting is not needed to name the modes.
        f"ceiling of {_MAX_SAME_QUERY}: {modes}. "
        "The same query on an unchanged path cannot return a different answer; each extra call is "
        "a process start that re-asks something already answered."
    )


def test_the_poll_states_no_paydown_figure_it_cannot_re_derive() -> None:
    """⚑⚑⚑ THE POLL HARDCODED A THREE-PART SUM AND REPRINTED IT EVERY TICK, THREE OFF.

    It announced a blocked paydown as `hooks 41 + mdstruct 55 + ratchet 11 = 107`. Measured at the
    tick this arm was written: ratchet is **8** — three were paid down two ticks earlier, by me,
    and the poll went on asserting the pre-paydown figure. Hooks is **43**, having GROWN by two
    from directives I added while paying ratchet.

    ⚑⚑ THIS IS THE DEFECT THE POLL EXISTS TO PREVENT, in the poll. Its own opening states the
    rule: *a claim with no re-derivation procedure will not be re-checked however load-bearing it
    is, because nothing about it announces that it could be.* A typed figure announces nothing.
    Worse, it sits in the section reporting OPERATOR DECISIONS — the figure a reader would use to
    judge whether the decision is still worth its cost.

    ⚑ AND IT IS ALSO THE PARTITION SHAPE. Three terms and a total, all from one typing, none
    re-measured: the terms agree with the total because they were written together, which is
    agreement that carries no information. The poll refuses exactly this arrangement elsewhere.

    ⚑ THE ARM DOES NOT REQUIRE THE FIGURE TO BE PRINTED. Deriving three ruff runs inside the poll
    would add three subprocess starts per run to a script this session has just measured at 222 —
    and the honest alternative to a stale number is no number, with a pointer to the command that
    yields one. What must not survive is a figure a reader will believe and nothing will correct.
    """
    body = _POLL.read_text(encoding="utf-8")
    commands = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    # ⚑ POSITIVE CONTROL: the decision must still be reported, or this arm passes because the
    # section vanished rather than because its figure stopped being asserted.
    assert "RUF201" in commands, (
        "the carried operator decision must still be reported; this arm would pass on its absence"
    )
    # ⚑⚑ A BARE MULTI-DIGIT COUNT NEXT TO A DISTRIBUTION NAME IS THE SHAPE THAT ROTS. Matching the
    # shape rather than the specific numbers, so a reader who updates the figures by hand — which
    # is the move that produced this defect — does not satisfy the arm by editing digits.
    # ⚑ NARROWED AT THE CALL. `findall` is typed `list[Any]`, and under `disallow_any_expr` that
    # `Any` poisons every downstream expression — three errors from one call. THIRD instance of
    # this in three ticks: mdstruct, then this file, now this file again. The fix is recorded
    # twice already and did not reach the hand writing the next `findall`.
    stale: list[str] = pyre.findall(r"\b(?:hooks|mdstruct|ratchet)\s+\d+", commands)
    assert not stale, (
        f"the poll states {len(stale)} hardcoded per-distribution figure(s): {stale}. A typed "
        "count announces no way to re-check it and will be reprinted after the work it describes "
        "is done — measured three off, two ticks after the paydown that moved it."
    )


def test_every_tool_the_gate_invokes_is_refused_when_absent() -> None:
    """⚑⚑⚑ THE GATE STATES THIS RULE ABOUT ITSELF AND THEN BREAKS IT SIXTY LINES LATER.

    At its tool-presence loop it says: *a skip here would report green over a check that never
    executed* — and refuses the commit when `ruff`, `mypy` or `python3` is missing from any
    distribution. That is the fail-CLOSED shape this repository takes from linux-sources and
    refuses substrate's `check_scratch_runtime.py` over.

    ⚑⚑ IT THEN DID EXACTLY THAT, THREE TIMES, IN `if [ -x <tool> ]` BLOCKS THAT SKIP SILENTLY.
    Two named `mdstruct/.venv/bin/python3`, which the loop above ALREADY refuses on — redundant,
    and harmless only by accident. The third named `ratchet/.venv/bin/mikemol-ratchet`, which is
    in NO distribution's `ruff mypy python3` triple and lives ONLY in `ratchet/` (measured: absent
    from fence, hooks and mdstruct). Its absence silently dropped the preview-debt ratchet — the
    check that has refused most often here — and the commit reported green.

    ⚑ THE ABSENCE PATH HAD NEVER BEEN EXERCISED: every guarded tool exists on this host, so the
    guards had only ever taken their true branch. An armed-looking check whose refusal arm has
    never run is the shape this suite exists to catch. All three are now gone — two deleted as
    redundant, the third replaced by a real refusal.

    ⚑⚑ THE ARM DERIVES BOTH POPULATIONS RATHER THAN NAMING THEM. Typing the tool paths here would
    go stale the moment the gate grew another, which is the hand-written-population defect one
    layer up from the gate.

    ⚑⚑⚑ AND ITS *CONSUMER* POPULATION WAS ITSELF HAND-WRITTEN, AT SIZE ONE, WHICH IS WHY THE SAME
    DEFECT SURVIVED ITS OWN REPAIR ONE FILE OVER. It read `_GATE` alone, so it could not see
    `preflight.sh:114` carrying the IDENTICAL guard on the IDENTICAL tool — in a file whose own
    comment says *"an absent one REFUSES rather than skips … this script exists to predict the gate
    rather than to produce a second, weaker verdict."* A check written against hand-written
    populations had one. Both consumers are now checked by one predicate.

    ⚑⚑ TWO COLUMN-ANCHOR MISTAKES, THE SECOND MADE WHILE FIXING THE FIRST. `^if` missed
    preflight's guard because it nests inside a `for dist` loop; `^_singleton=` then missed the
    refusal that replaced it, for the same reason, in the same edit. Both allow leading whitespace
    now. The same
    defect twice in one sitting is the argument for repairing a CLASS over an instance.

    ⚑⚑⚑ AND IT REFUSES TO PASS VACUOUSLY, WHICH IT DID ON THE FIRST RUN AFTER THE REPAIR. With
    every guard removed the guarded set is empty, so `assert not unrefused` is trivially true and
    the arm asserts NOTHING — green over a property nobody is checking, which is the defect one
    level up from the one it was written for. So it also requires the refusals it credits to be
    present: a gate that deleted its `mikemol-ratchet` refusal fails here even with no guards left.
    """
    # ⚑ THE CONSUMERS, DERIVED: every shell file in this repository that invokes a `.venv/bin`
    # tool. Measured with `grep -rln 'venv/bin' .githooks/ preflight.sh` — exactly these two.
    shell_consumers = sorted(
        p for p in [_GATE, _DIST.parent / "preflight.sh"] if p.is_file()
    )
    # ⚑ NON-EMPTY, ASSERTED: every loop below is over this set, so an empty one makes the whole arm
    # vacuous — the exact failure this arm hit once already when its guard population went empty.
    assert shell_consumers, "no shell consumer of the host venv was found — the arm reads nothing"

    for consumer in shell_consumers:
        _assert_no_unrefused_guards(consumer)


def _assert_no_unrefused_guards(consumer: Path) -> None:
    """Refuse any `if [ -x <tool> ]` guard on a tool the file does not also refuse on.

    ⚑ SPLIT OUT SO BOTH CONSUMERS GET THE SAME PREDICATE. A second copy inlined per file is how
    two checks drift into checking slightly different things.
    """
    body = consumer.read_text(encoding="utf-8")

    # ⚑ POSITIVE CONTROL: a refusal must be findable, or "no guards found" below would mean this
    # arm could not read the file rather than that the file is sound. The two consumers word it
    # differently — the gate says "commit refused", preflight says "cannot predict the gate" — so
    # the control is the SHARED substring rather than either spelling.
    assert "not found — cannot" in body, (
        f"{consumer.name}: no tool-presence refusal found — the arm is reading the wrong thing"
    )

    # ⚑⚑ THE COVERED POPULATION IS THE UNION OF TWO REFUSAL SHAPES, AND READING ONLY THE LOOP
    # WOULD MISS THE SECOND. The per-distribution loop iterates `ruff mypy python3`; a SINGLETON
    # tool that lives in exactly one distribution (`mikemol-ratchet`, measured absent from fence,
    # hooks and mdstruct) cannot be expressed that way and gets its own `if [ ! -x ]` refusal.
    # shellcheck's SC2043 refuses a one-element `for`, so the shapes are genuinely different.
    # ⚑⚑ EVERY `pyre` RESULT IS ANNOTATED, because `findall`/`group` are typed `Any` and this
    # distribution refuses `Any` in an expression. Same leak that made a `dataclasses.fields()`
    # arm unusable one commit ago — mypy is the instrument that names it, and the answer is to
    # state the type rather than to widen the config.
    loop = pyre.search(r"for tool in ([^;]+); do", body)
    assert loop, f"{consumer.name}: no `for tool in ...` tool-presence population any more"
    tools: str = loop.group(1)
    covered: set[str] = set(tools.split())
    # ⚑ THE VARIABLE'S VALUE, NOT ITS NAME. A first cut also matched `if [ ! -x "$VAR" ]` and put
    # `VAR` itself into the set — harmless here, and a set holding a shell variable name alongside
    # tool basenames is a population with two different kinds in it, which is how a later reader
    # gets a false positive. Only the assignments are read.
    # ⚑ `^\s*` HERE TOO, AND MISSING IT COST A SECOND ROUND. Having just fixed the guard pattern's
    # column anchor, I left the identical anchor on this one — preflight's assignment is indented
    # inside its `for dist` loop, so the refusal it declares read as absent and the arm refused a
    # file that had just been repaired. The same defect twice in one edit is the argument for
    # fixing a CLASS rather than the instance in front of you.
    singletons: list[str] = pyre.findall(r"^\s*_singleton=(\S+)$", body, flags=pyre.MULTILINE)
    covered |= {Path(m).name for m in singletons}

    # ⚑⚑⚑ `^\s*`, NOT `^` — AND THE FIRST VERSION ANCHORED AT COLUMN ZERO AND MISSED AN INDENTED
    # GUARD. `preflight.sh:114` nests its `if [ -x ... ]` inside a `for dist` loop, so a
    # column-anchored pattern reported ZERO guards there and the file read as sound. The
    # anti-vacuity assertion below is what actually caught it — a second assertion catching what
    # the primary one could not see is the argument for having both, not a redundancy.
    guarded: list[str] = pyre.findall(
        r"^\s*if \[ -x ([^\]]+?) \]; then", body, flags=pyre.MULTILINE,
    )
    unrefused: list[str] = sorted({g for g in guarded if Path(g.strip()).name not in covered})
    assert not unrefused, (
        f"{consumer.name} guards on {unrefused} with `if [ -x ]` and skips silently when absent, "
        f"while its refusals cover only {sorted(covered)} — a missing tool here reports green over "
        f"a check that never executed, which is the rule this file states about itself"
    )

    # ⚑⚑⚑ AND WITHOUT THIS, THE ASSERTION ABOVE PASSES VACUOUSLY THE MOMENT THE LAST GUARD IS
    # REMOVED — zero guards, empty set, green, asserting nothing. Measured: that is exactly what
    # happened on the first run after the repair. So the arm also requires the refusals it credits
    # to BE THERE, which is a claim about the gate rather than about the absence of a pattern.
    assert "mikemol-ratchet" in covered, (
        f"`mikemol-ratchet` is not in any refusal population {sorted(covered)} — it lives only in "
        f"ratchet/.venv, so no iteration of the per-distribution triple covers it, and its absence "
        f"would silently drop the preview-debt ratchet"
    )
    assert {"ruff", "mypy", "python3"} <= covered, (
        f"the per-distribution triple lost a member: {sorted(covered)}"
    )


def test_the_gate_does_not_run_a_second_copy_of_a_check_the_graph_already_runs() -> None:
    """⚑⚑⚑ ONE SUBJECT THROUGH TWO INSTRUMENTS IS A GATE THAT CAN DISAGREE WITH ITSELF.

    Operator ruling: *the gate verdicts should use the build's venv; the gates should be build
    TARGETS.* Measured first, because most of it was already true — `bazel query
    'kind("sh_test", //...)'` returns ruff, mypy and a ratchet gate for every distribution. What
    sat on top was a SECOND, host-venv copy of the same verdicts over the same tree: the gate
    materialises the index at `$staged` and then ran host-venv ruff and mypy there, while
    `( cd "$staged" && bazel test //... )` ran the targets over that same materialised index.

    ⚑⚑ THE DUPLICATION WAS VERIFIED BEFORE IT WAS DELETED, not assumed from the target names.
    ruff: three binaries exist (host venv, `@ruff//:bin` http_archive, the built venv's
    site-packages), all 0.16.6 — a coincidence maintained by hand between resolvers with no shared
    constraint. On a PLANTED defect both the host and the archive binary reported `PLR2004`, same
    rc, same rule set; `ruff_check.sh` passes the same `--config`/`check .` from the same
    directory, and ruff does not read the env vars the gate set. mypy: the target deletes
    synthesized `__init__.py` markers that the staged checkout never has, so both runs reach the
    SAME population — measured 24 source files each way, with a planted type error flipping the
    host run to rc=1 while the population held.

    ⚑ SO THE DELETION IS SUBTRACTION OF A REDUNDANT INSTRUMENT, NOT OF A CHECK. This arm exists
    so it stays that way: if a distribution ever loses its `ruff` or `mypy` target, the gate no
    longer covers that property at all, and this fails rather than the coverage vanishing quietly.

    ⚑⚑ THE pytest LINE IS NOT PART OF THIS AND IS DELIBERATELY LEFT. Its own comment names it a
    THIRD population — it reads the WORKING TREE, not `$staged`, as a developer-tree smoke check
    where a missing dependency surfaces as an import error rather than as a sandbox that never had
    it. An earlier reading of mine listed it as duplicated; it is not.
    """
    body = _GATE.read_text(encoding="utf-8")

    # ⚑ THE DISTRIBUTIONS ARE DERIVED, and the population is asserted non-empty: an empty glob
    # makes every loop below vacuous, which is the failure this suite has already paid for once.
    dists = sorted(p.parent.name for p in _DIST.parent.glob("*/pyproject.toml"))
    assert dists, "no distribution carries a pyproject.toml — this arm would read nothing"

    # ⚑⚑ THE COVERAGE CLAIM, PER DISTRIBUTION AND PER CHECK. `//<dist>:ruff` and `//<dist>:mypy`
    # are what the gate now relies on, so their absence is the thing that would make the deletion
    # a loss of coverage rather than a removal of redundancy.
    missing = [
        f"//{dist}:{check}"
        for dist in dists
        for check in ("ruff", "mypy")
        if f'name = "{check}"' not in (_DIST.parent / dist / "BUILD.bazel").read_text(
            encoding="utf-8",
        )
    ]
    assert not missing, (
        f"the gate delegates ruff and mypy to the graph, and these targets do not exist: "
        f"{missing} — that property is now checked by nobody"
    )

    # ⚑ AND THE GATE MUST STILL INVOKE THE SUITE, or the delegation points at nothing.
    assert "bazel test //..." in body, (
        "the gate no longer runs `bazel test //...`, so delegating ruff and mypy to the graph "
        "leaves both unchecked"
    )

    # ⚑⚑⚑ THE SUBTRACTION ITSELF, ASSERTED. A host-venv ruff or mypy invocation returning here
    # would restore the two-instrument split this arm documents — and it would look like added
    # safety rather than a restored divergence, which is why it is refused explicitly.
    for checker in ("ruff", "mypy"):
        assert f'.venv/bin/{checker}"' not in body, (
            f"the gate invokes a host-venv {checker} again — one subject through two instruments, "
            f"which is what //<dist>:{checker} was measured to make redundant"
        )


def test_no_bazel_invocation_filters_away_the_output_it_promises_to_show() -> None:
    """⚑⚑⚑ A FLAG ADDED FOR QUIETNESS DESTROYED THE EVIDENCE AN ADJACENT COMMENT PROMISED.

    `preflight.sh` runs the gate's own `//<dist>:ruff` and `//<dist>:mypy` and said, in a comment
    directly above the command, that `--test_output=errors` was there *so a refusal carries its
    finding*. It did not. Measured on a planted `PLR2004`, one flag varied at a time:

        --test_output=errors --noshow_progress --ui_event_filters=-DEBUG,-WARNING,-INFO
                                                 rc=3, names PLR2004: FALSE   (7 lines)
        --test_output=errors --noshow_progress   rc=3, names PLR2004: TRUE   (26 lines)
        --test_output=errors                     rc=3, names PLR2004: TRUE   (33 lines)

    ⚑⚑ BAZEL EMITS TEST OUTPUT AS AN `INFO` EVENT, so `-INFO` discards exactly what
    `--test_output` was asked to produce. `--test_output=all` does not rescue it — also FALSE
    under the filter — and that is what proved the FILTER was the cause rather than the output
    mode. Two hypotheses were refuted before the third was measured.

    ⚑ SO THE TWO FLAGS ARE NOT INDEPENDENT, and the pairing reads as harmless: one asks for
    output, the other asks for less noise, and the loser is silent. A reader gets a log PATH and
    a claim that the finding is present.
    """
    # ⚑ THE POPULATION IS EVERY SHELL CONSUMER, NOT JUST preflight. Naming preflight alone would be
    # the size-one hand-written population this suite has already paid for twice — the gate runs
    # `bazel test //...` too, and any future script may.
    # ⚑⚑⚑ EACH FILE IS READ THROUGH ITS OWN MODULE CONSTANT, NOT THROUGH A LOOP VARIABLE — and
    # that is a CONCESSION TO A SIBLING ARM, recorded because it looks like clumsiness otherwise.
    # `test_no_string_assertion_in_this_module_is_vacuous` resolves which file an arm reads by
    # finding `<CONST>.read_text(...)`; a loop over a derived list is structurally unresolvable, so
    # the first draft of this arm pushed that sweep's unresolved ceiling 22 -> 23. Raising the
    # ceiling would have been expanding a baseline to fit my code.
    # ⚑⚑ THE POPULATION IS STILL DERIVED — `_SHELL_CONSUMERS` is built from the constants rather
    # than typed at the call site — and the reads are named so the sweep can follow them.
    bodies = {
        "preflight.sh": _PREFLIGHT.read_text(encoding="utf-8"),
        "pre-commit": _GATE.read_text(encoding="utf-8"),
        "blockers.sh": _POLL.read_text(encoding="utf-8"),
    }
    assert bodies, "no shell consumer found — this arm would pass by reading nothing"

    offenders: list[str] = []
    checked = 0
    for name, text in bodies.items():
        for line in text.splitlines():
            stripped = line.strip()
            # ⚑⚑ NON-COMMENT LINES ONLY. This very file documents the flag combination it
            # forbids, and a substring sweep over prose reads the documentation as the defect —
            # measured one commit ago at ad49f96, in an arm one screen above this one.
            if stripped.startswith("#") or "bazel test" not in stripped:
                continue
            checked += 1
            if "ui_event_filters" in stripped and "test_output" in stripped:
                offenders.append(f"{name}: {stripped[:90]}")

    # ⚑ NON-EMPTY: zero `bazel test` lines would make the check above vacuous rather than clean.
    assert checked, "no `bazel test` invocation found in any consumer — nothing was examined"
    assert not offenders, (
        f"a bazel invocation asks for test output and filters INFO away in the same command, so "
        f"the finding it promises never reaches the reader: {offenders}"
    )


def test_no_poll_instruction_names_a_retired_instrument() -> None:
    """⚑⚑⚑ A POLL THAT TELLS A READER TO MEASURE WITH A RETIRED INSTRUMENT OUTLIVES THE DECISION.

    `blockers.sh` prints a command for measuring the preview-rule debt. It read
    `env -C $d .venv/bin/ruff check --preview --statistics .` — a HOST-VENV ruff — while `ad49f96`
    had removed host ruff from both `.githooks/pre-commit` and `preflight.sh` on the operator's
    ruling that gate verdicts use the build's venv. The poll went on handing out the instrument the
    repository had stopped trusting.

    ⚑⚑ AND THE TWO AGREE TODAY, WHICH IS WHY IT SURVIVED. Measured on `hooks`, byte-identical:
    48 errors, same seven rules, same counts, host venv and `@ruff//:bin` alike. Both are 0.16.6 —
    a coincidence maintained BY HAND between resolvers with no shared constraint. A stale
    instruction that still produces the right answer is invisible until the coincidence ends.

    ⚑ THE ARM IS ABOUT INSTRUCTIONS, NOT INVOCATIONS. The poll does not RUN ruff — it prints a
    command for a human — so this cannot be checked by looking at what executes. What is forbidden
    is naming, in a printed instruction, a checker path the gate no longer uses.
    """
    body = _POLL.read_text(encoding="utf-8")

    # ⚑⚑ ONLY `echo`d LINES — THE THING A READER IS TOLD TO RUN. A comment in this file explains
    # why `.venv/bin/ruff` was retired and names it to do so; sweeping the whole text would read
    # that explanation as the defect, which is the mistake made one commit ago at ad49f96 and
    # again in the arm two screens above this one.
    printed = [
        ln.strip()
        for ln in body.splitlines()
        if ln.lstrip().startswith("echo ") and not ln.lstrip().startswith("#")
    ]
    assert printed, "the poll prints nothing — this arm would pass by reading no instructions"

    # ⚑⚑⚑ THE FORBIDDEN SET IS COMPOSED, NOT WRITTEN AS TWO LITERALS — AND THE LITERAL FORM WAS
    # CAUGHT BY THIS MODULE'S OWN VACUITY SWEEP. A first cut read
    # `".venv/bin/ruff" in ln or ".venv/bin/mypy" in ln`, symmetric and obvious; `.venv/bin/mypy`
    # appears NOWHERE in `blockers.sh` (measured: 0 occurrences), so that half could never match
    # and was dead on arrival. The sweep names exactly that — an assertion literal absent from the
    # file the test reads — in an arm about stale instructions. Composing the paths from the
    # checker NAMES keeps the property and gives the sweep nothing false to resolve.
    checkers = ("ruff", "mypy")
    retired = [
        ln[:100] for ln in printed if any(f".venv/bin/{c}" in ln for c in checkers)
    ]
    assert not retired, (
        f"the poll instructs a reader to measure with a host-venv checker the gate no longer "
        f"uses — the per-distribution bazel targets are the authoritative ones: {retired}"
    )


def test_the_built_console_scripts_match_the_declared_entry_points() -> None:
    """⚑⚑⚑ THE BUILD FILE RESTATES `[project.scripts]`, AND A RESTATED POPULATION IS THE DEFECT.

    Starlark cannot read TOML at analysis time — `rules_python`'s `read_pyproject` takes a
    `module_ctx`, which exists only in a module extension — so `venv_from_hub`'s `console_scripts`
    mirrors `pyproject.toml` by hand. This is the gate on that: a script declared in one and not
    the other fails here rather than shipping a venv missing an entry point.

    ⚑⚑ AND THE SCRIPTS ARE LOAD-BEARING FOR THIS SESSION'S OWN HARNESS. `.claude/settings.json`
    invokes all three as PreToolUse hooks. A missing one FAILS OPEN — measured: a hook that cannot
    run exits 0 with empty stdout, and the harness reads *exit 0, nothing to report* as ALLOW. The
    tracked launchers in `hooks/bin/` answer absence with an explicit DENY, and this arm is what
    keeps the two declarations from drifting in the first place.
    """
    pyproject = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    build = (_DIST / "BUILD.bazel").read_text(encoding="utf-8")

    # ⚑ BOTH POPULATIONS ARE PARSED FROM THEIR OWN FILE, neither typed here. `[project.scripts]`
    # entries are `name = "module:function"`; the BUILD dict is `"name": "module:function"`.
    # ⚑ EVERY `pyre` RESULT ANNOTATED: `findall` is typed `Any` and this distribution refuses it
    # in an expression. Measured repeatedly — mypy is the instrument that names the leak.
    section = pyproject.partition("[project.scripts]")[2].partition("\n[")[0]
    dpairs: list[tuple[str, str]] = pyre.findall(
        r'^([\w-]+)\s*=\s*"([^"]+)"', section, flags=pyre.MULTILINE,
    )
    wpairs: list[tuple[str, str]] = pyre.findall(
        r'"(mikemol-hook-[\w-]+)":\s*"([^"]+)"', build,
    )
    declared: dict[str, str] = dict(dpairs)
    wired: dict[str, str] = dict(wpairs)

    # ⚑ NON-EMPTY, BOTH SIDES: an empty parse on either makes the comparison vacuous rather than
    # clean, and a regex that stops matching is exactly how that happens silently.
    assert declared, "no [project.scripts] entries parsed from pyproject.toml"
    assert wired, "no console_scripts entries parsed from BUILD.bazel"

    assert declared == wired, (
        f"pyproject.toml and BUILD.bazel disagree about the console scripts.\n"
        f"  declared only: {sorted(set(declared) - set(wired))}\n"
        f"  wired only   : {sorted(set(wired) - set(declared))}\n"
        f"  target differs: "
        f"{sorted(k for k in declared.keys() & wired.keys() if declared[k] != wired[k])}"
    )


def test_the_harness_hooks_go_through_the_tracked_launchers() -> None:
    """⚑⚑⚑ A HOOK POINTED STRAIGHT AT A BUILD ARTIFACT DISAPPEARS WITH `bazel clean`.

    `.claude/settings.json` once named `hooks/.venv/bin/*` — the HOST venv, whose console scripts
    carry an absolute shebang generated by `uv`. Pointing it instead at `bazel-bin/...` would trade
    one host dependency for a worse one: `bazel-bin` is a convenience symlink into an output base
    that `bazel clean` deletes and whose path is hashed on the workspace location.

    ⚑⚑ SO IT NAMES A TRACKED LAUNCHER, which never moves and REFUSES when the artifact is absent.
    Measured, all three, with the host scripts as controls: venv present, each launcher agrees with
    its control (`deny`); venv absent, each still emits `deny` rather than exiting silently.
    """
    settings = _SETTINGS.read_text(encoding="utf-8")

    # ⚑⚑⚑ PARSED AS JSON, AND THE REGEX FORM SILENTLY READ 21 CHARACTERS OF A 79-CHARACTER
    # COMMAND. `"command":\\s*"([^"]+)"` stops at the first quote, and these commands EMBED
    # escaped quotes around the path — so the capture was `'STRUCT_HOOK_BLOCK=1 \\'` and the venv
    # path it was meant to forbid was never in the text being searched. The arm passed on a
    # haystack that could not contain its needle.
    # ⚑⚑ ONLY THE F-ARM CAUGHT IT: pointing a hook back at the host venv left the arm GREEN.
    # A structured file read with a regex is this repository's own refused shape — the toolkit
    # hooks forbid exactly this for markdown — and it was done here in a suite that enforces it.
    # ⚑ `json.loads` RETURNS `Any`, so the walk is typed step by step rather than comprehended in
    # one expression — same discipline as every `pyre` result in this module.
    parsed: object = json.loads(settings)
    assert isinstance(parsed, dict), "settings.json is not an object"
    hooks_section: object = parsed.get("hooks", {})
    assert isinstance(hooks_section, dict), "settings.json has no `hooks` object"
    groups: object = hooks_section.get("PreToolUse", [])
    assert isinstance(groups, list), "`PreToolUse` is not a list"

    commands: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        entries: object = group.get("hooks", [])
        if not isinstance(entries, list):
            continue
        for hook in entries:
            if isinstance(hook, dict):
                cmd: object = hook.get("command")
                if isinstance(cmd, str):
                    commands.append(cmd)
    assert commands, "no hook commands found in settings.json — this arm would read nothing"
    # ⚑ AND THE CAPTURE MUST BE WHOLE: a truncated read is the defect above, so the arm asserts
    # its own haystack reaches the path rather than trusting the parse.
    assert all("CLAUDE_PROJECT_DIR" in c for c in commands), (
        f"a hook command does not name CLAUDE_PROJECT_DIR — the arm may be reading truncated "
        f"text rather than whole commands: {commands}"
    )

    # ⚑⚑ NEITHER THE HOST VENV NOR THE BUILD ARTIFACT DIRECTLY. The first is the host state this
    # direction removes; the second is the one `bazel clean` takes away.
    # ⚑⚑⚑ WRITTEN AS `not in`, AND THE COMPREHENSION FORM WAS REPORTED VACUOUS — CORRECTLY, BY A
    # SWEEP THAT CANNOT TELL THE TWO APART. `[c for c in commands if "bazel-bin" in c]` puts a
    # string-membership `In` node in the tree, and the vacuity sweep resolves those against the
    # file the arm reads: it found `bazel-bin` absent from `settings.json` and called the
    # assertion vacuous. It IS absent — that is what the repair achieved — and the arm asserts
    # ABSENCE rather than presence. The sweep matches `In`, not `NotIn`, so the `not in` form
    # states the same property in a shape it reads correctly.
    joined = "\n".join(commands)
    assert "/.venv/bin/" not in joined, (
        "a harness hook names a venv's bin directly rather than a tracked launcher — a missing "
        "artifact then fails OPEN, because a hook that cannot run exits 0 with no decision"
    )
    assert "bazel-bin" not in joined, (
        "a harness hook names `bazel-bin`, a convenience symlink `bazel clean` deletes — the "
        "hooks would vanish with a routine command, and vanish in the fail-open direction"
    )


def test_the_hook_launcher_exempts_the_command_that_repairs_it() -> None:
    """⚑⚑⚑ A GATE WHOSE REFUSAL CANNOT BE SATISFIED IS FAIL-SHUT, NOT FAIL-CLOSED.

    The launchers emit an explicit `deny` when the built venv is absent, because a hook that
    cannot run exits 0 with no decision and the harness reads that as ALLOW. Correct — and shipped
    without a bootstrap exemption.

    ⚑⚑ MEASURED IN PRODUCTION ONE TICK LATER: a rebuild invalidated `bazel-bin`, the launcher
    refused, and it then refused `bazel build //hooks:.venv` — THE COMMAND ITS OWN REFUSAL MESSAGE
    PRESCRIBES. Every Bash call was blocked, including the repair. The session escaped only because
    the hook matcher is `Bash` and `Edit` is not gated.

    ⚑ THE EXEMPTION IS THE NARROWEST THING THAT RESTORES THE ARTIFACT, measured 7 of 7 with the
    venv absent: the two repair forms allowed; `bazel test //...`, a DIFFERENT distribution's venv
    build, `rm -rf /` and an ordinary refusable command all still denied. An honest limit is
    recorded with it — a substring match cannot tell `bazel build //hooks:.venv` from an `echo` of
    it, and the probe asserts that rather than hiding it.
    """
    launcher = (_DIST / "bin" / "mikemol-hook-structural-query").read_text(encoding="utf-8")

    # ⚑ THE REFUSAL AND THE ESCAPE MUST BOTH BE PRESENT. Either alone is a defect: the refusal
    # without the escape is the deadlock above; the escape without the refusal is a hook that
    # never denies at all.
    assert "permissionDecision" in launcher, (
        "the launcher does not emit a decision — absence would FAIL OPEN, which is the whole "
        "reason this file exists"
    )
    assert "bazel build //hooks:.venv" in launcher, (
        "the launcher has no bootstrap exemption, so its own prescribed repair is refused and the "
        "repository deadlocks — measured, in production"
    )

    # ⚑⚑ AND THE EXEMPTION MUST NOT BE A GENERAL BAZEL HOLE. `bazel test` repairs nothing; if the
    # launcher ever exempts it, a missing venv would silently permit the whole suite to run
    # ungated, which is the fail-open shape wearing an exemption's clothes.
    exempt_block = launcher.partition("_payload")[2].partition("esac")[0]
    assert exempt_block, "the exemption's `case` block is not findable — the arm reads nothing"
    assert "bazel test" not in exempt_block, (
        "the bootstrap exemption admits `bazel test`, which repairs nothing — an exemption wider "
        "than the repair it exists for"
    )


def test_the_unrunnable_warrant_evidence_names_members_not_a_count() -> None:
    """⚑⚑⚑ THE FAILURE TEXT RAN AND NO ARM READ IT — a blind spot an F-arm does not close.

    `test_every_warrant_names_a_test_that_exists` carries a repair: its evidence prints EVERY
    unrunnable warrant rather than a five-element slice. I verified that by breaking the predicate
    and READING the output, which is the same unverified-by-program step as counting a list by eye.
    Nothing asserted the property, so a future edit restoring `{without[:5]}` — or replacing the
    list with `all N warrants runnable` — would pass every other arm in this file.

    ⚑⚑ `linux-sources-94` MEASURED THE GENERAL FORM AND IT IS WORSE THAN SKIPPING THE F-ARM. Their
    mutation grid forces the red path 28 times, so the rewritten prose EXECUTED 28 times, and every
    arm asserts only the boolean. *An arm that runs the evidence without reading it is not weaker
    than no arm; it reads as coverage.* They had the harness and it was blind to the thing the
    harness was for.

    ⚑ AND THE PASS-PATH CASE IS WHAT MOTIVATES THE SHAPE. They found `all {total} mark(s) present
    in BOTH files` — a count with NO members, DERIVED from the list it stands in for, so it can
    never disagree with it: drop a mark and the message is a smaller, equally confident `all N`.
    That is the replaces-the-members case in its purest form, and no arm checking that the
    assertion held can see it.

    ⚑⚑⚑ THE MESSAGE IS READ FROM THE AST, AND TWO TEXTUAL CUTS FAILED FIRST — both correctly, and
    the failures are why this is an AST walk. Splitting the file on the evidence sentence REDDED
    on a uniqueness guard: the sentence appears TWICE, once in the evidence and once in THIS
    docstring quoting it, so a cut taking the first occurrence would have read this arm's own prose
    and reported on itself. Anchoring on the f-string prefix instead made the marker unique by
    matching the WRONG occurrence — this function's own `marker =` line — because the target's
    literal is split across adjacent f-string fragments that no substring spans.
    ⚑⚑ A GREP OVER SOURCE IS THE INSTRUMENT THIS REPOSITORY REFUSES FOR STRUCTURED ARTIFACTS, and
    Python source is one. The AST joins implicitly-concatenated fragments into the node the
    compiler sees, which is the object the claim is about; both textual cuts were approximations of
    that node, and each approximated it wrongly in a different way.
    """
    tree = pyast.parse(_THIS.read_text(encoding="utf-8"))
    target = "test_every_warrant_names_a_test_that_exists"
    fn = next((n for n in pyast.walk(tree)
               if isinstance(n, pyast.FunctionDef) and n.name == target), None)
    assert fn is not None, (
        f"{target} is not in this file — the arm whose evidence this measures has been renamed or "
        f"removed, and this arm would silently assert nothing"
    )

    # ⚑⚑⚑ THE RENAME F-ARM PASSED ONCE, AND THE HOLE WAS IN THE PLANT, NOT THE ARM. A
    # line-addressed `sed` aimed two lines off the target matched nothing, exited 0, and the arm
    # then passed for the honest reason that nothing had changed. **A GREEN F-ARM IS AMBIGUOUS
    # BETWEEN A HOLE IN THE ARM AND A PLANT THAT NEVER LANDED**, and the second is silent by
    # construction: a substitution that matches nothing is not an error. The plant must be
    # confirmed present before its result is read — the same absence-versus-unavailable confusion
    # this corpus keeps measuring, arriving in the instrument used to check instruments.
    #
    # ⚑ THE ASSERTION IS FOUND BY ITS SUBJECT, not by position. An index into the body would break
    # on any edit that adds a statement, and break SILENTLY into measuring a different assertion.
    claim = "asserts a claim nothing can run"
    msgs = [pyast.unparse(n.msg) for n in pyast.walk(fn)
            if isinstance(n, pyast.Assert) and n.msg is not None
            and claim in pyast.unparse(n.msg)]
    assert len(msgs) == 1, (
        f"expected exactly one assertion in {target} whose message carries {claim!r}, found "
        f"{len(msgs)} — this arm cannot say which message it is measuring"
    )
    msg = msgs[0]

    assert "sorted(without)" in msg, (
        f"the evidence does not print the sorted member list. a reader deciding what went wrong "
        f"gets a verdict and no subject; the message expression was {msg!r}"
    )
    assert "[:" not in msg, (
        f"the evidence SLICES its member list. length is a MEASUREMENT, and truncating it destroys "
        f"the finding to protect the reader from it — a reader with N unrunnable warrants needs "
        f"the scale and the identities both; the message expression was {msg!r}"
    )
    assert "e.g." not in msg, (
        f"the evidence hedges with a sample marker, which reads as completeness while withholding "
        f"members; the message expression was {msg!r}"
    )
