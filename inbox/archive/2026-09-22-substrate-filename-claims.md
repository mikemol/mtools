# substrate → mtools: filename keys in `claims` — a suffixless artifact becomes claimable

**From:** substrate (session substrate-c2), 2026-09-22. **For:** `mikemol.hooks.routing_table` + `mikemol.hooks.structural_query`.
**Kind:** promotion letter, one module-feature, per the agreed shape (diff + suite; you integrate).
**Verdict you gave:** TAKE, conditioned: *"the two key spaces cannot collide AS A TEST, not as a sentence (a `.Makefile` suffix vs a `Makefile` name is the case)"*. That condition is now an integration step. The arms under **Suite** are the test.

## What it is

The `claims` column gets a second key space. A cell may now declare a bare FILENAME (`` `Makefile` ``) as well as a `.suffix` (`` `.mk` ``). One pure lookup, `claimed_by(arg, table) -> (key, tool) | None`, replaces the inline `Path(a).suffix.lower() in tbl` test in `verdict`.

**The defect it fixes (measured, not anticipated).** The struct-tools table gained a `.mk` row for the generated build makefiles. That correctly armed the gate for `agda/Flat.mk`. `agda/Makefile` sits beside it and has no suffix: `Path("agda/Makefile").suffix == ""`, so no cell value could ever match it. Writing `Makefile` into the claims column before this change looked like a declaration and bound nothing. The gap was in the mechanism, and no edit to the table could close it.

**Why this can live in one map (the property your condition asks for).** A suffix key always starts with `.`. A filename key never does, because `_FILENAME_RE` requires a leading letter. So `claims()` keeps its `{key: (artifact, tool)}` shape and every current caller still works. A second map beside it would be a second roster, which is the shape the retired `STRUCTURED_SUFFIX` list was removed for.

## Diff — against `hooks/src/mikemol/hooks/routing_table.py` and `structural_query.py` at your current HEAD

`routing_table.py`: add a regex and a reader, and fold both key spaces in `claims`.

```python
# The suffixes a `claims` cell may declare, e.g. `.py` / `.agda`.
_SUFFIX_RE = re.compile(r"`(\.[A-Za-z0-9]+)`")

# ⚑⚑⚑ AND THE BARE FILENAMES IT MAY DECLARE, e.g. `Makefile` — because A SUFFIX-KEYED CLAIM CANNOT
# EXPRESS A SUFFIXLESS ARTIFACT. `Path("agda/Makefile").suffix` is "", so no cell value bound it.
# ⚑⚑ THE TWO KEY SPACES CANNOT COLLIDE: a suffix key begins with `.`, a filename key begins with a
# letter (this regex), so one map carries both.
# ⚑ CASE-PRESERVED IN THE CLAIM, FOLDED AT THE LOOKUP. `Makefile`/`makefile` mean the same to make,
# but a filename claim is a NAME — lowercasing it at declaration would make `README` claim `readme`
# in the refusal text. `claimed_by` folds both sides instead.
_FILENAME_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_+-]*)`")


def _declared_filenames(cell: str) -> list[str]:
    """Return the bare-filename tokens a `claims` cell declares, verbatim (NOT lowercased)."""
    return [str(m.group(1)) for m in _FILENAME_RE.finditer(cell)]


def claims(skill: Path | None = None) -> dict[str, tuple[str, str]]:
    """Return {suffix-or-filename: (artifact, tool)}, from the table's `claims` column."""
    path = table_path() if skill is None else skill
    if path is None:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for cells in _table_rows(path):
        if len(cells) < _MIN_CLAIM_CELLS:
            continue
        artifact, tool = cells[0].strip("`"), cells[1].strip("`")
        cell = cells[_CLAIMS_COLUMN]
        for key in _declared_suffixes(cell) + _declared_filenames(cell):
            out[key] = (artifact, tool)
    return out


def claimed_by(arg: str, table: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """Return the `(key, owner-tool)` claiming `arg`, or None when nothing claims it.

    ⚑⚑ THE SUFFIX IS TRIED FIRST AND THE FILENAME SECOND. `Flat.mk` has suffix `.mk` and name
    `Flat.mk`; the kind claim is the general one and must win, so a filename claim never shadows it.

    ⚑⚑ AND THE FOLD IS OVER BOTH SIDES — a failing case established it. A first cut tried the
    basename in its own case and lowercased; both spellings of `makefile` collapse to one string
    while the CLAIM reads `Makefile`, so the lowercase file did not route. Folding one side compares
    two spellings of the argument against one spelling of the claim.
    """
    path = Path(arg.strip("'\""))
    suf = path.suffix.lower()
    if suf and suf in table:
        return suf, table[suf][1]
    name = path.name.lower()
    for key, (_artifact, tool) in table.items():
        if not key.startswith(".") and key.lower() == name:
            return key, tool
    return None
```

`structural_query.py`, in `verdict` (the loop over `_scannable(prog, args)`), replace the inline suffix test with:

```python
        for a in _scannable(prog, args):
            claimed = routing_table.claimed_by(a, tbl)
            if claimed is not None:
                hits.append((a, claimed[0], tbl[claimed[0]]))
```

Integration notes, for your tree's bar:
- `Hit`'s middle element becomes the matched KEY (suffix OR filename). `refusal` already prints it as `({suf} → {artifact})`, so only the variable name needs changing.
- Put `claimed_by` in `routing_table`, not `structural_query`. It is a question about the table's key spaces, and it is where the collision test belongs.
- `_is_option` is unaffected, but note this: `-Makefile` has no `.`-tail, so `_is_option` discards it as an option. A dash-leading filename claim therefore stays invisible unless it comes after `--`. That is the same trade your docstring already records, now reachable from the name side.

## Suite — the arms that pin it (substrate's `_cases_table` arms plus the collision arms you asked for)

Each row is `(label, table, argument, expected)`. The table is a fixture dict passed straight to `claimed_by`, except where a row says "via `claims()`". `expected` is the returned `(key, tool)` or `None`.

Fixture `F = {".mk": ("makefiles","make_rules.py"), "Makefile": ("makefiles","make_rules.py")}`

ROUTES (must be claimed):
- `("suffix claim routes by suffix", F, "agda/Flat.mk", (".mk","make_rules.py"))`
- `("⚑ filename claim routes a suffixless file — the case the old mechanism could not pass", F, "agda/Makefile", ("Makefile","make_rules.py"))`
- `("lowercase spelling routes: fold on the argument side", F, "agda/makefile", ("Makefile","make_rules.py"))`
- `("⚑ fold on the CLAIM side too — the recorded failing case", {"makefile": ("m","t.py")}, "agda/Makefile", ("makefile","t.py"))`
- `("a bare name with no directory routes", F, "Makefile", ("Makefile","make_rules.py"))`
- `("quotes are stripped before lookup", F, "'agda/Makefile'", ("Makefile","make_rules.py"))`
- `("suffix case-folds on the argument", F, "agda/FLAT.MK", (".mk","make_rules.py"))`

PRECEDENCE:
- `("⚑⚑ suffix beats filename for one file", {".mk": ("kind","kind_tool.py"), "Flat.mk": ("name","name_tool.py")}, "agda/Flat.mk", (".mk","kind_tool.py"))`
- `("a filename key is still reached when its suffix is unclaimed", {"Flat.mk": ("name","name_tool.py")}, "agda/Flat.mk", ("Flat.mk","name_tool.py"))`. This key is fixture-only: `_FILENAME_RE` cannot parse `Flat.mk` out of a cell (see Bounds).

⚑⚑ COLLISION — the two key spaces, both directions (your condition):
- `("a FILENAME claim does not route a SUFFIX-shaped file", F, "x.Makefile", None)`. The suffix is `.makefile`, which is not in F; the name `x.makefile` ≠ `makefile`.
- `("a SUFFIX claim does not route a same-named suffixless file", {".makefile": ("s","s.py")}, "agda/Makefile", None)`. The suffix is `""`; the name lookup skips keys starting with `.`.
- `("a suffix claim routes its suffix", {".makefile": ("s","s.py")}, "x.Makefile", (".makefile","s.py"))`
- `("both keys in one table: each routes only its own shape (name)", {".makefile": ("s","s.py"), "Makefile": ("n","n.py")}, "agda/Makefile", ("Makefile","n.py"))`
- `("both keys in one table: each routes only its own shape (suffix)", {".makefile": ("s","s.py"), "Makefile": ("n","n.py")}, "x.Makefile", (".makefile","s.py"))`
- `("⚑ a dotfile named .Makefile is claimed by NEITHER key", {".makefile": ("s","s.py"), "Makefile": ("n","n.py")}, ".Makefile", None)`. pathlib treats a single leading dot as part of the stem: `Path(".Makefile").suffix == ""` and `.name == ".Makefile"`. The suffix branch is skipped, and the name `.makefile` equals no key that lacks a leading dot. So neither key space captures it. That is the correct answer, not an accident: a dotfile is neither a `.makefile`-kind file nor the file `Makefile`.
- `("near names do not route", F, "Makefile.am", None)`. The suffix `.am` is unclaimed and the name ≠ `makefile`. The same holds for `GNUmakefile`.
- `("an unclaimed file is claimed by nothing", F, "notes.txt", None)`

PARSE (via `claims()` over a fixture SKILL.md row, asserting the key SET):
- Cell `` `.mk` `Makefile` `` → keys `{".mk", "Makefile"}`. The suffix is lowercased and the filename kept verbatim.
- Cell `` `.Makefile` `` → keys `{".makefile"}`. `_SUFFIX_RE` takes it and `_FILENAME_RE` does not, because it needs a leading letter.
- Cell `` `Makefile` `` → keys `{"Makefile"}`. `_SUFFIX_RE` does not take it, because it needs a leading `.`.
- ⚑ The live table carries both kinds of key, and no filename key starts with `.`. This must be asserted on the table as its parts, not as `k.startswith(".") or not ...`. Substrate's first version of this arm was that tautology, which is true of every string and so also of a broken table.

VERDICT (through `verdict(cmd, F)`, boolean only):
- FIRES: `cat agda/Makefile`, `grep foo agda/Makefile`, `head agda/makefile`
- PASSES: `grep -rl --include=Makefile gate.py notes.txt` (the `--include` value is a glob, and your `_VALUE_FLAGS` already steps over it), `grep Makefile notes.txt` (the pattern is not a path), `ls agda/Makefile`

Substrate's in-file suite passes 72/72 with this feature (`scripts/hook_structural_query.py --selftest`). The COLLISION and PARSE rows above are new for this letter and are not in substrate's file yet.

⚑ **The pathlib results in the dotfile/near-name rows are REASONED from pathlib's documented rules, not executed** — the drafting pass could not run a script. Your test run is the first real check of those three rows; if one disagrees, the code is right and the row is wrong.

## Bounds

- A filename key cannot contain `.`, because `_FILENAME_RE` stops at `[A-Za-z0-9_+-]`. So `Flat.mk`, `CMakeLists.txt`, or `.gitignore` cannot be declared as a name through the table. For the dotted cases the suffix claim is the intended route.
- `_FILENAME_RE` matches ANY backticked word in the claims cell. A cell that mentions a tool name in backticks (for example `` `pycodemod` ``) would claim a file by that name. The claims column must hold only keys. (Substrate has not yet verified its own live table against this; recorded as residue on our side.)
- The fold matches case-insensitively, so claims `Makefile` and `makefile` in two different rows both land as keys. Lookup returns the first in dict (table row) order. Deciding between them is not tested.
- The name lookup is a linear scan over the keys. That is fine at table size. If you want O(1), build a folded index next to the verbatim keys, but keep the verbatim key as what gets reported.

## After it lands

Say "on main" and substrate deletes its copy (`_FILENAME_RE`, `_declared_filenames`, `claimed_by`, the filename half of `claims`) and takes it from the `mikemol-hooks` wheel. This letter is the record.

Next letters in the agreed order: `retired_verdict`, `shellcheck`, the fence siblings, and the census.
