"""Expedition loot rules. Pure Python: no discord or database imports.

An expedition is decided entirely by one stored seed, so closing the bot, running /scavenge
twice or retrying can never change the result:

    haul = roll_haul(seed, zone)            # rolled when the expedition starts
    result = roll_push(seed, zone, haul)    # what Push Deeper would give (or take away)

Items are stored as small specs (slot, rarity, element, seed) and turned into real Item
objects with build_item() only when the player claims them. All numbers are placeholders
on the "hundreds" scale and are meant to be tuned in playtests.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from src.game.daily import DAY as RUN_WINDOW, RESET_UTC_SECONDS, next_reset, window_start  # noqa: F401
from src.game.items import RARITIES, SLOTS, Item, generate_item

PUSH_CHANCE = 0.55       # chance that Push Deeper succeeds
PUSH_MULT = 2            # gold and shards are multiplied by this after a successful Push
GEM_CHANCE = 0.30        # chance of one Socket Gem after a successful Push
MAX_RUNS = 3             # expeditions a player can start between two daily resets


@dataclass(frozen=True)
class Zone:
    key: str
    name: str
    element: str                         # element of the gear that drops here
    duration: int                        # seconds
    entry_fee: int                       # gold
    gold: tuple[int, int]
    shards: tuple[int, int]
    base_weights: dict[str, int]         # rarity weights for a normal haul
    deep_weights: dict[str, int]         # rarity weights after a successful Push


ZONES = {
    "ruins": Zone(
        key="ruins", name="Mossy Ruins", element="neutral", duration=30 * 60, entry_fee=0,
        gold=(400, 800), shards=(10, 30),
        base_weights={"common": 70, "rare": 25, "epic": 5},
        deep_weights={"common": 35, "rare": 45, "epic": 20},
    ),
}
DEFAULT_ZONE = "ruins"


@dataclass(frozen=True)
class ItemSpec:
    slot: str
    rarity: str
    element: str
    seed: int


@dataclass
class Haul:
    gold: int = 0
    shards: int = 0
    gems: int = 0
    items: list[ItemSpec] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({"gold": self.gold, "shards": self.shards, "gems": self.gems,
                           "items": [vars(i) for i in self.items]})

    @classmethod
    def from_json(cls, text: str) -> "Haul":
        d = json.loads(text)
        return cls(d["gold"], d["shards"], d["gems"], [ItemSpec(**i) for i in d["items"]])


@dataclass
class PushResult:
    success: bool
    haul: Haul | None        # None when the push failed: everything is lost


def _roll_item(rng: random.Random, zone: Zone, weights: dict[str, int]) -> ItemSpec:
    slot = rng.choice(SLOTS)
    rarity = rng.choices(RARITIES, weights=[weights.get(r, 0) for r in RARITIES])[0]
    return ItemSpec(slot, rarity, zone.element, rng.getrandbits(62))


def roll_haul(seed: int, zone: Zone) -> Haul:
    """The normal haul of an expedition: gold, shards and one item."""
    rng = random.Random(seed)
    return Haul(gold=rng.randint(*zone.gold), shards=rng.randint(*zone.shards),
                items=[_roll_item(rng, zone, zone.base_weights)])


def roll_push(seed: int, zone: Zone, haul: Haul) -> PushResult:
    """What Push Deeper does for this expedition. The same seed always gives the same answer.

    Success: gold and shards double, the player keeps every item they were shown, one bonus item
    is added from the better rarity table, and there is a chance of a Socket Gem. A success is
    never worse than banking. Failure: everything is lost.
    """
    rng = random.Random(f"{seed}:push")
    success = rng.random() < PUSH_CHANCE
    bonus = _roll_item(rng, zone, zone.deep_weights)
    gems = 1 if rng.random() < GEM_CHANCE else 0
    if not success:
        return PushResult(False, None)
    return PushResult(True, Haul(haul.gold * PUSH_MULT, haul.shards * PUSH_MULT, gems,
                                 list(haul.items) + [bonus]))


def build_item(spec: ItemSpec) -> Item:
    """Turn a stored item spec into a real, unsaved Item (the same spec always gives the same item)."""
    return generate_item(spec.slot, spec.rarity, random.Random(spec.seed), spec.element)


def next_run_at(starts: list[int], now: int) -> int | None:
    """When the player can start another expedition, given the start times of their runs (any
    time). None means they can start one right now. All charges come back together at the daily
    reset, so a player who used all MAX_RUNS waits until next_reset()."""
    used = sum(1 for t in starts if t >= window_start(now))
    return None if used < MAX_RUNS else next_reset(now)


def seconds_left(ends_at: int, now: int) -> int:
    return max(0, ends_at - now)
