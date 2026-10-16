# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure parts of re-vendoring the mtools wheels at one commit (mtools:W989, lifted from W988).

⚑ LIFTED FROM luthen-observability's `checks/revendor_mtools` (luthen-observability:W811), which
did by tool what `vendor/wheels/README.md` recorded as a hand recipe: `git archive <sha> hooks
pathsforward`, the local version `+g<short>` set in the ARCHIVED pyproject only, `uv build --wheel`
for each dist, the wheels copied in, the two `[tool.uv.sources]` paths moved. `mikemol-repin` names
a vendored wheel and never rewrites it, so the move it could not make is this one.

⚑ BOTH DISTS MOVE TOGETHER AND NOTHING HERE TOUCHES A DISK OR A PROCESS. The names, the pin
matching, the source rewrite and the plan text are functions of strings, so they are tested without
git or uv; the build, the throwaway-venv check and the swap sit behind a runner seam in
`revendor_apply`. Two specs of one repo at different commits can resolve to two copies of the
shared `mikemol` namespace (docs/repinning.md), which is why `DISTS` is a pair and never one dist.
"""

import re

DISTS = ("hooks", "pathsforward")
# ⚑ THE FENCE IS OPT-IN BY PRESENCE (mtools:W1031, luthen-observability:W843). A repo that vendors
# the hooks wheel has no commit lock unless `mikemol-membudget` sits beside its interpreter, which
# is the fence wheel. A repo adds that wheel once (`mikemol-wheel fence`, a `[tool.uv.sources]`
# path and a dependency); from then on `--revendor` moves it with the pair.
KNOWN = (*DISTS, "fence")
VERSION = "0.1.0"
_SOURCE = re.compile(
    r"(vendor/wheels/mikemol_(?:hooks|pathsforward|fence)-0\.1\.0\+g)([0-9a-f]+)"
    r"(-py3-none-any\.whl)"
)
_FULL_SHA = re.compile(r"[0-9a-f]{40}")
_SHORT = 7


def vendored(pyproject: str) -> tuple[str, ...]:
    """Name the mtools dists a pyproject vendors, in `KNOWN` order.

    Returns:
        each dist whose wheel path the file names; the hooks and pathsforward pair when it names
        none (the caller refuses a repo that vendors nothing before it gets here).

    """
    found = tuple(d for d in KNOWN if f"vendor/wheels/mikemol_{d}-" in pyproject)
    return found or DISTS


def wheel_name(dist: str, short: str) -> str:
    """Name the wheel a dist builds to at a short sha.

    Returns:
        the wheel file name, with the local version `+g<short>`.

    """
    return f"mikemol_{dist}-{VERSION}+g{short}-py3-none-any.whl"


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
    return {m.group(2) for m in _SOURCE.finditer(pyproject)}


def move_sources(pyproject: str, short: str) -> str:
    """Move every vendored mtools wheel path in a pyproject to a short sha.

    Returns:
        the text with each path rewritten and everything else untouched.

    """
    return _SOURCE.sub(rf"\g<1>{short}\g<3>", pyproject)


def with_local_version(archived: str, short: str) -> str | None:
    """Set the local version in an ARCHIVED pyproject, never in the tree.

    Returns:
        the text with `version = "0.1.0+g<short>"`, or None when it has no 0.1.0 to extend.

    """
    marker = f'version = "{VERSION}"'
    if marker not in archived:
        return None
    return archived.replace(marker, f'version = "{VERSION}+g{short}"', 1)


SYNC_LINE = (
    "uv lock, uv sync --frozen: REMOVES every package not named in uv.lock from .venv "
    "(use --no-sync where extras are installed on purpose)"
)
NO_SYNC_LINE = "uv lock only (--no-sync): .venv is left exactly as it is"


def plan_lines(
    sha: str, old: set[str], source: str, dists: tuple[str, ...] = DISTS, *, sync: bool = True
) -> list[str]:
    """Say what an apply would do, for printing before it does it.

    ⚑ THE SYNC LINE CARRIES ITS OWN WARNING (amr-skills:W358). `uv sync --frozen` makes `.venv`
    match `uv.lock` exactly, so it REMOVES every package the lock does not name: a re-vendor run in
    a checkout with deliberately installed extras (amr-skills' vllm stack, ~142 packages) deleted
    them. The plan said only "uv sync --frozen"; the warning sat in a README nobody read then.

    Returns:
        one line per step, in order.

    """
    short = short_of(sha)
    kept = ", ".join(sorted(old)) or "none"
    return [
        f"git archive {short} {' '.join(dists)} from {source}; +g{short} in the archive only",
        *(f"uv build --wheel {d} -> {wheel_name(d, short)}" for d in dists),
        "throwaway venv: install all; the new writer's --hash on a COPY of the queue == live",
        f"copy the wheels to vendor/wheels, git rm the old ({kept})",
        f"move the {len(dists)} [tool.uv.sources] paths in pyproject.toml to +g{short}",
        SYNC_LINE if sync else NO_SYNC_LINE,
        "print the new sha256 lines for vendor/wheels/README.md (a hand-written record)",
    ]
