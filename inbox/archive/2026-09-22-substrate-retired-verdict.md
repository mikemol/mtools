# substrate → mtools: `retired_verdict` — a retired tool mode is refused, and the refusal names its successor

**From:** substrate (session substrate-c2), 2026-09-22. **For:** `mikemol.hooks.structural_query` (plus one reader in `mikemol.hooks.routing_table`).
**Kind:** promotion letter covering one module-feature, in the agreed shape (diff + suite; you integrate).
**Verdict you gave:** TAKE (the take-all revision). Second of the five.

## What it is

A second verdict that runs independently of `verdict()`. `retired_verdict(cmd) -> str` returns a refusal when `cmd` invokes a RETIRED mode of a structural tool, and `""` otherwise. The refusal names the retired flag, why it was retired, the measurement that retired it, and the successor to run instead. It never answers.

The two predicates ask different questions. `verdict()` asks whether a TEXTUAL tool is being pointed at a STRUCTURED artifact. `retired_verdict()` asks whether a RETIRED mode of a structural tool is being invoked. One predicate carrying both would answer two things at once, and the routing table that feeds the first has nothing to say about the second.

**The measured defect it repairs.** Two `pycodemod` modes returned FALSE ZEROS with full confidence, each reproduced against a positive control:

- `--attr <Recv>.<leaf>` was documented but never implemented. Only `.*` was special-cased, so a dotted operand was compared against a bare attribute name and could never match. For `corpus.ROOT` the origin said 0; the successor `substrate/attr_reads.py` finds 121 in 66 files.
- `--importers <module>` keyed on the first dotted component. Inside a package every importer spells the dependency as the package, so a submodule query answered 0. For `substrate.corpus` the origin said 0; the successor `substrate/module_importers.py` finds 68 in 68 files.

A superseded reader that still RESPONDS is worse than a deleted one: it answers whoever reaches the old spelling first, wrongly, and substrate deletes on a zero (`--dead`). So the contract is refuse-with-redirect — your repo's own gate shape (`orphan_check`, the poll's UNREADABLE lines), carried into the hook layer. (It fired on substrate's own session twice on 2026-09-21, which is how the redirect's wording below was tested on a real reader.)

**The pairing.** You dissolved `consumer_operators` in favour of one operator authority (`cmdparse.OPERATORS`). Substrate is PORTING to that — deleting its roster and the bridge — rather than sending it. If a stray invocation of the dissolved surface ever needs refusing, this verdict is the mechanism; see the whole-tool bound below.

## Diff — against `hooks/src/mikemol/hooks/structural_query.py` at 40733e6

Substrate's copy has two parts. The verdict lives in `scripts/hook_structural_query.py` (`retired_verdict`, :408-438; main call site :501-511; optional import :81-93). The roster and the conjunction live in `substrate/pycodemod_retired.py` (`SUPERSEDED`, `ORIGIN_STEMS`, `names_origin`, `retired_in_command`, `superseded_in`, `refusal`), imported optionally so borrowing checkouts without a `substrate/` package degrade to "no retirement verdict here" rather than crash.

**Where the roster should live: a per-repo table, read the way `routing_table.claims()` reads.** The roster is a fact about the ADOPTING repo's tools (`pycodemod` exists only in substrate), so it should neither travel as package data nor stay a Python import (the import is what forced the `_RETIRED is None` branch). It becomes a second table in the same skill file, read by the same parser. An adopter with no such table gets no retirements — the honest degradation substrate built by hand with `try/except ImportError`.

Proposed table, in `.claude/skills/struct-tools/SKILL.md` under its own heading:

```markdown
| retired | origin | successor | why | measured |
|---|---|---|---|---|
| `--attr` | `pycodemod` | `substrate/attr_reads.py` | dotted operand compared against a bare attr name; could never match | corpus.ROOT: origin 0, successor 121 in 66 files |
| `--importers` | `pycodemod` | `substrate/module_importers.py` | keyed on first dotted component; submodule queries answered 0 | substrate.corpus: origin 0, successor 68 in 68 files |
```

⚑ Your `_table_rows` currently takes every `|` row in the file, so a second table would be read as routing rows too. Neither current reader breaks (`claims()` needs a backticked `.suffix` in column 3, and a retirement row's column 3 is a path), but `routes()` would list retirement rows as (artifact, tool) pairs. The reader below selects rows by the header they follow; adopt that or your own section scoping, as long as the two tables stay disjoint.

In `routing_table.py`:

```python
from dataclasses import dataclass

# The header cell that opens the retirement table; rows are read only under it.
_RETIRED_HEADER = "retired"
_MIN_RETIRED_CELLS = 5


@dataclass(frozen=True, slots=True)
class Retirement:
    """One retired mode of one tool, its successor, and the measurement that retired it.

    ⚑ `measured` is what makes the retirement FALSIFIABLE: a reader re-runs that comparison and
    sees the origin's zero against the successor's count, rather than trusting the table.
    """

    flag: str
    origin: str      # a file STEM, not a path: every invocation spelling shares it
    successor: str
    why: str
    measured: str


def retirements(skill: Path | None = None) -> dict[tuple[str, str], Retirement]:
    """Return {(origin_stem, flag): Retirement} from the repo's retirement table.

    ⚑ An absent table and an empty one both yield {} here, and that collapse is harmless in this
    direction only: no row means no refusal, which is the pre-feature behaviour.
    """
    path = table_path() if skill is None else skill
    if path is None:
        return {}
    try:
        src = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    out: dict[tuple[str, str], Retirement] = {}
    inside = False
    for line in src.splitlines():
        if not line.startswith("|"):
            inside = False
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if cells and cells[0].lower() == _RETIRED_HEADER:
            inside = True
            continue
        if not inside or set(cells[0]) <= set("-: ") or len(cells) < _MIN_RETIRED_CELLS:
            continue
        r = Retirement(flag=cells[0], origin=cells[1], successor=cells[2],
                       why=cells[3], measured=cells[4])
        out[(r.origin, r.flag)] = r
    return out
```

In `structural_query.py`:

```python
_END_OF_FLAGS = "--"


def retired_in(words: list[str],
               table: dict[tuple[str, str], routing_table.Retirement]) -> routing_table.Retirement | None:
    """Return the retirement this word list invokes, or None.

    ⚑⚑⚑ BOTH HALVES ARE REQUIRED: the ORIGIN'S STEM and a retired FLAG, before `--`. Keyed on the
    flag alone, it refuses the SUCCESSOR (`attr_reads.py` takes the same flag). Keyed on the tool
    alone, it refuses the tool's WORKING modes, and since `refusal()` RECOMMENDS that tool as the
    owner of `.py`, every refusal the gate issues becomes a dead end.
    ⚑ `--` ends both scans: after it every word is an OPERAND, so `--literal -- --attr` asks about
    the STRING `--attr`.
    """
    stems = {origin for origin, _flag in table}
    origin = None
    for w in words:
        if w == _END_OF_FLAGS:
            return None
        stem = Path(w.strip("'\"")).stem
        if origin is None and stem in stems:
            origin = stem
            continue
        if origin is not None and (origin, w) in table:
            return table[(origin, w)]
    return None


def retired_refusal(r: routing_table.Retirement, root: Path) -> str:
    """Render the refusal: flag, why, measurement, and a successor route anchored at `root`.

    ⚑⚑ THE ROUTE NAMES THE DIRECTORY IT ASSUMES. A peer took substrate's redirect from `~/github`
    and read both successors as one component short. Neither spelling was wrong; they differed in
    the reader's position. So the root is printed beside the repo-relative route.
    """
    return "\n".join((
        f"{r.origin}: {r.flag} is RETIRED — it returned FALSE ZEROS.",
        f"  why:      {r.why}",
        f"  measured: {r.measured}",
        f"  use:      python3 {r.successor} <operand>",
        f"     from:  {root}   (the route is REPO-RELATIVE — from elsewhere, spell it absolute)",
        "  ⚑ REFUSING rather than answering. A superseded reader that still",
        "     RESPONDS is worse than a deleted one: it answers whoever reaches",
        "     the old spelling first, wrongly.",
    ))


def retired_verdict(cmd: str, table: dict[tuple[str, str], routing_table.Retirement] | None = None) -> str:
    """Return the refusal for a RETIRED mode invoked by `cmd`, or "" if none is.

    ⚑ THE PROGRAM WORD IS PREPENDED. `cmdparse.programs` reports `./scratch/pycodemod.py --attr X`
    with the script AS the program and its stem absent from `args`; without rejoining, the
    direct-execution spelling sails through while the `python3 …` one is caught.
    """
    tbl = routing_table.retirements() if table is None else table
    if not tbl:
        return ""
    for prog, args in cmdparse.programs(cmd):
        r = retired_in([prog, *args], tbl)
        if r is not None:
            return retired_refusal(r, routing_table.project_dir())
    return ""
```

In `main`, before the `if not routing_table.claims():` early return (a repo may retire modes without claiming suffixes):

```python
    # ⚑⚑ CHECKED FIRST AND DENIED UNCONDITIONALLY, where the textual verdict is advisory unless
    # armed. An advisory textual query still gets a truthful, if clumsy, answer. A retired mode
    # answers `0` with full confidence, and an adopter that DELETES on a zero banks it as a fact.
    # Advisory suits a style rule and is wrong for a known-wrong instrument.
    retired = retired_verdict(cmd)
    if retired:
        sys.stdout.write(deny_payload(retired) + "\n")
        return 0
```

Integration notes, for your tree's bar:
- **The unconditional deny is a deliberate departure from your `_emit`/`armed()` default.** If your bar says every refusal starts advisory, say so and substrate keeps the deny through its own `STRUCT_HOOK_BLOCK=1` — but advisory output on a retired mode reproduces the exact defect this feature exists to stop.
- **The stem match.** Substrate's copy tests the stem against every word before `--` and the flag against every word before `--`, with no ordering. The diff above requires the flag AFTER the origin, which is stricter; both pass every arm below. Keep the stricter form only if your mutation grid shows it earns its place.
- **The tool also refuses itself.** `substrate/pycodemod_retired.refuse()` returns exit 2 for the tool's own use. That half stays in substrate (it concerns the tool, not the hook) and can read the same table once it exists.

## Suite — both directions (from substrate's `_cases_retired`, :775-827)

Each arm drives `retired_verdict(cmd, table)` with a fixture table holding the two rows above. The assertion is `"RETIRED" in result` or `result == ""`, plus the successor name where stated.

FIRES (the retirement must refuse, and name its successor):
- `python3 scratch/pycodemod.py --attr corpus.ROOT` → refused, contains `attr_reads.py`
- `python3 scratch/pycodemod.py --importers substrate.corpus` → refused, contains `module_importers.py`
- `./scratch/pycodemod.py --attr corpus.ROOT` — direct execution: the stem is the PROGRAM and absent from args. Substrate's first draft missed this arm.
- `timeout 60 python3 scratch/pycodemod.py --attr corpus.ROOT` — a wrapper does not hide it (`cmdparse.programs`)

PASSES (the retirement must not become a wholesale block):
- Working modes untouched: `--calls reach_ratchet`, `--binding MODES`, `--source _cached_defs`, `--literal foo`, `--forwards x`, `--snapshots`, each on `python3 scratch/pycodemod.py`
- ⚑⚑⚑ **The collision arm, the one that matters most.** `refusal(verdict("wc -l scratch/tool.py")[1])` still names `pycodemod`, AND `retired_verdict("python3 scratch/pycodemod.py --calls foo") == ""`. The gate must still let through the tool it recommends. Your fixture routing table needs a `.py` row owned by `pycodemod` for this arm.
- `python3 scratch/pycodemod.py --literal -- --attr` — after `--` the flag is an operand
- `python3 substrate/attr_reads.py corpus.ROOT` — the successor takes the same kind of operand and must not be refused
- `echo --importers` — an unrelated command carrying the word passes

One arm substrate lacked, created by the per-repo table: **with an empty table, every FIRES arm above returns `""`** — the borrowing-checkout degradation, which substrate covered only with `# pragma: no cover`.

## Bounds

- **Mode retirement only, not whole-tool retirement.** The conjunction requires a retired FLAG. Retiring an entire tool would need a row whose flag matches any invocation (e.g. `*`), safe only when the retired tool is not also an owner the routing table recommends. Not built; named so it is not mistaken for coverage.
- **The origin is matched by file stem.** A different tool sharing the stem is refused for the same flags — a false FIRE, answered by using the successor, never a false pass.
- **Only the textual command is seen.** An alias, a shell function, or an `import` of the origin reaches the retired mode without passing this gate; the tool's own `refuse()` covers that layer.
- The Python above is a proposal: not run against your ruff/mypy bar or test harness.

## After it lands

Say "on main". Substrate will then:
1. move `SUPERSEDED`'s two rows into the retirement table in `.claude/skills/struct-tools/SKILL.md`;
2. delete `retired_verdict`, `_cases_retired` and the optional `_RETIRED` import from `scripts/hook_structural_query.py`, and take the verdict from the `mikemol-hooks` wheel;
3. have `substrate/pycodemod_retired.py` keep only the tool's own `refuse()`, reading the same table.

This letter is the record. Remaining letters in the agreed order: `shellcheck`, the four fence siblings, and the census.
