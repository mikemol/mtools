# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that every dist is built from the pinned sha in a clean tree and each artifact checked.

W1188. ⚑ THE UNCOMMITTED EDIT IS THE CONTROL FOR "NOTHING COMES FROM THE WORKING TREE": after the
commit, one dist's working-tree version is changed to a local one, and the result for the committed
sha must not move. ⚑ THE BAD DIST AND THE BROKEN DIST ARE THE OTHER CONTROLS: a local version is
refused by the metadata check, and an unparseable `pyproject.toml` is a row with a build error, with
the good dist still reported beside it. ⚑ THE BUILDS ARE REAL: setuptools builds a real sdist and
wheel into `tmp_path`, so the artifacts the checker reads are the ones a publish would upload.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import privacycheck, relcheck, wheel

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

PYTHON = sys.executable
PATHS = os.pathsep.join(sys.path)
_OWNER_ONLY = 0o700
_PYPROJECT = (
    '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n'
    '[project]\nname = "{name}"\nversion = "{version}"\ndescription = "a demonstration"\n'
    'readme = "README.md"\nrequires-python = ">=3.13"\nlicense = {{text = "Apache-2.0"}}\n'
)
_TWO = 2


def _tool(directory: Path, name: str, status: int, text: str) -> Path:
    """Write an executable stub that prints `text` and exits `status`.

    Returns:
        its path.

    """
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stdout.write({text!r})\nsys.exit({status})\n",
        encoding="utf-8",
    )
    script.chmod(_OWNER_ONLY)
    return script


def _judge(tool: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Name `tool` as the shipped-file privacy judge for the rest of the test (W1199)."""
    monkeypatch.setenv(privacycheck.TOOL_ENV, str(tool))


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _dist(root: Path, name: str, version: str) -> None:
    """Write one dist directory with a package, a README and a pyproject."""
    package = root / name / name.replace("-", "_")
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    # setuptools ships any LICEN[CS]E* in the dist directory and names it in `License-File` (W1205).
    (root / name / "LICENSE").write_text("Apache-2.0 text\n", encoding="utf-8")
    text = _PYPROJECT.format(name=name, version=version)
    if name.endswith("-rst"):
        # An unclosed inline literal: valid enough to build, refused by the README renderer.
        (root / name / "README.rst").write_text(f"{name}\n====\n\nUnclosed ``literal\n", "utf-8")
        text = text.replace('readme = "README.md"', 'readme = "README.rst"')
    else:
        (root / name / "README.md").write_text(f"# {name}\n\nreads well\n", encoding="utf-8")
    (root / name / "pyproject.toml").write_text(text, encoding="utf-8")


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, versions: dict[str, str]) -> Path:
    """Build a committed repository with one dist per entry of `versions`.

    A judge that passes is named first, so the build tests are about the build: without a named
    tool the privacy state is `unavailable`, a failure by design, which would fail every row.

    Returns:
        the repository's root.

    """
    _judge(_tool(tmp_path / "stubs", "privacy-ok", 0, ""), monkeypatch)
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    for name, version in versions.items():
        _dist(root, name, version)
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "dists")
    return root


def test_every_dist_at_the_sha_is_built_and_both_artifacts_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two clean dists: two rows, ok, built, an sdist and a wheel verdict each, in name order."""
    root = _repo(tmp_path, monkeypatch, {"demo-b": "0.0.2", "demo-a": "0.0.1"})
    sha = _git(root, "rev-parse", "HEAD")
    rows = relcheck.release_check(root, sha, tmp_path / "out")
    assert [r["dist"] for r in rows] == ["demo-a", "demo-b"]
    for row in rows:
        assert row["ok"] is True, row
        assert row["build"] == "ok"
        assert row["sha"] == sha
        assert isinstance(row["artifacts"], list)
        assert len(row["artifacts"]) == _TWO
    assert any(p.suffix == ".whl" for p in (tmp_path / "out" / "demo-a").iterdir())


def test_an_uncommitted_edit_does_not_change_what_the_sha_builds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: a local version in the working tree is not in the commit, so it is not seen."""
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1"})
    sha = _git(root, "rev-parse", "HEAD")
    (root / "demo-a" / "pyproject.toml").write_text(
        _PYPROJECT.format(name="demo-a", version="0.0.1+dirty"), encoding="utf-8"
    )
    rows = relcheck.release_check(root, sha, tmp_path / "out")
    assert rows[0]["ok"] is True, rows


def test_a_committed_local_version_is_refused_and_the_command_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bad dist is `ok` false with the reason in its artifacts, the good one still passes."""
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1", "demo-bad": "0.0.1+g0acbc18"})
    sha = _git(root, "rev-parse", "HEAD")
    assert wheel.main(["release-check", str(root), sha, str(tmp_path / "out")]) == 1
    rows = [cast("dict[str, object]", json.loads(x)) for x in capsys.readouterr().out.splitlines()]
    by_name = {str(r["dist"]): r for r in rows}
    assert by_name["demo-a"]["ok"] is True
    assert by_name["demo-bad"]["ok"] is False
    assert "local part" in json.dumps(by_name["demo-bad"]["artifacts"])


def test_a_dist_that_cannot_be_built_is_a_row_with_the_reason_beside_the_good_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unparseable pyproject: `ok` false and a build error, while demo-a is still reported."""
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1", "demo-broken": "0.0.1"})
    (root / "demo-broken" / "pyproject.toml").write_text("[project\nname =", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "break one")
    rows = relcheck.release_check(root, _git(root, "rev-parse", "HEAD"), tmp_path / "out")
    by_name = {str(r["dist"]): r for r in rows}
    assert by_name["demo-a"]["ok"] is True
    assert by_name["demo-broken"]["ok"] is False
    assert by_name["demo-broken"]["build"] != "ok"


def test_the_commands_stdout_is_json_only_and_the_build_noise_goes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run as a real process: every stdout line parses, and the backend's progress is on stderr.

    ⚑ A REAL PROCESS, NOT `main` IN THIS ONE: pytest swaps the logging handlers setuptools prints
    through, so an in-process run never showed the noise. The first real run over 34 dists buried
    34 result lines in 280 KB of `copying ...` on standard output.
    """
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1"})
    sha = _git(root, "rev-parse", "HEAD")
    env = {**os.environ, "PYTHONPATH": PATHS}
    command = [PYTHON, "-m", "mikemol.pkgbuild.wheel", "release-check", str(root), sha]
    done = subprocess.run(
        [*command, str(tmp_path / "out")], capture_output=True, text=True, env=env, check=False
    )
    assert done.returncode == 0, done.stderr
    rows = [cast("dict[str, object]", json.loads(line)) for line in done.stdout.splitlines()]
    assert [r["dist"] for r in rows] == ["demo-a"]
    assert "running sdist" in done.stderr


def test_a_tracked_test_file_the_sdist_drops_fails_the_row_until_the_manifest_grafts_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1230: conftest.py is not test*.py, so setuptools leaves it out; a graft puts it back."""
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1"})
    (root / "demo-a" / "tests").mkdir()
    (root / "demo-a" / "tests" / "conftest.py").write_text("X = 1\n", encoding="utf-8")
    (root / "demo-a" / "tests" / "test_a.py").write_text("def test_a() -> None: ...\n", "utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "tests")
    (failed,) = relcheck.release_check(root, _git(root, "rev-parse", "HEAD"), tmp_path / "o1")
    assert failed["ok"] is False
    assert failed["tests"] == "failed"
    assert "tests/conftest.py" in str(failed["tests_detail"])
    assert "tests/test_a.py" not in str(failed["tests_detail"])
    (root / "demo-a" / "MANIFEST.in").write_text("graft tests\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "manifest")
    (fixed,) = relcheck.release_check(root, _git(root, "rev-parse", "HEAD"), tmp_path / "o2")
    assert fixed["ok"] is True, fixed
    assert fixed["tests"] == "ok"


def test_a_readme_the_renderer_refuses_fails_the_row_though_the_metadata_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stdlib check passes both artifacts, twine's rendering refuses, so the row is not ok.

    ⚑ THIS IS WHAT W1189 ADDS: before it, `ok` came from the metadata alone, and a README that is
    valid text to a person and invalid to `readme_renderer` reached the upload before it failed.
    """
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1", "demo-rst": "0.0.1"})
    sha = _git(root, "rev-parse", "HEAD")
    by_name = {str(r["dist"]): r for r in relcheck.release_check(root, sha, tmp_path / "out")}
    assert by_name["demo-a"]["ok"] is True
    assert by_name["demo-a"]["twine"] == "ok"
    bad = by_name["demo-rst"]
    assert all(v["ok"] for v in cast("list[dict[str, object]]", bad["artifacts"]))
    assert bad["twine"] == "failed"
    assert bad["ok"] is False
    assert "render" in str(bad["twine_detail"]).lower()


def test_a_privacy_finding_fails_the_row_with_the_judge_output_beside_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The judge exits 1 with a finding: privacy `failed`, `ok` false, the output in the row.

    ⚑ THIS IS WHAT W1199 ADDS: metadata and rendering can both pass while a shipped file carries a
    secret or a home path nobody accepted.
    """
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1"})
    finding = '{"kind": "deny", "rule": "env-file"}\n'
    _judge(_tool(tmp_path / "stubs", "privacy-found", 1, finding), monkeypatch)
    sha = _git(root, "rev-parse", "HEAD")
    row = relcheck.release_check(root, sha, tmp_path / "out")[0]
    assert row["twine"] == "ok"
    assert row["privacy"] == "failed"
    assert row["ok"] is False
    assert "env-file" in str(row["privacy_detail"])


def test_a_missing_or_failing_judge_is_unavailable_and_never_a_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No tool named, and a judge that exits 2 (no opa), are both `unavailable` and not ok."""
    root = _repo(tmp_path, monkeypatch, {"demo-a": "0.0.1"})
    sha = _git(root, "rev-parse", "HEAD")
    monkeypatch.delenv(privacycheck.TOOL_ENV)
    row = relcheck.release_check(root, sha, tmp_path / "out")[0]
    assert row["privacy"] == "unavailable"
    assert row["ok"] is False
    _judge(_tool(tmp_path / "stubs", "privacy-nojudge", 2, "usage\n"), monkeypatch)
    row = relcheck.release_check(root, sha, tmp_path / "out2")[0]
    assert row["privacy"] == "unavailable"
    assert row["ok"] is False


def test_the_wrong_number_of_arguments_is_a_usage_error(tmp_path: Path) -> None:
    """`release-check ROOT` alone exits 2 and builds nothing."""
    assert relcheck.run([str(tmp_path)]) == _TWO
