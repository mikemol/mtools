# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1486, W1566: rank one bazel invocation's test targets by how long they ran, from BuildBuddy.

A gate runs for about thirty-five minutes and bazel is a third of it. To say where the rest goes the
first question is which targets took the time, and BuildBuddy keeps it per target in the invocation
it already stores: `GetInvocation` answers `invocation[0].targetGroups[].targets[]`, each target
carrying `metadata.label`, `status` and, for a test, `testSummary.totalRunDurationMillis`. This is
the one reader of that shape, as `bb_records` is of the execution records.

⚑ EVERY GROUP IS PAGED AND THIS READER FOLLOWS IT (W1566). `GetInvocation` returns the first twelve
targets of each group with a `nextPageToken` beside a `totalCount`; the rest of a group comes from
`GetTarget` with `{invocationId, status, pageToken}` (the group's own status, read from the service
2026-10-18), which answers `targetGroups[0]` with the next twelve and the next token. A group is
followed until a page carries no token. A token seen twice ends the walk, as a witness of no
progress, never a timer.

⚑ A RANKING OF A PART IS NOT A MAXIMUM (github-8f, 2026-10-18). The report says COMPLETE only when
every target the groups hold was listed and nothing was unreadable. Otherwise its status says
INCOMPLETE with the counts, and the rows come under `observed_only`, never `tests`, so no reader
takes the first row of a partial listing for the slowest target. A failed or unreadable page counts
as unreadable and stops that group; nothing is dropped silently.

⚑ A BUILT TARGET IS NOT A TEST: only a target with a `testSummary` has a duration, so the others
count toward `listed` and carry no rank.

    python -m mikemol.buildtel.bb_targets <invocation-id>   # the longest test targets, JSON
"""

import http.client
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

from mikemol.buildtel import bb_records

RPC = "/rpc/BuildBuddyService/GetInvocation"
RPC_PAGE = "/rpc/BuildBuddyService/GetTarget"
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
HTTP_OK = 200
USAGE = "bb_targets <invocation-id>"
TOP_TESTS = 30

Fetch = Callable[[str], object]
"""Fetch one invocation: its id to parsed JSON."""

Page = Callable[[str, str, str], object]
"""Fetch the next page of one group: (invocation id, group status, page token) to parsed JSON."""


@dataclass(frozen=True)
class Ranked:
    """One test target and how long its runs took."""

    label: str
    status: str
    millis: int


@dataclass(frozen=True)
class GroupCount:
    """How many targets one group lists against how many it holds."""

    status: str
    listed: int
    total: int

    def short(self) -> bool:
        """Say whether the group lists fewer targets than it holds.

        Returns:
            True when some of its targets were not listed.

        """
        return self.listed < self.total


@dataclass
class Report:
    """The tests of one invocation, and how much of the response that covers."""

    tests: list[Ranked] = field(default_factory=list)
    groups: list[GroupCount] = field(default_factory=list)
    listed: int = 0
    total: int = 0
    unreadable: int = 0

    def complete(self) -> bool:
        """Say whether every target the groups hold was listed and none was unreadable.

        Returns:
            True only then; a ranking of anything less is not a maximum.

        """
        return self.unreadable == 0 and self.listed == self.total

    def verdict(self) -> str:
        """Say COMPLETE, or INCOMPLETE with the counts and each group that is short.

        ⚑ A GROUP WITH NO STATUS IS NOT PAGED BY THE SERVICE (read 2026-10-18 on invocation
        9761e453): `GetTarget` refuses its token, so only its first twelve targets are listed. Those
        carry no test results, and every test of that invocation sat in a group that listed in
        full, but the unlisted rest is not proven to hold none, so the verdict stays INCOMPLETE and
        names the group.

        Returns:
            `COMPLETE`, or `INCOMPLETE: listed N of M; short: <group> a of b, ...`.

        """
        if self.complete():
            return "COMPLETE"
        short = ", ".join(f"{g.status} {g.listed} of {g.total}" for g in self.groups if g.short())
        return f"INCOMPLETE: listed {self.listed} of {self.total}; short: {short or 'none named'}"


def _send(path: str, body: dict[str, object], host: str, port: int) -> object:
    """POST one request to the service and parse the answer.

    Returns:
        the response body, parsed.

    Raises:
        OSError: when the service answers with any status but 200.

    """
    conn = http.client.HTTPConnection(host, port, timeout=bb_records.TIMEOUT_S)
    try:
        conn.request(
            "POST", path, body=json.dumps(body), headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != HTTP_OK:
            msg = f"HTTP {resp.status}"
            raise OSError(msg)
    finally:
        conn.close()
    raw: object = json.loads(data)
    return raw


def post(invocation_id: str, host: str = bb_records.HOST, port: int = bb_records.PORT) -> object:
    """Fetch the invocation, as parsed JSON.

    Returns:
        the response body, parsed.

    """
    return _send(RPC, {"lookup": {"invocationId": invocation_id}}, host, port)


def post_page(
    invocation_id: str,
    status: str,
    token: str,
    host: str = bb_records.HOST,
    port: int = bb_records.PORT,
) -> object:
    """Fetch the next page of one target group, as parsed JSON.

    Returns:
        the response body, parsed.

    """
    body: dict[str, object] = {"invocationId": invocation_id, "status": status, "pageToken": token}
    return _send(RPC_PAGE, body, host, port)


def _is_dict(value: object) -> bool:
    # A plain bool, so nothing narrows to dict[Any, Any].
    return isinstance(value, dict)


def _is_list(value: object) -> bool:
    return isinstance(value, list)


def _mapping(value: object) -> dict[str, object] | None:
    # A JSON object typed as `object` values, or None for anything else.
    return cast("dict[str, object]", value) if _is_dict(value) else None


def _rows(value: object) -> list[object]:
    # A JSON array's elements typed as `object`, or [] for anything else.
    return cast("list[object]", value) if _is_list(value) else []


def _int(value: object) -> int:
    # A protobuf-JSON int64 arrives as a string; anything else counts as 0.
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def _rank(test: Ranked) -> tuple[int, str]:
    # Longest first, ties by label so the order is stable.
    return (-test.millis, test.label)


def _add(report: Report, target: object) -> None:
    """Fold one target into the report: a test gets a row, a built target only counts."""
    report.listed += 1
    found = _mapping(target)
    meta = _mapping(found.get("metadata")) if found is not None else None
    label = meta.get("label") if meta is not None else None
    if found is None or not isinstance(label, str):
        report.unreadable += 1
        return
    summary = _mapping(found.get("testSummary"))
    if summary is None:
        return
    status = found.get("status")
    named = status if isinstance(status, str) else "?"
    report.tests.append(Ranked(label, named, _int(summary.get("totalRunDurationMillis"))))


def _token(group: dict[str, object]) -> str:
    # The group's next page token, or "" when it has none.
    token = group.get("nextPageToken")
    return token if isinstance(token, str) else ""


def _follow(
    report: Report, group: dict[str, object], invocation_id: str, more: Page | None
) -> None:
    """Walk a group's remaining pages: until no token, a repeated token or an unreadable page.

    ⚑ A TOKEN SEEN TWICE IS NO PROGRESS and ends the walk as unreadable; a page that cannot be
    fetched or read does the same. Both leave `listed` short of `total`, so the report says so.
    """
    status = group.get("status")
    token = _token(group)
    if more is None or not token or not isinstance(status, str):
        return
    seen = {token}
    while token:
        try:
            answer = more(invocation_id, status, token)
        except OSError:
            report.unreadable += 1
            return
        root = _mapping(answer)
        groups = _rows(root.get("targetGroups")) if root is not None else []
        page = _mapping(groups[0]) if groups else None
        if page is None:
            report.unreadable += 1
            return
        for target in _rows(page.get("targets")):
            _add(report, target)
        token = _token(page)
        if token in seen:
            report.unreadable += 1
            return
        seen.add(token)


def parse(page: object, more: Page | None = None, invocation_id: str = "") -> Report:
    """Read the tests out of one `GetInvocation` response, following each group's pages.

    Returns:
        the report, the tests longest first; a response with no invocation counts one unreadable.

    """
    report = Report()
    root = _mapping(page)
    rows = _rows(root.get("invocation")) if root is not None else []
    first = _mapping(rows[0]) if rows else None
    if first is None:
        report.unreadable += 1
        return report
    for group in _rows(first.get("targetGroups")):
        found = _mapping(group)
        if found is None:
            report.unreadable += 1
            continue
        held = _int(found.get("totalCount"))
        report.total += held
        before = report.listed
        for target in _rows(found.get("targets")):
            _add(report, target)
        _follow(report, found, invocation_id, more)
        named = found.get("status")
        report.groups.append(
            GroupCount(
                named if isinstance(named, str) else "(no status)", report.listed - before, held
            )
        )
    report.tests.sort(key=_rank)
    return report


def main(argv: Sequence[str] | None = None, fetch: Fetch = post, more: Page = post_page) -> int:
    """Print the longest test targets of one invocation as JSON.

    Returns:
        0 on success, 2 for a usage error, 3 when the service is unreachable.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    try:
        report = parse(fetch(args[0]), more, args[0])
    except OSError as err:
        sys.stderr.write(f"bb_targets: {bb_records.HOST}:{bb_records.PORT} unreachable: {err}\n")
        return EXIT_UNREACHABLE
    rows = [
        {"label": t.label, "status": t.status, "millis": t.millis} for t in report.tests[:TOP_TESTS]
    ]
    whole = report.complete()
    out: dict[str, object] = {
        "status": report.verdict(),
        "listed": report.listed,
        "total": report.total,
        "unreadable": report.unreadable,
        "groups": [
            {"status": g.status, "listed": g.listed, "total": g.total} for g in report.groups
        ],
        "tests_found": len(report.tests),
        "tests" if whole else "observed_only": rows,
    }
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
