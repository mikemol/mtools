# swarm2 drafter: census (W173, W180)

Draft only. Nothing moved, nothing committed, queue not written.
The matching was done by a throwaway scratch script (outside the repo:
`$SCRATCH/census.py`, which runs `git log --all -F --grep "<first line>"` on each msg file).
Its output is a DRAFT MEASUREMENT, not evidence. To cite it, re-run it per file with the
git command below, or land it as tracked code (see W173-c).

## W173: drain .claude/

### Measured
- `ls -la .claude/`: 249 `msg*.txt`, plus gen_warrants.py, paths_forward_render.py,
  preamble.txt, paths-forward.{json,ledger,md,flock}, queue.md, README.md, settings.json,
  scheduled_tasks.lock, and the design/ skills/ swarm/ worktrees/ directories.
- `git ls-files .claude`: README.md, msgW34c.txt, msgW34d.txt, queue.md, settings.json,
  skills/struct-tools/SKILL.md.
- census (one `git log --all -F --grep` per file): **matched 248, unmatched 1**.
  - Unmatched: `msgGE.txt`. It is a peer letter to substrate (pycodemod --guarded contract
    divergence), not a commit message. It cites `.claude/design/W196-spec/` and `W210-elif.py`.
  - The 248 matched include msgW179 (2ec718c). The 2026-09-27 census marked it pending;
    it has landed since. The newest ones landed today: msgW184 is 2d15774, msgW233 is
    de5715e, msgW246 is 7a1167f (HEAD), msgW350 is e6161eb, msgW374 is a70989c.
  - The full matched table (file, short hash, first line) is in this swarm's transcript.
    Re-derive it with the scratch script rather than citing it.
- Delta from the recorded 2026-09-27 census (133 matched): the 115 new matched files
  are post-census commit messages. The "135 archived" evidence does not describe the
  current tree; they are back or were never removed.

### Other loose files: proposed home or retirement
| file | proposed |
|---|---|
| msgW34c.txt, msgW34d.txt (TRACKED) | `git rm` them: their commits are 141ca6b and bd3615e |
| 246 untracked matched msg*.txt | retire with `rm`: git history is the home. Record the count and HEAD in the evidence |
| msgGE.txt | the peer-letter channel. Check whether substrate received it (`summit ask --for substrate` / inbox). If it was delivered, retire it; otherwise send it, then retire it |
| gen_warrants.py | W180 (below) |
| paths_forward_render.py | retire: the 09-27 census found it superseded at 600745c with no caller. Re-verify with `git grep paths_forward_render` |
| preamble.txt | retire: the text is carried in paths-forward.json (`--preamble-set`) |
| paths-forward.json/.ledger/.md/.flock, scheduled_tasks.lock | home in place: loop state (untracked by design) |
| queue.md (tracked, modified) | home in place, but `M` in status; the operator should decide whether it is still live or superseded by paths-forward.md |
| settings.json, README.md, skills/ | tracked homes, no action |
| design/*.py (W10-sync, W128/W187/W189/W192 count, W196-*, W207, W210, W213/215/220 peek, W228, W36-modemap/trace, W425-census, W436-tally) | load-bearing-code risk under W464: each one either goes into a tracked package (if its output is cited) or gets retired. W469 already retired the differential harness, so the rest needs a per-file waypoint |
| design/*.jsonl, *.xml (about 12 MB) | data behind the above: retire along with its script |
| design/*.md, *.tsv, W196-spec/, W231/ | notes, allowed untracked |
| design/__pycache__ | rm |
| swarm/ (tq1-5) | swarm-1 drafts; its batches landed (5447a09, 710d043, de1d4fd, 0102a4e, 6b394dc), so retire |
| worktrees/ | workflow harness worktrees; out of scope, the harness cleans them |

### Landing units (each one is one tick; no commit needed except a)
- **W173-a** (commit): `git rm .claude/msgW34c.txt .claude/msgW34d.txt`. Message:
  "Untrack two stray commit-message files; their commits are 141ca6b and bd3615e (W173)".
- **W173-b** (no commit): rm the 246 matched untracked msg files. Then
  `--update W173 --evidence-append "2026-10-02: 248/249 msg files matched by git log -F --grep at 7a1167f; rm'd; msgGE is a peer letter -> W173-d"`.
- **W173-c** (optional, commit): if the census should be citable, land it as
  `mikemol-paths-forward`-adjacent or hooks CLI `mikemol-claude-census` with a test,
  rather than keeping it as a scratch script.
- **W173-d**: mint a waypoint for msgGE delivery/retirement (it touches substrate, so it's a peer).
- **W173-e**: mint one waypoint per design/*.py group (it gates W464 alongside W466).

## W180: gen_warrants.py

### Measured
- Read in full (62 lines). It takes `argv <dist> <module>=<section>...`, parses
  `<dist>/tests/test_<module>.py` with ast, and prints `@misc{...}` bib entries to stdout
  for each test_ function not already in `<dist>/warrants.bib` (it skips duplicates by check
  string, by un-trimmed key, and by trimmed key). It refuses braces in docstrings.
  The repo root comes from `Path(__file__).parent.parent`, so the script is location-coupled
  to `.claude/`.
- `git grep -n gen_warrants -- ':!*.md'`:
  - hooks/policy/standing.rego:37-38: standing rule 14 requires warrants.bib to be
    appended from gen_warrants.py output
  - hooks/policy/standing_test.rego:35: test_14_append_control uses
    `python3 .claude/gen_warrants.py hooks cmdparse=X >> hooks/warrants.bib`
- Consumers: all 18 `*/warrants.bib`, one for each distribution (fence, hooks, corpus,
  witness, ledger, pycodemod, pytestspec, icsstruct, audiostruct, mdstruct, ratchet,
  pathsforward, transcriptstruct, rules_py, check_ruff, check_mutants, check_ratchet,
  gmailstruct).

### Finding
It is a cross-distribution maintainer tool, and the standing policy (in hooks) names it.
Its home should be hooks, as a non-`mikemol-hook-` console script, following the
`mikemol-shellcheck` precedent (pyproject.toml:73-76: "a tool a maintainer runs,
not a gate the harness wires").

### Landing unit (one commit). W464 is unblocked on the W180 side once it lands.
1. `hooks/src/mikemol/hooks/gen_warrants.py`: same logic, wrapped as
   `def emit(root: Path, dist: str, pairs: list[tuple[str,str]]) -> list[str]` plus
   `main(argv) -> int`. `root` = `Path.cwd()` (or `--root`), not `__file__`. The brace refusal
   becomes a returned/raised error with exit 2, and the `{n} warrants` stderr line stays.
2. `hooks/pyproject.toml [project.scripts]`:
   `mikemol-gen-warrants = "mikemol.hooks.gen_warrants:main"` with a ⚑ comment explaining why
   it has no `mikemol-hook-` prefix.
3. `hooks/tests/test_gen_warrants.py` against a tmp dist, one test per behaviour:
   emits a new function; skips one already checked by file+name; does not skip a same-named
   test in another module; skips an article-keyed legacy entry; strips a leading article from
   the key; refuses a brace in a docstring; multi-pair order is preserved; prints nothing
   (with the count on stderr) when all are present.
4. Its own warrants: run the NEW tool on itself, e.g.
   `hooks/.venv/bin/mikemol-gen-warrants hooks gen_warrants=<RUBRIC KEY> >> hooks/warrants.bib`.
5. standing.rego rule 14 text plus standing_test.rego:35: replace `python3 .claude/gen_warrants.py`
   with `mikemol-gen-warrants`. Keep the old spelling as a second allowed control until (6).
6. `rm .claude/gen_warrants.py` (it is untracked, so the rm is not in the diff; record it in
   evidence).

Needs an operator check: the RUBRIC KEY section name for the new module in hooks' rubric.
That is a single read of hooks' rubric file by the lander, not a blocker.
