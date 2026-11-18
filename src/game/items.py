"""Item generation and gear stats. Pure Python, no discord or database imports."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from src.game.combat import DEFAULT_SKILL_COST, DEFAULT_SKILL_MULT, Fighter
from src.game.stats import base_stats, defense_to_reduction

ARMOR_SLOTS = ("helmet", "chestplate", "leggings", "boots")
SLOTS = ("weapon",) + ARMOR_SLOTS            # the weapon's ability is the Skill, so no spell slot
RARITIES = ("common", "rare", "epic")        # legendary and mythic come later
AFFIX_SLOTS = {"common": 1, "rare": 2, "epic": 3}
ELEMENTS = ("neutral", "fire", "ice", "lightning", "water")

# Chance of each affix tier on a roll (T1 is common, T5 is rare)
TIER_WEIGHTS = {1: 35, 2: 28, 3: 20, 4: 12, 5: 5}
PITY_THRESHOLD = 10        # failed rerolls before a T4 or T5 is guaranteed (N, tune later)

# (T1 value, T5 value); tiers in between are evenly spaced, so T3 is about 58% of T5.
# T5 values come from the balance simulation (Gear & Affixes Spec). Strength is in
# points (1 point = +1% attack damage). Elemental DMG is left out until the engine has it.
AFFIX_RANGES = {
    "strength":    (1, 7),
    "crit_chance": (0.02, 0.12),
    "crit_mult":   (0.03, 0.20),   # added on top of the 1.5x base crit multiplier
    "armor_pen":   (0.02, 0.14),
    "lifesteal":   (0.01, 0.05),
    "dodge":       (0.01, 0.08),
    "thorns":      (0.01, 0.05),
}
AFFIX_LABELS = {
    "strength": "Strength", "crit_chance": "Crit Chance", "crit_mult": "Crit Multiplier", "armor_pen": "Armor Pen",
    "lifesteal": "Lifesteal", "dodge": "Dodge", "thorns": "Thorns",
}

# Base stats by item kind and rarity, on the "hundreds" scale: a level 1 fighter has 100 HP and
# gear provides the bulk. A Common set gives 400 HP and 75 defense, Rare 480 and 100, Epic 560
# and 125. Defense points turn into damage reduction with defense / (defense + 500), so a full
# Epic set removes about 20%. Each armor piece has its own base HP and defense; the weapon
# carries the Skill (a basic test weapon for now). Rerolling never changes base stats.
BASE_STATS = {
    "weapon": {
        "common": {"attack": 100}, "rare": {"attack": 120}, "epic": {"attack": 140},
    },
    "armor": {
        "common": {"chestplate": {"defense": 24, "hp": 140}, "leggings": {"defense": 21, "hp": 100},
                   "helmet": {"defense": 18, "hp": 100}, "boots": {"defense": 12, "hp": 60}},
        "rare":   {"chestplate": {"defense": 32, "hp": 170}, "leggings": {"defense": 28, "hp": 120},
                   "helmet": {"defense": 24, "hp": 120}, "boots": {"defense": 16, "hp": 70}},
        "epic":   {"chestplate": {"defense": 40, "hp": 200}, "leggings": {"defense": 35, "hp": 140},
                   "helmet": {"defense": 30, "hp": 140}, "boots": {"defense": 20, "hp": 80}},
    },
}
WEAPON_SKILL = {"skill_name": "Heavy Strike", "skill_cost": DEFAULT_SKILL_COST,
                "skill_mult": DEFAULT_SKILL_MULT}
MAX_CRIT_MULT = 2.0        # total crit multiplier cap


# Public item codes: one letter for the slot plus the item's creation number in that slot,
# written with the digits 1-9 and the letters A-Z (no zero, no dash): W1, W2 ... W9, WA ... WZ, W11.
# The number counts up in the order items are generated, so a higher number is a newer item.
ID_DIGITS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"          # 35 symbols
SLOT_PREFIX = {"weapon": "W", "helmet": "H", "chestplate": "C", "leggings": "L", "boots": "B"}


def encode_seq(n: int) -> str:
    """1 -> '1', 9 -> '9', 10 -> 'A', 35 -> 'Z', 36 -> '11'. Counting without a zero symbol."""
    if n < 1:
        raise ValueError("sequence numbers start at 1")
    out = []
    while n > 0:
        n -= 1
        out.append(ID_DIGITS[n % len(ID_DIGITS)])
        n //= len(ID_DIGITS)
    return "".join(reversed(out))


def decode_seq(text: str) -> int:
    n = 0
    for ch in text:
        n = n * len(ID_DIGITS) + ID_DIGITS.index(ch) + 1
    return n


def make_uid(slot: str, seq: int) -> str:
    return SLOT_PREFIX[slot] + encode_seq(seq)


def normalize_uid(text: str) -> str:
    """What a player typed -> the stored format: upper case, no spaces or dashes."""
    return text.strip().upper().replace(" ", "").replace("-", "")


def tier_value(stat: str, tier: int) -> float:
    lo, hi = AFFIX_RANGES[stat]
    return round(lo + (hi - lo) * (tier - 1) / 4, 4)


def base_for(slot: str, rarity: str) -> dict:
    """Fresh base stats for a new item of this slot and rarity."""
    if slot == "weapon":
        return {**BASE_STATS["weapon"][rarity], **WEAPON_SKILL}
    return dict(BASE_STATS["armor"][rarity][slot])


@dataclass
class Affix:
    stat: str
    tier: int
    value: float
    locked: bool = False

    def describe(self) -> str:
        if self.stat == "strength":
            return f"Strength +{self.value:g} (T{self.tier})"
        return f"{AFFIX_LABELS[self.stat]} +{self.value * 100:.1f}% (T{self.tier})"


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
    id: int | None = None          # internal database key
    owner_id: int | None = None
    uid: str = ""                  # public code like H12; given by the database when the item is saved

    # ---- database helpers (JSON columns) ----
    def base_json(self) -> str:
        return json.dumps(self.base)

    def affix_json(self) -> str:
        return json.dumps([a.__dict__ for a in self.affixes])

    @classmethod
    def from_row(cls, row) -> "Item":
        return cls(
            id=row["id"], uid=row["uid"], owner_id=row["owner_id"], slot=row["slot"], rarity=row["rarity"],
            element=row["element"], base=json.loads(row["base_json"]),
            affixes=[Affix(**a) for a in json.loads(row["affix_json"])],
        )

    def describe(self) -> str:
        if self.slot == "weapon":
            base = f"ATK {self.base['attack']}"
            if self.base.get("skill_name"):
                base += f", {self.base['skill_name']} ({self.base['skill_cost']} mana)"
        else:
            base = f"DEF {self.base['defense']:g}, +{self.base['hp']} HP"
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
                base=base_for(slot, rarity))
    taken: set[str] = set()
    for _ in range(AFFIX_SLOTS[rarity]):
        affix = roll_affix(rng, taken)
        taken.add(affix.stat)
        item.affixes.append(affix)
    return item


def build_fighter(name: str, gear: dict[str, Item | None] | None = None, level: int = 1,
                  disposition: str = "balanced") -> Fighter:
    """Turn a level and equipped gear (slot -> Item or None) into a Fighter for the duel engine."""
    gear = {slot: item for slot, item in (gear or {}).items() if item}
    base = base_stats(level)
    f = Fighter(name, level=level, disposition=disposition, max_hp=base["hp"],
                max_mana=base["mana"], strength=base["strength"],
                defense=base["defense"], crit_chance=base["crit_chance"],
                crit_mult=1 + base["crit_damage"])
    stats = {"crit_chance": f.crit_chance, "armor_pen": f.armor_pen, "lifesteal": f.lifesteal,
             "dodge": f.dodge, "thorns": f.thorns, "strength": f.strength}
    crit_bonus, hp_bonus, defense = 0.0, 0, f.defense
    weapon = gear.get("weapon")
    if weapon:
        f.attack = weapon.base["attack"]
        f.element = weapon.element
        f.skill_name = weapon.base.get("skill_name", f.skill_name)
        f.skill_cost = weapon.base.get("skill_cost", f.skill_cost)
        f.skill_mult = weapon.base.get("skill_mult", f.skill_mult)
    for slot in ARMOR_SLOTS:
        piece = gear.get(slot)
        if piece:
            defense += piece.base.get("defense", 0)
            hp_bonus += piece.base.get("hp", 0)
    for item in gear.values():
        for a in item.affixes:
            if a.stat == "crit_mult":
                crit_bonus += a.value
            else:
                stats[a.stat] += a.value
    for stat, value in stats.items():
        setattr(f, stat, value)
    f.defense = defense
    f.defense_reduction = defense_to_reduction(defense)
    f.crit_mult = min(f.crit_mult + crit_bonus, MAX_CRIT_MULT)
    f.max_hp += hp_bonus
    f.__post_init__()      # re-apply stat caps and reset live duel state
    return f