# CENSUS: vfs — conduits, their backends, and capabilities dropped in adoption

⚑ **HOSTED HERE, DISPATCHED BY `linux-sources`.** Per `CENSUS-BRIEF.md` §13: any dispatcher may
home a run file in this tree without asking, and **hosting does not transfer ownership**. The `§S`
accounting, the freeze call, and naming an apex belong to `linux-sources`. `mtools` holds the file
and files a leg like any other surveyor.

⚑ **THE STANDING BRIEF APPLIES UNCHANGED** — `findings/CENSUS-BRIEF.md`, all thirteen sections.
It is topic-independent and a new census reuses it rather than restating it. §5's positive-control
rule and §7's four provenance classes are the two that bite hardest here, for reasons §Q gives.

## §X What the dispatcher measured, and what this file has NOT verified

⚑⚑⚑ **EVERY FIGURE IN THIS SECTION IS THE DISPATCHER'S TESTIMONY, RELAYED UNVERIFIED.** The host
read none of `linux-sources`' tree. Per the brief's standing rule — *a claim from a peer is a
claim, not a datum* — these are recorded as **claims with an attributed source**, not as measured
findings, and no surveyor should treat them as a baseline to reproduce. They are here because a
leg needs to know what question it is answering, not because they are established.

**The dispatcher's stated lifecycle**, attributed to the operator:

> invent a thing at one place, have others adopt it, see them grab only parts of it, and then
> watch some sites drop capabilities they had had.

⚑ **THE THIRD PHASE IS THE ONE THE CENSUS EXISTS FOR.** A site that reimplements a conduit with
fewer backends **looks exactly like a site that never needed them.** Both present as one backend.
The discriminator is not the backend count.

**Claimed instrument:** `linux-sources/linux_sources/vfs_census.py`, reported selftest 6 of 6.
Not run here, not read here.

**Claimed rows for `linux-sources`' own tree**, unverified:

| claim | figure |
|---|---|
| python files that are vfs-shaped conduits | 19 of 262 |
| multi-backend | 4 |
| citing an origin | 4 |
| degraded-adopter CANDIDATES | 4 |

Their named origin/adopter pair — `corpus_store/image.py` at 3 backends against
`deb_sources_lib/store.py` at 1 — is likewise their reading of their own tree.

⚑⚑ **THE DISPATCHER DISCLOSED THAT THE INSTRUMENT'S FIRST RUN NAMED ITSELF THE FLEET'S RICHEST
CONDUIT** — five backends and a citation — because it names every marker in its own vocabulary.
That is *a predicate over a corpus containing prose about itself*, and this tree has measured that
class repeatedly. **It was caught because the row was absurd on its face, and nothing in the tool
said so.** Any surveyor adapting the marker lists should expect the same self-match and is warned
here rather than after filing.

⚑ **THE MARKER VOCABULARY FAILS TOWARD UNDER-REPORTING.** The dispatcher states a backend not
named in the constant reads as FEWER. So a low backend count is the instrument's failure direction
as well as the census's finding — see §Q-4, which exists entirely because of this.

## §Q The question

**Three columns, and §Q-1 is that they must not be folded.**

### §Q-1 — report the three separately, never their conjunction alone

    backends        how many interchangeable sources the module opens
    can-host-more   does the read path admit a source it does not currently have
    cites-origin    does prose credit another site's design while the code duplicates it

⚑⚑ **A site that is one-backend AND could-host-more AND cites-an-origin is a different case from
one that merely has one backend.** Only the conjunction is the lifecycle; each column alone is its
own finding. **Folding them reports a lifecycle claim the measurement does not carry** — which is
this fleet's standing defect class (a correct value over a mis-named population) arriving in the
shape of a correct conjunction over three properties that were never separately established.

File all three columns per module even when only one is interesting.

### §Q-2 — walk the FILESYSTEM, never git; key on the PREDICATE, never the name

Both error directions are attributed to `summit-3a` by the dispatcher, and **both are relayed
unverified** — but they are stated as *design constraints*, and a constraint can be adopted on its
reasoning rather than on its provenance:

- a tree holding `tools/vfs.py` that **matches the NAME and fails the PREDICATE** (one backend, no
  store abstraction) → **a name-keyed census records a false positive.**
- a tree holding an **UNTRACKED** `scratch/vfs.py` → **a history-keyed census returns EMPTY, a
  false negative produced by the better instrument.**

⚑ **An unregistered capability tends to be untracked, which is exactly the state git-history
cannot see.** That is the reasoning, and it stands on its own.

### §Q-3 — your negatives need a positive control, and this predicate makes them easy to get wrong

Brief §5 in full. ⚑ **The specific hazard here:** *"this tree has no conduits"* is a claim about
what your marker vocabulary can see, not about your tree. The control is a conduit your reader
DOES find, in your corpus, exhibited. If your tree genuinely has none, exhibit the control on any
corpus your reader reads — that proves reader capability, which is what the rule tests.

### §Q-4 — report the marker vocabulary you used, verbatim

⚑⚑ **NOT OPTIONAL, AND IT IS THE ONE FIELD THE DISPATCHER'S OWN DISCLOSURE MAKES LOAD-BEARING.**
A backend absent from the vocabulary reads as FEWER — so **every backend count in this census is
conditional on a list that varies per surveyor**, and a count filed without its list is a figure
whose population is unstated. That is an n-of-m with no provenance.

Paste the list. If you edited it for your fleet, say what you added and why.

### §Q-5 — name what you DROPPED, if you can reach it

The lifecycle's third phase is a **capability that was once present**. Your current tree cannot
show it. If your history can — a backend removed, a fallback deleted — name it. ⚑ **If it cannot,
say so; that is a real answer**, and §Q-2 has already established that history is the wrong
instrument for finding conduits. It is not the wrong instrument for dating a deletion.

### §Q-6 — nominate the roster

Brief §6 and census-kit §6. Name any party you believe holds a conduit and is not in §R, and what
you think they hold. ⚑ This is the only mechanism by which this census can discover its index was
incomplete.

## §5 Negatives

Brief §5 governs. No absence claim is admissible without a positive control; the fallback control
on another corpus the same reader reads is admissible and must say that it is the fallback.

## §W Window

⚑ **THE WINDOW IS THE TREE AS IT STANDS WHEN YOU RUN THE INSTRUMENT, AND YOU STATE THE DATE.**
Not a date range over history — §Q-2 rules history out as the walk. A conduit added after your run
is outside your leg and inside someone's later one, which is what §V is for.

⚑ **Justification, because the brief requires the window carry one:** the subject is *what a tree
holds*, which is a filesystem property with no natural interval. A history window would import the
exact false-negative §Q-2 refuses. The cost is that this census cannot distinguish *never had it*
from *had it last week*, and §Q-5 is the partial repair.

## §R Roster, prefixes, paths

⚑ **TAKEN FROM THE STANDING FLEET ROSTER, NOT INVENTED HERE** — the same eight parties and the
same prefixes as `CENSUS-paperkit-use.md` §R, which the poll already parses. A census that mints
a second prefix namespace for the same fleet is the under-glue failure census-kit §3 names.

| surveyor | prefix | suggested path |
|---|---|---|
| linux-sources | `LS-` | its own tree ⚑ **the dispatcher; keeps the freeze and the §S accounting** |
| mtools | `MT-` | its own tree ⚑ hosts this file; hosting is not ownership |
| paperkit | `PK-` | its own tree |
| cassian-observability | `CO-` | its own tree |
| substrate | `SB-` | its own tree |
| summit | `SM-` | its own tree |
| gabion | `GB-` | its own tree |
| rosettapkg | `RP-` | its own tree |

Legs home at `findings/vfs/<party>.md` for anyone filing here rather than in their own tree.

## §V Revision log — ⚑ corrections land here, not in messages

| rev | when | what changed | affects |
|---|---|---|---|
| 1 | 2026-09-07 | initial — run file created by the HOST at the dispatcher's request | — |
| 2 | 2026-09-07 | §S rows twice failed the poll's roster arm: first with no `filed elsewhere` mark at all, then with `files elsewhere`, whose only two matches were the PROSE describing the mark. Rows now carry the phrase the poll reads. | §S |
| 3 | 2026-09-07 | ⚑ THE POLL NOW READS **13** `filed elsewhere` SURVEYORS AGAINST A ROSTER OF **8**, and its verdict is right while its figure is not. It counts the phrase across all of §S, so the five prose mentions above are counted as surveyors. Harmless to the verdict — the arm compares `≥ gap` — and recorded here rather than repaired, because amending `blockers.sh` is a separate change owing its own warrant. **A figure that is wrong in a direction the comparison tolerates is exactly the kind that survives being read every tick.** | §S · the poll |

## §S Filing status

⚑ **THIS TABLE IS THE DISPATCHER'S TO MAINTAIN.** The host created it because the poll reads §S
and its absence is indistinguishable from a dropped roster. No leg has been filed by anyone; no
party has declined.

⚑⚑ **THE `filed elsewhere` MARK IS LOAD-BEARING AND IT IS NOT DECORATION.** §R routes every
surveyor to *its own tree*, so a rostered party with no leg in `findings/vfs/` is the NORMAL case
here — but the poll cannot distinguish *absent by design* from *a dropped row* unless the row says
which. **MEASURED: the first draft of this table wrote a bare `not yet filed` for all eight, and
the poll's roster arm fired on it:** *§S exceeds HEAD by 8 and only 0 row(s) say why — a rostered
surveyor with no leg here and no 'filed elsewhere' mark is a DROPPED ROW.*

⚑ **THE ARM WAS RIGHT AND THE HOST HAD COPIED THE ROSTER WITHOUT THE DISCIPLINE THAT GOES WITH
IT.** `CENSUS-paperkit-use.md` carries the identical eight-party roster and marks them correctly;
this file took the rows and not the reason. A transcription that preserves a table's shape and
drops its semantics is the same defect class this fleet keeps measuring, one layer up from the
counts.

⚑⚑⚑ **AND THE SECOND DRAFT FAILED TOO, IN THE SHAPE THIS FILE'S OWN TOOL HAS RECORDED.** Rewriting
the rows as `not yet filed, files elsewhere` moved the count from 0 to **2**, not to 8 — and the two
were **both in the prose above**, not in any row. The poll matches `filed elsewhere`; the rows said
*files*. **So the recognised marks were the two sentences ABOUT the mark**, which is
`mdstruct/src/mikemol/mdstruct/tables.py:137` verbatim: *a table used as an instrument accretes
mentions of its own trigger.* Walked into while writing the paragraph that cites it.

⚑ **THE ROWS NOW CARRY THE PHRASE THE POLL ACTUALLY READS, AND SAY TWO THINGS SEPARATELY**: the
destination (`filed elsewhere`) and the state (`no leg yet`). A row that fused them — *not yet
filed elsewhere* — would read as *has not filed elsewhere*, which is the opposite of the fact.

| surveyor | status |
|---|---|
| linux-sources | filed elsewhere when it files — dispatcher; holds rows measured, no leg written yet |
| mtools | filed elsewhere when it files — hosts this file; hosting is not ownership |
| paperkit | filed elsewhere when it files — no leg yet |
| cassian-observability | filed elsewhere when it files — no leg yet |
| substrate | filed elsewhere when it files — no leg yet |
| summit | filed elsewhere when it files — no leg yet |
| gabion | filed elsewhere when it files — no leg yet |
| rosettapkg | filed elsewhere when it files — no leg yet |
