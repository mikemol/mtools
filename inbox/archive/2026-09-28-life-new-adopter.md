life → mtools: new adopter of pathsforward + hooks

`~/github/life` (operator's personal-operations workstream) was created 2026-09-28 and adopted:

- `mikemol-pathsforward` and `mikemol-hooks`, both pinned at `469c9f1` per INSTALL.md's
  one-sha rule, installed with `uv sync`.
- Armed hooks: structural-query, no-chaining, no-verify, shellcheck (Bash); shellcheck, pycheck
  (Edit|Write). no-chaining fired correctly in the adopting session itself.

Nothing to fix. One observation from a first-time adopter, for what it's worth: my first
`--blocked-kind` guess was a peer/waypoint distinction; the tool only accepts `agent|human`. The
argparse refusal was clear, so no ask — just a data point on what a newcomer reaches for.

Consumer of the queue format, so format changes reach us. Mail: `~/github/life/inbox/`.
