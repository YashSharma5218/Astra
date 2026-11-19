"""Salvaging and rerolling. Pure Python: no discord or database imports.

    shards = salvage_value(item)                     # what breaking an item down gives
    cost = reroll_cost(item.rarity, n_locks)         # what the next reroll costs
    result = reroll_affixes(item, {0}, pity, rng)    # new affix lines, with line 0 kept

Rerolling never touches base stats, only affix lines. Every unlocked line is rolled again; each
lock doubles the cost. After PITY_THRESHOLD rerolls in a row that rolled no T4 or T5 line, the
next reroll is guaranteed one. All numbers are placeholders on the "hundreds" scale, to be tuned
in playtests (an expedition gives 10 to 30 shards).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from src.game.items import PITY_THRESHOLD, Affix, Item, roll_affix

SALVAGE_SHARDS = {"common": 8, "rare": 24, "epic": 60}
REROLL_BASE_COST = {"common": 15, "rare": 30, "epic": 60}      # with no locks
LOCK_COST_MULT = 2                                              # each locked line doubles the cost
GOOD_TIER = 4                                                   # T4 and T5 count as a good roll


class CraftingError(ValueError):
    """A request the rules do not allow. The message is safe to show to the player."""


def salvage_value(item: Item) -> int:
    return SALVAGE_SHARDS[item.rarity]


def reroll_cost(rarity: str, locks: int) -> int:
    return REROLL_BASE_COST[rarity] * LOCK_COST_MULT ** locks


def check_locks(item: Item, locked: set[int]) -> None:
    """Locked lines are positions (0 = first line). At least one line must stay open."""
    if any(i < 0 or i >= len(item.affixes) for i in locked):
        raise CraftingError("That line does not exist on this item.")
    if len(locked) >= len(item.affixes):
        raise CraftingError("Leave at least one line unlocked, or there is nothing to reroll.")


@dataclass
class RerollResult:
    affixes: list[Affix]       # the item's new lines, in the same positions
    pity: int                  # the player's new pity counter
    forced: bool               # True when the pity guarantee was used
    good: bool                 # True when a rerolled line came out T4 or T5


def reroll_affixes(item: Item, locked: set[int], pity: int, rng: random.Random) -> RerollResult:
    """Roll every unlocked line again. Locked lines stay as they are, and a new line never
    repeats a stat that is already on the item."""
    check_locks(item, locked)
    taken = {item.affixes[i].stat for i in locked}
    guaranteed = pity >= PITY_THRESHOLD
    new: list[Affix] = []
    good = False
    for i, old in enumerate(item.affixes):
        if i in locked:
            new.append(Affix(old.stat, old.tier, old.value))
            continue
        # the guarantee is on the first open line, so one good line is enough
        affix = roll_affix(rng, taken, GOOD_TIER if guaranteed and not good else 1)
        taken.add(affix.stat)
        good = good or affix.tier >= GOOD_TIER
        new.append(affix)
    return RerollResult(new, 0 if good else pity + 1, guaranteed, good)