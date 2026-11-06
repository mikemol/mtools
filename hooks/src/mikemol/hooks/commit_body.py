# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A commit body is plain text: the trailers are the tool's, never the caller's (mtools:W1273).

⚑ `mikemol-commit` WRITES TWO TRAILERS ITSELF, the `Waypoint:` line and the co-author line
(`commit_kata.message_of`). A caller that also puts either in `--body` (or in a stack file's body)
gets it TWICE: measured on 2026-10-15, every commit made by one session carried its `Co-Authored-By`
line in the body and again as the tool's own trailer. The rule used to live in a tick prompt, where
nothing enforced it; this is the check, run where the body enters, so the prompt can drop the rule.

⚑ A REFUSAL, NOT A QUIET REPAIR: stripping the line would hide that the caller misunderstood the
tool, and the next caller would repeat it. The message names the two trailers the tool adds.
"""

_OWNED = ("waypoint:", "co-authored-by:", "admission:")

# ⚑ AN ADMISSION TRAILER IS THE PACE GUARD'S, NEVER THE CALLER'S (W2301): it is the proof that a
# pinned row was spent, written for an admitted entry by the landing step, so a body that carries
# one could forge a spent row or hide an unspent one.
_ADMISSION = "admission:"

# The one non-W waypoint form `waypoint_trailer` accepts.
_NONE = "none"


def refusal(body: str) -> str | None:
    """Say why a commit body may not be used, if it may not.

    Returns:
        the reason when any line of the body starts with a trailer the tool adds itself
        (`Waypoint:`, `Co-Authored-By:` or `Admission:`, any case, after leading space), else None.

    """
    for number, line in enumerate(body.splitlines(), start=1):
        if line.strip().lower().startswith(_OWNED):
            word = line.strip().split(":", 1)[0]
            if line.strip().lower().startswith(_ADMISSION):
                return (
                    f"the body's line {number} is an {word} trailer: the pace guard writes it "
                    "for an admitted entry as the proof that its row was spent, so a body may "
                    "not carry one"
                )
            return (
                f"the body's line {number} is a {word} trailer: mikemol-commit adds the Waypoint "
                "and Co-Authored-By trailers itself, so a body carrying either has it twice"
            )
    return None


def subject_refusal(subject: str) -> str | None:
    """Say why a commit subject may not be used, if it may not.

    ⚑ THE SUBJECT IS INTERPOLATED RAW INTO THE MESSAGE (`commit_kata.message_of`), so it needs
    the body's check too: a subject of `Admission: r/1` would register as a spent row, and one
    with a line break could carry a trailer on its second line (W2301, github-14's review).

    Returns:
        the reason when the subject spans lines or starts with a tool-owned trailer, else None.

    """
    if subject.splitlines() != [subject]:
        return "the subject is one line: a line break would let a second line carry a tool trailer"
    reason = refusal(subject)
    return None if reason is None else reason.replace("the body's line 1", "the subject")


def waypoint_refusal(waypoint: str) -> str | None:
    """Say why a waypoint may not be written into a message, if it may not.

    ⚑ THE WAYPOINT IS INTERPOLATED RAW TOO (W2301, github-14's second review): a waypoint with a
    line break and `Admission: forged/row` after it put a forged trailer on a line of its own.

    ⚑ `none` IS A FORM THE COMMIT-MSG HOOK ACCEPTS (`waypoint_trailer`) and live callers use it
    (the fleet state sync, luthen's settings commit), so it passes; nothing else but W and digits.

    Returns:
        the reason when it is neither `none` nor `W` and ASCII digits on one line, else None.

    """
    if waypoint == _NONE:
        return None
    if waypoint.startswith("W") and waypoint[1:].isdigit() and waypoint.isascii():
        return None
    return f"the waypoint {waypoint!r} must be W and digits on one line, or none"


def trailer_refusal(trailer: str) -> str | None:
    """Say why a co-author trailer may not be written into a message, if it may not.

    Returns:
        the reason when it spans lines or starts with an Admission trailer, else None.

    """
    if trailer.splitlines() != [trailer]:
        return "the trailer is one line: a line break would let a second line carry a tool trailer"
    if trailer.strip().lower().startswith(_ADMISSION):
        return "the trailer may not be an Admission trailer: the pace guard writes those"
    return None


def message_refusal(message: str) -> str | None:
    """Say why an ASSEMBLED commit message may not be used, if it may not.

    ⚑ THE LAST CHECK, ON THE OUTPUT, SO EVERY INPUT ROUTE IS COVERED (github-14): the subject,
    body, waypoint and trailer each have their own check at the door, and this one reads what they
    made. No message built by `commit_kata.message_of` carries an `Admission:` line; the pace guard
    adds its own after this, to an entry it admitted.

    Returns:
        the reason when any line of the message starts with `Admission:`, else None.

    """
    for number, line in enumerate(message.splitlines(), start=1):
        if line.strip().lower().startswith(_ADMISSION):
            return f"the assembled message's line {number} is an Admission trailer"
    return None
