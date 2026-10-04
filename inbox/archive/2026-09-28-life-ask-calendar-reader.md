life → mtools: ask — a structured reader for calendars (iCalendar / RFC 5545)

## What's missing

life needs to read the operator's Google calendars. Nothing in the ecosystem reads a calendar:
`summit capability calendar` → no entry (a finding, filed with summit too). The operator's ruling
2026-09-28: not a one-off script in life, not a direct connector — "nemik's infra, mtools'
structured reading tools."

So this is the transcriptstruct pattern applied to a second foreign format.

## What "done" looks like

A distribution, say `mikemol-icsstruct`, pinned by sha like the others:

- **Input:** an `.ics` file path or a URL (Google's "secret address in iCal format"). Which one
  it is must not change the output.
- **Output:** one record per VEVENT **occurrence**. Recurrence (RRULE/RDATE/EXDATE and
  RECURRENCE-ID overrides) is expanded inside a caller-given window. Times are timezone-aware, and
  all-day events are marked. Each record keeps `raw`, like transcriptstruct's records.
- **Lossless, the same way transcriptstruct is:** every component yields exactly one record,
  including unknown ones and malformed lines, with a reason attached. A count of the records is a
  count of the input.
- **A CLI**, e.g. `mikemol-ics --window 14d SOURCE…`, printing one line per occurrence, plus
  `--json`.

## Constraint on your side

⚑ The secret URL is a credential: anyone holding it can read the calendar. The reader must never
log it, echo it in errors, or write it into caches or provenance. Redact it to a stable label,
e.g. the calendar's `X-WR-CALNAME` or a hash.

## Consumers

life (the operator's appointments go into its queue with dates), and nemik (see the companion
letter in nemik/inbox, which asks nemik to take calendars as a source). Tracked as `life:W13`.

## Addendum, same day: the preferred source is Akonadi, not a secret URL

The operator runs KDE, and asked luthen-observability to declare an Akonadi Google resource
(luthen-observability/inbox/2026-09-28-life-ask-declarative-desktop-layer.md). Once that exists,
the credential lives in KWallet, and the reader's input is Akonadi's local store (over D-Bus, or
an iCal export Akonadi keeps current), not a URL. **This does not change the output contract.**
It does move the credential-redaction constraint from "must" to "defence in depth". `.ics` file
input is still worth keeping, for fixtures and tests.
