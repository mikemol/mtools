#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑⚑ A STANDING WITNESS ON A CHECKER'S DOMAIN. An action's verdict ranges over its DECLARED
# inputs, so a checker whose declaration is short of its real domain returns a stale green for
# every input it cannot see. mypy is the case that matters here, because it is the one checker
# whose verdict on a file depends on files it does not name: editing an imported module changes
# the importer's type-correctness while leaving its bytes untouched.
#
# ⚑⚑ THE CLAIM WAS TRUE AND UNARMED, WHICH IS THE STATE THIS REPOSITORY REFUSES ELSEWHERE. The
# BUILD file declares `glob(["src/**/*.py", ...])` — structurally right, and never once tested
# against a transitive edit. A glob that silently stopped matching, a `srcs` narrowed during a
# refactor, or a distribution added without the pattern would each produce a green mypy over a
# domain smaller than the type checker's own.
#
# ⚑ AND A ONE-ARMED VERSION OF THIS WITNESS IS WORSE THAN NONE. Asserting only that the action
# RE-RUNS proves the file is an input; asserting only that mypy FAILS proves mypy works. Neither
# alone proves the DOMAIN is complete — the pair does: a transitive edit must reach the action,
# and a transitive DEFECT must reach the verdict.
set -uo pipefail

dist="${1:?the distribution directory was not passed}"
target="${2:?the target was not passed}"
victim="${3:?the transitive module was not passed}"

# ⚑⚑⚑ THE ARM-2 PAYLOAD IS THE CHECKER'S OWN DEFECT CLASS, AND HARDCODING IT SILENTLY SCOPED THIS
# WITNESS TO ONE CHECKER. The first cut planted a Python TYPE error — which mypy catches and ruff
# and the ratchet do not. Pointed at `//ratchet:ruff`, that witness would have reported arm 2
# FAILED and read as "ruff's domain is short" when the truth was "I planted a defect ruff does not
# look for". ⚑ A PROBE THE CHECKER IGNORES IS INDISTINGUISHABLE FROM A DOMAIN THAT EXCLUDES IT.
#
# ⚑⚑ So the payload is a parameter and its DEFAULT is stated rather than assumed:
#   mypy     a return type that does not match its annotation
#   ruff     an unused import (F401)
#   ratchet  a preview-rule violation, which grows the census by a key
probe_kind="${4:-mypy}"

cd "$(dirname "$0")" || exit 1
restore() { git checkout "$victim" 2>/dev/null; }
trap restore EXIT

fail=0
say() { printf '  %s\n' "$*"; }

# ⚑ THE CONTROL RUNS FIRST AND MUST PASS. An arm measured against an already-red tree reports the
# pre-existing failure as its own finding — and every subsequent arm agrees for the wrong reason.
if ! bazel test "$target" >/dev/null 2>&1; then
    say "CONTROL FAILED: $target is red BEFORE the probe — the arms below would be meaningless"
    exit 1
fi

# ⚑⚑ ARM 1 — REACHABILITY. A CONTENT change (not `touch`: bazel keys on bytes, so an mtime bump
# invalidates nothing and an arm built on one measures the clock, not the graph).
# ⚑⚑⚑ THE PROBE CARRIES A NONCE, AND WITHOUT ONE THIS ARM IS UNFALSIFIABLE-GREEN'S TWIN: A
# PERMANENT FALSE RED. A fixed probe string is a digest the cache has already seen, so the second
# run of this witness is served from the remote cache — `Executed 0 out of 1` — and the arm
# concludes the file is outside the domain. Measured: identical `# probe` appends returned
# `Executed 0` while a nonce-carrying append returned `1 linux-sandbox`, same file, seconds apart.
#
# ⚑⚑ AND THE TWO EXPLANATIONS ARE INDISTINGUISHABLE IN THE OUTPUT THIS ARM READS. "Not an input"
# and "already answered" both print `Executed 0`. A witness that cannot separate them is not
# measuring the domain — it is measuring whether it has run before, which is the one question it
# was not asked.
printf '\n# transient domain probe %s\n' "$(date +%s%N)" >> "$victim"
# ⚑⚑⚑ THE OUTPUT IS CAPTURED, THEN MATCHED — NEVER `bazel | grep -q`. Under `pipefail`, a `grep -q`
# that MATCHES closes the pipe, bazel takes SIGPIPE, and the pipeline reports bazel's death as the
# verdict: the arm fails precisely BECAUSE it found what it was looking for. Measured here — both
# arms of this witness reported FAILED against a tree that had passed the same probes by hand
# minutes earlier. That is this repository's Rule 14 defect (the reporter's status standing in for
# the subject's) reappearing inside the witness written to enforce the rule it belongs to.
out="$(bazel test "$target" 2>&1)"
if printf '%s' "$out" | grep -q "Executed 1 out of 1 test"; then
    say "arm 1 REACHABILITY: a transitive content change re-executes the action"
else
    say "arm 1 FAILED: editing $victim did NOT invalidate $target — it is outside the domain"
    fail=1
fi
restore

# ⚑⚑ ARM 2 — VERDICT. Reachability alone only proves the bytes are keyed; this proves the checker
# actually ranges over them.
case "$probe_kind" in
    mypy)    printf '\n\ndef _transient_domain_probe() -> int:\n    return "not an int"\n' >> "$victim" ;;
    ruff)    printf '\nimport os  # transient domain probe\n' >> "$victim" ;;
    ratchet) printf '\n\ndef _transient_domain_probe():\n    """Probe."""\n    return 1\n' >> "$victim" ;;
    *)       say "arm 2 FAILED: unknown probe kind $probe_kind"; exit 1 ;;
esac
out="$(bazel test "$target" 2>&1)"
if printf '%s' "$out" | grep -q "FAILED"; then
    say "arm 2 VERDICT: a $probe_kind defect in $victim fails $target"
else
    # ⚑ THE TWO EXPLANATIONS ARE NAMED, because this arm cannot tell them apart and a message that
    # asserted only the first would send a reader to repair a declaration that is already correct.
    say "arm 2 FAILED: $target did not refuse a planted $probe_kind defect in $victim"
    say "  either the domain is SHORT, or the $probe_kind probe is not a defect THIS checker seeks"
    fail=1
fi
restore

# ⚑ ARM 3 — RESTORATION. A witness that leaves the tree dirty makes the NEXT gate's verdict a
# fact about this script.
if bazel test "$target" >/dev/null 2>&1; then
    say "arm 3 RESTORED: $dist is green again"
else
    say "arm 3 FAILED: $victim was not restored — the tree is dirty"
    fail=1
fi

[ "$fail" -eq 0 ] || { echo "domain_witness: REFUSED" >&2; exit 1; }
printf 'domain_witness: %s — domain is reachable, ranged-over, and restored\n' "$target"
