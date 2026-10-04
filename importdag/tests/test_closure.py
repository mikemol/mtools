# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `closure`: a claim's engine roots, cones, file toggles and content toggles."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from mikemol.importdag.closure import (
    FuncDef,
    Witness,
    claim_rows,
    concept_keys,
    const_int,
    const_str,
    content_edges,
    dir_consts,
    dispatch_claims,
    div_literal,
    engine_cone,
    exists_paths,
    load,
    local_reads,
    main,
    membership_literal,
    module_roots,
    parents_prefix,
    parse_args,
    read_text_target,
    reads,
    resolve_path,
    resolved_roots,
    roots,
    script_roots,
    toggle_rows,
)

SEVEN = 7
USAGE_ERROR = 2
ROW_COUNT = 15
PARTS = ["paper", "checks", "claims.py"]
ENGINE = [
    "paperkit/bib.py",
    "paperkit/bibparse.py",
    "paperkit/gate.py",
    "paperkit/resolver.py",
    "paperkit/proj.py",
    "paperkit/model.py",
]

CHECK = """\
import model
from pathlib import Path

README = "gate.py"
ROOT = Path(__file__).resolve().parents[1]
CLAIMS = {"alpha": alpha, "beta": beta, "gamma": gamma}


def helper():
    import bib


def alpha():
    helper()
    return (ROOT / "report" / "gen.py").exists()


def beta():
    text = (ROOT / "README.md").read_text()
    other = "concept:gamma" + "concept:nowhere"
    return "needle" in text and "other" in (ROOT / "README.md").read_text() and other


def gamma():
    import resolver
    run = ["sibling.py", "broken.py", "claims.py", "missing.py"]
    return (ROOT / "checks" / "claims.py").exists() and (ROOT / "report").exists() and run
"""


def _expr(text: str) -> ast.expr:
    """Parse one expression.

    Returns:
        Its syntax tree.

    """
    return ast.parse(text, mode="eval").body


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Lay out an engine, a check module with three claims and its siblings, and enter it.

    Returns:
        The repository root, which is also the working directory.

    """
    monkeypatch.chdir(tmp_path)
    eng = tmp_path / "paperkit"
    eng.mkdir()
    for stem, text in {
        "bib": "import bibparse\n",
        "bibparse": "VALUE = 1\n",
        "gate": "import bib\n",
        "resolver": "VALUE = 2\n",
        "proj": "VALUE = 3\n",
        "model": "VALUE = 4\n",
    }.items():
        (eng / f"{stem}.py").write_text(text, encoding="utf-8")
    checks = tmp_path / "paper" / "checks"
    checks.mkdir(parents=True)
    (tmp_path / "paper" / "report").mkdir()
    (tmp_path / "paper" / "README.md").write_text("a needle here\n", encoding="utf-8")
    (checks / "claims.py").write_text(CHECK, encoding="utf-8")
    (checks / "sibling.py").write_text("import proj\n", encoding="utf-8")
    (checks / "broken.py").write_text("def (:\n", encoding="utf-8")
    return tmp_path


def _witness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Witness:
    """Load the project's check module against its engine.

    Returns:
        The witness context.

    """
    _project(tmp_path, monkeypatch)
    return load(Path("paper/checks/claims.py"), "paper/checks/claims.py", ENGINE)


def test_const_str_reads_only_string_constants() -> None:
    """A string constant yields its text; any other node yields None."""
    assert const_str(_expr("'abc'")) == "abc"
    assert const_str(_expr("7")) is None
    assert const_str(_expr("name")) is None


def test_const_int_reads_only_integer_constants() -> None:
    """An integer constant yields its value; any other node yields None."""
    assert const_int(_expr("7")) == SEVEN
    assert const_int(_expr("'7'")) is None
    assert const_int(_expr("name")) is None


def test_div_literal_splits_a_division_by_a_string() -> None:
    """`LEFT / "text"` yields the left node and the text; other shapes yield None."""
    got = div_literal(_expr("base / 'sub'"))
    assert got is not None
    assert ast.unparse(got[0]) == "base"
    assert got[1] == "sub"
    assert div_literal(_expr("base / other")) is None
    assert div_literal(_expr("base * 'sub'")) is None
    assert div_literal(_expr("base")) is None


def test_reads_finds_py_constants_naming_an_engine_stem() -> None:
    """Only a string ending in `.py` whose stem is an engine name counts, with any directory."""
    tree = ast.parse("a = 'gate.py'\nb = 'x/bib.py'\nc = 'other.py'\nd = 'bib'\ne = 7\n")
    assert reads(tree, {"gate", "bib", "bibparse"}) == {"gate", "bib"}


def test_parents_prefix_drops_n_plus_one_components() -> None:
    """`parents[N]` of the check path drops N+1 trailing components."""
    chain = "Path(__file__).resolve().parents[{}]"
    assert parents_prefix(_expr(chain.format(0)), PARTS) == "paper/checks"
    assert parents_prefix(_expr(chain.format(1)), PARTS) == "paper"
    root = parents_prefix(_expr(chain.format(2)), PARTS)
    assert root is not None
    assert not root


def test_parents_prefix_needs_file_and_a_constant_index() -> None:
    """Without `__file__`, or with a non-constant index, or off a non-subscript: None."""
    assert parents_prefix(_expr("Path(x).parents[1]"), PARTS) is None
    assert parents_prefix(_expr("Path(__file__).parents[i]"), PARTS) is None
    assert parents_prefix(_expr("Path(__file__).parents"), PARTS) is None
    assert parents_prefix(_expr("Path(__file__).other[1]"), PARTS) is None


def test_dir_consts_extends_known_prefixes_and_copies_its_input() -> None:
    """A chain binds a prefix, `NAME / "sub"` extends it, and the given mapping is not mutated."""
    src = (
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "ENGINE = ROOT / 'paperkit'\n"
        "TOP = Path(__file__).parents[2]\n"
        "UNDER = TOP / 'x'\n"
        "UNKNOWN = NOPE / 'y'\n"
        "plain = 3\n"
        "a, b = 1, 2\n"
        "NUM = ROOT / other\n"
    )
    given = {"EXTRA": "e"}
    got = dir_consts("paper/checks/claims.py", ast.parse(src).body, given)
    assert got == {
        "EXTRA": "e",
        "ROOT": "paper",
        "ENGINE": "paper/paperkit",
        "TOP": "",
        "UNDER": "x",
    }
    assert given == {"EXTRA": "e"}


def test_dir_consts_without_a_starting_mapping() -> None:
    """With no mapping given the result starts empty."""
    assert dir_consts("a/b.py", ast.parse("X = 1\n").body) == {}


def test_resolve_path_handles_chains_names_and_nested_divisions() -> None:
    """An inline chain, a known name and nested divisions resolve; anything else is None."""
    pref = {"ROOT": "paper"}
    assert resolve_path(_expr("Path(__file__).parents[1]"), pref, PARTS) == "paper"
    assert resolve_path(_expr("ROOT"), pref, PARTS) == "paper"
    assert resolve_path(_expr("ROOT / 'a' / 'b.py'"), pref, PARTS) == "paper/a/b.py"
    assert resolve_path(_expr("Path(__file__).parents[2] / 'a'"), pref, PARTS) == "a"
    assert resolve_path(_expr("UNKNOWN"), pref, PARTS) is None
    assert resolve_path(_expr("UNKNOWN / 'a'"), pref, PARTS) is None
    assert resolve_path(_expr("ROOT / name"), pref, PARTS) is None
    assert resolve_path(_expr("f(ROOT)"), pref, PARTS) is None


def test_exists_paths_collects_resolvable_exists_calls_only() -> None:
    """Only `exists()` calls on a resolvable path count; `is_file()` and unknown bases do not."""
    pref = {"ROOT": "paper"}
    src = (
        "def w():\n"
        "    (ROOT / 'a.txt').exists()\n"
        "    (ROOT / 'b.txt').is_file()\n"
        "    (UNKNOWN / 'c.txt').exists()\n"
        "    plain()\n"
    )
    assert exists_paths(ast.parse(src), pref, PARTS) == {"paper/a.txt"}


def test_read_text_target_returns_the_receiver() -> None:
    """A `X.read_text()` call yields X; other calls and nodes yield None."""
    got = read_text_target(_expr("(ROOT / 'a').read_text()"))
    assert got is not None
    assert ast.unparse(got) == "ROOT / 'a'"
    assert read_text_target(_expr("(ROOT / 'a').read_bytes()")) is None
    assert read_text_target(_expr("read_text()")) is None
    assert read_text_target(_expr("name")) is None


def test_local_reads_binds_names_to_resolved_paths() -> None:
    """A single-target assignment from `PATH.read_text()` binds the name to the path."""
    pref = {"ROOT": "paper"}
    src = (
        "def w():\n"
        "    gen = (ROOT / 'g.py').read_text()\n"
        "    unknown = (NOPE / 'g.py').read_text()\n"
        "    a = b = (ROOT / 'h.py').read_text()\n"
        "    other = (ROOT / 'i.py').read_bytes()\n"
        "    (x, y) = (ROOT / 'j.py').read_text()\n"
    )
    assert local_reads(ast.parse(src), pref, PARTS) == {"gen": "paper/g.py"}


def test_membership_literal_reads_a_single_in_test() -> None:
    """`"S" in X` yields S; other comparisons and non-literal lefts yield None."""
    assert membership_literal(_expr("'s' in text")) == "s"
    assert membership_literal(_expr("'s' not in text")) is None
    assert membership_literal(_expr("'s' in a in b")) is None
    assert membership_literal(_expr("name in text")) is None
    assert membership_literal(_expr("'s'")) is None


def test_content_edges_resolves_inline_and_local_comparators() -> None:
    """Both an inline `read_text()` comparator and a local bound to one give an edge."""
    pref = {"ROOT": "paper"}
    src = (
        "def w():\n"
        "    gen = (ROOT / 'g.py').read_text()\n"
        "    return ('one' in gen, 'two' in (ROOT / 'h.py').read_text(),\n"
        "            'three' in unbound, 'four' in (NOPE / 'x').read_text(), name in gen,\n"
        "            'five' in [1])\n"
    )
    assert content_edges(ast.parse(src), pref, PARTS) == {
        ("paper/g.py", "one"),
        ("paper/h.py", "two"),
    }


def test_engine_cone_is_transitive_and_includes_the_seed() -> None:
    """The cone follows every hop, survives a cycle, and tolerates a stem with no edges."""
    graph = {"a": {"b"}, "b": {"c", "a"}, "d": {"a"}}
    assert engine_cone(graph, {"a"}) == {"a", "b", "c"}
    assert engine_cone(graph, {"z"}) == {"z"}
    assert engine_cone(graph, set()) == set()


def test_dispatch_claims_reads_any_of_the_table_spellings() -> None:
    """Each spelling is read, a key becomes its text, and a non-name value is skipped."""
    src = (
        "CLAIMS = {'a': fa, 'b': 'text', 3: fc, **rest}\n"
        "CONCEPTS = {'c': fd}\n"
        "WITNESSES = {'w': fw}\n"
        "OTHER = {'x': fx}\n"
        "CLAIMS2 = 5\n"
        "NOTDICT = CLAIMS\n"
        "CLAIMS = [1]\n"
    )
    got = dispatch_claims(ast.parse(src))
    assert got == {"a": "fa", "3": "fc", "c": "fd", "w": "fw"}


def test_load_builds_names_graph_functions_and_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The witness holds stem to path, the flat import graph, the functions and the claims."""
    w = _witness(tmp_path, monkeypatch)
    assert w.names["bib"] == "paperkit/bib.py"
    assert w.igraph["gate"] == {"bib"}
    assert w.igraph["bib"] == {"bibparse"}
    assert set(w.funcs) == {"helper", "alpha", "beta", "gamma"}
    assert w.claims == {"alpha": "alpha", "beta": "beta", "gamma": "gamma"}
    assert w.relpath == "paper/checks/claims.py"
    assert w.check == Path("paper/checks/claims.py")


def test_load_keeps_the_last_path_of_a_repeated_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stem named twice resolves to its last path, unlike the refusing derivation."""
    _project(tmp_path, monkeypatch)
    (tmp_path / "paperkit" / "sub").mkdir()
    (tmp_path / "paperkit" / "sub" / "bib.py").write_text("VALUE = 5\n", encoding="utf-8")
    engine = [*ENGINE, "paperkit/sub/bib.py"]
    w = load(Path("paper/checks/claims.py"), "paper/checks/claims.py", engine)
    assert w.names["bib"] == "paperkit/sub/bib.py"


def test_module_roots_split_imports_from_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Top-level imports and `.py` reads are the shared roots; function bodies are not."""
    w = _witness(tmp_path, monkeypatch)
    assert module_roots(w) == ({"model"}, {"gate"})


def test_roots_follow_local_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A witness inherits the imports of the local helper it calls."""
    w = _witness(tmp_path, monkeypatch)
    assert roots(w, "alpha", set()) == ({"bib"}, set())
    assert roots(w, "gamma", set()) == ({"resolver"}, set())
    assert roots(w, "helper", set()) == ({"bib"}, set())


def test_roots_of_an_unknown_or_seen_function_are_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name that is not a function, or one already walked, contributes nothing."""
    w = _witness(tmp_path, monkeypatch)
    assert roots(w, "nowhere", set()) == (set(), set())
    assert roots(w, "alpha", {"alpha"}) == (set(), set())


def test_roots_include_reads_and_terminate_on_mutual_calls(tmp_path: Path) -> None:
    """A pure read is its own root kind, and two helpers that call each other terminate."""
    src = "def a():\n    b()\n    x = 'gate.py'\n\n\ndef b():\n    a()\n    import bib\n"
    tree = ast.parse(src)
    funcs: dict[str, FuncDef] = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    w = Witness(
        names={"bib": "bib.py", "gate": "gate.py"},
        igraph={},
        check=tmp_path / "x.py",
        relpath="x.py",
        tree=tree,
        funcs=funcs,
        claims={},
    )
    assert roots(w, "a", set()) == ({"bib"}, {"gate"})


def test_concept_keys_name_registered_claims_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `concept:` constant counts only when its key is a registered claim."""
    w = _witness(tmp_path, monkeypatch)
    assert concept_keys(w.funcs["beta"], w.claims) == {"gamma"}
    assert concept_keys(w.funcs["alpha"], w.claims) == set()
    assert concept_keys(_expr("'gamma'"), w.claims) == set()


def test_resolved_roots_follow_keys_transitively_and_stop_on_a_seen_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resolved key brings its witness's roots and those of the keys it resolves in turn."""
    w = _witness(tmp_path, monkeypatch)
    assert resolved_roots(w, "gamma", {"beta"}) == ({"resolver"}, set())
    assert resolved_roots(w, "gamma", {"gamma"}) == (set(), set())
    assert resolved_roots(w, "nowhere", set()) == (set(), set())
    chained = ast.parse("def p():\n    import bib\n\n\ndef q():\n    return 'concept:p'\n")
    funcs: dict[str, FuncDef] = {f.name: f for f in chained.body if isinstance(f, ast.FunctionDef)}
    chain = Witness(
        names={"bib": "bib.py"},
        igraph={},
        check=tmp_path / "x.py",
        relpath="x.py",
        tree=chained,
        funcs=funcs,
        claims={"kp": "p", "kq": "q"},
    )
    assert resolved_roots(chain, "kq", set()) == (set(), set())
    assert resolved_roots(chain, "kp", set()) == ({"bib"}, set())


def test_script_roots_read_sibling_scripts_and_skip_the_check_and_broken_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A named sibling script seeds its imports; the check itself and a syntax error do not."""
    w = _witness(tmp_path, monkeypatch)
    assert script_roots(w, w.funcs["gamma"]) == {"proj"}
    assert script_roots(w, w.funcs["alpha"]) == set()


def test_toggle_rows_decide_polarity_from_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent file is injected, a present one dropped, a directory skipped."""
    w = _witness(tmp_path, monkeypatch)
    assert toggle_rows("alpha", w.funcs["alpha"], w) == ["alpha\tfile+:paper/report/gen.py"]
    assert toggle_rows("gamma", w.funcs["gamma"], w) == ["gamma\tfile-:paper/checks/claims.py"]
    assert toggle_rows("beta", w.funcs["beta"], w) == [
        "beta\tcontent-\tpaper/README.md\tneedle",
        "beta\tcontent+\tpaper/README.md\tother",
    ]


def test_toggle_rows_inject_a_substring_into_a_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substring tested against a file that does not exist is an injection."""
    w = _witness(tmp_path, monkeypatch)
    (tmp_path / "paper" / "README.md").unlink()
    assert toggle_rows("beta", w.funcs["beta"], w) == [
        "beta\tcontent+\tpaper/README.md\tneedle",
        "beta\tcontent+\tpaper/README.md\tother",
    ]


def test_claim_rows_emit_cone_reads_files_and_contents_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cone is expanded, a pure read follows it, then the file and content toggles."""
    w = _witness(tmp_path, monkeypatch)
    base = module_roots(w)
    assert claim_rows(w, "alpha", base) == [
        "alpha\tpaperkit/bib.py",
        "alpha\tpaperkit/bibparse.py",
        "alpha\tpaperkit/model.py",
        "alpha\tread:paperkit/gate.py",
        "alpha\tfile+:paper/report/gen.py",
    ]
    assert claim_rows(w, "beta", base) == [
        "beta\tpaperkit/model.py",
        "beta\tpaperkit/resolver.py",
        "beta\tread:paperkit/gate.py",
        "beta\tcontent-\tpaper/README.md\tneedle",
        "beta\tcontent+\tpaper/README.md\tother",
    ]
    assert claim_rows(w, "gamma", base) == [
        "gamma\tpaperkit/model.py",
        "gamma\tpaperkit/proj.py",
        "gamma\tpaperkit/resolver.py",
        "gamma\tread:paperkit/gate.py",
        "gamma\tfile-:paper/checks/claims.py",
    ]


def test_an_import_wins_over_a_read_of_the_same_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A module both imported and read is in the cone, so it is not also a read root."""
    w = _witness(tmp_path, monkeypatch)
    rows = claim_rows(w, "alpha", ({"model", "gate"}, {"gate"}))
    assert "alpha\tpaperkit/gate.py" in rows
    assert "alpha\tread:paperkit/gate.py" not in rows


def test_parse_args_types_the_namespace_and_defaults_relpath() -> None:
    """The check, the engine paths and an empty default relpath are read."""
    a = parse_args(["--check", "c.py", "e1.py", "e2.py"])
    assert (a.check, a.relpath, a.engine) == ("c.py", "", ["e1.py", "e2.py"])


def test_parse_args_keeps_argparse_abbreviations_and_the_relpath_option() -> None:
    """An unambiguous abbreviation of an option still works, as it did under argparse."""
    a = parse_args(["--ch", "c.py", "--rel", "p/c.py", "e.py"])
    assert (a.check, a.relpath, a.engine) == ("c.py", "p/c.py", ["e.py"])


def test_parse_args_requires_the_check_and_an_engine_module() -> None:
    """A missing `--check` or an empty engine list is a usage error, exit 2."""
    with pytest.raises(SystemExit) as no_check:
        parse_args(["e.py"])
    assert no_check.value.code == USAGE_ERROR
    with pytest.raises(SystemExit) as no_engine:
        parse_args(["--check", "c.py"])
    assert no_engine.value.code == USAGE_ERROR


def test_help_describes_the_tool(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` survives the move to a typed namespace: it prints the usage and exits 0."""
    with pytest.raises(SystemExit) as ex:
        parse_args(["--help"])
    assert ex.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: closure ")
    assert "--relpath" in out
    assert "closure roots" in out


def test_main_prints_every_claim_in_key_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rows come out claim by claim, sorted by key, one per line."""
    _project(tmp_path, monkeypatch)
    assert main(["--check", "paper/checks/claims.py", *ENGINE]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "alpha\tpaperkit/bib.py"
    assert [ln.split("\t")[0] for ln in lines] == sorted(ln.split("\t")[0] for ln in lines)
    assert "gamma\tfile-:paper/checks/claims.py" in lines
    assert len(lines) == ROW_COUNT


def test_main_uses_relpath_to_resolve_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The repository-relative path decides what `parents[N]` means, not the file's location."""
    _project(tmp_path, monkeypatch)
    check = ["--check", "paper/checks/claims.py", "--relpath", "deep/er/checks/claims.py"]
    assert main([*check, *ENGINE]) == 0
    assert "alpha\tfile+:deep/er/report/gen.py" in capsys.readouterr().out.splitlines()


def test_main_reads_sys_argv_when_not_given_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv the process arguments are used."""
    _project(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["closure", "--check", "paper/checks/claims.py", *ENGINE])
    assert main() == 0
    assert capsys.readouterr().out.startswith("alpha\t")


def test_runs_as_a_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`python -m mikemol.importdag.closure` prints the rows and exits 0."""
    _project(tmp_path, monkeypatch)
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "mikemol.importdag.closure",
            "--check",
            "paper/checks/claims.py",
            *ENGINE,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout.startswith("alpha\tpaperkit/bib.py\n")
