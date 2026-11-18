"""Duel engine for the micro-ARPG battler.

Pure Python: no discord imports, so the same code runs in the bot, in the
terminal playtest and in the balance simulation. Rules follow the Combat Spec.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class Move(str, Enum):
    ATTACK = "attack"
    GUARD = "guard"
    SKILL = "skill"


# --- Tunable constants (tuned in simulation, see the Combat Spec) -----------
MAX_ROUNDS = 5
# Skill is the weapon's ability and is paid with mana. The mana numbers are placeholders
# that copy the old energy timing (start 1, +1 a round, Skill costs 2, cap 3) in units of 30.
START_MANA = 30
MANA_REGEN = 30           # gained at the end of every round
GUARD_MANA_BONUS = 30     # extra mana for playing Guard
DEFAULT_SKILL_COST = 60   # the basic test weapon's Skill
DEFAULT_SKILL_MULT = 1.5  # heavy strike: 1.5 times the base hit
GUARD_BLOCK = 0.70        # share of a hit a guard blocks
SKILL_PIERCE = 0.8        # a Skill keeps 80% of the guard's block (70% -> 56%)
INTERRUPT_MULT = 0.45     # Skill hit while the opponent attacks lands at 45%
GUARD_COUNTER = 0.70      # a Guard against an Attack counters for 70% of the guarder's attack
ELEMENT_MULT = 1.25       # 1.25 to 1.5 in the design doc
BEATS = {"fire": "ice", "ice": "lightning", "lightning": "water", "water": "fire"}

# Hard caps so no single stat decides a duel
CAPS = {
    "dodge": 0.25,
    "crit_chance": 0.70,
    "lifesteal": 0.25,
    "armor_pen": 0.50,
    "defense_reduction": 0.70,
    "thorns": 0.20,
}


@dataclass
class Fighter:
    name: str
    max_hp: int = 100
    attack: float = 20.0
    defense_reduction: float = 0.10
    armor_pen: float = 0.0
    crit_chance: float = 0.30       # base mechanic: 30% chance, +50% damage
    crit_mult: float = 1.5
    strength: float = 0.0           # percent bonus to attack damage
    defense: float = 0.0            # defense points, for display; the engine uses defense_reduction
    level: int = 1
    max_mana: int = 100
    skill_name: str = "Heavy Strike"
    skill_cost: int = DEFAULT_SKILL_COST
    skill_mult: float = DEFAULT_SKILL_MULT
    dodge: float = 0.0
    lifesteal: float = 0.0
    thorns: float = 0.0
    element: str = "neutral"
    disposition: str = "balanced"   # used by the async policy

    # live duel state
    hp: int = field(init=False)
    mana: int = field(init=False)
    damage_dealt: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        for stat, cap in CAPS.items():
            setattr(self, stat, min(getattr(self, stat), cap))
        self.reset()

    def reset(self) -> None:
        self.hp = self.max_hp
        self.mana = min(START_MANA, self.max_mana)
        self.damage_dealt = 0


@dataclass
class RoundResult:
    number: int
    moves: dict[str, Move]
    events: list[str]
    hp: dict[str, int]
    mana: dict[str, int]


def _incoming(att: Fighter, att_move: Move, dfn_move: Move) -> tuple[float, float] | None:
    """Return (power, block share) for the hit `att` lands with `att_move` on `dfn_move`."""
    if att_move is Move.ATTACK:
        return 1.0, (GUARD_BLOCK if dfn_move is Move.GUARD else 0.0)
    if att_move is Move.SKILL:
        power = att.skill_mult * (INTERRUPT_MULT if dfn_move is Move.ATTACK else 1.0)
        return power, (GUARD_BLOCK * SKILL_PIERCE if dfn_move is Move.GUARD else 0.0)
    return None  # Guard deals no damage


class Duel:
    def __init__(self, a: Fighter, b: Fighter, seed: int | None = None,
                 max_rounds: int = MAX_ROUNDS):
        self.a, self.b = a, b
        self.seed = seed if seed is not None else random.randrange(2**32)
        self.rng = random.Random(self.seed)
        self.max_rounds = max_rounds
        self.round = 0
        self.history: list[RoundResult] = []
        a.reset()
        b.reset()

    # ---- state -----------------------------------------------------------
    @property
    def over(self) -> bool:
        return (self.round >= self.max_rounds or self.a.hp <= 0 or self.b.hp <= 0)

    @staticmethod
    def legal_moves(f: Fighter) -> list[Move]:
        moves = [Move.ATTACK, Move.GUARD]
        if f.mana >= f.skill_cost:
            moves.append(Move.SKILL)
        return moves

    def winner(self) -> Fighter | None:
        """Higher HP wins, then more damage dealt, otherwise a draw (None)."""
        if self.a.hp != self.b.hp:
            return self.a if self.a.hp > self.b.hp else self.b
        if self.a.damage_dealt != self.b.damage_dealt:
            return self.a if self.a.damage_dealt > self.b.damage_dealt else self.b
        return None

    # ---- one hit ---------------------------------------------------------
    def _hit(self, att: Fighter, dfn: Fighter, att_move: Move, dfn_move: Move):
        power, block = _incoming(att, att_move, dfn_move)
        # 1. dodge (Skill cannot be dodged)
        if att_move is not Move.SKILL and self.rng.random() < dfn.dodge:
            return 0, False, True
        dmg = att.attack * power * (1 + att.strength / 100)
        # 2. crit (a guarded hit cannot crit)
        crit = dfn_move is not Move.GUARD and self.rng.random() < att.crit_chance
        if crit:
            dmg *= att.crit_mult
        # 3. element
        if BEATS.get(att.element) == dfn.element:
            dmg *= ELEMENT_MULT
        # 4. defense, shrunk by armor penetration
        dmg *= 1 - dfn.defense_reduction * (1 - att.armor_pen)
        # 5. guard block
        dmg *= 1 - block
        return max(1, round(dmg)), crit, False

    # ---- one round -------------------------------------------------------
    def play_round(self, move_a: Move, move_b: Move) -> RoundResult:
        if self.over:
            raise RuntimeError("duel is already over")
        for f, m in ((self.a, move_a), (self.b, move_b)):
            if m not in self.legal_moves(f):
                raise ValueError(f"{f.name} cannot play {m.value} with {f.mana} mana")
        self.round += 1
        events: list[str] = []

        for f, m in ((self.a, move_a), (self.b, move_b)):
            if m is Move.SKILL:
                f.mana -= f.skill_cost

        # Both hits are worked out before either is applied (simultaneous)
        hits = []
        for att, dfn, am, dm in ((self.a, self.b, move_a, move_b),
                                 (self.b, self.a, move_b, move_a)):
            if am is Move.GUARD:
                continue
            dmg, crit, dodged = self._hit(att, dfn, am, dm)
            hits.append((att, dfn, am, dmg, crit, dodged))

        # Pass 1: apply all damage at the same time
        landed = []
        for att, dfn, am, dmg, crit, dodged in hits:
            label = att.skill_name if am is Move.SKILL else "Attack"
            if dodged:
                events.append(f"{dfn.name} dodges {att.name}'s {label}.")
                continue
            dmg = min(dmg, dfn.hp)  # cannot take more than remaining HP
            dfn.hp -= dmg
            att.damage_dealt += dmg
            events.append(f"{att.name}'s {label}{' (CRIT)' if crit else ''} hits "
                          f"{dfn.name} for {dmg}.")
            landed.append((att, dfn, dmg))

        # Guard counter: guarding against an Attack hits back (no crit, no dodge, no element)
        for att, dfn, am, dm in ((self.a, self.b, move_a, move_b),
                                 (self.b, self.a, move_b, move_a)):
            if am is Move.ATTACK and dm is Move.GUARD:
                dmg = dfn.attack * GUARD_COUNTER * (1 + dfn.strength / 100) * (1 - att.defense_reduction * (1 - dfn.armor_pen))
                dmg = min(max(1, round(dmg)), att.hp)
                att.hp -= dmg
                dfn.damage_dealt += dmg
                events.append(f"{dfn.name} blocks and counters {att.name} for {dmg}.")

        # Pass 2: thorns reflect damage actually taken (no crit, no bounce back)
        for att, dfn, dmg in landed:
            reflect = min(round(dmg * dfn.thorns), att.hp)
            if reflect:
                att.hp -= reflect
                dfn.damage_dealt += reflect
                events.append(f"{dfn.name}'s thorns reflect {reflect} to {att.name}.")

        # Pass 3: lifesteal heals after damage, up to max HP, never revives
        for att, dfn, dmg in landed:
            if att.hp <= 0:
                continue
            heal = min(round(dmg * att.lifesteal), att.max_hp - att.hp)
            if heal:
                att.hp += heal
                events.append(f"{att.name} steals {heal} HP.")

        if not hits:
            events.append("Both players guard. Nothing happens.")

        # Mana: regenerates every round, Guard gives extra, capped at max mana
        for f, m in ((self.a, move_a), (self.b, move_b)):
            f.mana = min(f.max_mana, f.mana + MANA_REGEN + (GUARD_MANA_BONUS if m is Move.GUARD else 0))

        result = RoundResult(
            number=self.round,
            moves={self.a.name: move_a, self.b.name: move_b},
            events=events,
            hp={self.a.name: self.a.hp, self.b.name: self.b.hp},
            mana={self.a.name: self.a.mana, self.b.name: self.b.mana},
        )
        self.history.append(result)
        return result


# ---- async defender policy -----------------------------------------------
DISPOSITIONS = {
    "aggressive": {Move.ATTACK: 0.45, Move.SKILL: 0.40, Move.GUARD: 0.15},
    "balanced":   {Move.ATTACK: 0.35, Move.SKILL: 0.30, Move.GUARD: 0.35},
    "defensive":  {Move.ATTACK: 0.20, Move.SKILL: 0.20, Move.GUARD: 0.60},
}


def policy_move(me: Fighter, opponent: Fighter, rng: random.Random) -> Move:
    """Pick a legal move from the fighter's disposition weights.

    If the opponent can afford a Skill, Attack gets a little heavier because it
    interrupts Skill. Illegal moves are dropped and the weights renormalised.
    """
    weights = dict(DISPOSITIONS.get(me.disposition, DISPOSITIONS["balanced"]))
    if opponent.mana >= opponent.skill_cost:
        weights[Move.ATTACK] *= 1.3
    legal = Duel.legal_moves(me)
    moves = [m for m in legal]
    return rng.choices(moves, weights=[weights[m] for m in moves])[0]


def format_round(r: RoundResult) -> str:
    moves = " vs ".join(f"{n}: {m.value}" for n, m in r.moves.items())
    hp = ", ".join(f"{n} {v} HP" for n, v in r.hp.items())
    return f"Round {r.number} ({moves})\n  " + "\n  ".join(r.events) + f"\n  -> {hp}"
