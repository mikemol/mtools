# W50 — touches[] contention: what already exists

Derived working notes for W50 (paths-forward). Not a design: W99 (W50.1) is a read
of what the keyway and the store already provide. W100 measures, W101 designs.

## W99 — the read (2026-09-27)

### pathsforward: what `--lock` protects

`pathsforward/README.md:59-63` (## Writes): every read-modify-write holds `flock` on the
state file's `.flock` sidecar, and every write is temp-file-then-replace. A stale-lock
takeover is written to the ledger.

So the only exclusion pathsforward has covers **its own control-plane file**. The
`--lock/--unlock <holder>` tick lock serialises ticks against each other, and nothing else.
No mode reads `touches[]` to decide anything; it is stored and rendered, never compared.

### fence: the claim keyway (`fence/src/mikemol/fence/admit.py`)

- **A claim is a lease label with the prefix `claim:`** (`claim_key`, admit.py:326-341).
  A label without the prefix makes no claim (returns None).
- **The kind is declared by the claimant, never guessed** (`Kind`, admit.py:286-299):
  - `claim:path:<p>` compares by `os.path.realpath(p)` (admit.py:336-337).
  - `claim:label:<l>` compares by `normalise_label` (admit.py:309-323): a Bazel-label
    canonicaliser (`//pkg` → `//pkg:pkg`, trailing `/` dropped), never a filesystem op.
    ⚑ For a name that does not start with `//` or `@`, `normalise_label` returns it
    unchanged except for a trailing-`/` strip, so a non-Bazel tag under `label:` is in
    effect byte-compared.
  - A bare `claim:<tag>` is byte-compared (`Kind.BARE`, admit.py:340).
- **The key is `(kind, canonical)`** (`ClaimKey`, admit.py:302-306). Two claims exclude
  each other only when both fields are equal, so a `path:` and a `label:` claim on the
  same spelling never collide.
- **Contention** (admit.py:395-397): a request whose key equals any held lease's key gets
  `Verdict.CLAIMED` (block, or refuse under NOBLOCK/TIMEOUT). A claim needs no capacity:
  `mb=0` with a claim is a first-class request (admit.py:386).
- **Release** (`release`, admit.py:779-790): the lease is dropped from the ledger under
  its lock. If the lock cannot be taken, it is left for gc, which is safe because the
  owner is this process.
- **Reap** (`gc`, admit.py:226-247, `reap`, admit.py:630-642): leases whose owner is dead
  are dropped, then orphans of dropped parents, to a fixpoint on one snapshot. Liveness is
  `alive` (admit.py:214-222): the owner is `pid:starttime`, and it is alive only when that
  pid exists **with the same start time**, so PID reuse cannot keep a lease alive.

### ⚑ The mismatch W101 must face (an observation, not a choice)

A fence lease lives exactly as long as its **owner process**; the kernel-level guarantee
("released on any exit including SIGKILL") comes from `pid:starttime` liveness. A waypoint
in `working` lives across **ticks and sessions**: a tick is one turn of an agent, and the
next tick is often a different process. A fence claim taken per tick would therefore
exclude only within one tick, which is the span `--lock` already covers. Holding a claim
across ticks needs an owner that outlives the tick, which is not something fence
provides today.

This is why W101 has three candidates, not one: a writer-side lease, a reader-side
overlap flag (render/nemik), or both. W100's count of how often ready waypoints share a
touches tag is the figure the choice should rest on.

## W100 — the measure (2026-09-27)

Instrument: `scratchpad/w100measure.py` (read-only; this session), over
`~/github/<repo>/.claude/paths-forward.json`. "Live" = status `ready` or `working`.
A pair is two live waypoints whose `touches[]` intersect. All six files were readable;
none was counted as zero for being unreadable.

| repo | waypoints | live | live with touches | distinct tags | live pairs sharing a tag |
|---|---|---|---|---|---|
| gabion | 27 | 7 | 7 | 47 | 3 |
| luthen-observability | 138 | 56 | 46 | 160 | 153 |
| mtools | 112 | 3 | 3 | 44 | 0 |
| paperkit | 119 | 37 | 32 | 81 | 14 |
| rosettapkg | 17 | 1 | 0 | 39 | 0 |
| substrate | 74 | 33 | 33 | 176 | 101 |

Across all six: 524 distinct tags, 1014 tag uses, 152 tags used by more than one waypoint
(all statuses). Live pairs sharing a tag: 271.

⚑ **The pair count is dominated by the GRAIN of the tag, not by contention.** Two kinds
of tag appear, and they behave differently:

- **Topic tags** (a subsystem or theme): substrate's `cleanroom` on 14 live items
  (W63–W76) alone yields 91 of its 101 pairs. luthen's `alerts`, `policy`, `terraform`,
  `md0` and `k3s` produce most of its 153. A lease keyed on these would serialise most
  of a repo's live queue, which is exclusion over a theme rather than over an artifact.
- **Artifact tags** (a file path): paperkit tags by file. `paperkit/resolver.py` is on
  5 live items (W25, W32, W62, W125, W127), giving 10 of its 14 pairs; the others are
  `bibparse.py`, `wcag_entail.py`/`wcag_model.py`, `lo-export.py` and `verb.bzl`. These are
  the pairs where two agents could actually write the same bytes.

⚑ **What this measures and what it does not.** It counts pairs that COULD contend,
because both are workable and name a common tag. It does not count pairs that DID
contend: nothing records two agents working overlapping waypoints at the same time.
The ledgers carry one line per tick per repo, and no ledger line names a second
repo's or session's concurrent work. So the figure is an upper bound on exposure,
not a measured collision rate.

For W101: any writer-side lease has to face the grain split first. Either it applies
only to artifact-grain tags (so it needs a way to tell them apart, e.g. a declared kind,
as fence's keyway does for claims), or it serialises topic-tagged queues wholesale. A
reader-side overlap flag has no such cost: showing that "W125 and W127 both touch
paperkit/resolver.py" is useful at either grain.

## W101 — the choice (2026-09-27)

**Chosen (revised same day, see the correction below): exclusion over declared overlap is
the target; the reader-side overlap flag is its first slice, not the whole answer.**
pathsforward first reports when two live waypoints share a `touches[]` tag (a read mode, plus
a payload line in ATOMIZE's advisory shape). Enforcement follows once its two preconditions
(below) exist. The flag's first slice is W118, the W100 instrument made re-runnable.

⚑ **Operator correction (2026-09-27): "that's why we have touches".** `touches[]` is the
DECLARATION of potential overlap, made in advance. The earlier draft of this section argued
that because no ledger records a collision, there was no evidence to justify enforcement.
That inverts the field's purpose: a declared overlap is the reason to act, and waiting for an
observed collision means acting only after the damage the declaration exists to prevent.
That argument is withdrawn (kept as residue below). What still stands against enforcing
TODAY is mechanical, not evidential: points 1 and 2.

**Why, from the two readings above:**

1. *The lifetime mismatch (W99).* A fence lease lives as long as its owner process. A
   `working` waypoint spans ticks and sessions. A writer-side lease therefore either
   excludes within one tick, which `--lock` already covers, or needs an owner that
   outlives the tick, which does not exist. The flag needs no owner at all.
2. *The grain split (W100).* 271 live pairs share a tag, and topic tags produce most of
   them (substrate's `cleanroom`: 91 of 101). A lease keyed on those would serialise most
   of luthen's and substrate's queues. The flag is useful at both grains: an artifact
   overlap ("W125 and W127 both touch paperkit/resolver.py") is a warning, and a topic
   overlap is context.
3. ~~*Exposure is not collision (W100).*~~ WITHDRAWN, see the correction above. The W100
   figure is still correctly labelled as an upper bound on exposure; what was wrong was
   treating the absence of recorded collisions as a reason not to exclude.

### Residue (rejected, kept with reasons)

- **Writer-side lease now (fence `claim:label:touches/<tag>`).** Rejected on 1 and 2.
  Revisit if both hold: an owner that outlives a tick exists (e.g. a lease held by a
  long-lived session process, or one renewed per tick with a declared expiry), and tags
  declare their grain so only artifact tags are leased. ⚑ Note also that `label:`
  normalisation is a no-op for non-Bazel names (W99), so this spelling is in effect a
  byte-compared bare claim.
- **Both at once.** Rejected as sequencing, not on the merits. The flag lands first; the
  lease follows once the two preconditions above are met. ⚑ An earlier draft also required
  "real overlap evidence" first; that condition is withdrawn (the declaration is the
  evidence).
- **"No recorded collision, so no enforcement yet."** WITHDRAWN (operator, 2026-09-27). It
  treated a declaration of overlap as weaker evidence than an observed collision, which is
  backwards for a field whose job is to be read before the work starts.
- **Declaring tag grain (e.g. `path:`/`topic:` prefixes on touches).** Not rejected: it
  is a precondition of the lease (point 2), now on the path rather than deferred.

### For W102 (review)

Send this section and the W100 table to el-openglo-e8 (offered to spec it) and nemik-bb
(renders touches, and would carry the flag in nemik's views). The question to ask: is a
lease over declared overlap blocked only on the two preconditions (an owner that outlives
a tick; tags that declare their grain) the right shape for your loop, and which of your
tags are artifact-grain?

## W102 — review replies (2026-09-27)

### nemik-45 (renders touches)

1. **Line shape: one line per tag, not per pair.** `OVERLAP <tag>: W3,W7`. Pairs grow n²,
   a tag line is one line per contention point. Grep-stable like ATOMIZE. nemik computes
   cross-repo overlap itself from the adapter's `nemik:touches`; the pathsforward line is
   the local advisory view. → shapes W118.
2. **Shape agreed.** A lease blocked only on W119/W120 is right for nemik. nemik's loop
   suspends when idle, so a per-tick claim would lapse constantly: this supports W119
   needing an owner beyond one tick.
3. **Grain: all topic, no file tags** (web-ui, gate, operator, docs, shapes, cli, ...).
   Only `operator` is live, once: no overlap today. A `file:` prefix convention would do
   for W120.

⚑ **Defect reported:** three nemik tags are comma-joined single strings
(`adapter,cleanup`, `check,verification`, `paperkit,docs[,tests]`); `--touches` accepted
each as one tag. Proposed: `--check` flags a comma inside a tag. → W121.

### el-openglo-f6

Shape agreed, with amendments.

0. ⚑ **Roster gap (census B3):** el-openglo has 98 waypoints with touches[] and is not in
   the W100 table, so 271 pairs is over six of seven queues. W118's run must include it.
1. **Lease `working` only; `ready` stays report-only.** Their need is exclusion across
   sessions (swarm worktrees, peer loops), not within one queue. ⚑ Their worst swarm
   defect (their W62) was verification against a tree five commits stale; a touches lease
   would not catch it, but a claim that records the **base sha** it was taken against
   would. → W119 claim content.
2. **Three grains, not two:** topic (hooks, emitters, plasma, ...); **module as a bare
   stem** (make_deb, display_types, ... never byte-equal to paperkit-style path tags);
   **external party** (summit, paperkit, android, ...). ⚑ And shared stems can be a shared
   upstream READ, not a write (their W30: a rejected collapse W30/W43 on display_types,
   W30/W58 on make_notify_marquee). So W120 needs a **read/write** distinction as well as
   grain; a lease on read tags serialises work that cannot collide.
3. **Per-tick-renewed claim with declared expiry: agreed, on conditions.**
   (a) expiry > cadence + longest bounded step (their commit held the tree 10+ min;
   check_tree_writes timed out at 600 s on 09-26): per-waypoint, or at least 2x cadence.
   (b) a lapse is a ledger line and a report, never a silent release.
   (c) the holder identity must survive compaction: the loop's job/state path, not the
   session pid.

## W119 — precondition A: an owner that outlives a tick (2026-09-27)

Design only. Built from W99's lifetime mismatch and el-openglo's condition 3 (a)-(c) above.

1. **The owner is the loop, not the process.** Holder = `<state_path>#<lock holder>`, the
   same identity `--lock` already records (e.g. `mtools-tick-opus`). It survives compaction
   and session restart because both names live on disk (condition c). A fence
   `pid:starttime` owner is kept for the per-tick hold only.
2. **Only `working` is leased.** `ready` stays report-only (OVERLAP line, W123).
   el-openglo amendment 1.
3. **The claim records its base.** Fields: `tag`, `holder`, `waypoint`, `base_sha`
   (`git rev-parse HEAD` when taken), `taken_at`, `renewed_at`, `expires_at`. A holder
   whose tree has moved past `base_sha` sees that at renewal. This is the stale-tree case
   (their W62) the lease exists to surface: it is reported, not refused.
4. **Expiry is declared.** Per waypoint (`lease_ttl`), default `max(2 x cadence, cadence +
   longest recorded bounded step)`. Measured today: cadence 15 min, longest step 10+ min
   (their 600 s gate timeout), so the default is 30 min. That equals the existing `--lock`
   stale-takeover bound (30 min, skill section 4.1), so a lapse and a lock takeover agree.
5. **Renewal is part of the tick.** Every tick that holds the lock renews every claim its
   holder has, whatever item it works. A loop that still ticks keeps its claims. A
   suspended loop (nemik suspends when idle) lets them lapse, which is correct: a
   suspended loop is not working anything.
6. **A lapse is written, never silent.** When a tick finds a claim past `expires_at`, it
   writes a ledger line `lapsed W<n> <tag> holder=<h> base=<sha>`, and `--check` reports the
   lapse until the holder renews or the waypoint leaves `working`. Nothing is released
   without that line (condition b).
7. **Where it lives.** In the state file, beside `lock`, as `leases[]`. pathsforward's
   `flock` plus temp-file-replace (W99) already makes that write atomic. A cross-repo lease
   (el-openglo's swarm worktrees) is fence's job, keyed `claim:label:touches/<tag>` once
   W120 gives the tag a grain. This section does not design that.

Open, handed to W120: which tags get leased at all (grain, and read versus write). Until
W120 lands, nothing here refuses a tick. This is the owner model W103 will enforce over.

## W120 — precondition B: tags declare grain and access (2026-09-27)

Design only. Built from W100's grain split, el-openglo's three grains and read/write point,
nemik's all-topic tags, and nemik-overlaps' fleet run (55 OVERLAP lines, 10 cross-repo, all
10 topic coincidences such as `gate`, `gpu`, `bazel`, `corpus`).

1. **Grain is a prefix, declared by the author, never guessed.** This is the same rule as
   fence's keyway (W99: the kind is declared by the claimant).

   | prefix | grain | compares by | example |
   |---|---|---|---|
   | `file:` | artifact | repo-relative path, normalised (no `./`, no trailing `/`) | `file:pathsforward/src/mikemol/pathsforward/ops.py` |
   | `mod:` | artifact | dotted or bare stem, byte-compared | `mod:display_types` |
   | `party:` | external | name, byte-compared | `party:summit` |
   | none | topic | byte-compared, as today | `cleanroom`, `gate` |

   An unprefixed tag stays a topic, so every existing tag keeps its meaning with zero
   migration (1014 tag uses over six queues, W100).
2. **Access is a suffix on artifact tags only: `!w` for write, default read.** Example:
   `file:pathsforward/.../ops.py!w`. el-openglo's W30/W43 case (a shared upstream READ of
   `display_types`) then never excludes, because two reads cannot collide. A topic or
   `party:` tag with `!w` is refused by `--touches`: neither names bytes.
3. **Leasable = artifact grain AND `!w`.** Only those enter W119's `leases[]`. Everything
   else stays report-only on the OVERLAP line. Under this rule cleanroom's 91 pairs lease
   nothing, and paperkit's `resolver.py` pairs lease only where both items write it.
4. **`mod:` and `file:` do not unify.** A stem does not determine a path (el-openglo stems
   are never byte-equal to paperkit-style path tags). A `mod:X!w` and a `file:.../X.py!w`
   show as a cross-grain OVERLAP line, `OVERLAP? mod:X ~ file:.../X.py`, and never lease
   against each other. Unifying them needs a per-repo module map, which is its own
   waypoint if the report shows it matters.
5. **Cross-repo.** `file:` paths are repo-relative, so a cross-repo lease (fence
   `claim:label:touches/<repo>/<tag>`) must add the repo. Topic tags across repos stay
   report-only, which retires all 10 of nemik-overlaps' cross-repo lines from enforcement.
6. **`--check` rules this adds:** an unknown prefix (e.g. `path:`), `!w` on a non-artifact
   tag, and a `file:` path with `..` or a leading `/` are each flagged, the same way W121
   flags a comma in a tag.

With W119 (the owner) and this section (what is leasable), both preconditions of W103 are
designed. What W103 builds: `--touches` parsing of prefix and suffix, the `--check` rules
in point 6, `leases[]` in the state file, and renew/lapse in the tick.
