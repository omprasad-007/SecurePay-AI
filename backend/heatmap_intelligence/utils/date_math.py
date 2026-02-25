from __future__ import annotations

from datetime import date, timedelta


def previous_period(start_date: date, end_date: date) -> tuple[date, date]:
    span_days = max(1, (end_date - start_date).days + 1)
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)
    return previous_start, previous_end

