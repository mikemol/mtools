# W889: a working card holds a claim on its touches (2026-10-09)

Operator, 2026-10-09: shared `touches` tags and fence are meant to coordinate sessions; "I don't know
if we've mechanized that kind of mutex/claim." Measured: they are not. `nemik-overlaps` shows which
CARDS share a tag (a view); nothing records that a LIVE SESSION is working under a tag, so two
sessions find out by colliding in the working tree (this session deferred a card by judgment
because a peer "was in pycodemod", and the measurement afterwards showed the files were disjoint).

## What exists to compose

- `fence.admit` already has the claim: a zero-capacity lease whose label `claim:<kind>:<name>` excludes
  any other holder of the same name, waits or refuses, names the holder, and is reaped when its owner
  (`pid:starttime`) dies. `claim:label:` compares by label, `claim:path:` by realpath.
- W886/W885: the commit already uses it, per repository, and a blocked claim names its holder.
- A card's `touches` tags are the declaration (memory: touches is the declaration): a shared tag is a
  reason to coordinate, never a reason to wait for an observed collision.

## The gap

A claim must outlive any one command: its owner is the SESSION, but `hold` owns the lease through
the child it spawns. Nothing takes a lease owned by a long-lived process and returns.

## Mechanism

1. **fence: a `claim` verb that outlives the command** (W911): `mikemol-membudget claim LABEL [--owner-pid N]`
   writes a lease owned by `pid:starttime` of the named process (default: the caller's parent, the
   Claude session) and returns; `release LABEL` drops it; `claims` lists holders with age. Dead owners
   are reaped by the existing gc. Tests: held claim excludes a second `claim`, a dead owner is
   reaped, the listing names the holder.
2. **the declaration travels with the card** (W912): the tick gate and the UserPromptSubmit
   context hook, when a card is `working`, take `claim:label:touch:<repo>:<tag>` for each of its
   touches (a hook can run the verb; pathsforward itself cannot import fence until W317). A refusal
   prints the holder and its files, and does not block: it is an advisory with a name on it.
3. **the view** (W913): `nemik-overlaps` (and the inbound-asks context line) print live holders next
   to the overlapping cards, so a session that is about to start work under a tag sees who is
   there before it edits.

## Why not a lock

A hard mutex on a tag would stall unrelated work (two sessions rarely collide on every file a tag
covers). The measured need is NAMING the other party and the files it declared; the commit claim is
the only place a true mutex belongs, and it exists.
