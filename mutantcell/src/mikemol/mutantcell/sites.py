# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Enumerate every perturbation site of an engine as (module, SPEC) pairs.

Ported from paperkit's `tools/sites.py` (paperkit:W142). A SPEC is a mutation the sibling
`mikemol.mutation.mutate` understands. The def-sweep's original surface was def-sites only, a def's
behaviour going from present to absent. A perturbation toggles an element's presence, so the surface
generalizes to the import graph, enumerating present elements to DROP and absent ones to INJECT:

    QUALNAME      drop a def's behaviour (a bare qualname is a def-drop to the mutator).
    branch:QN#N   drop one branch arm's behaviour: a finer, still monotone reach probe, additive
                  to the def-drop, with the same raise and the same grid path.
    flip:QN#N     invert one condition. Non-monotone, so it is routed to the decision-coverage
                  grid and not to the sensitivity sweep.
    data-:NAME#N  drop one key or element of a module-level dict, list, set or tuple literal: the
                  data analog of a branch drop, still monotone. A dict whose every read swallows a
                  dropped key is refused by the data enumerator.
    dflip:NAME#N  perturb one dict value or non-set element to a valid same-position
                  counterfactual: the data analog of a flip, non-monotone. A set element has no
                  perturbable value, so a set contributes no dflip.
    import+:NAME  inject an absent engine import, the negative polarity over which a "module does
                  not import X" assertion becomes falsifiable. NAME ranges over the engine
                  modules the target does not already import: a bounded candidate set.

The command line prints `module<TAB>spec`, one line per site; the grid runs the mutator on each
pair. The mutator's own module spells the specs, and its enumerators are the one source the
in-process sweep also reads, so there is no second copy to drift. An import drop is omitted:
dropping an import breaks the module, which the def-drop of any function using it already covers.

The mutator is a sibling distribution, imported by package name. This module never runs it as a
child process, so no interpreter path is chosen here; the grid that consumes the output runs
`python -m mikemol.mutation.mutate MODULE SPEC`.

Usage:  python -m mikemol.mutantcell.sites <module.py> ...
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.importdag.dagderive import flat_imports
from mikemol.mutation.mutate import branch_sites, data_sites, flip_sites

from mikemol.mutantcell.def_sites import def_sites

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


def sites(path: str | Path, names: set[str]) -> Iterator[str]:
    """Enumerate the perturbation SPECS for one module, in a fixed order.

    The order is its def-drops, its branch-arm and condition sites, its data key-drops and
    value-perturbs, and its import injects of the engine modules in `names` that it does not
    already import by the flat spelling (and that are not the module itself), sorted.

    Yields:
        Each spec string.

    """
    text = Path(path).read_text(encoding="utf-8")
    yield from def_sites(text)
    for qn, n, _arm in branch_sites(text):
        yield f"branch:{qn}#{n}"
    for qn, n, _test in flip_sites(text):
        yield f"flip:{qn}#{n}"
    for qn, n, kind, _key, _val in data_sites(text):
        yield f"data-:{qn}#{n}"
        if kind != "Set":
            yield f"dflip:{qn}#{n}"
    absent = names - flat_imports(text, names) - {Path(path).stem}
    for name in sorted(absent):
        yield f"import+:{name}"


def main(argv: Sequence[str] | None = None) -> int:
    """Print `module<TAB>spec` for every site of every named module.

    The engine's module set is the stem of each named file, so the files named are the engine.

    Returns:
        0.

    """
    paths = list(sys.argv[1:] if argv is None else argv)
    names = {Path(p).stem for p in paths}
    for p in paths:
        for spec in sites(p, names):
            sys.stdout.write(f"{p}\t{spec}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
