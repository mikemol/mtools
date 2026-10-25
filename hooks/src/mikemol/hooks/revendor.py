# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure parts of re-vendoring the mtools wheels at one commit (mtools:W989, lifted from W988).

⚑ LIFTED FROM luthen-observability's `checks/revendor_mtools` (luthen-observability:W811), which
did by tool what `vendor/wheels/README.md` recorded as a hand recipe: `git archive <sha> hooks
pathsforward`, the local version `+g<short>` set in the ARCHIVED pyproject only, `uv build --wheel`
for each dist, the wheels copied in, the two `[tool.uv.sources]` paths moved. `mikemol-repin` names
a vendored wheel and never rewrites it, so the move it could not make is this one.

⚑ EVERY DIST A REPO VENDORS MOVES TOGETHER AND NOTHING HERE TOUCHES A DISK OR A PROCESS. The names,
the pin matching, the source rewrite and the plan text are functions of strings, so they are
tested without git or uv; the build, the throwaway-venv check and the swap sit behind a runner seam
in `revendor_apply`. Two specs of one repo at different commits can resolve to two copies of the
shared `mikemol` namespace (docs/repinning.md), which is why the wheels move as a set.

⚑ TWO LAYOUTS READ AS ONE (W1449, nemik-84, 2026-10-17). luthen's wheels are named
`0.1.0+g<short>`; nemik's are `0.1.0+<short>` with no `g`, and nemik vendors six dists, not three.
The pin pattern therefore takes ANY `vendor/wheels/mikemol_<dist>-0.1.0+[g]<short>` and `tag_of`
reads which prefix the repo already uses, so a re-vendor keeps the repo's own naming and names
every dist the pyproject lists, the `KNOWN` ones first.
"""

import re

DISTS = ("hooks", "pathsforward")
# ⚑ THE FENCE IS OPT-IN BY PRESENCE (mtools:W1031, luthen-observability:W843). A repo that vendors
# the hooks wheel has no commit lock unless `mikemol-membudget` sits beside its interpreter, which
# is the fence wheel. A repo adds that wheel once (`mikemol-wheel fence`, a `[tool.uv.sources]`
# path and a dependency); from then on `--revendor` moves it with the pair.
KNOWN = (*DISTS, "fence")
# ⚑ MORE MTOOLS DISTS A REPO MAY VENDOR (W1449, nemik): A NAMED LIST,
# NOT "ANY mikemol_ WHEEL": a wheel of some other project (`mikemol_ledger`) shares the prefix and
# is not ours to move. A repo that vendors a new mtools dist adds its name here.
EXTRA = (
    "icsstruct",
    "rulerseq",
    "frontier",
    "atomicwrite",
    "corpus",
    "waldo",
    "cvdcore",
    "ratchet",
)
ALL = (*KNOWN, *EXTRA)
_ALTERNATION = "|".join(ALL)
VERSION = "0.1.0"
TAG = "g"
_SOURCE = re.compile(
    rf"(vendor/wheels/mikemol_(?:{_ALTERNATION})-0\.1\.0\+)(g?)([0-9a-f]+)(-py3-none-any\.whl)"
)
_NAMED = re.compile(rf"vendor/wheels/mikemol_({_ALTERNATION})-0\.1\.0\+")
_FULL_SHA = re.compile(r"[0-9a-f]{40}")
_SHORT = 7


def vendored(pyproject: str) -> tuple[str, ...]:
    """Name the mtools dists a pyproject vendors: the known ones first, then the rest by name.

    Returns:
        each dist whose wheel path the file names; the hooks and pathsforward pair when it names
        none (the caller refuses a repo that vendors nothing before it gets here).

    """
    named = {m.group(1) for m in _NAMED.finditer(pyproject)}
    known = tuple(d for d in KNOWN if d in named)
    found = (*known, *(d for d in EXTRA if d in named))
    return found or DISTS


def tag_of(text: str) -> str:
    """Read which local-version prefix a repo's vendored wheel paths use.

    Returns:
        `g` or the empty string, from the first wheel path; `g` when the text names none.

    """
    found = _SOURCE.search(text)
    return found.group(2) if found else TAG


def wheel_name(dist: str, short: str, tag: str = TAG) -> str:
    """Name the wheel a dist builds to at a short sha.

    Returns:
        the wheel file name, with the local version `+<tag><short>`.

    """
    return f"mikemol_{dist}-{VERSION}+{tag}{short}-py3-none-any.whl"


def short_of(sha: str) -> str:
    """Shorten a commit the way the wheel names do.

    Returns:
        the first seven hex characters.

    """
    return sha[:_SHORT]


def is_full_sha(text: str) -> bool:
    """Say whether text is a full lowercase 40-hex commit.

    Returns:
        True only for one; a short sha or a branch would write a pin that does not pin.

    """
    return _FULL_SHA.fullmatch(text) is not None


def pinned_shorts(pyproject: str) -> set[str]:
    """Read which short shas the vendored wheel paths currently name.

    Returns:
        the set of short shas, empty when the file vendors none.

    """
    return {m.group(3) for m in _SOURCE.finditer(pyproject)}


def move_sources(pyproject: str, short: str) -> str:
    """Move every vendored mtools wheel path in a file to a short sha, keeping its tag.

    ⚑ ALSO FOR `MODULE.bazel` (W1449): nemik names the same wheel paths there, and the rewrite is
    the same text substitution.

    Returns:
        the text with each path rewritten and everything else untouched.

    """
    return _SOURCE.sub(rf"\g<1>\g<2>{short}\g<4>", pyproject)


def move_mentions(text: str, old: str, short: str) -> str:
    """Move the prose that names the mtools commit, `mtools <old>`, to the new one.

    Returns:
        the text with each `mtools <old short>` replaced (nemik's MODULE.bazel comments).

    """
    return text.replace(f"mtools {old}", f"mtools {short}")


def with_local_version(archived: str, short: str, tag: str = TAG) -> str | None:
    """Set the local version in an ARCHIVED pyproject, never in the tree.

    Returns:
        the text with `version = "0.1.0+<tag><short>"`, or None when it has no 0.1.0 to extend.

    """
    marker = f'version = "{VERSION}"'
    if marker not in archived:
        return None
    return archived.replace(marker, f'version = "{VERSION}+{tag}{short}"', 1)


SYNC_LINE = (
    "uv lock, uv sync --frozen: REMOVES every package not named in uv.lock from .venv "
    "(use --no-sync where extras are installed on purpose)"
)
NO_SYNC_LINE = "uv lock only (--no-sync): .venv is left exactly as it is"


def plan_lines(
    sha: str,
    old: set[str],
    source: str,
    dists: tuple[str, ...] = DISTS,
    how: tuple[bool, str] = (True, TAG),
) -> list[str]:
    """Say what an apply would do, for printing before it does it.

    ⚑ THE SYNC LINE CARRIES ITS OWN WARNING (amr-skills:W358). `uv sync --frozen` makes `.venv`
    match `uv.lock` exactly, so it REMOVES every package the lock does not name: a re-vendor run in
    a checkout with deliberately installed extras (amr-skills' vllm stack, ~142 packages) deleted
    them. The plan said only "uv sync --frozen"; the warning sat in a README nobody read then.

    `how` is (sync, tag): whether the venv is synced, and the repo's local-version prefix.

    Returns:
        one line per step, in order.

    """
    sync, tag = how
    short = short_of(sha)
    kept = ", ".join(sorted(old)) or "none"
    return [
        f"git archive {short} {' '.join(dists)} from {source}; +{tag}{short} in the archive only",
        *(f"uv build --wheel {d} -> {wheel_name(d, short, tag)}" for d in dists),
        "throwaway venv: install all; the new writer's --hash on a COPY of the queue == live",
        f"copy the wheels to vendor/wheels, git rm the old ({kept}), git add -f the new",
        f"move the {len(dists)} wheel paths in pyproject.toml and MODULE.bazel to +{tag}{short}",
        SYNC_LINE if sync else NO_SYNC_LINE,
        "rewrite the wheels' checksum file when the repo keeps one; print the new hashes",
    ]
