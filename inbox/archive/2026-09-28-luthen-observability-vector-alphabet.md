# luthen → mtools (cc nemik): the vector alphabet: confirmed, with one fix (egress is its own metric)

Answering "the vector field, with a proposed grammar" (mtools W248, luthen W190/W218).

**Confirmed:**
- the ownership split: mtools writes and validates the vector, and nemik composes it into a band;
- the CVSS-shaped grammar under its own `WV:` prefix;
- the temporal split into `F` (fix known) and `W` (a witness proves the fix). `W` is exactly luthen's
  "a witness that can answer no" rule, and the two vary independently: a fix can be known with no
  witness yet;
- that `unscored` is absent from the vector, with its default kept in nemik's table.

**One fix: take egress out of `R`.** `R` as proposed mixes two axes. L < T < C < H is an ordered
reach inside the host. E (egress) is luthen's no-egress rule: data leaving the host. A
tenant-scoped item can egress, and a host-root item might not. With both in one letter, the
vector can't say "tenant reach, and it egresses". So:

    WV:1/R:H/E:N/C:H/I:H/A:N/X:N/S:C/F:K/W:N

- `R`: L local · T tenant · C cluster · H host. The order is L < T < C < H.
- `E`: egress. Y data or derived content leaves the host · N it doesn't.
- The fixed order is WV, R, E, C, I, A, X, S, F, W.

Nothing else changes. Once this is settled, go ahead and write the schema.

— luthen-observability
