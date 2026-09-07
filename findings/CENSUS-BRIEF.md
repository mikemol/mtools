# `CENSUS-BRIEF.md` — the standing brief

Copy this into the coordinating repo **once**. It does not change per survey; the run file does.
Surveyors read it; nobody retypes it.

---

## §0 Roster

The roster in the run file's `§R` is complete and **includes you**. You are surveying your own
corpus, not auditing peers. Do not infer a recipient list from any message — the roster is in `§R`
and only there.

⚑ **One extra question, answered in your filing:** name any party you believe should be on this
roster and is not, and what you think they hold. A survey run over the wrong index computes the
wrong result, and nomination is the only way that gets discovered.

## §1 Your deliverable

Exactly one file: the path given in `§R`. **One file — not one per round.** Draft privately, revise
freely, file once. There is no second-order or third-order document; if you find yourself writing
one, the brief changed under you and the change belongs in `§V`.

## §2 Independence, and when it ends

Until the **freeze**: do not read another leg, do not send a peer message about findings, and do not
act on a peer's finding relayed to you. If one reaches you anyway, record it as **testimony** under
§7 and continue. After the freeze, cross-reading is the entire point.

Coordination traffic (paths, filenames, conventions) is not findings traffic — but it should not be
happening either, because those live in `§R`. If you need a convention that is not there, ask for an
append to `§V` rather than negotiating one peer-to-peer.

## §3 Inclusion predicate — stated as inclusions

State what you read, never as one-minus-exclusions. Report each source with its own count and the
total. List exclusions separately, with their own counts.

```
A  <predicate>                                   -> n
B  <predicate>                                   -> m
C  none — <shapes checked and found to carry nothing>
                                        TOTAL    -> n+m
```

## §4 Shapes — enumerate before you filter

Enumerate every record shape in your corpus **with counts, before filtering**. A scan covers the
shapes it knows to look for and reports that as coverage of the *question*; nothing about an
incomplete result announces itself as partial.

If the corpus is Claude session transcripts, read `references/transcript-shapes.md` — seven shapes
are listed there and each has already swallowed findings in a real run.

## §5 Negatives — the positive-control rule

Every asserted absence carries: *spelling searched · denominator · shapes read · shapes your reader
returns empty · reader name+version · **positive control***.

The positive control is a hit of the same shape from the same corpus. If that shape is genuinely
empty here, exhibit the control on another corpus the same reader reads — the rule tests reader
*capability*. Declare any mode your instrument silently accepts and ignores.

Without a control, write the finding as what it is: *"no such record appears among the shapes my
reader decodes."*

## §6 Window

Take the window from `§W`. It is stated **and justified** there. Independently of it, run the
**antecedent probe**: for each artifact you cite, search unbounded by date for its origin. If a
load-bearing artifact was created outside the window, report it. A window is a property of the query;
findings inside it are not facts about the subject.

## §7 Provenance classes — four, and they do not mix

**citation** (the source, in this corpus, verbatim) · **testimony** (relay, summary quote, anything
second-hand — evidence a thing exists, not the thing) · **machine** (harness-generated, scheduled,
or synthesized) · **inference** (yours).

Every quoted line carries its class. ⚑ Relays degrade: measured instances include a normalized typo,
a permuted recipient list, and an inserted bracket — all presented as "Verbatim."

## §8 Verbatim means verbatim

Preserve typos, casing, unclosed emphasis. Normalising makes the record a rendering rather than a
citation. Where someone quotes your own prose back at you, mark the quoted block as yours — their
contribution is the response, not the block being answered.

## §9 Disclosures, in your first paragraph

Whether you authored or own the subject under survey; any way your inputs differed from peers'
(including a differently-worded dispatch); anything you were told that you suspect others were not.

## §10 Coverage, stated as a population

Files, bytes, records per shape, unparseable/unreadable items (**count them; claim nothing about
what they held**), what you did not search **and why**. A list of found items with no population
statement is not a census.

## §11 ID namespace

Use the prefix assigned in `§R`, and only that prefix. ⚑ **IDs are directory-wide identifiers, not
file-local ones.** Two documents numbering their own findings `1, 2, 3…` produce citations that
resolve differently depending on which file the reader opened — a failure that is invisible to
anyone holding one document, which is every reader until the apex.

## §12 Termination test

Before filing, answer in one line: *could a reader of my file alone reconstruct what was asked of
the other legs?* If no — that is expected. Say so, and name it as the apex's job.

## §13 Homing — hosting a run file here, and what that does not grant

⚑⚑⚑ **FOUR CENSUSES WERE HOMED IN THIS TREE BEFORE THIS SECTION EXISTED, ALL BY PRECEDENT.** A
fifth dispatcher asked rather than assuming, split the ask into hosting and ownership, and was
right on both counts — there was no written grant to read, and precedent is what a peer has to
guess at. *A permission with no written form is worse than a claim with no re-derivation
procedure: the next party to ask cannot find it, and the one who does not ask cannot be refused.*

**Any dispatcher may host a run file here**, at `findings/CENSUS-<name>.md` with legs at
`findings/<name>/<party>.md`. No further permission is needed and none should be waited for. The
operator asked for findings homed here rather than scattered, and a session that has to be awake
to say yes is a bottleneck standing where a written rule belongs.

⚑⚑ **Hosting does not transfer ownership, and the two are genuinely different permissions.** The
`§S` accounting, the freeze, and naming an apex belong to whoever the **operator** put in that
seat. A homing tree that assumed them because the file sits in its directory would be settling an
ownership question by writing code — and a dispatcher who hands ownership away with the file has
given away something that was not theirs either.

⚑ **SO A HOSTED RUN FILE NAMES ITS OWN DISPATCHER IN `§X`, and that party keeps the freeze.**
`blockers.sh` here reports every census it finds on the filesystem, hosted or not; being *reported*
is not being *owned*, and the poll says which is which.

⚑ **A DISPATCHER WHO IS ALSO THE LEAST QUALIFIED SURVEYOR SHOULD SAY SO IN `§X` RATHER THAN
RECUSE.** Testimony about the alternative is evidence, and recording it as bias is what makes it
usable; a recusal loses the leg and the bias both.
