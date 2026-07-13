from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


class AiRateLimitExceeded(RuntimeError):
    def __init__(self, scope: str) -> None:
        self.scope = scope
        super().__init__(f"AI rate limit exceeded for {scope}")


@dataclass(frozen=True)
class AiRateLimitReservation:
    browser_key: str
    ip_key: str
    timestamp: datetime


class AnonymousAiRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def consume(
        self,
        *,
        browser_key: str,
        ip_key: str,
        browser_limit: int,
        ip_limit: int,
    ) -> tuple[int, AiRateLimitReservation]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        safe_browser_limit = max(1, browser_limit)
        safe_ip_limit = max(1, ip_limit)

        with self._lock:
            browser_events = self._events[browser_key]
            ip_events = self._events[ip_key]
            self._prune(browser_events, cutoff)
            self._prune(ip_events, cutoff)

            if len(browser_events) >= safe_browser_limit:
                raise AiRateLimitExceeded("browser")
            if len(ip_events) >= safe_ip_limit:
                raise AiRateLimitExceeded("network")

            browser_events.append(now)
            ip_events.append(now)

        reservation = AiRateLimitReservation(
            browser_key=browser_key,
            ip_key=ip_key,
            timestamp=now,
        )
        remaining = max(0, safe_browser_limit - len(browser_events))
        return remaining, reservation

    def refund(self, reservation: AiRateLimitReservation) -> None:
        with self._lock:
            self._remove_event(reservation.browser_key, reservation.timestamp)
            self._remove_event(reservation.ip_key, reservation.timestamp)

    @staticmethod
    def _prune(events: deque[datetime], cutoff: datetime) -> None:
        while events and events[0] < cutoff:
            events.popleft()

    def _remove_event(self, key: str, timestamp: datetime) -> None:
        events = self._events.get(key)
        if not events:
            return
        try:
            events.remove(timestamp)
        except ValueError:
            return
        if not events:
            self._events.pop(key, None)


ai_rate_limiter = AnonymousAiRateLimiter()
