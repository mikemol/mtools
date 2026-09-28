# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# ⚑⚑ recurring-ical-events 3.8 SHIPS NO py.typed, so without this file every call is
# `import-untyped` under the strict block (measured, W258 probe). This declares the one chain the
# expansion layer calls, `of(calendar).between(start, stop)`, and nothing else.
#
# ⚑ `between` returns icalendar components, typed here as the stub's `Component`. The runtime
# `DateArgument` also admits tuples, strings and ints; icsstruct passes dates only, so the stub
# admits dates only and a caller that tries anything else is refused by mypy, not by the library.

import datetime

from icalendar import Component

class CalendarQuery:
    def between(
        self,
        start: datetime.date,
        stop: datetime.date | datetime.timedelta,
    ) -> list[Component]: ...

def of(
    a_calendar: Component,
    keep_recurrence_attributes: bool = False,
    components: tuple[str, ...] = ...,
    skip_bad_series: bool = False,
    calendar_query: type[CalendarQuery] = ...,
) -> CalendarQuery: ...
