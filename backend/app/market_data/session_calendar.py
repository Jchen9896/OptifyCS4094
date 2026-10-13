"""Get exchange trading dates from the installed exchange_calendars package."""

from datetime import date

import exchange_calendars
from exchange_calendars.errors import InvalidCalendarName

from app.core.errors import AppError


class ExchangeSessionCalendar:
    """Implement the calculation service's calendar with real exchange schedules.

    The caller supplies the calendar name, such as XNYS for the MVP. Schedule
    rules come from the installed package; no network request is made here.
    """

    def __init__(self, name: str) -> None:
        try:
            self._calendar = exchange_calendars.get_calendar(name)
        except InvalidCalendarName as error:
            raise AppError(
                f"Trading calendar '{name}' is not supported.",
                code="unsupported_calendar", status_code=422,
            ) from error
        self.name = self._calendar.name

    def sessions_in_range(self, start_date: date, end_date: date) -> tuple[date, ...]:
        """Return trading dates oldest first, including both bounds if open."""
        if start_date > end_date:
            raise AppError(
                "The calendar start date must not be after the end date.",
                code="invalid_calculation_input", status_code=422,
            )
        try:
            sessions = self._calendar.sessions_in_range(start_date, end_date)
        except ValueError as error:
            raise AppError(
                f"Calendar {self.name} supports dates from "
                f"{self._calendar.first_session.date()} to {self._calendar.last_session.date()}. "
                "Choose a period within those bounds.",
                code="unsupported_period", status_code=422,
            ) from error
        return tuple(session.date() for session in sessions)
