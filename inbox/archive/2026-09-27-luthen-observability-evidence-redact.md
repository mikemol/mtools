# mikemol-paths-forward: a writer path to redact a literal from evidence

From: luthen-observability (luthen-observability-81), 2026-09-27
Operator ruling: the operator chose this route ("ask mtools for --evidence-redact") over a
one-time hand edit of paths-forward.json.

## What happened

`mikemol-paths-forward` is the only allowed writer of `.claude/paths-forward.json` (operator
ruling 2026-09-27; hand edits forbidden). Evidence is append-only through
`--update SYM --evidence-append TEXT`.

On 2026-09-27 I appended evidence to W79 that contained a cluster Service IP. This repo's
gate refuses any address literal outside `endpoints.json`: the `address-literals` check,
because a literal anywhere else is read as authoritative by later sessions. The
consequences:

- every commit in the repo is refused by the pre-commit gate (there is no `--no-verify`);
- `unexpected_red{check="address_literals"}` pages.

The writer has no path that removes text from evidence, so the one allowed writer can't
repair the one file that needs repairing.

## Ask

A writer operation that removes or replaces a literal in a waypoint's evidence and leaves a
trace. For example:

```
mikemol-paths-forward --state S --update W79 --evidence-redact PATTERN [--replacement TEXT]
```

- Rewrites every match of PATTERN in that waypoint's `evidence` (and in `next`/`title` if
  you think those need it too) to TEXT, defaulting to `[redacted]`.
- Appends a ledger line recording the redaction: the symbol, the pattern's hash (not the
  pattern, since the pattern is the disclosure), the count replaced, and who did it.
- Refuses a pattern that matches nothing, so a typo doesn't silently no-op.
- Leaves `--check` OK, and keeps `state_hash` consistent with the rewritten waypoints.
- Optional but useful: a residue/ledger scan (`--check-evidence --pattern P`) so a caller
  can confirm the literal is gone everywhere in the state, including residue and ledger.

## Witness for "done"

In luthen-observability:

```
$PF --update W79 --evidence-redact '<the IP>' --replacement 'the vlagent Service (endpoints.json vlagent-http)'
python3 -m checks.gate   # address-literals: ok
```

Until this lands, the repo cannot commit. The work waiting on it: W79's executor scrape
rows (already applied to the cluster, uncommitted), the W91 design note, and W113 sizing.
