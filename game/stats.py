"""Player levels and base stats. Pure Python, no discord or database imports.

Base stats follow the progression decision in the Combat Spec: a level 1 fighter has
the values in BASE_STATS, and each level adds PER_LEVEL. Gear and affixes are added
on top in game/items.py (build_fighter).
"""
from __future__ import annotations

BASE_STATS = {
    "hp": 100,
    "mana": 100,
    "defense": 0,            # defense points; armor pieces add to it (see defense_to_reduction)
    "strength": 0,           # percent bonus to attack damage
    "crit_chance": 0.30,
    "crit_damage": 0.50,     # +50% on a crit, so the multiplier is 1.5
    "vitality": 100,         # reserved: has no effect yet (what it does is still open)
}
PER_LEVEL = {"hp": 5, "strength": 1}     # placeholder: HP and strength growth are still to be matched
MIN_LEVEL = 1
DEFENSE_K = 500          # damage reduction = defense / (defense + 500): 125 defense is about 20%


def defense_to_reduction(defense: float) -> float:
    """Turn defense points into the share of damage they remove (diminishing returns)."""
    defense = max(0.0, defense)
    return defense / (defense + DEFENSE_K)


def base_stats(level: int) -> dict:
    """Base stats of a fighter at `level`, before any gear."""
    level = max(MIN_LEVEL, int(level))
    stats = dict(BASE_STATS)
    for stat, per in PER_LEVEL.items():
        stats[stat] += per * (level - 1)
    return stats


# XP curve, shaped like Hypixel SkyBlock's skills: each level costs more than the last by a growing
# percentage at first, then by a fixed amount. Placeholder numbers, stingy on purpose.
XP_BASE = 150            # XP to go from level 1 to level 2
XP_GROWTH = 1.2          # each level up to XP_LINEAR_FROM costs 20% more than the one before
XP_LINEAR_FROM = 15      # from this level on, each level costs XP_STEP more than the previous one
XP_STEP = 300


def xp_to_next(level: int) -> int:
    """XP needed to go from `level` to the next one: exponential up to level 15, then linear."""
    level = max(MIN_LEVEL, int(level))
    if level <= XP_LINEAR_FROM:
        return round(XP_BASE * XP_GROWTH ** (level - 1))
    return round(XP_BASE * XP_GROWTH ** (XP_LINEAR_FROM - 1)) + XP_STEP * (level - XP_LINEAR_FROM)


def duel_levels(level_a: int, level_b: int, real_levels: bool = False) -> tuple[int, int]:
    """The levels both players fight at in a duel.

    By default both fight at the average of the two levels (rounded up on a half), so a
    big level gap does not decide the duel. With real_levels each keeps their own level.
    """
    if real_levels:
        return level_a, level_b
    avg = (level_a + level_b + 1) // 2
    return avg, avg
