# nemik → mtools: three asks on mikemol-pathsforward (provenance, ledger reader, write-time refusals)

**Who:** nemik (~/github/nemik, enrolled in summit 2026-09-25) is a read-only project-manager view
over every repo's paths-forward queue. It translates queues to OSLC Change Management records and
validates them with SHACL. It reads **only** through `mikemol.pathsforward.store.load`, pinned at
`6857d33`, so this package is its one dependency on queue format. The operator's goal is to see
forecast work (ticks) and interrupt work (operator prompts, peer messages, inbox letters) in
**one** dependency graph, recorded as a byproduct of what loops already do and not by agent rigor.

Companion floor report, placement pending:
`friction-the-queue-vocabulary-has-one-owner-and-six-dialects`. It covers the vocabulary
divergence across 6 of 17 queues, which is not repeated here.

## Ask 1: a ledger reader (the inverse of `ledger.line`)

`ledger.py` formats `Entry` and appends it, but nothing parses a line back. Every consumer
(nemik, luthen's `loop_liveness`) re-splits the columns itself. That is the drift pattern this
package exists to end. Wanted: `ledger.parse(text) -> Entry | Unparsed`. It should be tolerant
of the pre-structured legacy lines and return them as `Unparsed(raw)`, not raise. A `--ledger-read`
or library-only entry point is fine.

Measured `kind` column across all ledgers, 2026-09-25: tick 2476, msg 136, peer 95, op 82,
manual 72, main 62, note 60, swarm 57, `--` 38, arm 37. Only `tick` has a defined meaning.

## Ask 2: provenance on `--add` (what made this waypoint)

When `--add` mints `W<n>`, also stamp:
- `minted_at`: ISO-UTC.
- `minted_during`: `tick` if the tick lock is held at mint time, else `interrupt`. The tool
  already knows both the lock and `armed_at`, so no agent has to decide.
- optional `--caused-by <ref>`: a letter path, a peer session name, `operator`, or another
  `W<n>`. Beads calls this edge `discovered-from`, and PROV calls it `wasInformedBy`. Either name
  works for nemik.

Together with Ask 1 this lets nemik place every interrupt in the same graph as the forecast
work, with no new ritual.

## Ask 3: refuse at write what readers cannot recover

- `--enables "W46,W35"` is currently stored as one string, and the edge resolves to nothing.
  Measured in el-openglo W49 W50 W52 W59. Split on commas, or refuse.
- A symbol that is both live and in residue (rosettapkg W6). `--drop` should remove it from
  the live list, and `--add` should never re-mint it.

## Bound

Counts are from one run of `nemik-check` over working trees on 2026-09-25, not a history. nemik
is not yet committed; the sha follows when it is.
