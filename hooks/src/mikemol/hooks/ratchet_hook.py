# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Put the ratchet-emit call into a repository's own gate script, once (W1928, github:W42).

    mikemol-ratchet-hook SCRIPT --after TEXT --tool EXPR --ratchet EXPR --name EXPR --dir EXPR
                         [--write]

The template is written from the two real cases: mtools' pre-commit (after the gate-target emit)
and nemik's `tools/gate_staged.sh` (after the ratchet check, nemik:W1027, 38b2042). Both are the
same block: the tool is run best-effort with the repository's real NAME and the gated DIR, naming
the census tool through `RATCHET_BIN`, and nothing it does can change the verdict.

⚑ THE FOUR INPUTS ARE SHELL EXPRESSIONS THE CALLER SUPPLIES, not paths this guesses. NAME is the
real checkout's basename and never the snapshot's (a gate runs in a directory named `tree`, and
every series was once labelled `tree`), DIR is the gated tree, TOOL and RATCHET name the two
executables as the gate script reaches its own tools. This knows no path under another checkout.

⚑ IDEMPOTENT AND ANCHORED. The block goes after the first line that contains `--after`; a script
that already calls `mikemol-ratchet-emit` is left as it is, and an anchor that is in no line is
refused (exit 4) rather than the block being appended where it might follow an `exit`. Without
`--write` the block is printed and nothing is saved.

CONSUMED BY: the `mikemol-ratchet-hook` console script.
"""

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

MARK = "mikemol-ratchet-emit"
EXIT_REFUSED = 4
EXIT_USAGE = 2
_FLAGS = ("--after", "--tool", "--ratchet", "--name", "--dir")
_USAGE = (
    "usage: mikemol-ratchet-hook SCRIPT --after TEXT --tool EXPR --ratchet EXPR "
    "--name EXPR --dir EXPR [--write]\n"
)


@dataclass(frozen=True)
class Spec:
    """What the block names: where it goes and the four shell expressions it runs."""

    after: str
    tool: str
    ratchet: str
    name: str
    tree: str


def block(spec: Spec) -> list[str]:
    """Spell the block, the lines inserted into the script.

    Returns:
        the lines, without trailing newlines.

    """
    return [
        "# W1928 (github:W42): this repository's ratchet census goes to the metrics store.",
        f'_ratchet_emit_tool="{spec.tool}"',
        'if [ -x "$_ratchet_emit_tool" ]; then',
        f'    RATCHET_BIN="{spec.ratchet}" "$_ratchet_emit_tool" "{spec.name}" "{spec.tree}" \\',
        '        || echo "mikemol-ratchet-emit failed; no ratchet values sent" >&2',
        "else",
        '    echo "mikemol-ratchet-emit not found; no ratchet values sent" >&2',
        "fi",
    ]


def insert(text: str, spec: Spec) -> str | None:
    """Insert the block after the anchor line, once.

    Returns:
        the new script text; the text unchanged when it already calls the tool; None when the
        anchor is in no line.

    """
    if MARK in text:
        return text
    lines = text.splitlines()
    at = next((i for i, line in enumerate(lines) if spec.after in line), None)
    if at is None:
        return None
    merged = [*lines[: at + 1], *block(spec), *lines[at + 1 :]]
    return "\n".join(merged) + ("\n" if text.endswith("\n") else "")


def _spec_of(args: list[str]) -> tuple[Path, Spec, bool] | None:
    # SCRIPT, the five flags and an optional --write; None for a malformed command line.
    write = "--write" in args
    rest = [a for a in args if a != "--write"]
    values: dict[str, str] = {}
    script: str | None = None
    while rest:
        word = rest.pop(0)
        if word in _FLAGS and rest:
            values[word] = rest.pop(0)
        elif script is None and not word.startswith("--"):
            script = word
        else:
            return None
    if script is None or set(values) != set(_FLAGS):
        return None
    given = (values[f] for f in _FLAGS)
    return Path(script), Spec(*given), write


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Insert the ratchet-emit block into a gate script, or say why not.

    Returns:
        0 when the script now calls the tool (inserted or already did), EXIT_REFUSED when the anchor
        is in no line or the script cannot be read, EXIT_USAGE for a malformed command line.

    """
    sink = out or sys.stdout
    parsed = _spec_of(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    script, spec, write = parsed
    try:
        text = script.read_text(encoding="utf-8")
    except OSError as refusal:
        sys.stderr.write(f"mikemol-ratchet-hook: {refusal}\n")
        return EXIT_REFUSED
    result = insert(text, spec)
    if result is None:
        sys.stderr.write(f"mikemol-ratchet-hook: no line of {script} contains {spec.after!r}\n")
        return EXIT_REFUSED
    if result == text:
        sink.write(f"{script}: already calls {MARK}; unchanged\n")
    elif write:
        script.write_text(result, encoding="utf-8")
        sink.write(f"{script}: {MARK} block inserted after the line containing {spec.after!r}\n")
    else:
        sink.write("\n".join(block(spec)) + "\n")
        sink.write(f"dry run: add --write to insert this after {spec.after!r} in {script}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
