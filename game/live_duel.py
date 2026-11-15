"""State of one live duel: who has locked in which move, timeouts and forfeits.

Pure Python (no discord), so it is tested without a bot. The Discord layer calls
submit() when a button is clicked and resolve() when the round ends.
"""
from __future__ import annotations

import json
from enum import Enum

from game.combat import Duel, Fighter, Move, RoundResult

MISSED_ROUNDS_TO_FORFEIT = 2     # missing this many rounds in a row forfeits the duel


class Submit(str, Enum):
    OK = "ok"
    NOT_PLAYER = "not_player"
    LOCKED = "locked"
    NO_ENERGY = "no_energy"
    OVER = "over"


class LiveDuel:
    def __init__(self, id_a: int, fighter_a: Fighter, id_b: int, fighter_b: Fighter,
                 seed: int | None = None):
        if fighter_b.name == fighter_a.name:        # round logs are keyed by name
            fighter_b.name += " (2)"
        self.ids = (id_a, id_b)
        self.fighters = {id_a: fighter_a, id_b: fighter_b}
        self.duel = Duel(fighter_a, fighter_b, seed=seed)
        self.choices: dict[int, Move] = {}
        self.missed = {id_a: 0, id_b: 0}
        self.forfeited: set[int] = set()
        self.last_result: RoundResult | None = None

    # ---- helpers ----
    def name_of(self, user_id: int) -> str:
        return self.fighters[user_id].name

    def other(self, user_id: int) -> int:
        a, b = self.ids
        return b if user_id == a else a

    def is_locked(self, user_id: int) -> bool:
        return user_id in self.choices

    @property
    def ready(self) -> bool:
        """True once both players have locked in a move."""
        return len(self.choices) == 2

    @property
    def finished(self) -> bool:
        return self.duel.over or bool(self.forfeited)

    # ---- a click on a move button ----
    def submit(self, user_id: int, move: Move) -> Submit:
        if user_id not in self.fighters:
            return Submit.NOT_PLAYER
        if self.finished:
            return Submit.OVER
        if user_id in self.choices:
            return Submit.LOCKED                    # a choice is final once locked in
        if move not in Duel.legal_moves(self.fighters[user_id]):
            return Submit.NO_ENERGY
        self.choices[user_id] = move
        return Submit.OK

    # ---- end of a round (both locked in, or the timer ran out) ----
    def resolve(self) -> RoundResult:
        if self.finished:
            raise RuntimeError("duel is already over")
        moves: dict[int, Move] = {}
        idle: list[int] = []
        for uid in self.ids:
            if uid in self.choices:
                moves[uid] = self.choices[uid]
                self.missed[uid] = 0
            else:
                moves[uid] = Move.GUARD             # no answer in time plays a default Guard
                self.missed[uid] += 1
                idle.append(uid)
        self.choices = {}
        a, b = self.ids
        result = self.duel.play_round(moves[a], moves[b])
        for uid in reversed(idle):
            result.events.insert(0, f"{self.name_of(uid)} did not answer in time and guards.")
        self.forfeited = {u for u in self.ids if self.missed[u] >= MISSED_ROUNDS_TO_FORFEIT}
        self.last_result = result
        return result

    # ---- outcome ----
    def winner_id(self) -> int | None:
        """The winner's user id, or None for a draw."""
        if not self.duel.over:
            if len(self.forfeited) == 1:
                return self.other(next(iter(self.forfeited)))
            return None
        w = self.duel.winner()
        if w is None:
            return None
        return next(uid for uid, f in self.fighters.items() if f is w)

    def end_reason(self) -> str:
        """One of: both_idle, forfeit, draw, ko, hp, damage."""
        if len(self.forfeited) == 2:
            return "both_idle"
        if self.forfeited and not self.duel.over:
            return "forfeit"
        if self.winner_id() is None:
            return "draw"
        a, b = self.fighters[self.ids[0]], self.fighters[self.ids[1]]
        if a.hp != b.hp:
            return "ko" if min(a.hp, b.hp) <= 0 else "hp"
        return "damage"

    def to_log(self) -> list[dict]:
        return [{"round": r.number,
                 "moves": {n: m.value for n, m in r.moves.items()},
                 "events": r.events, "hp": r.hp, "energy": r.energy}
                for r in self.duel.history]

    def log_json(self) -> str:
        return json.dumps(self.to_log())
