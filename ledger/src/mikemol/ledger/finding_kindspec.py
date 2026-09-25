# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Parse a `--register` KIND argument into a builder plus its arguments, or a refusal.

Moved from substrate (N-a row 6). This is the PURE half of registering a finding: it touches no
filesystem and no roster, and it is where every refusal a filer actually reads lives.

⚑⚑⚑ THE REFUSAL MENU IS THE MOST LOAD-BEARING TEXT IN THE LEDGER, AND IT ONCE OMITTED THE TWO
FALSIFIABLE KINDS. At that moment substrate's census read 150 of 163 witnesses `standing`: an
agent that guessed a kind wrong was handed a menu without `selftest:` or `refuses:` and picked the
one that always passes. **A tool's self-description at the point of refusal outranks its
docstring, because the refusal is what arrives at the moment of need.**

⚑⚑ SO THE ORDER IS PART OF THE CONTRACT: the falsifiable kinds come FIRST, and `standing` is
listed WITH the condition under which it is legitimate.

⚑ THE ONE-SHELL-WORD HAZARD SHIPPED ONCE: `KIND` is one argv element, so an unquoted
`selftest:tool selftest` donates the subcommand to the NOTE and the witness runs the tool bare.
A command that parses to nothing is refused, and the refusal names both fixes.
"""

from __future__ import annotations

from dataclasses import dataclass

# The two kinds that carry no command and therefore no polarity.
BARE: tuple[str, ...] = ("standing", "unwitnessed")

# ⚑ A KEY IS EMITTED AS SOURCE AND READ BACK BY A REGEX IN THE BIB'S WITNESS RESOLVER, so its
#   alphabet is part of the contract rather than a style preference.
KEY_CHARS = "-_"

# `mode:TOOL:FLAG` splits into exactly these three parts.
_MODE_PARTS = 3


@dataclass(frozen=True, slots=True)
class Spec:
    """One parsed kind: which builder to emit, and the arguments it takes.

    ⚑ `cmd` IS EMPTY FOR A BARE KIND, and that is how a caller knows there is no polarity to
    probe — rather than by re-testing the kind name at each site.
    """

    builder: str
    cmd: tuple[str, ...]
    tool: str
    flag: str

    @property
    def probed(self) -> bool:
        """Whether this kind runs a command whose polarity can be checked at filing time.

        ⚑ `mode:` IS PROBED THOUGH IT CARRIES NO argv: its reader runs the caller's lens, so a
        predicate keyed only on `cmd` would silently exempt it.
        """
        return bool(self.cmd) or self.builder == "_mode_undocumented"


def _split_command(raw: str) -> list[str]:
    """Split a command that may be space- or comma-separated.

    ⚑ COMMAS ARE ACCEPTED BECAUSE THE SHELL EATS SPACES: being told to quote only helps the filer
    who reads the refusal, not the one who already typed it.

    Returns:
        the command's words.

    """
    parts = raw.split(",") if "," in raw else raw.split()
    return [word for word in parts if word]


def menu(kind: str) -> str:
    """Return the five-kind menu, which is the only kind documentation most filers read.

    Returns:
        the refusal text.

    """
    return (
        f"unknown kind {kind!r}. The kind picks the EXIT CODE — prefer a FALSIFIABLE one:\n"
        "  selftest:<command>   holds when the command exits 0 — a mechanism WORKS. Quote it.\n"
        "  refuses:<command>    holds when the command exits NON-ZERO — an installed REFUSAL is "
        "still installed. Quote it. Use this for any 'the repair landed' finding whose repair is "
        "a refusal; `standing` cannot notice a revert.\n"
        "  mode:TOOL:FLAG       holds while the flag is DOCUMENTED (roster-vs-dispatch, through "
        "the lens the ledger's caller supplies). NOT a test that anything works.\n"
        "  unwitnessed          reports 2. The honest kind for a judgement or a lesson no "
        "command can distinguish true from false.\n"
        "  standing             holds at 0 unconditionally. LEGITIMATE ONLY for a measured FACT "
        "about how something behaves, never for a claim that a repair landed — its witness "
        "asserts the finding is still RECORDED, and no change to the code can flip it."
    )


def parse(kind: str) -> tuple[Spec | None, str]:
    """Return `(spec, "")` for a well-formed kind, or `(None, refusal)`.

    ⚑ THE REFUSAL IS RETURNED, NEVER RAISED, so a tool whose main job is refusing can assert on
    its own refusals.

    Returns:
        the parsed spec and an empty string, or None and the refusal.

    """
    if kind.startswith("mode:"):
        parts = kind.split(":")
        if len(parts) != _MODE_PARTS or not parts[1] or not parts[2]:
            return None, "mode kind must be mode:TOOL:FLAG, e.g. mode:fix_notinscope.py:--summary"
        return Spec("_mode_undocumented", (), parts[1], parts[2]), ""
    for verb in ("selftest", "refuses"):
        if not kind.startswith(verb + ":"):
            continue
        cmd = _split_command(kind.split(":", 1)[1])
        if not cmd:
            return None, (
                f"{verb} kind must be {verb}:<command>, e.g. "
                f'"{verb}:scripts/cgroup-scope selftest" (QUOTE it — an unquoted space ends the '
                "KIND argument and the rest becomes the note), or pass it comma-separated"
            )
        return Spec(f"_{verb}", tuple(cmd), "", ""), ""
    if kind in BARE:
        return Spec(f"_{kind}", (), "", ""), ""
    return None, menu(kind)


def bad_key(key: str) -> str:
    """Return a refusal if `key` cannot survive the round trip, else the empty string.

    ⚑⚑ THE ALPHABET IS A CONTRACT WITH A READER IN ANOTHER TOOL: a character outside it makes a
    witness that exists, works, and is INVISIBLE to the resolver whose refusal it has to clear.

    Returns:
        the refusal, or "".

    """
    if not key:
        return "a key is required — it names the finding in both the roster and the bib"
    if not all(c.isalnum() or c in KEY_CHARS for c in key):
        return (
            f"key {key!r} must be [A-Za-z0-9-_] — it is emitted as source and read back by a "
            "regex in the bib's witness resolver"
        )
    return ""
