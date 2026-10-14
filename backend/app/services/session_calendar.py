"""Expected trading-session lists for return alignment (Decision 005)."""

from abc import ABC, abstractmethod
from datetime import date, timedelta


class SessionCalendar(ABC):
    """Returns ordered session dates for a closed date range."""

    @abstractmethod
    def sessions_in_range(self, start: date, end: date) -> list[date]:
        """Return session dates from `start` to `end` inclusive, oldest first."""


class WeekdaySessionCalendar(SessionCalendar):
    """Treat Monday through Friday as sessions.

    Exchange holidays are not removed here. Missing holiday prices drop
    the affected return intervals in calculation_service, which matches
    Decision 005. A full XNYS calendar can replace this adapter later.
    """

    def sessions_in_range(self, start: date, end: date) -> list[date]:
        sessions: list[date] = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                sessions.append(current)
            current += timedelta(days=1)
        return sessions
