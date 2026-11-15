"""Item generation and gear stats. Pure Python, no discord or database imports."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from game.combat import Fighter

SLOTS = ("weapon", "armor")                  # spell and relic come later
RARITIES = ("common", "rare", "epic")        # legendary and mythic come later
AFFIX_SLOTS = {"common": 1, "rare": 2, "epic": 3}
ELEMENTS = ("neutral", "fire", "ice", "lightning", "water")

# Chance of each affix tier on a roll (T1 is common, T5 is rare)
TIER_WEIGHTS = {1: 35, 2: 28, 3: 20, 4: 12, 5: 5}
PITY_THRESHOLD = 10        # failed rerolls before a T4 or T5 is guaranteed (N, tune later)

# (T1 value, T5 value); tiers in between are evenly spaced. Starting values to tune.
# Elemental DMG is left out until the engine has a stat for it.
AFFIX_RANGES = {
    "crit_chance": (0.02, 0.11),
    "crit_mult":   (0.05, 0.30),   # added on top of the 1.5x base crit multiplier
    "armor_pen":   (0.02, 0.12),
    "lifesteal":   (0.01, 0.07),
    "dodge":       (0.01, 0.06),
    "thorns":      (0.02, 0.10),
}
AFFIX_LABELS = {
    "crit_chance": "Crit Chance", "crit_mult": "Crit Multiplier", "armor_pen": "Armor Pen",
    "lifesteal": "Lifesteal", "dodge": "Dodge", "thorns": "Thorns",
}

BASE_STATS = {
    "weapon": {"common": {"attack": 20}, "rare": {"attack": 24}, "epic": {"attack": 28}},
    "armor": {
        "common": {"defense_reduction": 0.10, "hp": 0},
        "rare":   {"defense_reduction": 0.15, "hp": 5},
        "epic":   {"defense_reduction": 0.20, "hp": 10},
    },
}
MAX_CRIT_MULT = 2.0        # total crit multiplier cap


def tier_value(stat: str, tier: int) -> float:
    lo, hi = AFFIX_RANGES[stat]
    return round(lo + (hi - lo) * (tier - 1) / 4, 4)


@dataclass
class Affix:
    stat: str
    tier: int
    value: float
    locked: bool = False

    def describe(self) -> str:
        pct = f"+{self.value * 100:.1f}%"
        return f"{AFFIX_LABELS[self.stat]} {pct} (T{self.tier})"


def roll_affix(rng: random.Random, taken: set[str], min_tier: int = 1) -> Affix:
    """Roll one affix of a stat not already on the item, at tier >= min_tier."""
    stats = [s for s in AFFIX_RANGES if s not in taken]
    stat = rng.choice(stats)
    tiers = [t for t in TIER_WEIGHTS if t >= min_tier]
    tier = rng.choices(tiers, weights=[TIER_WEIGHTS[t] for t in tiers])[0]
    return Affix(stat, tier, tier_value(stat, tier))


@dataclass
class Item:
    slot: str
    rarity: str
    element: str = "neutral"
    base: dict = field(default_factory=dict)
    affixes: list[Affix] = field(default_factory=list)
    id: int | None = None
    owner_id: int | None = None

    # ---- database helpers (JSON columns) ----
    def base_json(self) -> str:
        return json.dumps(self.base)

    def affix_json(self) -> str:
        return json.dumps([a.__dict__ for a in self.affixes])

    @classmethod
    def from_row(cls, row) -> "Item":
        return cls(
            id=row["id"], owner_id=row["owner_id"], slot=row["slot"], rarity=row["rarity"],
            element=row["element"], base=json.loads(row["base_json"]),
            affixes=[Affix(**a) for a in json.loads(row["affix_json"])],
        )

    def describe(self) -> str:
        if self.slot == "weapon":
            base = f"ATK {self.base['attack']}"
        else:
            base = f"DEF {self.base['defense_reduction'] * 100:.0f}%"
            if self.base.get("hp"):
                base += f", +{self.base['hp']} HP"
        head = f"{self.rarity.title()} {self.slot.title()}"
        if self.element != "neutral":
            head += f" ({self.element})"
        return " | ".join([f"{head}: {base}"] + [a.describe() for a in self.affixes])


def generate_item(slot: str, rarity: str, rng: random.Random | None = None,
                  element: str = "neutral") -> Item:
    rng = rng or random.Random()
    if slot not in SLOTS or rarity not in RARITIES or element not in ELEMENTS:
        raise ValueError(f"bad item spec: {slot}, {rarity}, {element}")
    item = Item(slot=slot, rarity=rarity, element=element,
                base=dict(BASE_STATS[slot][rarity]))
    taken: set[str] = set()
    for _ in range(AFFIX_SLOTS[rarity]):
        affix = roll_affix(rng, taken)
        taken.add(affix.stat)
        item.affixes.append(affix)
    return item


def build_fighter(name: str, weapon: Item | None = None, armor: Item | None = None,
                  disposition: str = "balanced") -> Fighter:
    """Turn equipped gear into a Fighter for the duel engine."""
    f = Fighter(name, disposition=disposition)
    stats = {"crit_chance": f.crit_chance, "armor_pen": f.armor_pen,
             "lifesteal": f.lifesteal, "dodge": f.dodge, "thorns": f.thorns}
    crit_bonus = 0.0
    hp_bonus = 0
    if weapon:
        f.attack = weapon.base["attack"]
        f.element = weapon.element
    if armor:
        f.defense_reduction = armor.base["defense_reduction"]
        hp_bonus += armor.base.get("hp", 0)
    for item in (weapon, armor):
        for a in (item.affixes if item else []):
            if a.stat == "crit_mult":
                crit_bonus += a.value
            else:
                stats[a.stat] += a.value
    for stat, value in stats.items():
        setattr(f, stat, value)
    f.crit_mult = min(f.crit_mult + crit_bonus, MAX_CRIT_MULT)
    f.max_hp += hp_bonus
    f.__post_init__()      # re-apply stat caps and reset live duel state
    return f
