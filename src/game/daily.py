"""The daily reset that all per-day limits share. Pure Python: no discord or database imports.

Every player's daily counts (expeditions started, duels that give XP) start again at the same
moment each day, so "today" is the same for everyone. Change RESET_UTC_SECONDS to move it.
"""
from __future__ import annotations

DAY = 24 * 60 * 60
RESET_UTC_SECONDS = 9 * 3600 + 30 * 60   # seconds after midnight UTC: 09:30 UTC = 3:00 pm IST


def window_start(now: int) -> int:
    """When the current daily window began: the most recent reset at or before `now`."""
    reset = now - now % DAY + RESET_UTC_SECONDS
    return reset if reset <= now else reset - DAY


def next_reset(now: int) -> int:
    """When the daily counts reset next. The same moment for every player."""
    return window_start(now) + DAY
