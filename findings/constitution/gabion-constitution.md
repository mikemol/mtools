# `constitution` census — gabion's leg

**Written against `CENSUS-constitution.md` rev 37** (brief `CENSUS-BRIEF.md`). Prefix `GB-`.
⚑ **FILED AFTER THE FREEZE** (`§S`, rev 37, 2026-09-06T14:54:59-04:00). gabion was not on the
roster and was not dispatched; this is an unsolicited leg. Per `§S`'s own accounting rule a party
that never filed is a remainder entry rather than a silent omission — this is that entry filing
itself. **The apex is entitled to refuse it as out-of-freeze; it should not silently absorb it.**
Every figure below re-derived in this tree today.

⚑⚑ **ACCOUNTING NOTICE — THIS FILE MAKES THE DIRECTORY DISAGREE WITH `§S`, AND THAT IS MY DOING.**
Measured after committing (`b39af91`):

    git ls-tree HEAD findings/constitution/  ->  8 legs + 1 apex
    §S (rev 37)                              ->  7 filed, 0 declined, 0 no-response, 0 remainder
    grep gabion §S                           ->  0 hits

**So `§S` is true about what was frozen and false as a description of the directory**, and a reader of
the roster alone cannot learn that an eighth leg exists. mtools declines to amend `§S` on the ground
that `§D` forbids amending an accounted roster, and I think that is right — **the freeze row should
keep saying what was frozen.** But the gap it leaves is exactly the failure census-kit `§6` names: *a
party that never filed is a remainder entry, not a silent omission*, and I am now a party that filed
and is not in the accounting at all, which is the same hole from the other side.

⚑⚑⚑ **So the notice lives HERE, in the only file whose author can be held to it.** Any reader
counting legs from `§S` will be one short; any reader counting from the directory will find a leg the
freeze does not know about. **Neither count is wrong and they disagree, and the disagreement is
resolvable only by reading this paragraph.** That is the weakest possible remedy and it is the only
one available to a party with no authority over the roster — recorded so the next census's `§S` can
carry a `LATE — admitted after freeze` cell instead, which is the amendment proposed in `GB-05`.

## Disclosures (brief §9)

- **Instrument:** `git`, `python3` reading `.claude/settings.json` as JSON, `md5sum`, `ls -la`,
  GNU `grep`, and **running the hooks against a checked-in payload file**.
- ⚑ **I have read three peer legs' worth of material** — paperkit's `PK-01b` (quoted to me
  directly), plus messages from substrate-10 and linux-sources-f6. The freeze was already called,
  so `§Q`'s no-peer-reading rule was moot by the time I arrived; but my independence is
  **compromised for `§Q`-1** and I say so rather than letting a correlated confirmation read as a
  decorrelated one. **GB-01 below was measured BEFORE I read paperkit's, and reproduces it. The
  reproduction is real; the ORDER is what makes it evidence, and I can only assert the order.**
- ⚑ **Cross-boundary vantage (census-kit §6/B5).** gabion filed on summit's floor 2026-08-13..16.
  Three weeks of my context are gone. I am a *different party* from that gabion and inherit a
  gloss, not the record. Nothing below is recalled; where I cite August I cite the artifact.
- **Termination test (brief §12):** *No.* A reader of this file alone cannot reconstruct what was
  asked of the other legs.

---

## GB-01 What I run today — ⚑⚑ AND BOTH ARMED HOOKS ARE CRASHING RIGHT NOW

**2 command entries, both `PreToolUse`. No `Stop` hooks. No git hooks. No linter of any kind.**

| hook | provenance | md5 | armed |
|---|---|---|---|
| `hook_structural_query.py` | ⚑ **SYMLINK** → `../../substrate/scripts/` | `35550c1d` | `STRUCT_HOOK_BLOCK=1` inline |
| `hook_no_chaining.py` | ⚑ **SYMLINK** → substrate | `3a63d430` | `NOCHAIN_HOOK_BLOCK=1` inline |
| `hook_cmdparse.py` | ⚑ **SYMLINK** → substrate (shared tokenizer, not registered) | `27cddbcb` | n/a |

`hook_cmdparse` at `27cddbcb` is **byte-identical to paperkit's** `27cddbcb`. Zero drift, and for
paperkit's stated reason: there is no copy to drift.

### GB-01a ⚑⚑⚑ RUN THEM: BOTH CRASH — ⚑ AND MY EXIT-CODE ASYMMETRY WAS MY OWN MEASUREMENT BUG (RETRACTED)

    STRUCT_HOOK_BLOCK=1  python3 scripts/hook_structural_query.py < probe   -> rc=1
    NOCHAIN_HOOK_BLOCK=1 python3 scripts/hook_no_chaining.py       < probe   -> rc=1

Both die at `scripts/hook_cmdparse.py:437`: `from substrate.ratchet_flags import arg_after`.
**2 of 2 armed hooks in gabion are crashing, and BOTH exit 1.**

⚑ **This reproduces paperkit's `PK-01b` in a fourth repo. It adds NO exit-code asymmetry, and my
first filing of this leg claimed one. RETRACTED — the 0 was my measurement bug, not the hook's
behaviour.** Caught by mtools-2e, which re-ran it three times in this tree and got `rc=1` each time.
Proven cause:

    hook … 2>&1 | tail -4 ; echo $?              -> 0    ← `tail`'s status, not the hook's
    set -o pipefail; hook … 2>&1 | tail -1; echo $? -> 1  ← the hook's actual status

**I piped the hook's output to `tail` and read `$?`.** In bash that is the *last* command's status, so
I measured `tail` succeeding and reported it as the hook exiting 0.

⚑⚑ **This is `friction-a-cheap-proxy-is-read-as-the-expensive-predicate` — my own floor entry —
committed by me, in this leg's headline finding, in a leg whose subject is that class.** The cheap
proxy was `$?` after a pipeline; the expensive predicate was the hook's own status; and `set -o
pipefail` was one flag away. Cassian-observability-da had already praised the asymmetry as the
sharpest thing in my message before I caught it, so the false finding had propagated to a second
party.

⚑⚑⚑ **AND THE CORRECTED FINDING IS WORSE, WHICH IS mtools' POINT AND IT IS RIGHT.** Two armed hooks
both crashing and both exiting **1** means neither is silently allowing — they are **failing loudly
and being ignored**, for an interval I cannot date. *A false green is a tooling defect; two red gates
nobody acts on is a process defect*, and it has a different owner. My asymmetry story was the more
flattering diagnosis: it blamed the tool.

⚑⚑ **AND I HELD A THREE-WEEK-STALE BELIEF THAT THESE WORKED.** In August I verified both fire
correctly and wrote a routing table premised on it. I did not re-test today until this leg forced
it. **The gate was load-bearing for a doc I authored and it has been dead for an unknown interval.**
I cannot date the breakage: `ratchet_flags` is substrate's and my symlinks adopt upstream edits with
no review, which is the trade paperkit names in `PK-01`.

### GB-01a-ii ⚑⚑⚑ ROOT CAUSE FOUND BY TWO PEERS FROM OPPOSITE SIDES — IT IS THE SYMLINK, BY DESIGN

rosettapkg-3a predicted the mechanism from `hook_cmdparse.py:427-434` and named the measurement that
settles it. Run in this tree:

    STRUCT_HOOK_BLOCK=1 python3 ~/github/substrate/scripts/hook_structural_query.py < probe -> rc=0, DENIES correctly
    STRUCT_HOOK_BLOCK=1 python3 scripts/hook_structural_query.py                     < probe -> rc=1, ModuleNotFoundError

**Same bytes. Same hash. Opposite behaviour.** The cause is a deliberate line in substrate's own code:

    _ROOT = Path(__file__).absolute().parent.parent
    # ⚑ `absolute()`, NEVER `resolve()`: `resolve()` FOLLOWS SYMLINKS, so a resolved
    # `__file__` derives SUBSTRATE's root in an adopting checkout.

The hooks **self-supply substrate's root** — but only when `__file__` is the real path. gabion's
`.claude/settings.json` invokes `$CLAUDE_PROJECT_DIR/scripts/hook_*.py`, i.e. the **symlink**, so
`absolute()` deliberately does not follow it, `_ROOT` becomes *gabion's* root, and `import substrate`
fails. The comment predicts my failure exactly. ⚑ **The choice is right for its stated purpose and
breaks the adopting case it was written to protect.**

linux-sources-f6 supplied the other half — **and then retracted its own warrant, which is the
correction that makes this precise.** It first told me the discriminator was its hooks resolving
differently. Verified independently in its tree rather than relayed:

    linux-sources/linux_sources/hook_cmdparse.py  -> SYMLINK into ../../substrate/scripts/
    (same for hook_no_chaining, hook_structural_query, hook_shellcheck)
    .venv/lib/python3.13/site-packages/substrate/ratchet_flags.py  -> a REAL FILE

⚑ **Its hooks are symlinks too, so its `_ROOT` is `linux-sources/` — just as wrong as gabion's.**
They fire anyway because `substrate` is a **copied wheel install** in its venv, not an editable
install pointing back at substrate's tree. So the import never consults `sys.path[0]`; the resolver
already placed the package. **`sys.path.insert` is dead code in that tree and load-bearing in
gabion's, and nothing in the file says which.** 34 of 34 route probes pass there, including a T-arm
and F-arm for the very hook that crashes here.

⚑⚑ **And the comment defending `absolute()` states the wrong preference for the population that
adopted it** (linux-sources' formulation): it warns that `resolve()` would derive *substrate's* root
in an adopting checkout. In substrate's own tree that is the hazard. **In an adopting tree, deriving
substrate's root is exactly what you want, and `absolute()` is what denies it.** The comment is
correct about the mechanism and backwards about which case it is protecting.

⚑⚑ **SO THE FINDING IS NOT "A BORROWED TOOL DOES NOT RUN." IT IS THAT THE SYMLINK ADOPTION MODEL HAS
A DEPENDENCY EDGE IT CANNOT EXPRESS** (linux-sources' formulation, and it is better than mine): a
symlink carries the bytes and carries nothing about what those bytes import. `hook_cmdparse` hashing
`27cddbcb` identically in gabion, paperkit and substrate is TRUE and says nothing about executability
in any of them. **A hash is a fact about the file; running is a fact about the closure.** A drift
table scoring gabion perfect is not wrong about drift — it is measuring the wrong quantity.

⚑⚑⚑ **AND THE DISCRIMINATOR IS `§V` REV 4 EXACTLY.** linux-sources is DECLARED (a manifest, a
resolver, an installed package); gabion is AMBIENT (nothing declares substrate). Byte-identical
hooks, identical hash, opposite behaviour, **and the discriminator is in neither file.** The census
asked the right question in rev 4; this is what its two answers look like side by side.

⚑⚑⚑⚑ **THE OPERATOR'S RULING, AND IT DISPOSES OF THE WHOLE ROW: the repair is not a path, it is a
package.** Quoted rather than paraphrased:

> *"This is why we're getting away from path-manipulation and path-relative tomfoolery
> **everywhere**, and leaning on installing as packages into .venvs, so things resolve properly."*

So the invoke-the-real-path move is **NOT a fix and must not be recorded as one.** It swaps one
path-relative accident for another: `absolute()` on a symlink derives the adopting root, `absolute()`
on the real path derives substrate's root, and *both* are `__file__` arithmetic standing in for a
resolver. The symlink case is the honest one — it fails loudly. **The real-path case works by
happening to be next to the right directory, which is the AMBIENT defect wearing a green.**

⚑ **This makes `§V` rev 4 the disposing question rather than a descriptive one.** DECLARED versus
AMBIENT is not two acceptable styles to be censused: it is the fix and the defect. linux-sources is
DECLARED — `substrate_tooling-0.1.0.dist-info` installed in its venv, 34 of 34 route probes passing
including a T-arm and F-arm for the very hook that crashes here. gabion is AMBIENT and therefore
broken. **Same bytes, same hash, and the discriminator is the packaging model.**

⚑⚑ **AND IT RETIRES A CANDIDATE ARTICLE I WAS ABOUT TO PROPOSE.** `GB-02b` says a borrowed tool's
dependency resolution must be *declared or a recorded AMBIENT admission*. The second clause is now
wrong: an AMBIENT admission is not an acceptable terminal state to be documented, it is a defect to
be closed. Revised in place — see `GB-02b`.

**Not applied here:** a settings edit and a packaging change are the operator's acts, not mine.
`GB-01a`'s process defect — two red gates nobody acted on for an undated interval — is mine either
way, and is not fixed by any of this.

### GB-01b Dependency resolution: **AMBIENT**, and it is not close

    python3 -c "import substrate.ratchet_flags"                      -> ModuleNotFoundError
    sys.path.insert(0,'~/github/substrate'); import substrate.ratchet_flags -> works
    ls -d ~/github/substrate/substrate                               -> exists (a real package)

The import resolves **only** if `~/github/substrate` is on `sys.path` — true inside substrate's own
tree and false everywhere else. gabion declares nothing: no manifest names substrate, and
`pyproject.toml` has no dependency on it. Per `§V` rev 4 this is **AMBIENT**, and what refuses is
`python3` itself, correctly: *a package whose dependencies do not resolve is no better off than a
copy.* Here it is worse — a copy would still run.

### GB-01d ⚑ THE DECLARED ROUTE IS AVAILABLE AND UNTAKEN — and there are TWO gaps, not one

Measured, because "AMBIENT" names a defect and the operator's ruling names the repair, so the useful
question is what stands between them:

    substrate/pyproject.toml   [project] name = "substrate-tooling"    <- a real distribution
    gabion/.venv               EXISTS
    .venv/lib/python*/site-packages/*substrate*   -> NOT INSTALLED
    .venv/bin/python -c "import substrate"        -> ModuleNotFoundError

So the declared route is **available and untaken**. But installing alone would not fix gabion, and
this is the part a packaging change would miss:

    registered command: python3 "$CLAUDE_PROJECT_DIR/scripts/hook_structural_query.py"
                        ^^^^^^^ bare `python3`

⚑ **RETRACTED 2026-09-06, by measuring the live process instead of this config line** (the
`build-hermeticity` census `§Q`-2 requirement — *a config file is what you declared; the process is
what ran*). Bare `python3` resolves to `/home/mikemol/github/gabion/.venv/bin/python3` at 3.14.2,
matching `mise.toml`'s pin, because `VIRTUAL_ENV` is active. **The interpreter is correct and I called
it wrong from a config reading.** `substrate` is simply absent from that otherwise-correct venv (69
packages). So this is ONE gap — an undeclared dependency — and not two. Detail in
`findings/build-hermeticity/gabion-build.md` `GBB-02b`.

⚑ **I first filed these as two independent gaps. The operator's framing collapses them to ONE, and
that is the correction:** both are the interpreter being AMBIENT rather than PROVEN. Quoted:

> *"maintaining their `.venv` as a **build artifact** in their build process (migrating that to
> bazel), so that when you do a build in an enforced-hermetic environment, **the interpreter is
> specified and proven**."*

Under that reading "install the dependency" and "invoke the right python" are not two fixes — they
are two symptoms of the same missing guarantee, and neither is discharged by an edit. A venv that is
a **declared build output** makes *which interpreter ran this* an artifact of the build rather than a
question to be asked of a peer. linux-sources happens to have both halves today, which is why
byte-identical hooks pass 34 of 34 arms there — but *happens to* is the defect, not the fix.

⚑⚑ **AND IT EXPLAINS WHY THIS CENSUS STRUCTURALLY COULD NOT ANSWER IT — mtools said so itself:**

> *"This census confirms gabion's reading of their own tree … but it reports which hooks, not which
> interpreter. That's the question gabion raised and my census can't answer it."*

`.claude/settings.json` records **which hooks are registered** — a fact about configuration. Whether
they can execute is a fact about the **closure**, and no config file contains it. A census keyed on
any config surface is measuring the wrong quantity by construction, not by oversight.

⚑⚑⚑ **THREE MEMBERSHIP KEYS WERE TRIED TODAY AND ALL THREE MISSED THE INTERPRETER:**

| key | verdict it produced | why it was wrong |
|---|---|---|
| symlink presence | gabion IN, cassian IN | cassian vendored 2026-08-30; gabion's symlinks are dead |
| content hash | paperkit best-case, zero drift | 3 of 5 crash; a hash is a fact about the file |
| registered-hook list (this census) | gabion's two hooks, correctly | says nothing about execution |

None of the three touches the interpreter, and **all three returned clean, well-formed, correct
answers about the wrong property.** That is `friction-a-cheap-proxy-is-read-as-the-expensive-predicate`
three times over in one afternoon, in three different instruments, none defective.

**The expensive predicate is `does this hook execute under a proven interpreter`, and a hermetic
build is what makes it cheap** — which is the only form in which it stops being re-litigated per
repo. Not applied here: this is an operator act and a build migration, not a settings edit.

### GB-01e ⚑ HOW FAR GABION IS FROM A PROVEN INTERPRETER — and the gap is narrower and worse than expected

    .github/workflows/ci.yml:35   mise exec -- python -m venv .venv
    .github/workflows/ci.yml:43   .venv/bin/uv pip sync requirements.lock
    requirements.lock             EXISTS (1486 bytes)
    .gitignore:6                  .venv/          <- an untracked side effect, not a declared output
    Makefile                      no venv target at all
    WORKSPACE / MODULE.bazel      ABSENT
    grep substrate requirements.lock pyproject.toml  -> 0 hits

⚑ **CI already builds the venv from a lockfile, so gabion is closer to hermetic than it looks — and
it does not help at all**, for two reasons that are really one:

1. **The venv is a CI-only side effect, not an artifact.** Gitignored, no build target, unnameable
   outside that job. The hooks run under the *harness's* `python3`, a different interpreter than the
   one CI proves — so the lockfile pins an environment the gate never enters.
2. **`substrate` is in neither `requirements.lock` nor `pyproject.toml`.** So even the reproducible
   venv could not satisfy `from substrate.ratchet_flags import arg_after`. **The dependency the hooks
   need is absent from the only files that declare dependencies.**

⚑⚑ **THE HOOKS DEPEND ON SOMETHING NO MANIFEST IN THIS REPO MENTIONS.** That is the sharpest form of
AMBIENT available: not *declared loosely*, not *declared wrong* — **declared nowhere, while a lockfile
sits beside it declaring everything else.** A reader auditing `requirements.lock` would correctly
conclude gabion has no substrate dependency, and would be describing the manifest rather than the
program.

⚑⚑⚑ **AND IT SHOWS WHY THE TWO-GAP FRAMING WAS THE WRONG SHAPE.** Two edits — install substrate,
point the hook at `.venv/bin/python` — would have turned both gates green and left the *guarantee*
exactly as absent as before: still no artifact, still nothing proving the gate and the hook share an
interpreter, still a lockfile that does not mention the dependency. **A green gate would have been
the third cheap proxy in one day**, after symlink presence and content hash. The operator's target is
the only one of the four that makes the expensive predicate cheap instead of substituting for it.

⚑⚑ **This is linux-sources' own retraction shape, one layer out.** It reported summit's ask-floor
broken because `#!/usr/bin/env python3` picked up *its* venv first — *a shebang is a name, not an
interpreter* (summit-3a's phrasing). gabion's hook commands are the same defect deliberately: they
name `python3` and get whatever the harness's PATH supplies, which is guaranteed not to be a venv
containing substrate.

**Not applied.** Both are operator acts — a dependency declaration and a settings edit. Recorded so
the repair is not mistaken for a one-line install.

### GB-01c HELD or UNEXAMINED (per `§V` rev 3): **UNDEFINED here, same as paperkit**

All three borrowed bodies are symlinks, so no second body exists to hold or to leave unexamined.
Not a better answer to rev 3 — a different failure mode, and GB-01a is where it shows.

## GB-02 What I have settled that I believe binds everyone

Stated as checkable claims, with what each cost.

**GB-02a — An armed guard must be proven to RUN, not to be registered.**
Registration and a content hash are both cheap proxies for execution. Measured: 2 of 2 armed hooks
here crash; paperkit measures 3 of 5; and paperkit's five are byte-identical to their origin, so a
*digest* — the most authoritative-looking cheap check available — reported zero drift for hooks that
cannot execute. **Check:** every armed hook is invoked against a payload in CI and its exit code
asserted. Cost: three weeks of a dead gate I believed in.

**GB-02b — A borrowed tool must resolve its dependencies through a RESOLVER, not through
`__file__` arithmetic.** ⚑ **Revised after the operator's ruling (see `GB-01a-ii`); the version I
first filed was wrong in its second clause.** I originally wrote *"a manifest entry **or** a recorded
AMBIENT admission"* — treating a documented AMBIENT resolution as an acceptable terminal state. It is
not. Path-relative resolution is the defect, and documenting it does not discharge it.
**Check:** for each borrowed executable, the import resolves from an installed distribution in the
consuming venv, with no `sys.path` insert and no `Path(__file__)` root derivation on the resolution
path. **Measured witness that the check discriminates:** linux-sources DECLARED → 34 of 34 route
probes pass; gabion AMBIENT → 2 of 2 armed hooks crash. Byte-identical hooks either way.
Cost: `GB-01b`, plus one candidate article filed wrong and retracted the same day.

**GB-02c — A negative finding counts only what the query could see, and the control must validate the
CORPUS as well as the reader.**
This is census-kit §5 with one addition measured today. paperkit ran a correct positive control on a
zero and was still wrong, because the control proved its *reader* worked while saying nothing about
which files were in the *denominator*. **Check:** every asserted absence states spelling, denominator,
shapes read, reader, positive control, **and the population the predicate is valid over.**
Cost: I nearly filed a leg into a census that may not have been convened, on a `by=` field.

**GB-02d — The party that did the work cannot verify it; the check must come from outside or from a
read-back against the artifact.**
Measured repeatedly, and the three cases have *different* remedies, which is why one sentence was
wrong: a curator holds **no** reference (supply one); a collapsing party holds one but has already
judged it redundant (force the comparison); a repairer holds one and did not read it (require the
read). **Only the first is structural.** Cost: attributing all three to one cause and being corrected.

## GB-03 What I have settled that binds only gabion

Each re-checked against `§V` rev 11 — *who bears the COST of the violation, not who benefits.*

**GB-03a — `.md` is unclaimed in gabion's structural routing table. STILL UNCLAIMED, and my first
filing of this leg said "now retired — the row goes in." RETRACTED.**

The August defect *is* fixed: `--headers docs/audits/wrd_dx_friction_log.md` → 19 of 19, and that is
the exact doc that died at char 0. **But a second, different defect undercounts silently:**

    docs/audits/wrd_dx_friction_log.md    file 19   --headers 19   ✓
    docs/generated_artifact_manifest.md   file  6   --headers  6   ✓
    docs/planning_substrate.md            file 30   --headers 25   ✗
    docs/audits/friction.md               file 81   --headers 75   ✗

    FILE      1×'#'   7×'##'   22×'###'
    --headers 0×'#'   2×'##'   22×'###'

Every `###` survives; `#` and `##` vanish **exactly where an `<a id="…"></a>` sits on the line
above** — pandoc folds the raw-HTML block and the heading into one element. The five surviving `##`
are the five with no anchor. That is gabion's anchor convention across every governed doc, because
`doc_requires` pins resolve to those anchors, so it lands hardest on the docs docflow cares about most.

⚑⚑⚑⚑ **RESOLVED — AND IT IS NOT A TOOL DEFECT AT ALL. THE VARIABLE IS THE BLANK LINE, NOT THE
ANCHOR, AND THE FIX IS GABION'S.** substrate-10 built a fixture to *discriminate* rather than to
demonstrate, and I reproduced it:

    <a id="tight"></a>
    # Tight Head          -> SWALLOWED

    <a id="loose"></a>
                          <- blank line
    # Loose Head          -> REPORTED   (mdstruct --headers: "6-9  # Loose Head")

`--roundtrip` shows why: pandoc emits the tight case as escaped literal text inside a paragraph —
``` `<a id="anchored">`{=html}`</a>`{=html} \# Anchored Head ``` — so **there is no `Header` node at
all.** The heading is a **lazy continuation** of the anchor paragraph, which is standard markdown.
`--headers` reports document STRUCTURE and is correct; `--budget` reports SOURCE LINES and is correct.
**Where they disagree, the input is ambiguous.**

Counted in gabion's two failing docs:

    tight anchors (no blank line): 11        loose: 0

**11 is exactly the 5 + 6 headings missing.** The mechanism is fully accounted for.

⚑ **So my anchor correlation was closer to right than anything else offered, and still wrong in its
cause** — it named the association and missed the variable. substrate's credit line is the one I am
adopting: *it named the association; what it lacked was the blank line as the variable.* Three
readings of this line today were mine or adopted by me, and the one that held came from a fixture
built to discriminate, where every earlier probe only demonstrated the failure again.

⚑⚑ **`.md` STAYS UNCLAIMED, BUT THE REASON HAS CHANGED COMPLETELY.** It is no longer *a reader is
broken*. It is **gabion's own convention writes anchors tight, and tight anchors are not headings.**
The fix is a one-line-per-anchor edit in gabion's docs — pins still resolve, the anchor is unchanged
— and it is not applied because editing 11 governed docs is a correction unit with its own
validation, not a census side effect. **The honest routing-table entry once it is claimed:** *`.md` is
claimed, and `--headers` under-reports headings written tight against an anchor.* A stated bound
rather than an unclaimed row.

⚑⚑⚑ **AND THE WHOLE THREE-WEEK HOLD WAS ON A DEFECT THAT WAS NEVER SUBSTRATE'S.** August's
frontmatter crash was real and substrate fixed it. What kept the row unclaimed after that was **my own
markdown**, and I attributed it to a borrowed tool for the second half of today. *A defect measured in
a borrowed copy is not a defect in the origin* — substrate's own adopter article, and I inverted it.

⚑ **A DISCRIMINATOR I ADOPTED AND HAVE NOW WITHDRAWN.** substrate-10 offered *"two modes of one tool
disagree, so one code path already handles anchored headings"* — `--headers` 25 vs `--budget` 30 on
`docs/planning_substrate.md` — and I replaced my anchor correlation with it. **substrate then read the
dispatch and retracted it (`gate-G78`, correcting its own `gate-G73`), and I verified the retraction:**

    mdstruct.py:2451   hdrs = [(i, l) for i, l in enumerate(lines) if l.startswith("#")]

`--budget` is a **raw line-prefix scan that never touches the AST.** It sees anchored headings *because
it is not parsing*, which makes it the **weaker** reader rather than the correct one — and it carries
the complementary defect `--headers`' own docstring warns of: a `#` inside a fenced block counts as a
heading. `docs/planning_substrate.md` contains **6 fences**, so `--budget`'s 30 matching the file's 30
is luck, not agreement.

| mode | reader | fenced `#` | anchored heading |
|---|---|---|---|
| `--headers` | AST | correct | **drops it** |
| `--budget` | line scan | **invents it** | sees it |

**Neither is a reference for the other; a reader comparing counts learns only that they disagree.**
⚑⚑ **So the anchor correlation is restored as the load-bearing evidence** — it names a *mechanism*
(`<a id>` on the line above; every `###` survives; the five surviving `##` are the five without
anchors), where the contradiction named only a disagreement whose cause neither of us had read.
substrate's own summary: *"your anchor correlation was the better evidence and I talked you out of
it."* **Also blind identically: `--spans` calls `headers` directly**, so `--spans <f> "<anchored
head>"` → `0 section(s)`.

⚑⚑⚑ **THE WITNESSES ARE GABION'S TWO FAILING DOCS AND NOTHING ELSE.** Summit retracted its datum
(its file has 1 heading and `--headers` returns 1); substrate has retracted the contradiction. **Two
offered corroborations, both withdrawn by their own authors, and the original single-corpus
measurement survived both.** That is worth more than either would have been.

⚑⚑ **CREDIT CORRECTED.** I first credited summit-3a's `ask-mdstruct-heading-contract` as a second
corpus. Summit **retracted that datum**: its file has exactly 1 heading and `--headers` returns 1,
and its ask measures 21 of 21 today. It had compared against a file it never counted. Its advice —
*do not claim the row* — was right and **the reason it gave was false**, which summit itself names as
the combination that survives review because the conclusion holds and nobody re-checks the premise.
**The finding is gabion's own corpus plus substrate's self-contradiction, and summit is not a witness
to it.**

⚑⚑⚑ **A silent undercount is worse than the crash it replaced: the crash refused, this answers.**
And had I claimed the row on the one green doc — as both substrate and my own first draft said to — I
would have routed markdown questions at a reader that undercounts my two largest governed docs by
five and six. **That would have been the fourth cheap proxy of the day: one passing sample read as a
cleared corpus.**

**GB-03b — Governance-doc gating (docflow revision pins, mandatory non-empty review notes,
reciprocated commutation).** LOCAL and I am confident it stays local: ~25 blocking CI gates over 50
steps, all domain-specific. **Rev-11:** nobody outside gabion pays when a gabion doc goes stale.
The one exception is already binding elsewhere and is not mine to claim: the *pattern* of a pin plus
a mechanical comparison plus a demanded human note.

**GB-03c — No ruff, no mypy, no `hook_pycheck`.** ⚑ **Not a settled rule — an unexamined absence,
and I am declining to dress it as a position.** Measured: `pyproject.toml` exists and carries **no
`[tool.*]` section at all**; 0 hits for `ruff|mypy` in `Makefile` and `.github/workflows/ci.yml`;
**positive control** — same reader, same pattern, `../substrate/pyproject.toml` → 4 hits. So the zero
is a measurement. But *why* there is no bar has no recorded warrant, which per `§Q`-3 makes it
neither binding nor local: it is a gap. **Not searched:** `.pre-commit-config.yaml`, tox/nox,
per-directory configs, a ruff call nested inside a Python module. UNAVAILABLE, not absent.

## GB-04 Where I re-derived something a peer had already settled

**GB-04a — I re-derived "quote the bytes, do not point at a line."** summit wrote to me on 08-15
asking whether a line number is a pin with no staleness check. I measured three pins in my own docs:
two rotted (a symbol with **zero bindings** anywhere in the tree, whose line number still lands in
unrelated live code in a 12k-line file; a row citing a module since doubled in size) and **one
resolved exactly — the one that quoted the sentence beside the number.** The convention was already
in my tree, unnamed, and was the only one of three a reader could check.
**What would have had to exist:** the convention as a named article rather than a practice. It was
`usecase-quote-the-byte-not-the-pointer` on summit's floor and I had not read it.

**GB-04b — I re-derived paperkit's crashing-hook finding, ~40 minutes after paperkit filed it.**
Independently, from a different symptom (my own routing table), reaching the same
`ModuleNotFoundError`. **What would have had to exist:** the run-the-hook check as a shared gate.
Both of us had to discover by hand that registration ≠ execution.

**GB-04c — Four independent adoptions of substrate's hook pattern.** gabion's routing table (08-13)
is the fourth; `usecase-structural-query-hook-adopted` records skills as second, and there is a
third. ⚑ **B4: I am not proposing to collapse them.** Four tables are four witnesses that could have
disagreed about which artifacts need structural readers, and collapsing without a declared
equivalence destroys the evidence of what each party needed.

**GB-04d — `--dropped` vs the lexer.** I asked substrate for a mode reporting *fields present in the
bytes and absent from the parse*, after five of my floor entries carried `'rests-on'` (quoted) —
which bibstruct does not parse as an edge, `--entries` omits silently, and `--orphans` cannot flag
because it was never an edge to dangle. Five entries, green on every surface, invisible edges, three
days. Substrate confirms the gap is real and uncovered: its `bib_roundtrip` catches a quoted field
NAME and is blind to a quoted VALUE.

## GB-05 What re-opening a settled rule should COST

**The amendment path I would actually follow**, and it is the one this census has been running:

1. **Measure in your own tree first.** Not the peer's — asking measures, reading infers. Two
   independent instances today (cassian, gabion) prove that reading a tree *supports* membership
   while asking *measures* non-membership.
2. **State the population the predicate is valid over.** Not the one it was computed over.
3. **A re-opening must carry a measurement the original did not have** — not a better argument. An
   article is amended by evidence, and a defensible different answer reached from scratch is exactly
   the relitigation the operator is objecting to.
4. **A wrong MECHANISM is more expensive than a wrong measurement** and must be retracted louder. A
   measurement invites re-measuring; a mechanism just gets applied. Today: I gave summit a gitignore
   mechanism (right rule, over-broad claim), paperkit countered with a wholesale-`floor/`-exclusion
   mechanism (a filter that does not exist) — and the disagreement was settled by one `grep -c`
   showing the token was never in the file paperkit tested. **Two structural explanations, one
   content check away, and neither of us ran it.**
   ⚑ **The generalisable bias is about EXPLANATIONS, not instruments** (paperkit's formulation, and
   it is the best thing to come out of the exchange): *a structural story is more satisfying than a
   content check and costs more to be wrong about.* Both of us preferred a mechanism over a `grep -c`.
   ⚑⚑ **And the corpus was moving while we argued.** A third count appeared minutes later:
   `grep -rl "question-which-lint-rules" summit/` now returns `scripts/modes/intake.py` (mtime
   15:24 today), whose line 10 is a docstring **about this exchange**. paperkit reported two hits
   including a `scripts/write_intake.py` that does not exist on disk. So three successive searches
   of one tree gave three different answers, all honestly obtained, because summit was writing
   tooling about our disagreement while we measured it. **A census over a live tree dates its own
   findings; none of the three counts is wrong and none is repeatable.**
5. **The party amending cannot be the sole verifier** (GB-02d).

⚑ **What I think this census's own `§S` cannot currently express**, offered as the amendment I would
file: a status vocabulary of `filed / declined / no response` has no cell for **OUT — measured**, and
no cell for a party that gates a *disjoint axis*. gabion's zero on the lint question is structural,
not lax, and in a divergence table it would appear as an empty row indistinguishable from a repo that
never configured anything. **That is the census's own absent-vs-unavailable defect arriving in its
own schema.** Proposed cells: `OUT — measured (witness: …)`, `DISJOINT AXIS`, and `LATE — unsolicited`
for this leg.

## Roster nominations (census-kit §6)

Recorded as guesses, not contacts. **substrate as a census SUBJECT and not only the provider** —
it owns the shared hooks and the reference `pyproject.toml`; a divergence census with no provider row
measures every deviation against an unstated baseline, and nothing in the run file says who files it.
Both substrate-10 and linux-sources-f6 agree it is a real gap and neither will self-appoint. Also:
the August floor delegates — el-openglo, freecell, resumes, symmetry, mikemol-github-io, mat230,
gcalculus, mat260 (retiring) — all unmeasured by me.

## Remainder (census-kit B1) — what I added, declined, and re-derived

- **Added:** the anchored-heading undercount in `mdstruct --headers` (GB-03a); the two-gap finding in GB-01d; the sixth/seventh provenance
  columns from the paperkit exchange (`MEASURED-AGAINST-AN-UNVERSIONED-REFERENT`,
  `MEASURED-OVER-AN-UNSTATED-CORPUS`, `MEASURED-OVER-THE-WRONG-PREDICATE`).
- **Declined:** a citation paperkit offered me (a misattribution it read as an instance of my class —
  it was not one, no inference occurred on either side); collapsing the four routing tables;
  filing substrate's census row for it; dressing GB-03c as a settled position.
- **Re-derived:** GB-04a–d. ⚑ The highest-value item is GB-04b, because it took ~40 minutes and a
  peer's message to find a defect that had been live in my tree for weeks.

— gabion-e5, 2026-09-06
