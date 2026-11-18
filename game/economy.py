"""Gold prices and XP rules. Pure Python: no discord or database imports.

All numbers are placeholders and are stingy on purpose, so gear feels earned (see the Economy
Spec). Epic gear can never be bought: it only comes from expeditions.
"""
from __future__ import annotations

from game.items import Item
from game.stats import xp_to_next

SHOP_PRICE = {"common": 500, "rare": 4000}                 # no epic: it has to be earned
SELL_GOLD = {"common": 40, "rare": 150, "epic": 500}

XP_EXPEDITION = 30           # for every expedition you collect
XP_PUSH_BONUS = 60           # extra, only when a Push Deeper succeeds (a lost Push gives nothing)
XP_DUEL_WIN = 20
XP_DUEL_OTHER = 10           # a loss or a draw
DUEL_XP_PER_DAY = 3          # only this many duels in a rolling 24 hours give XP, so friends cannot farm each other
DUEL_XP_WINDOW = 24 * 60 * 60


def sell_value(item: Item) -> int:
    return SELL_GOLD[item.rarity]


def shop_price(rarity: str) -> int | None:
    """Gold price of a rarity, or None when it is not for sale."""
    return SHOP_PRICE.get(rarity)


def duel_xp(won: bool) -> int:
    return XP_DUEL_WIN if won else XP_DUEL_OTHER


def add_xp(level: int, xp: int, gain: int) -> tuple[int, int, int]:
    """Add XP and level up as often as the XP allows. Returns (level, xp, levels gained)."""
    start = level
    xp += max(0, gain)
    while xp >= xp_to_next(level):
        xp -= xp_to_next(level)
        level += 1
    return level, xp, level - start
