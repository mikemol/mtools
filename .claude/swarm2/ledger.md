# swarm2 drafter "ledger": W181, W124

Read-only draft. Nothing in the queue, ledger or git was written. The `--show` and `--overlaps` commands
used `/home/mikemol/github/mtools/pathsforward/.venv/bin/mikemol-paths-forward` (shortened to `mpf` below).

## W124: re-run --overlaps over all seven queues

### What I measured
The `ls` of the seven `/home/mikemol/github/<repo>/.claude/paths-forward.json` paths found every file. No file is missing.
I ran `mpf --state <file> --overlaps` once for each repo. Each run exited 0.

| repo | OVERLAP lines | largest line |
|---|---|---|
| gabion | 1 | test-suite-red: W24,W25,W10 |
| luthen-observability | 20 | terraform: 9 holders (W79,W144,W231,W233,W246,W259,W260,W261,W263) |
| mtools | 6 | swarm-census: W173,W180,W466,W484 |
| paperkit | 7 | paperkit/resolver.py: W78,W32,W25,W132 |
| rosettapkg | 0 | (no output) |
| substrate | 5 | cleanroom: 15 holders (W63..W78) |
| el-openglo | 9 | emitters.py: W161,W162,W193 |
| **total** | **48** | |

None of the 48 lines carries `[lease]`, and no `OVERLAP?` line appeared. This means no queue yet uses `file:`/`mod:` with `!w`. Paperkit's
bare paths (for example `paperkit/resolver.py`) are parsed as topics, not as `file:` tags. As a result, the 1197fb3 grain logic
does not merge any of their spellings.

### Finding
- All seven queues are present. The W102 roster gap is closed.
- The per-repo total of 48 is not the same quantity as nemik-overlaps' 55 lines (10 cross-repo, from W124's evidence). nemik's 55
  includes the cross-repo lines, which a per-repo `--overlaps` run cannot show. 55 - 10 = 45 is not 48, so the two
  instruments differ by 3 lines on the within-repo part. The queues have changed since 2026-09-27, so this gap is
  not a defect claim. It is the next measurement: run both instruments in the same minute.
- Adoption of the grain grammar is zero across the whole fleet.

### Landing unit (one commit; it appends to the W50 design file, which is a notes file)
Append to the W50 design file a section `## W118 re-measure (W124), 2026-10-02` containing the table above, plus the line:
"0 [lease], 0 OVERLAP? fleet-wide: grain grammar unadopted; paperkit's path-shaped topics are the first candidates for file:".
Then:
```
mpf --state /home/mikemol/github/mtools/.claude/paths-forward.json --update W124 --status "done" --evidence-append "2026-10-02: 7/7 queues present; per-repo OVERLAP: gabion 1, luthen-observability 20, mtools 6, paperkit 7, rosettapkg 0, substrate 5, el-openglo 9 (=48); 0 [lease]"
```
Optional follow-up waypoint (mint only if wanted): "run nemik-overlaps and the per-repo --overlaps in the same minute and reconcile 48 vs 55-10".

## W181: commit message compared with the ledger, the evidence and nemik

### What I measured
- `git show -s` for 2ec718c, 1197fb3 and 82255d0.
- `mpf --scan-literal <sha>` for each sha. Each sha has exactly one waypoint-evidence hit (W179, W176, W174 in that order), one
  ledger line (473, 470, 468) and one mirror hit. W181's own next-step also matches each sha.
- `mpf --show` for W174, W176 and W179, plus ledger lines 466-473.
- nemik activity was not queried separately. For these three waypoints, the queue fields are what nemik reads.

### Field-by-field comparison (what the message says that NO record holds)
| commit (W) | in message, absent from ledger + evidence + title |
|---|---|
| 82255d0 (W174) | the `unknown` grain for any other prefix; the normalisation rules (`./` and the trailing `/` dropped, **no filesystem call**); the definition of `leasable` (file:/mod: AND !w; only implied by W176's title); **consumer status**: "Nothing reads the parse yet; --check rules and the lease follow" |
| 1197fb3 (W176) | **compatibility claim**: an unprefixed topic keeps exactly the line it printed before (evidence says only "topics unchanged"); **rejected alternative**: mod:X and a file: path whose stem is X are never unified; **effect boundary**: "Still advisory: no exit code changes" |
| 2ec718c (W179) | **placement rationale**: it joins the pre-flight that already builds //ratchet:ratchet_cli "for the same reason"; **construction constraint**: one bash array, no shellcheck waiver |

The other direction matters just as much. None of the three messages names its waypoint. The ledger points to the sha, but the
commit does not point back to W<n>, so the link only runs one way. The records hold things the messages leave out:
test counts (353/357), gate-refusal history, and the BES outage.

### Finding
A message needs four field kinds that the records do not capture:
1. **unchanged**: what compatibility is kept (zero migration, same line for topics, exit code unchanged)
2. **not-done / rejected**: an alternative that was turned down, with its reason (mod~file not unified)
3. **consumers**: who reads the change now, and what follows (W-refs)
4. **constraint**: how it was built and why it lives where it does (array, no waiver, co-located pre-flight)

Everything else in the three messages (subject, mechanism, motivating failure) can be rebuilt from title + evidence +
caused_by. So the ledger under-records along exactly these four axes. That is W181's claim, now measured.

### Landing units (one commit each, in order)
- **L1, back-link trailer** (pre-commit or a commit-msg hook): require a `Waypoint: W<n>` trailer, or `Waypoint: none`.
  Test: a message without the trailer is refused, and `Waypoint: W174` is accepted.
- **L2, typed evidence fields**: `--update` gains `--unchanged TEXT`, `--rejected TEXT` and `--consumers TEXT`, each appended to
  the waypoint as a list field (shown by `--show`). Keep evidence free text. Test: the round-trip through `--show`.
- **L3, `--commit-message SYMBOL`**: emits a draft with the subject taken from title, the body from caused_by's failure + the latest evidence +
  the L2 fields, and the `Waypoint:` trailer. Test: a fixture waypoint carrying the 82255d0 facts reproduces that message's four
  field kinds. A missing L2 field prints `# thin: no <field>`, which is the "thin message is a finding" half of W181.
- Close W181 after the survey with:
```
mpf --state /home/mikemol/github/mtools/.claude/paths-forward.json --update W181 --next "L1 Waypoint trailer; then L2 typed fields; then L3 --commit-message" --evidence-append "2026-10-02 survey: 3/3 messages carry unchanged/rejected/consumers/constraint facts absent from ledger+evidence; 0/3 name their W<n>"
```
  Mint L1-L3 as separate waypoints, following atomize-waypoints.

## Blockers
None. One denial: a `bash /dev/stdin` loop over the seven repos was refused by the classifier. Running each repo's command on its own
gave the same data, so nothing is missing.
