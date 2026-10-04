# W247 — icsstruct: a lossless structured calendar reader

Asked for by life (inbox/2026-09-28-life-ask-calendar-reader.md, life:W13). Consumers: life and nemik.
It is transcriptstruct's pattern (every input unit yields exactly one record, and a record keeps
`raw`) applied to RFC 5545.

## Contract (from the letter, unchanged)

- Input is an `.ics` path, a URL, or an Akonadi-kept iCal export. The output does not depend on
  which kind of input it was.
- One record per VEVENT **occurrence** inside a window the caller gives. Expansion covers RRULE,
  RDATE, EXDATE and RECURRENCE-ID overrides. Times are timezone-aware, and all-day events are marked.
- Lossless: every component yields one record, including unknown components and malformed lines,
  which carry a `reason`. Counting the records counts the input.
- CLI: `mikemol-ics --window 14d SOURCE…` prints one line per occurrence; `--json` prints records.

## Two layers, because no library is lossless

1. **Lexical layer, written here.** Unfold content lines per RFC 5545 §3.1. Split
   `NAME;PARAMS:VALUE`, and nest `BEGIN`/`END` into components. Every physical line belongs to
   exactly one record. A malformed line (no colon, END without a matching BEGIN, a component left
   unclosed at EOF) becomes a record with `kind="malformed"` and a reason; it is never dropped.
   This layer is where the lossless count holds.
2. **Expansion layer, from a library.** Only well-formed VEVENTs, with their VTIMEZONEs, go to
   the recurrence expander. Candidates are `icalendar` plus `recurring-ical-events`: both on
   PyPI, maintained, and handling RECURRENCE-ID overrides and EXDATE.
   ⚑ Before adopting them, check they ship `py.typed` or need a stub (mdstruct/stubs precedent),
   and pin them through `requirements.txt` like other dists.
   If the expander raises on an event, that event yields one record with `kind="unexpandable"`,
   `raw` and the exception text. It is not dropped.

Why not let `icalendar` parse the file: its parser either raises on malformed input or silently
skips lines, depending on its strictness mode. Either way the count would stop matching the input.

## Record shape (draft)

`kind` (occurrence | component | malformed | unexpandable), `uid`, `start`, `end` (aware
datetimes, or dates for all-day events), `all_day`, `summary`, `recurrence_id`, `calendar`
(the stable label, see below), `line_span` (first and last physical line), `raw`.

## The credential

A secret URL is a credential. The whole source is read once, **redacted at the edge**, and
nothing inside the reader keeps the URL string: records, errors, `--json` and logs all use a
label. The label is the calendar's `X-WR-CALNAME` if present, else `url:<sha256[:12]>`.
Fetch errors are rewritten to use the label before they propagate, because a urllib error embeds
the full URL. A test must plant a URL and assert that it appears in no output stream and in no
exception text.

Akonadi (the letter's addendum): read the `.ics` export Akonadi keeps current. D-Bus is a later
input kind with the same output contract, and is not in the first cut.

## Open questions (each gets its own waypoint)

- Fixtures from life: sanitized `.ics` files covering a weekly RRULE with an EXDATE, a
  RECURRENCE-ID override, an all-day event, a TZID event and a floating-time event, plus one
  deliberately malformed file.
- Is an event that starts before the window and ends inside it an occurrence? Proposal: yes,
  using overlap semantics (the recurring-ical-events default).
