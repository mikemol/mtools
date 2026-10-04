# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The //:hook member list is HAND-TRANSCRIBED, and this makes its drift LOUD.

Ported from paperkit's `tools/hook_grid.py` (paperkit:W142). One behaviour change: paperkit
located `MODULE.bazel` and `BUILD.bazel` from the module's own path (`tools/..`); an installed
tool has no such path, so the repo root is the current directory, or `--root PATH`.

⚑ WHY THE LIST STAYS HAND-MAINTAINED. `BUILD.bazel`'s members are a per-project x per-target-kind
GRID that `tools/bibtex.bzl` already knows in full, transcribed by hand into a file the generator
cannot see, so members can fall out silently. The obvious repair (a generated per-project
`test_suite` and `@paperkit_*//:all` labels) CANNOT BE TAKEN: `paperkit/tests/boundaries_check.py`
proves the hook COMPLETE by comparing two INDEPENDENT TEXTUAL SOURCES (the literal member list in
BUILD.bazel against the `bib.project` tags in MODULE.bazel) and asserts SET-EQUALITY, which a
`:all` label fails by construction. Generating the list would let the audited thing supply its
own audit.

⚑ THEREFORE THIS GATE REMOVES THE **SILENTLY**, NOT THE HAND-MAINTENANCE. The duplication is kept
ON PURPOSE; what is added is a check that the two copies AGREE.

WHAT IT COMPARES. The emission rules, read from tools/bibtex.bzl and reproduced here as the ONLY
hand-copied thing:

    gate       every wired project                      (bibtex.bzl:932, unconditional)
    adequacy   adequacy = True                           (bibtex.bzl:985)
    cohere     emerge = True                             (bibtex.bzl:892)
    decisions  emerge = True                             (bibtex.bzl:906)

Usage:  mikemol-hook-grid [--root PATH]   # exit 0 = the transcription matches the declarations
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# The canary: the ONE non-project member (the harness positive control). Named, not filtered, for
# the same reason bnd-check uses set-equality: an unnamed residual admits any stray member.
NON_PROJECT = frozenset({"//canary:canary"})

# ⚑ HOOK-MEMBERSHIP EXEMPTIONS, DECLARED HERE BECAUSE THEY ARE DECLARED NOWHERE ELSE.
#
# The generator emits `gate` for EVERY wired project, unconditionally and regardless of tier, so
# the omission of these three is a HUMAN POLICY recorded only in prose. Naming them here makes
# the policy attributable and reviewable: each exemption carries WHY, and an unlisted absence is
# a red.
#
# ⚑ These are audit finding 5, still open, not settled facts (G4 in prototypes/README.md flags
# the setup/report pair as an unfixed gap; it does not authorise the exemption).
HOOK_EXEMPT: Mapping[str, str] = {
    "@paperkit_setup//:gate": (
        "tier=local (shells systemd-run, probes live /proc,/sys); ⚑ NOT "
        "authorised — G4 flags this as an unfixed gap, see Ω-F7"
    ),
    "@paperkit_report//:gate": (
        "tier=local for 10 of 16 warrants; they reach sibling projects via "
        "gen.py, so Ω-F5 (execroot vs source tree) blocks them, not host need"
    ),
    "@paperkit_image//:gate": (
        "tier=local; the 3 podman warrants need a PODMAN + base-digest stamp "
        "key before toolchain tier is sound (Ω-F2)"
    ),
}


def declared(module: str) -> dict[str, set[str]]:
    """Return `{repo: kinds}` the generator WOULD emit, from each bib.project tag's flags.

    Returns:
        the target kinds each `bib.project(name = ...)` line emits.

    """
    out: dict[str, set[str]] = {}
    for line in module.splitlines():
        if "bib.project(" not in line:
            continue
        m = re.search(r'name\s*=\s*"([^"]+)"', line)
        if not m:
            continue
        kinds = {"gate"}  # unconditional
        if "adequacy = True" in line:
            kinds.add("adequacy")
        if "emerge = True" in line:
            kinds |= {"cohere", "decisions"}
        out[m.group(1)] = kinds
    return out


def transcribed(build: str) -> set[str]:
    r"""Return the //:hook member list, verbatim.

    ⚑ DO NOT USE A NON-GREEDY `\[(.*?)\]` HERE. The member list's own comments contain wiki-style
    refs like [[place-by-ownership-not-need]], so the first `]` a non-greedy match finds is INSIDE
    a comment, above the real end of the list, and the scrape silently drops later members.

    So the list is bracket-COUNTED from `tests = [` to its matching close, and only then scanned
    for quoted labels. A label is `@repo//:target` or `//pkg:target`; a bracketed wiki-ref carries
    no quotes and cannot be mistaken for one, but the SLICE has to be right first.

    Returns:
        the quoted labels of the member list; empty when the list is not found.

    """
    i = build.find("tests = [", build.find('name = "hook"'))
    if i < 0:
        return set()
    i = build.index("[", i)
    depth = 0
    end = i
    for end in range(i, len(build)):
        if build[end] == "[":
            depth += 1
        elif build[end] == "]":
            depth -= 1
            if depth == 0:
                break
    quoted = cast("list[str]", re.findall(r'"([^"]+)"', build[i + 1 : end]))
    return {t for t in quoted if t.startswith(("@", "//"))}


def _exemption_findings(emitted: set[str], have: set[str], exempt: Mapping[str, str]) -> list[str]:
    """Name the exemptions that outlived their subject or contradict the hook.

    Returns:
        one message per stale exemption, then one per contradicted exemption.

    """
    found = [
        f"hook-grid: STALE EXEMPTION — {t}\n"
        "    HOOK_EXEMPT excuses it, but no bib.project tag emits it any more"
        for t in sorted(set(exempt) - emitted)
    ]
    found += [
        f"hook-grid: CONTRADICTED EXEMPTION — {t}\n"
        "    HOOK_EXEMPT excuses it AND //:hook runs it; drop the exemption"
        for t in sorted(set(exempt) & have)
    ]
    return found


def _drift_report(missing: list[str], extra: list[str]) -> list[str]:
    """Say which targets the hook lacks and which it names without a declaration.

    Returns:
        one message per drifted target, then the closing explanation.

    """
    found = [
        f"hook-grid: MISSING from //:hook — {t}\n"
        "    the generator emits this target and local CI never runs it"
        for t in missing
    ]
    found += [
        f"hook-grid: STALE in //:hook — {t}\n"
        "    no bib.project tag declares the flag that emits this"
        for t in extra
    ]
    found.append(
        f"\nhook-grid: the hand-transcribed //:hook grid has DRIFTED from MODULE.bazel's "
        f"declarations ({len(missing)} missing, {len(extra)} stale).  The list is "
        f"hand-maintained on purpose — it is one of bnd-check's two independent sources — so "
        f"the repair is to EDIT BUILD.bazel, never to relax this check."
    )
    return found


def check(module: str, build: str, exempt: Mapping[str, str] = HOOK_EXEMPT) -> int:
    """Compare the hook's member list in `build` with the declarations in `module`.

    Findings go to stderr, the agreement summary to stdout.

    Returns:
        0 when the transcription matches, 1 on any drift or exemption defect.

    """
    decl = declared(module)
    have = transcribed(build)
    if not have:
        sys.stderr.write("hook-grid: could not find the //:hook member list in BUILD.bazel\n")
        return 1

    emitted = {f"@{repo}//:{kind}" for repo, kinds in decl.items() for kind in kinds}
    want = (emitted - set(exempt)) | NON_PROJECT

    # An exemption that is no longer emitted is a STALE exemption; one whose target is ALSO in the
    # hook is contradictory: both excused and run.
    defects = _exemption_findings(emitted, have, exempt)
    if defects:
        sys.stderr.write("".join(f"{d}\n" for d in defects))
        return 1

    missing = sorted(want - have)  # the generator emits it; the hook does not run it
    extra = sorted(have - want)  # the hook names it; nothing emits it
    if missing or extra:
        sys.stderr.write("".join(f"{d}\n" for d in _drift_report(missing, extra)))
        return 1

    sys.stdout.write(
        f"hook-grid: //:hook matches MODULE.bazel — {len(decl)} project(s), {len(emitted)} "
        f"emitted target(s), {len(exempt)} declared exemption(s), "
        f"{len(NON_PROJECT)} harness member; {len(have)} transcribed\n"
    )
    for t, why in sorted(exempt.items()):
        sys.stdout.write(f"  exempt  {t}\n          {why}\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Read `MODULE.bazel` and `BUILD.bazel` under the root and check the hook grid.

    Returns:
        0 when the transcription matches the declarations, 1 otherwise.

    """
    ap = argparse.ArgumentParser(description="Check the //:hook list against MODULE.bazel.")
    ap.add_argument("--root", default=".", help="the repository root (default: the cwd)")
    root_arg: str = ap.parse_args(argv).root
    root = Path(root_arg)
    module = (root / "MODULE.bazel").read_text(encoding="utf-8")
    build = (root / "BUILD.bazel").read_text(encoding="utf-8")
    return check(module, build)


if __name__ == "__main__":
    raise SystemExit(main())
