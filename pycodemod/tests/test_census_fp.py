# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.census_fp`: the modelled set and the Census arithmetic.

The four wider-seed tests and the gcd-class pair are transcribed from the origin selftest; the
tests marked AUTHORED are fresh, covering the explicit-seed contract, returned skips and every
reader the origin never exercised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import census_fp as cf

if TYPE_CHECKING:
    from pathlib import Path

_PAIR = 2
_TRIPLE = 3


def _site(line: int, refs: set[str], path: str = "m.py") -> cf.FpSite:
    return cf.FpSite(path, line, "if", "unclassified", "f", f"snippet {line}", frozenset(refs))


def _fixture() -> list[cf.FpSite]:
    return [_site(2, {"rows"}), _site(3, {"core_id", "r", "lim"})]


def _seed(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _censuses(tmp_path: Path) -> tuple[cf.Census, cf.Census]:
    seed_a = _seed(tmp_path, "seed_a.py", 'T = "core_id"\n')
    seed_b = _seed(tmp_path, "seed_b.py", 'T = "core_id"\nU = "rows"\nV = "lim"\n')
    narrow = cf.Census(_fixture(), cf.modelled_keys([seed_a]).keys)
    wide = cf.Census(_fixture(), cf.modelled_keys([seed_b]).keys)
    return narrow, wide


def test_wider_seed_lowers_total_remainder_omega(tmp_path: Path) -> None:
    """A wider modelled set leaves fewer unmodelled referent-incidences."""
    narrow, wide = _censuses(tmp_path)
    assert (narrow.total_remainder_omega(), wide.total_remainder_omega()) == (_TRIPLE, 1)


def test_wider_seed_lowers_total_remainder_bits(tmp_path: Path) -> None:
    """A wider modelled set leaves a smaller total bit length."""
    narrow, wide = _censuses(tmp_path)
    assert wide.total_remainder_bits() < narrow.total_remainder_bits()


def test_wider_seed_explains_at_least_as_many_sites(tmp_path: Path) -> None:
    """Growing the seed never un-explains a site; here it explains one more."""
    narrow, wide = _censuses(tmp_path)
    assert (narrow.explained_sites(), wide.explained_sites()) == (0, 1)


def test_every_remainder_divides_its_narrower_seed_remainder(tmp_path: Path) -> None:
    """The law is per site: the wider remainder divides the narrower one, row by row."""
    narrow, wide = _censuses(tmp_path)
    assert all(x.rem % y.rem == 0 for x, y in zip(narrow.rows, wide.rows, strict=True))


def test_decode_is_exact_on_every_row(tmp_path: Path) -> None:
    """AUTHORED: the understood primes times the remainder recover each fingerprint."""
    narrow, _wide = _censuses(tmp_path)
    for row in narrow.rows:
        product = 1
        for key in row.known:
            product *= narrow.reg.primes[key]
        assert product * row.rem == row.fp


def test_empty_modelled_set_explains_nothing_and_leaves_whole_fingerprints() -> None:
    """AUTHORED: with nothing modelled every remainder is its fingerprint."""
    census = cf.Census(_fixture(), frozenset())
    assert [(r.rem, r.known) for r in census.rows] == [(r.fp, ()) for r in census.rows]


def test_empty_site_list_is_a_census_of_nothing() -> None:
    """AUTHORED: no sites give zero metrics and a maximum fingerprint of 1."""
    census = cf.Census([], frozenset({"a"}))
    assert (
        census.total_remainder_omega(),
        census.total_remainder_bits(),
        census.explained_sites(),
        census.max_fingerprint(),
    ) == (0, 0, 0, 1)


def test_primes_are_assigned_by_descending_frequency_then_key() -> None:
    """AUTHORED: the commonest referent gets 2; a tie falls to key order."""
    sites = [_site(1, {"z", "a"}), _site(2, {"z", "b"}), _site(3, {"z"})]
    census = cf.Census(sites, frozenset())
    assert [census.reg.prime_for(k) for k in ("z", "a", "b")] == [2, 3, 5]


def test_referent_incidences_and_max_fingerprint_count_the_site_refs() -> None:
    """AUTHORED: incidences repeat across sites; the maximum is the largest product."""
    census = cf.Census(_fixture(), frozenset())
    assert (census.referent_incidences(), census.max_fingerprint()) == (
        _TRIPLE + 1,
        max(r.fp for r in census.rows),
    )


def test_residual_order_puts_the_largest_remainder_first_and_ties_by_position() -> None:
    """AUTHORED: more unmodelled referents sort first; equal remainders sort by path then line."""
    sites = [_site(9, {"a"}), _site(5, {"a", "b", "c"}), _site(4, {"a"}, path="b.py")]
    census = cf.Census(sites, frozenset())
    order = [(r.site.path, r.site.line) for r in census.residual_order(_TRIPLE)]
    assert order == [("m.py", 5), ("b.py", 4), ("m.py", 9)]


def test_residual_order_truncates_to_n() -> None:
    """AUTHORED: only the first n rows are returned."""
    census = cf.Census(_fixture(), frozenset())
    assert len(census.residual_order(1)) == 1


def test_explaining_keys_count_sites_per_modelled_key() -> None:
    """AUTHORED: a key is credited once per site it decodes in; order is count then key."""
    sites = [_site(1, {"a", "b"}), _site(2, {"a"}), _site(3, {"c"})]
    census = cf.Census(sites, frozenset({"a", "b"}))
    assert census.explaining_keys(_TRIPLE) == [("a", _PAIR), ("b", 1)]


def test_explaining_keys_truncates_to_n() -> None:
    """AUTHORED: n bounds the table."""
    census = cf.Census([_site(1, {"a", "b"})], frozenset({"a", "b"}))
    assert census.explaining_keys(1) == [("a", 1)]


def _unknown_four() -> cf.Census:
    sites = [
        _site(1, {"u", "v", "w"}),
        _site(2, {"u", "v", "z"}),
        _site(3, {"q"}),
        _site(4, {"u", "q"}),
    ]
    return cf.Census(sites, frozenset())


def test_two_sites_sharing_two_unknown_referents_form_a_class_of_omega_two() -> None:
    """Two sites sharing two unknown referents are one class of Omega 2; the others are out."""
    classes, candidates = _unknown_four().gcd_classes(_TRIPLE)
    assert [(c.omega, [m.site.line for m in c.members]) for c in classes] == [(_PAIR, [1, 2])]
    assert candidates == 1


def test_gcd_classes_with_a_lower_floor_rank_by_membership_then_omega() -> None:
    """AUTHORED: min_omega 1 admits single shared referents; the biggest class ranks first."""
    classes, candidates = _unknown_four().gcd_classes(_TRIPLE, min_omega=1)
    assert [[m.site.line for m in c.members] for c in classes] == [[1, 2, 4], [1, 2], [3, 4]]
    assert candidates == _TRIPLE


def test_gcd_classes_truncate_to_top() -> None:
    """AUTHORED: top bounds the classes while the candidate count stays whole."""
    classes, candidates = _unknown_four().gcd_classes(1, min_omega=1)
    assert (len(classes), candidates) == (1, _TRIPLE)


def test_fully_modelled_sites_form_no_class() -> None:
    """AUTHORED: a site with remainder 1 shares no unknown structure."""
    census = cf.Census([_site(1, {"a", "b"}), _site(2, {"a", "b"})], frozenset({"a", "b"}))
    assert census.gcd_classes(_TRIPLE) == ([], 0)


def test_modelled_keys_reads_referents_and_declared_names(tmp_path: Path) -> None:
    """AUTHORED: strings, names, attributes, def and class names all join; SQL blobs do not."""
    seed = _seed(
        tmp_path,
        "decl.py",
        'T = "core_id"\nsql = "select * from t"\n\n'
        "def build(): ...\n\nasync def later(): ...\n\nclass Rel:\n    col = x.attr\n",
    )
    got = cf.modelled_keys([seed])
    assert (sorted(got.keys), got.skipped) == (
        ["Rel", "T", "attr", "build", "col", "core_id", "later", "sql", "x"],
        (),
    )


def test_modelled_keys_has_no_default_seed() -> None:
    """AUTHORED: no paths model nothing."""
    assert cf.modelled_keys([]) == cf.Modelled(frozenset())


def test_modelled_keys_returns_skipped_files(tmp_path: Path) -> None:
    """AUTHORED: a missing, an unparseable and an undecodable seed are returned, not swallowed."""
    good = _seed(tmp_path, "good.py", "ok = 1\n")
    broken = _seed(tmp_path, "broken.py", "def (:\n")
    binary = tmp_path / "binary.py"
    binary.write_bytes(b"\xff\xfe\x00bad")
    missing = str(tmp_path / "absent.py")
    got = cf.modelled_keys([good, broken, str(binary), missing])
    assert (sorted(got.keys), [(s.path, s.why) for s in got.skipped]) == (
        ["ok"],
        [(broken, "unparseable"), (str(binary), "undecodable"), (missing, "unreadable")],
    )


def test_modelled_keys_drops_an_over_long_declared_name(tmp_path: Path) -> None:
    """AUTHORED: a def name past MAX_TOKEN is prose and is dropped from the modelled set."""
    seed = _seed(tmp_path, "long.py", f"def {'f' * 65}(): ...\n")
    assert cf.modelled_keys([seed]).keys == frozenset()
