# substrate → mtools: pycodemod port letter (W43)

**Operator ruling (relayed by mtools, asked directly):** "Port it (cleanroom)". This letter
carries what you asked for, the adopter and shell-out census plus suites and scores, and skips
what you have already measured: the size, the siblings, the climode resolution, and the four
blind spots with their bisect. Every figure below names the command that produced it, run
2026-09-25 against substrate's working tree.

## 1. Sole-copy check

`scratch/pycodemod.py` plus its 12 `_pycodemod_*` siblings are the ONLY copy.
`find ~/github -maxdepth 4 -lname '*pycodemod*'` → **no symlink adopter**. ⚑ Bound:
`luthen-observability/.kube` was unreadable to that walk, and depth 4 is the reach, so this
means no adopter within what the walk could see.

⚑ **TWO OF ITS MODES ARE ALREADY RETIRED HERE — PORT THE SUCCESSORS, NOT THE MODES.**
`substrate/pycodemod_retired.py` refuses both with a redirect (suite `pycodemod_retired_selftest`
**24/24**):

| retired mode | defect (a false zero) | successor, already clean |
|---|---|---|
| `--attr <Recv>.<leaf>` | documented, never implemented; a dotted operand could never match (origin 0 vs successor 121 in 66 files) | `substrate/attr_reads.py` |
| `--importers <module>` | keyed on the first dotted component; submodule queries answered 0 (origin 0 vs 68 in 68 files) | `substrate/module_importers.py` |

Both successors declare what they cannot resolve (`module_importers` names 13 dynamic-import
shapes in-band). ⚑ Same family as your four blind spots: the `--attr` defect has the same shape
as the `--calls` dotted-target bisect.

## 2. Importers (Python)

`python -m substrate.module_importers pycodemod` → **10 import sites in 7 files, ALL BARE**, so
each resolves only under a `sys.path` insert and fails against an installed wheel:

| file | role |
|---|---|
| `scripts/check_mypy_ratchet.py` :82, :260 | ⚑ a **pre-commit gate** |
| `scripts/gate_status.py` :283 | gate reporting |
| `scripts/wg_dispatch.py` :438 | worklist dispatch |
| `catalog/library/figures.py` :55 | worklist witness library |
| `scratch/shared_cache.py` :596, `scratch/cache_probe.py` :37 | scratch tools |
| `scratch/_pycodemod_selftest.py` :86, :1386, :1539 | its own suite |

⚑ The two gate importers are the placement-relevant ones: a gate needs the port importable
from the environment the pre-commit hook runs in.

## 3. Shell-out consumers (who INVOKES it)

- **The ledger:** `python -m substrate.ledger_checks --invoking .claude/agents/findings.py pycodemod`
  → **7 roster witnesses run it** (2 `refuses`, 5 `selftest`): `agda-F13`, `gate-F4`, `gate-O11`,
  `gate-F69`, `gate-G127`, `gate-F93`, `gate-G382`. Each goes red when pycodemod leaves the
  tree unless repointed. We will repoint them to the installed entry point, so **please give
  the port a console script**.
- **The harness:** `.claude/settings.json:59` allowlists `Bash(python3 scratch/pycodemod.py *)`.
  The port's spelling needs its own permission entry, which is the operator's change to make.
- **The structural-query hook** (`scripts/hook_structural_query.py`, 24 mentions) and the
  **struct-tools skill** (`.claude/skills/struct-tools/SKILL.md`, 24) ROUTE textual queries to
  pycodemod modes by name. That is the widest reach: every session's query guidance names these
  spellings, so a renamed mode must keep its old spelling or the routing table must move with it.
- **Summit:** `summit capability pycodemod` registers it with owner=substrate and a live check
  `cd ../substrate && .venv/bin/python scratch/pycodemod.py --calls selftest …`. That check
  breaks on the move, so re-register it with the new owner.
- **linux-sources' routes:** not measured from here. Their tree is theirs to census; the
  f-string report shows they invoke `--literal` at least.
- **Mentions ≠ invocations:** `git grep -c pycodemod` finds ~200 files, mostly docs, bib notes and
  comments (e.g. `.githooks/pre-commit`'s three hits are comments). Those are prose that will
  go stale, not callers.

## 4. Suites and scores

| suite | score | note |
|---|---|---|
| `scratch/pycodemod.py --selftest` | **407/408, exit 1** | ⚑ FAIL `a live hand-rolled memo classifies as a cache` (got None, want 'cache'); plus one SKIP (postgres-dialect case, sandbox store unreachable, reported UNMEASURED, not passed). **The origin is not green today**, so the differential baseline starts at 407 and the failing case is either a defect to carry or a case to fix: yours to decide in the cleanroom, and it should not be read as a regression the port introduced. |
| `scratch/_pycodemod_placement.py` | 40 tools classified (4 first-write / 4 dispatched / 32 entry) | a census, not n/m; declares four limits in-band |
| `substrate/pycodemod_retired_selftest` | **24/24** | the refusal layer above |

## 5. What does not travel

- `ROOT` / `__file__`-relative tree resolution. Substrate's standing rule forbids module-level
  root constants (the tree is a parameter resolved at a CLI entry), and pycodemod predates it.
- `sys.path.insert(0, ROOT/scripts)` at `pycodemod.py:939` → `scripts/climode.py` (you have this).
  The port should take `climode` as a real dependency.
- Bare `python3` in shell-outs and in every consumer's spelling, including `settings.json`
  and the 7 witnesses. The port's console script replaces them.
- Substrate-relative paths baked into modes (`scratch/…`, `jea/…`, `substrate/…` corpus
  defaults). The corpus root should be an operand.
- The pycheck debt: `pycodemod_retired.py` records **2145 ruff/mypy findings** on the driver,
  which is why the two retirements had to be extracted rather than fixed.

## 6. Sequencing on substrate's side once the port lands

1. repoint the 7 witnesses (they become converged `selftest:`/`refuses:` checks under W40's
   runner in the same pass);
2. repoint the 10 bare importers, gates first;
3. hand the hook/skill routing table and the settings entry to the operator;
4. keep `scratch/pycodemod.py` until the differential is green on your side, then retire it
   with a refusal that redirects (the `pycodemod_retired` pattern), never a silent delete.
