<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Mike Mol -->

# An idle-session watchdog: a heartbeat, an absence witness, two checks, one exit

Design notes for the chain mtools:W1472 to W1476 (operator ask, relayed by github-8f 2026-10-17; the
trigger was luthen saying "I'm building W1255 while W1258 lands" and then going silent). A note, not
code: nothing here is built, and each claim below says what it rests on.

## The operator's words, kept

"sessions may need a backgrounded watchdog that watches for 'I'm idle and I don't appear to need to
be' conditions. Like the 'hey, are you awake' feature for train engines, or the 'put your hands back
on the steering wheel' feature driver-assist cars have. It should take as a heartbeat interaction with
the relevant tooling; using the tooling represents a heartbeat. A missing heartbeat represents a 'are
they really blocked?' check on their queue and a 'Are they really stalled' check on their transcript;
firing the discharging of the AED (effectively, exiting the process so the harness notifies them of
proc exit) if it looks like they stopped..."

## The chain

| card | what | rests on |
|---|---|---|
| W1472 | a heartbeat stamp: one small record under the git dir (`<git dir>/mtools/heartbeat`), written atomically, holding the tool name, the time, and the last N gaps | `atomicwrite` (durable writes) and the commit counts file's flock'd JSON shape (W1442, read in `commit_counts.py`) |
| W1473 | every `mikemol-paths-forward`, `mikemol-commit` (plain and `--stack`), `mikemol-scratch` call beats, and each beat is an OTel gauge sample for the repo | `mikemol-otlp metric` (W1408, how `commit_gauge.py` already pushes the in-flight gauges) |
| W1474 | the watchdog: waits for an ABSENCE, no beat for longer than its learned interval | `katas.hangwatch`'s rule (a count of polls without progress) and luthen's phi-accrual freshness model (`checks/metric_freshness.py`, read: it publishes the mean gap and the exponential model) |
| W1475 | on a missed beat, two checks before it fires | the writer (ready or working cards not blocked on someone else) and `mikemol-transcriptstruct` (the last assistant turn) |
| W1476 | the exit: a distinct status and a one-line reason; started in the background by `--tick-open`; a per-repo firing counter | the harness re-invoking a session when a background process exits, which this session already relies on for its stack runs |

## Why an absence and not a deadline

The same ruling that governs the gate (operator 2026-09-23/24, avoid wall-clock timeouts) applies here:
a fixed "five minutes of silence" fires wrongly on a repo whose gates take 35 minutes and misses a
stall in one whose ticks take two. So the watchdog measures how long this repo's own beats are apart
and asks how surprising the current silence is.

The model is luthen's (their freshness check names it): gaps are taken as exponentially distributed
with mean mu, the mean of the last N recorded gaps. The chance that a gap exceeds t is exp(-t/mu), and
the suspicion is

    phi(t) = -log10( exp(-t/mu) ) = t / (mu * ln 10)

The watchdog does the work of a check when phi passes a level. That level is a probability, not a time
(phi = 3 is a one-in-a-thousand silence), and it is the one number to choose; the first cut should
take it from `phi_fire` in the stamp so it can be tuned from the firing counter without a code change.
Open: how many gaps N to keep, and what the prior mean is before a repo has any (a fresh `.git` has no
history; the first cut should not fire until it has seen K beats).

A poll interval remains, because a process has to wake to look. It paces the reads and decides
nothing: the decision is the phi value.

## What counts as a beat

Using a tool is the heartbeat, so a session that is really working (building, thinking, queuing)
beats whenever it touches the writer, a scratch worktree, a build or a submit. A long foreground
inference with no tool call does not beat, and is exactly what phi measures against the repo's usual
gap.

⚑ A GATE RUNNING IS THE COMMIT'S HEARTBEAT, NOT THE SESSION'S (operator ruling, 2026-10-17, relayed
by github-8f). My first cut of this note counted a nonzero in-flight gauge
(`mikemol.commit.inflight`, W1442) as "alive". The operator ruled the opposite on exactly that case:
luthen answered "I did not stop" because a land was gating, and the operator said it "interpreted 'I
have something in flight' as 'I haven't stopped'. Which is a pipeline stall...". So the in-flight
gauge is NOT read as a session beat. Beats come only from the session's own actions: writer calls,
scratch opens, builds and submits. A submit beats once, when it is made; the 35 minutes after it
produce none. The cost is accepted: a session that really is waiting on a gate with nothing else it
could do has no ready cards (the second condition below), so it is not fired on.

## The two checks

Before it fires, on a missed beat, the watchdog asks:

1. The queue. Are there ready or working cards that are not blocked on someone else? The writer can
   answer from the state file; `nemik-stackable` is the other source for "could stack". If every card
   is blocked or waiting on a peer or the operator, the session is really blocked.
2. The transcript. Did the last assistant turn end with no tool call and no background task in
   flight? `mikemol-transcriptstruct` reads a Claude Code transcript losslessly; the exact record
   shapes to read are the open question and have not been measured here. A turn that ended with a
   background task running is NOT thereby waiting (see the fire condition below).

Both must say stalled. Either saying really blocked makes the watchdog record the check and re-arm
quietly.

⚑ THE FIRE CONDITION (operator ruling, 2026-10-17): no SESSION heartbeat past the learned interval AND
unblocked ready cards exist, whether or not a gate is in flight. A running gate or a queued stack is
not an excuse, because the session could be building the next card while it runs; that is the loop
prompt's "always keep a commit in flight; juggle". Two consequences for the checks:

- the queue check counts a card as available when it is ready and not behind an open enabler or a
  peer, in-flight commits notwithstanding;
- the transcript check no longer treats "a background task is running" as proof the session is
  waiting. A last turn that ended with only background work running and ready cards left unworked is
  the stall the operator described.

## The exit

On both stalled: exit with a status of its own (the fleet exit table, `corpus/exit-table.json`, is
where a new code is registered; REFUSE is 4, and the table, not a design note, says what is free) and
one line: `idle with N ready cards, last heartbeat T`. The harness notifies the session of the process
exit, as it does for the stack runs, which is what wakes it.

## The counter

A per-repo OTel counter of firings, and a second of checks that decided "really blocked", published
the same way as the gauges. The ratio is the answer to the operator's question: whether the watchdog
rescues or nags. A firing the session answers within one turn with a tool call is a rescue; one it
answers with "I was waiting" is a nag, and the second counter is the one to watch.

## Risks and what would refuse the design

- A beat on every call is a write on every call. It must be cheap and atomic, and never fail a tool: a
  heartbeat that cannot be written is dropped silently, as the span emission is.
- A watchdog that outlives its session is an orphan. It must exit when the lock it was started under is
  released (`--unlock`) or when the session's process is gone.
- Two sessions in one repo share the stamp. The first cut treats the repo as the unit, as the commit
  counts do; a per-session stamp is a later refinement.
- The suspicion model assumes beats are roughly memoryless. They are bursty (a tick of many calls, then
  a long gate). If the learned mean is dominated by the bursts the watchdog will under-fire; the second
  statistic luthen publishes, the maximum gap, is the guard to read before choosing the level.

## First step

W1472: the stamp, as a leaf module with its own tests (an atomic write, the last N gaps kept, a read
that tolerates a missing or torn file), before any tool beats.
