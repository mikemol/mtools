# W558: the bib cut for effective.py (cites mtools:W531, W532-plan.md, W552-engine-modules.md)

Drafted 2026-10-03, read-only. Probe script: /var/tmp/claude-1000/-home-mikemol-github-mtools/0709aae6-1dba-4fe5-bfbe-24d21edd31e0/scratchpad/probe.py (scratchpad only; no paperkit/substrate file written, bytecode off).

## 1. What effective.py needs from bib

- One call: effective.py:32 `import bib`, effective.py:55 `F = bib.parse_project(project_dir)`; sole argument is the project directory `Path` (from argv, effective.py:110). Nothing else of bib is touched.
- Result reads, all in `records()` (effective.py:51-66), per grade file with claim key `k = d["claim"]` (:59):
  - effective.py:60 `f = F.get(k, {})`: lookup by claim key, absent key tolerated as `{}`.
  - effective.py:61 `f.get("rests-on", [])`: a LIST of key strings (default `[]`).
  - effective.py:62 `f.get("check", "")`: a STRING (`concept:X` or `result:proj#claim`), consumed by `_delegation` (:36-48). If absent, `""`.
- No other field (title, claim, _src, _type, entails, consumer fields) is read. The two fields used are `rests-on` and `check`; the minimal contract is `{key: {"rests-on": [str], "check": str}}`. (The W552 survey said "rests-on edges" only; `check` is a second needed field, and cut (a) must carry it too.)
- Shape of parse_project's result (bib.py:544-586): `{key: {"_src": basename, "_type": entry type, <_SCALAR fields present, verbatim string>, "from"/"rests-on"/"reads"/"consumes"/"builds": list[str] always present (split on `[,\s]+`, bib.py:244-246), plus declared consumer fields}}`. Duplicate key across a project's bibs is `SystemExit` (:577-584); unknown field = stderr warning (:258-275); bad `entails` = `SystemExit` (:287-290); malformed bib = `bibparse.BibSyntaxError` (bibparse.py:47, 224-264).
- Call chain with file:line: parse_project :544 -> load_config :492 (needs project/paper.toml else `sys.exit` :495-496; `_misplaced_paper_key` :497 -> `paper_keys` :309 + `_param_config_keys` :325, the sibling-AST scan; `_bibpath` :295 resolves the `warrants` token list, default `["warrants.bib"]` :509; `consumer_fields` :523 with `_misplaced_consumer_fields` :461) -> `parse` :207 per bib (-> `bibparse.parse` :236, `_SCALAR/_LIST/_SCOPES` :45-70, `_WARNED` :93) -> duplicate-key refusal :577. Of all this, effective needs only: warrants list resolution (:509, :295), parse, composition, `rests-on`/`check`.

## 2. raw_bib / warrant_bib vs parse_project

- raw_bib.py (witness): `read_text(path)` :59 (str, `BibError` for absent/dir/non-UTF-8); `parse(text)` :114 returns `{key: {field: RAW STRING}}` via two regexes (`_ENTRY` :32 ends an entry at the first line-initial `}`; `_FIELD` :35 allows one nested brace level); `read(paths)` :124 returns `Corpus(entries, collisions)`, collision REPORTED not raised, last write wins; `entries_with_dropped_edges` :147; `EDGE_FIELDS` :29.
- warrant_bib.py: `consumer_fields(config)` :42 (tuple of str from `[paper] consumer_fields`), `claim_of` :69, `tag` :92, `WarrantError` :34. None returns edges. It does not read `warrants = [...]` from paper.toml.
- Field-by-field difference from parse_project:
  - `rests-on` is a raw string in raw_bib (`"a, b"`), a list in parse_project; the caller must apply the `[,\s]+` split (bib.py:246). Absent field: key missing in raw_bib, `[]` in parse_project.
  - raw_bib has no `_src`/`_type`; no whitelist, no loud-drop, no `entails` refusal.
  - Parser grammar differs: raw_bib's regex ends an entry at `\n}` and nests one brace level, the very truncation bibparse.py:1-21 and bib.py:137-166 record as a defect (an entry with a column-0 `}` parses with zero fields). Where parse_project raises `BibSyntaxError`, raw_bib returns a partial record or a missing entry. UNMEASURED on a malformed bib (probe ran only real, well-formed bibs).
  - Project resolution: neither raw_bib nor warrant_bib maps a project dir to its bib list (`warrants` tokens, Bazel-label tokens); parse_project does (bib.py:509, :295). A caller of raw_bib must supply the path list.
  - Duplicate keys: parse_project exits; raw_bib reports in `Corpus.collisions` (a caller can refuse itself).
- Probe (read-only), exact: `/home/mikemol/github/mtools/witness/.venv/bin/python <scratchpad>/probe.py`. It imports paperkit's `bib` and `bibparse` (path /home/mikemol/github/paperkit/paperkit) and `mikemol.witness.raw_bib` (path .../witness/src), for projects arch, talk, report, boundaries, setup, render: runs `bib.parse_project(p)`, `raw_bib.read(bib.load_config(p)["bibs"])` (bib list taken FROM paperkit's load_config, so project resolution is not tested for raw_bib), re-splits raw `rests-on` with the same regex, and compares. Output:

```
arch       n_pp 7  n_raw 7  keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 2   ; bibparse edges eq True
talk       n_pp 34 n_raw 34 keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 27  ; bibparse edges eq True
report     n_pp 16 n_raw 16 keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 0   ; bibparse edges eq True
boundaries n_pp 54 n_raw 54 keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 2   ; bibparse edges eq True
setup      n_pp 29 n_raw 29 keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 23  ; bibparse edges eq True
render     n_pp 34 n_raw 34 keys_eq True  edges eq True  check eq True  collisions 0  nonempty rests-on 3   ; bibparse edges eq True
```
  Verdict: on these six well-formed project bibs, `raw_bib.read` plus the `[,\s]+` split yields the SAME `rests-on` and `check` data as `parse_project`. No single raw_bib/warrant_bib function returns the same data as parse_project as-is: it needs the split, the missing-key default, and a bib list. Not covered by the probe: projects with Bazel-label `warrants` tokens, the 12-bib `paper/` project, library/concepts.bib (the `concept:` owner), the malformed-bib behaviour, and `_param_config_keys`-dependent refusals.

## 3. Candidate cuts

(a) Edges as data. effective.py takes `{key: {"rests-on": [...], "check": "..."}}` (JSON file or an argument) instead of `<project-dir>`; drops `import bib` and the `sys.path.insert` (effective.py:31). Cost: smallest code change (replace :55 `F = ...` with a loader), but the CLI signature changes (`effective.py <project-dir> ...` at :23, :110) and every caller (Bazel rules passing a project dir; UNMEASURED which) must supply the file, which needs a producer on the paperkit side that still calls bib. Moves the coupling, does not remove it.
(b) Move bibparse alone (264 lines, dataclasses only, bibparse.py:43-44) as a small mtools edges reader. Strictest parser; paperkit's bib.py:37 repoints to the pinned dist. effective would additionally need a project-to-bib-list resolver (paper.toml `warrants`, bib.py:495-509, :295; tomllib only) and the composition/duplicate refusal (bib.py:577-584); roughly 40 added lines. New dist or a module in witness; naming is mtools'. Cost: one module commit plus resolver plus new suite (the paperkit boundaries_* tests cover bibparse today, UNMEASURED which).
(c) Reuse raw_bib. Zero new parser, and measured equal on six real bibs (sec. 2). Cost: effective gains a dependency on mikemol-witness; needs the same resolver as (b) and the split; accepts raw_bib's weaker grammar (silent truncation at a column-0 `}`, no syntax error), which the engine explicitly rejected (bibparse.py:1-21), so a malformed bib would degrade effective's clamp input silently instead of refusing. That is the false-green class bib.py:137-166 documents.

## 4. Recommendation: (b), with raw_bib's read_text/collision reporting borrowed

Reason: effective feeds `grade.clamp`; a silently truncated bib drops `rests-on` edges and so weakens a clamp (an effective grade reads stronger than it is), the one direction this tool exists to prevent (effective.py:11-17). bibparse refuses malformed input by position and is the same parser paperkit's own bib.py uses, so effective and paperkit cannot disagree on edges. (a) leaves bib in the loop, so it does not meet the operator ruling; (c) trades safety for reuse.

Behaviour that changes under (b):
1. effective reads edges with `bibparse` from the pinned dist, not `bib.parse` (same parser, so same entries); no `_param_config_keys` guard runs (effective never needed it; `load_config` is not called): the [paper]-key misplacement refusals (bib.py:455-457, :479-488) no longer fire from effective (they still fire in paperkit's own gate), and a project with a bad paper.toml table placement no longer exits from effective.
2. Unknown-field stderr warnings and the `entails` SystemExit (bib.py:258-290) no longer occur in effective (they come from `parse`, not bibparse). Consumer fields need no declaration, since effective reads only `rests-on` and `check`.
3. Error types: a malformed bib raises `BibSyntaxError` as today; a duplicate key must be re-implemented as an error (do not copy raw_bib's report-only mode); a missing paper.toml must still fail loudly (do not fall back to `warrants.bib` silently, bib.py:495-496).
4. `sys.path.insert` hack and bare `import bib` leave effective.py (:31-32).

Test that proves equivalence on a real paperkit .bib: a pytest in mtools that, for each of arch, talk, report, boundaries, setup, render (and ideally paper/ and paperkit/library for the 12-bib and `concept:` cases, UNMEASURED here), computes `{key: {"rests-on": split, "check": check}}` with the new reader and asserts equality with the same projection of `bib.parse_project(project)` (the probe above is the skeleton), plus negative cases: an unterminated value, a duplicated field, a duplicate key across two bibs, and a missing paper.toml must each raise (not return a partial map). Because it imports paperkit's bib, it lives paperkit-side or as an optional-dependency test; UNMEASURED whether mtools CI may import paperkit (W532 rule: the engine is injected, never imported).

## Unmeasured, listed
- Malformed-bib behaviour of raw_bib (read from source only, not run).
- Bazel-label `warrants` tokens, paper/ (12 bibs) and library bibs through raw_bib/bibparse.
- Callers of effective.py by project-dir (Bazel rules) for the cost of (a).
- Which paperkit tests cover bibparse today.
