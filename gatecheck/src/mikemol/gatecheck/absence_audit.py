# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Refuse an unverified "nothing gates this" claim.

Ported from paperkit's `tools/absence_audit.py` (paperkit:W142). Behaviour is paperkit's, with
these changes: the log path is read from the environment when a report is written (paperkit read
it at import), `main` takes an `argv` without the program name and a `stdin` seam, and a
transcript row, message or content item of the wrong JSON shape reads as empty rather than
raising.

⚑ ADOPTED, NOT INVENTED. This is an instance of mat260's `watchword-audit` capability: a Stop
hook fails the turn when an agent asserts a limitation or an absence it never checked, as three
independent regexes (watchword x context x search-evidence). The transcript-walking machinery is
mat260's, HELD HERE as code rather than symlinked. **Ownership is not claimed.**

⚑ WHY PAPERKIT NEEDS IT. paperkit's central type is a TRISTATE (PASS / UNAVAILABLE / FAIL), and
the engine will not let a check say "I could not run it" and have that scored as "it is false".
The agent working on the engine did precisely that fold four times in one session (2026-08-28):
each is "my query did not find it" scored as "it is not there".

⚑ AND THE SEARCH THAT CLEARS A CLAIM HERE IS A MUTATION, NOT A GREP. The question a paperkit
absence claim asks is almost always *"can this check fail?"*, and a grep cannot answer it:
mutate the mechanism out, don't source-scan. A witness that survives its own delta is VACUOUS
however many greps agree with it.

Weakness, stated: this greps the assistant's TEXT for an absence claim and the turn's TOOL CALLS
for clearing evidence. It cannot tell a SOUND mutation from a mis-aimed one. It refuses the
unexamined claim, not the under-examined one.

Usage:
  mikemol-absence-audit --transcript PATH   # audit the last turn
  echo '<hookjson>' | mikemol-absence-audit # Stop-hook mode (advisory)
  mikemol-absence-audit --selftest          # prove it can SEE what it looks for
Exit: 0 clean, 2 if an unverified absence claim is found.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import TextIO

# ⚑ THE WATCHWORDS ARE ABSENCE PHRASINGS, and the dangerous ones are the CONFIDENT ones. These
# are the verdicts a queue/warrant audit reaches for, each of which asserts about the ENGINE what
# a query can only assert about ITSELF. "UNAVAILABLE" and "cannot-run" are deliberately NOT here:
# they are the correct forms and must never be flagged.
WATCHWORDS = re.compile(
    r"\b(nothing (?:gates|asserts|checks|witnesses|covers|reads|calls|invokes)|"
    r"no (?:warrant|claim|check|witness|gate|owner|bib entry|caller|consumer) (?:covers|asserts|"
    r"names|exists|reads|invokes)|"
    r"(?:is|are|grades?) vacuous|cannot (?:fail|red|flip)|can'?t (?:fail|red|flip)|"
    r"unwarranted|ungated|unwitnessed|un(?:der)?tested|"
    r"does(?:n'?t| not) exist|there is no \w+|there'?s no \w+|no such (?:verb|key|field|claim|"
    r"warrant|target|rule)|never (?:runs|ran|fires|fired|invoked)|"
    r"already gated|already covered|duplicate of|"
    r"the engine (?:does(?:n'?t| not)|has no|lacks)|not implemented|"
    r"tautolog\w*|dangling|silently (?:drops|passes|skips))",
    re.IGNORECASE,
)

# A watchword only matters when the claim is ABOUT the engine or its claim-DAG.
CONTEXT = re.compile(
    r"warrant|claim|witness|bib\b|check\b|gate\b|verdict|grade|vacuous|behavioral|"
    r"concept:|result:|cmd:|file:|agree:|sweep|mutation|delta|\bdcalc\b|adequacy|"
    r"resolver|projector|paperkit|\.bib\b|boundaries_|//:hook|bazel|dep_order|rests-on",
    re.IGNORECASE,
)

# ⚑ CLEARING EVIDENCE IS A MUTATION OR THE OWNING TOOL, never a textual sweep. A grep cannot
# answer "can this check fail?", which is what a paperkit absence claim almost always asks.
SEARCH = re.compile(
    r"bazel\s+(?:test|build|query|cquery)|"  # the owning build system
    r"paperkit/gate\.py|paperkit/discriminate\.py|paperkit/project\.py|"
    r"tools/(?:read_grade|sens|def_sites|closure|imports|effective|decisions)\.py|"
    r"checks/\w+\.py|boundaries_\w+\.py|concepts\.py\s+\S|"  # running a witness
    r"--check\b|--observe\b|--json\b|--only\b|--prove\b|--selftest\b|"
    r"(?:cp|rsync)\s+-r?[a-z]*\s+\S*paperkit|mkdtemp|scratchpad/fx|"  # a mutation fixture
    r"sed\s+-i|\.replace\(|git\s+checkout\s+\S+\.py",  # the delta itself
    re.IGNORECASE,
)

# ⚑ A LINE THAT ALREADY SAYS UNAVAILABLE IS THE CORRECT FORM, NOT A VIOLATION. Without this the
# audit would flag its own remedy, the predicate-matches-its-own-documentation defect.
_UNAVAILABLE = re.compile(r"\bUNAVAILABLE\b")

LOG_ENV = "ABSENCE_AUDIT_LOG"
_CLIP = 140  # characters of a flagged line kept in the report
_SHOWN = 8  # flags quoted in one report
_EXIT_FOUND = 2


def log_path() -> Path:
    """Name the log a report is appended to: `$ABSENCE_AUDIT_LOG`, else `~/.claude/...`.

    Returns:
        the log file path.

    """
    return Path(os.environ.get(LOG_ENV, Path.home() / ".claude" / "absence-audit.log"))


def _mapping(value: object) -> Mapping[str, object]:
    """Read a JSON object as a mapping; anything else reads as empty.

    Returns:
        the object itself, or an empty mapping.

    """
    if isinstance(value, dict):
        return cast("Mapping[str, object]", value)
    return {}


def _items(value: object) -> list[object]:
    """Read a JSON array as a list; anything else reads as empty.

    Returns:
        the array itself, or an empty list.

    """
    if isinstance(value, list):
        return cast("list[object]", value)
    return []


def rows(path: str) -> list[Mapping[str, object]]:
    """Parse a JSONL transcript, one mapping per non-blank line.

    Returns:
        the rows in file order.

    """
    text = Path(path).read_text(encoding="utf-8")
    return [_mapping(cast("object", json.loads(ln))) for ln in text.splitlines() if ln.strip()]


def is_user(r: Mapping[str, object]) -> bool:
    """Say whether a transcript row is a user turn.

    Returns:
        True for `type == "user"` or a message whose role is `user`.

    """
    return r.get("type") == "user" or _mapping(r.get("message")).get("role") == "user"


def last_turn(rs: Sequence[Mapping[str, object]]) -> Sequence[Mapping[str, object]]:
    """Slice the rows from the last user row on.

    Returns:
        the final turn; every row when none is a user row.

    """
    start = 0
    for i, r in enumerate(rs):
        if is_user(r):
            start = i
    return rs[start:]


def scan_turn(turn: Sequence[Mapping[str, object]]) -> tuple[str, bool]:
    """Collect the assistant text asserted this turn, and whether an owning tool was invoked.

    Reads the assistant's TEXT (what it asserts to a peer) and the turn's TOOL CALLS. Thinking is
    not scanned: a hypothesis considered is not a claim made.

    Returns:
        `(newline-joined text, searched)`.

    """
    texts: list[str] = []
    searched = False
    for r in turn:
        for c in _items(_mapping(r.get("message", r)).get("content")):
            item = _mapping(c)
            if item.get("type") == "text":
                text = item.get("text", "")
                texts.append(text if isinstance(text, str) else "")
            elif item.get("type") == "tool_use":
                blob = str(item.get("name", "")) + " " + json.dumps(_mapping(item.get("input")))
                if SEARCH.search(blob):
                    searched = True
    return "\n".join(texts), searched


def flags_in(text: str) -> list[tuple[str, str]]:
    """Find absence watchwords on lines about the engine that do not already say UNAVAILABLE.

    Returns:
        `(watchword, clipped line)` for every hit, in order.

    """
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not CONTEXT.search(line):
            continue
        if _UNAVAILABLE.search(line):
            continue
        out.extend((m.group(0), line.strip()[:_CLIP]) for m in WATCHWORDS.finditer(line))
    return out


def report(flags: Sequence[tuple[str, str]]) -> int:
    """Append the flags to the log and print them on stderr.

    Returns:
        2, the exit code for an unverified absence claim.

    """
    msg = (
        "absence-audit — an absence was asserted this turn with NO invocation of the tool "
        "that owns the question. This corpus can say UNAVAILABLE (not in this version / not "
        "fetched); it cannot say DOES NOT EXIST. Verify or requalify:\n"
        + "\n".join(f"  • {w!r}: {ln}" for w, ln in flags[:_SHOWN])
    )
    log = log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n---\n")
    sys.stderr.write(msg + "\n")
    return _EXIT_FOUND


def selftest() -> int:
    """PROVE THE AUDIT SEPARATES ITS CASES: both arms, or it certifies nothing.

    An audit that flagged everything would look identical to a strict one, and an audit that
    flagged nothing would look identical to a clean tree. The T-arms are real claims made on
    2026-08-28, not invented fixtures.

    Returns:
        0 when every arm holds, 1 otherwise.

    """
    arms = [
        (
            "T: an unqualified 'nothing gates this' about a warrant is flagged",
            bool(flags_in("No warrant covers the WITNESSES dispatch table's domain.")),
        ),
        (
            "T: a vacuity verdict asserted without a mutation is flagged",
            bool(flags_in("That witness is vacuous — the check cannot fail under any delta.")),
        ),
        (
            "T: 'already gated' (the duplicate verdict) is flagged",
            bool(flags_in("This claim is already gated by bnd-verdict; the row is a duplicate.")),
        ),
        (
            "F: the same claim qualified as cannot-run is NOT flagged",
            not flags_in("The concept resolves to cannot-run here — UNAVAILABLE, not refuted."),
        ),
        (
            "F: an absence claim with no engine context is NOT flagged",
            not flags_in("There is no meeting scheduled for Thursday."),
        ),
        (
            "F: running a witness counts as clearing evidence",
            bool(SEARCH.search("python3 checks/claims.py depth-annotates-without-reordering")),
        ),
        (
            "F: a mutation fixture counts as clearing evidence",
            bool(SEARCH.search("sed -i '203s/rests-on/from/' paperkit/genre.py")),
        ),
        (
            "F: a bare recursive grep does NOT count — it is the refused move",
            not SEARCH.search("grep -rn 'rests-on' paperkit/"),
        ),
    ]
    for name, ok in arms:
        sys.stdout.write(f"  {'ok  ' if ok else 'FAIL'} {name}\n")
    bad = [n for n, ok in arms if not ok]
    sys.stdout.write(
        f"absence-audit --selftest: {'PASS' if not bad else 'FAIL'} "
        f"({len(arms) - len(bad)} of {len(arms)} arms)\n"
    )
    return 1 if bad else 0


def _audit_files(files: Sequence[str]) -> int:
    """Scan plain files for flagged lines; an unreadable file is skipped.

    Returns:
        2 when any file holds a flagged line, else 0.

    """
    bad: list[tuple[str, str]] = []
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8")
        except OSError:
            continue
        bad += [(w, f"{f}: {ln}") for w, ln in flags_in(text)]
    return report(bad) if bad else 0


def main(argv: Sequence[str] | None = None, *, stdin: TextIO | None = None) -> int:
    """Run the audit in selftest, files, transcript or Stop-hook mode.

    `argv` excludes the program name. `stdin` is the Stop-hook JSON source (default: stdin).

    Returns:
        0 when clean (and always 0 in advisory hook mode), 2 on an unverified absence claim.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return selftest()
    if "--files" in args:
        return _audit_files(args[args.index("--files") + 1 :])

    advisory = False
    if "--transcript" in args:
        tpath: object = args[args.index("--transcript") + 1]
    else:
        # ⚑ HOOK MODE IS ADVISORY: it LOGS and returns 0. A regex over prose has false positives,
        # and a Stop hook that fails a turn on one would make the guard's cost exceed its value.
        advisory = True
        try:
            tpath = _mapping(cast("object", json.load(sys.stdin if stdin is None else stdin))).get(
                "transcript_path"
            )
        except ValueError:
            return 0
    if not isinstance(tpath, str) or not tpath or not Path(tpath).exists():
        return 0

    text, searched = scan_turn(last_turn(rows(tpath)))
    flags = flags_in(text)
    if flags and not searched:
        report(flags)
        return 0 if advisory else _EXIT_FOUND
    return 0


if __name__ == "__main__":
    sys.exit(main())
