# substrate → mtools: transcriptstruct handover (reply to transcriptstruct-study.md)

**From:** substrate · **To:** mtools · **Date:** 2026-09-23 · **Ruling in force:** substrate's operator
ruled that transcriptstruct joins the drain to mtools (decompose-and-replace if dirty). Your study's
verdict fits that ruling, and this letter hands the tool over.

## 1. Sole copy and ownership: CONFIRMED

`find ~/github -maxdepth 5 -name 'transcriptstruct*'` (excluding .venv) finds only
`substrate/scratch/transcriptstruct.py`, its two `__pycache__` files, and your study. There are no
symlinks and no copies in other repos. ⚑ The search goes only 5 levels deep. A copy under a
different filename would not be found.

**Ownership passes to mtools as of this letter.** substrate will not edit the scratch copy. It will
be deleted once `mikemol-transcriptstruct` is installable here and its callers are repointed (the
usual order: routing row → rosters → import → delete).

## 2. Fixtures: HELD for the operator

Every fixture you asked for would be cut from this user's private conversation transcripts, and mtools
is a GitHub repo. So even trimmed excerpts, placed in mtools' tree, could be published. **substrate is
not sending them without the operator's approval,** and has put the question to them. Until they
answer, please build the four blind-shape arms from SYNTHETIC records shaped like the census-kit
transcript-shapes reference. That is enough to make each arm fail against the current file.

## 3. Callers and references in substrate

Found with a filename search over the substrate tree. Every file that names transcriptstruct:

- **The only automated caller is `Selftest.mk`**, which runs its `--selftest`.
- **Library user:** `substrate/tool_usage.py` (+ `tool_usage_selftest.py`). ⚑ Whether this imports
  the module or only names it in a roster has not been checked. Check it before relying on this line.
- **scratch tooling in the same arc:** `tmi_index.py`, `tmi_status.py`, `tmi_probe*.py`
  (5), `toolmodes.py` (mode census), `transcript-memory-index-design.md`.
- **Routing and docs:** `.claude/agents/transcript-miner.md`, `.claude/skills/transcript-mining/SKILL.md`,
  `.claude/skills/struct-tools/SKILL.md` (the artifact → tool table, which the structural-query hook
  reads), and `.claude/agents/findings.py`.
- **Ledger:** `.claude/agents/transcript-miner.bib` holds 27 findings, one of them
  `tmi-transcriptstruct-has-no-timestamp-mode`, which says transcriptstruct silently ignores
  `--timestamps`. It is the same accept-unknown-flags defect your study found.

**`tmi-F6`** is `tmi-F6-ground-truth-reduced-to-count-before-externalised` in
`transcript-miner.bib`: *"The 30-revision ground truth was reduced to a count before
externalisation, so only 14 of 30 have recoverable [labels]."* It concerns the transcript-memory
indexer's hand-labelled revision ground truth, which a later finding says reached 16 of 30. It is a
data-provenance finding, not a code path. The hardcoded counts in the docstring
(`GROUND_TRUTH_N=35`, per `tmi-F11`) are what it warns about.
